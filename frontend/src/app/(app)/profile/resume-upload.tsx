"use client";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import { Icon } from "@/components/ui";

export default function ResumeUpload() {
  const fileRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const [status, setStatus] = useState<"idle" | "uploading" | "done" | "error">(
    "idle",
  );
  const [selected, setSelected] = useState("");
  const [message, setMessage] = useState("");
  async function upload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setStatus("uploading");
    try {
      const {
        data: { session },
      } = await createClient().auth.getSession();
      if (!session) throw new Error("Please sign in again.");
      const form = new FormData();
      form.append("file", file);
      const result = await apiFetch<{ parsed_at: string | null }>(
        "/resumes",
        session.access_token,
        { method: "POST", body: form },
      );
      setStatus("done");
      setMessage(
        result.parsed_at
          ? `${file.name} uploaded and processed.`
          : `${file.name} saved. We couldn’t extract details from this file.`,
      );
      router.refresh();
    } catch {
      setStatus("error");
      setMessage("Upload failed. Please try a PDF, DOCX, or text file.");
    }
  }
  return (
    <form onSubmit={upload}>
      <div className="upload-zone">
        <span className="icon-tile">
          <Icon name="upload" />
        </span>
        <h3>Make your experience count.</h3>
        <p>Choose your latest resume · PDF, DOCX, or TXT</p>
        <input
          className="file-input"
          aria-label="Choose resume file"
          ref={fileRef}
          type="file"
          accept=".pdf,.docx,.txt"
          onChange={(e) => {
            setSelected(e.target.files?.[0]?.name ?? "");
            setStatus("idle");
          }}
        />
      </div>
      <div className="upload-footer">
        <button
          className="button button-primary"
          type="submit"
          disabled={!selected || status === "uploading"}
        >
          <Icon name="upload" size={15} />
          {status === "uploading" ? "Uploading…" : "Upload resume"}
        </button>
        <span className="field-hint">Only visible to you</span>
      </div>
      {(status === "done" || status === "error") && (
        <p
          role={status === "error" ? "alert" : "status"}
          className={status === "error" ? "form-error" : "form-status"}
          style={{ marginTop: 15 }}
        >
          {message}
        </p>
      )}
    </form>
  );
}
