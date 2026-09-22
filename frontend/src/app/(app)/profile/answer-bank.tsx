"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import type { Answer } from "@/lib/types";

export default function AnswerBank({ initialAnswers }: { initialAnswers: Answer[] }) {
  const [answers, setAnswers] = useState(initialAnswers);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sensitive, setSensitive] = useState(false);
  const [saving, setSaving] = useState(false);

  async function addAnswer() {
    if (!question.trim() || !answer.trim()) return;
    setSaving(true);
    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) return;

      const saved = await apiFetch<Answer>("/answers", session.access_token, {
        method: "POST",
        body: JSON.stringify({ question: question.trim(), answer: answer.trim(), sensitive }),
      });
      setAnswers((prev) => [saved, ...prev.filter((a) => a.question !== saved.question)]);
      setQuestion("");
      setAnswer("");
      setSensitive(false);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex max-w-lg flex-col gap-2 rounded-lg border border-stone-200 bg-white p-4">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Question (e.g. Why do you want to work here?)"
          className="rounded-md border border-stone-300 px-3 py-2 text-sm"
        />
        <textarea
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="Answer"
          rows={3}
          className="rounded-md border border-stone-300 px-3 py-2 text-sm"
        />
        <label className="flex items-center gap-2 text-xs text-stone-600">
          <input
            type="checkbox"
            checked={sensitive}
            onChange={(e) => setSensitive(e.target.checked)}
            className="rounded border-stone-300"
          />
          Sensitive — confirm before reuse each time
        </label>
        <button
          onClick={addAnswer}
          disabled={saving}
          className="mt-1 self-start rounded-full bg-stone-900 px-4 py-2 text-xs font-medium text-white hover:bg-stone-700 disabled:opacity-60"
        >
          {saving ? "Saving…" : "Save answer"}
        </button>
      </div>

      <div className="flex flex-col gap-2">
        {answers.length === 0 && (
          <p className="text-sm text-stone-400">No answers saved yet.</p>
        )}
        {answers.map((a) => (
          <div key={a.id} className="rounded-md border border-stone-200 bg-white p-3">
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium text-stone-900">{a.question}</p>
              {a.sensitive && (
                <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700">
                  sensitive
                </span>
              )}
            </div>
            <p className="mt-1 text-sm text-stone-600">{a.answer}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
