"use client";
import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import type { Answer } from "@/lib/types";
import { Icon } from "@/components/ui";

export default function AnswerBank({
  initialAnswers,
}: {
  initialAnswers: Answer[];
}) {
  const [answers, setAnswers] = useState(initialAnswers);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sensitive, setSensitive] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  async function addAnswer(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!question.trim() || !answer.trim()) return;
    setSaving(true);
    setError("");
    try {
      const {
        data: { session },
      } = await createClient().auth.getSession();
      if (!session) throw new Error("Please sign in again.");
      const saved = await apiFetch<Answer>("/answers", session.access_token, {
        method: "POST",
        body: JSON.stringify({
          question: question.trim(),
          answer: answer.trim(),
          sensitive,
        }),
      });
      setAnswers((prev) => [
        saved,
        ...prev.filter((a) => a.question !== saved.question),
      ]);
      setQuestion("");
      setAnswer("");
      setSensitive(false);
    } catch {
      setError("Your answer couldn’t be saved. Please try again.");
    } finally {
      setSaving(false);
    }
  }
  return (
    <div className="answer-grid">
      <form className="form-stack" onSubmit={addAnswer}>
        <label className="field">
          <span className="field-label">Application question</span>
          <input
            className="input"
            required
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="What are you looking for in your next role?"
          />
        </label>
        <label className="field">
          <span className="field-label">Your answer</span>
          <textarea
            className="input"
            required
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Describe the work, team, or impact that matters to you."
            rows={4}
          />
        </label>
        <label className="check-label">
          <input
            type="checkbox"
            checked={sensitive}
            onChange={(e) => setSensitive(e.target.checked)}
          />
          <span>Sensitive information — confirm before reuse</span>
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <div>
          <button
            className="button button-primary"
            disabled={saving || !question.trim() || !answer.trim()}
            type="submit"
          >
            {saving ? "Saving…" : "Save answer"}
            <Icon name="arrow" size={15} />
          </button>
        </div>
      </form>
      <div className="answer-list" aria-live="polite">
        {!answers.length && (
          <div className="answer-empty">
            <Icon name="message" size={28} />
            <h3>Your words, ready when you need them.</h3>
            <p>Save an answer to start building your personal library.</p>
          </div>
        )}
        {answers.map((a) => (
          <article key={a.id} className="answer-item">
            <h3>{a.question}</h3>
            <p>{a.answer}</p>
            {a.sensitive && (
              <span className="pill">
                <Icon name="shield" size={11} />
                Confirm before reuse
              </span>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
