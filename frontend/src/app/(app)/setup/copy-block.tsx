"use client";
import { useState } from "react";
import { Icon } from "@/components/ui";

export default function CopyBlock({
  label,
  code,
}: {
  label: string;
  code: string;
}) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard access is unavailable; the block stays selectable.
    }
  }
  return (
    <div className="code-block">
      <div className="code-block-bar">
        <span>{label}</span>
        <button className="text-action" onClick={copy}>
          <Icon name={copied ? "check" : "file"} size={14} />
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre>
        <code>{code}</code>
      </pre>
    </div>
  );
}
