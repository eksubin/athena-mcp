"use client";

import { useRef, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";

export default function ResumeUpload() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "done" | "error">("idle");
  const [filename, setFilename] = useState<string | null>(null);

  async function upload() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;

    setStatus("uploading");
    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) return;

      const form = new FormData();
      form.append("file", file);

      await apiFetch<{ id: string; original_filename: string }>("/resumes", session.access_token, {
        method: "POST",
        body: form,
      });
      setFilename(file.name);
      setStatus("done");
    } catch {
      setStatus("error");
    }
  }

  return (
    <div className="flex max-w-md items-center gap-3 rounded-lg border border-stone-200 bg-white p-4">
      <input
        ref={fileRef}
        type="file"
        accept=".pdf,.docx,.txt"
        className="text-sm text-stone-600"
      />
      <button
        onClick={upload}
        disabled={status === "uploading"}
        className="rounded-full bg-stone-900 px-4 py-2 text-xs font-medium text-white hover:bg-stone-700 disabled:opacity-60"
      >
        {status === "uploading" ? "Uploading…" : "Upload"}
      </button>
      {status === "done" && <span className="text-xs text-emerald-700">Saved {filename}</span>}
      {status === "error" && <span className="text-xs text-red-600">Upload failed</span>}
    </div>
  );
}
