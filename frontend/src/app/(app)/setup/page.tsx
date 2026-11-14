import Link from "next/link";
import { PageHeading, SectionHeading } from "@/components/ui";
import CopyBlock from "./copy-block";

// The address assistants must call is this deployment's public API URL —
// the same one baked into the browser bundle — so the commands below are
// already correct for whoever is reading them.
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const PACKAGE = "git+https://github.com/eksubin/Athena";
const SKILL_URL =
  "https://raw.githubusercontent.com/eksubin/Athena/main/skills/athena-jobs/SKILL.md";
const TOKEN = "athena_pat_PASTE_YOUR_TOKEN";

const CLAUDE_CODE = `claude mcp add athena -s user -e ATHENA_API_URL=${API_URL} -e ATHENA_TOKEN=${TOKEN} -- uvx --from "${PACKAGE}" athena-mcp`;
const CODEX = `codex mcp add athena --env ATHENA_API_URL=${API_URL} --env ATHENA_TOKEN=${TOKEN} -- uvx --from "${PACKAGE}" athena-mcp`;
const DESKTOP = JSON.stringify(
  {
    mcpServers: {
      athena: {
        command: "uvx",
        args: ["--from", PACKAGE, "athena-mcp"],
        env: { ATHENA_API_URL: API_URL, ATHENA_TOKEN: TOKEN },
      },
    },
  },
  null,
  2,
);
const SKILL_UNIX = `mkdir -p ~/.claude/skills/athena-jobs && curl -fsSL ${SKILL_URL} -o ~/.claude/skills/athena-jobs/SKILL.md`;
const SKILL_WINDOWS = `New-Item -ItemType Directory -Force "$HOME\\.claude\\skills\\athena-jobs"; Invoke-WebRequest ${SKILL_URL} -OutFile "$HOME\\.claude\\skills\\athena-jobs\\SKILL.md"`;

export default function SetupPage() {
  return (
    <>
      <PageHeading
        eyebrow="Set up your assistant"
        title="Connect once, and your search keeps itself up to date."
        description="Five steps to let Claude or ChatGPT find roles, prepare applications, and record every job it handles in Athena."
      />
      <div className="setup-stack">
        <section className="card card-pad">
          <SectionHeading
            icon="key"
            title="1. Create your token"
            description="A private key that lets your assistant act as you in Athena."
          />
          <div className="setup-body">
            <p>
              Open <Link href="/settings">Settings</Link>, name the connection,
              and create a personal access token. Copy it straight away — it is
              shown once. Treat it like a password: paste it only into your
              assistant’s configuration, never into a chat.
            </p>
            <p>
              Before you connect, add your resume and preferences under{" "}
              <Link href="/profile">My profile</Link> so your assistant has
              verified facts to work from.
            </p>
          </div>
        </section>

        <section className="card card-pad">
          <SectionHeading
            icon="link"
            title="2. Connect the Athena server"
            description="Your assistant fetches and runs it for you. The only thing to install first is uv."
          />
          <div className="setup-body">
            <p>
              Install{" "}
              <a
                href="https://docs.astral.sh/uv/getting-started/installation/"
                target="_blank"
                rel="noreferrer"
              >
                uv
              </a>{" "}
              on the computer your assistant runs on. Then use the block for
              your assistant, replacing{" "}
              <code className="inline-code">{TOKEN}</code> with the token from
              step 1. The address of this Athena is already filled in.
            </p>
            <CopyBlock label="Claude Code — run in a terminal" code={CLAUDE_CODE} />
            <CopyBlock
              label="Claude Desktop — add to claude_desktop_config.json"
              code={DESKTOP}
            />
            <CopyBlock label="ChatGPT Codex — run in a terminal" code={CODEX} />
          </div>
        </section>

        <section className="card card-pad">
          <SectionHeading
            icon="spark"
            title="3. Install the skill (Claude)"
            description="Makes Claude check it is connected to Athena before any job work, and record every role as it goes."
          />
          <div className="setup-body">
            <p>
              Without a working connection the skill stops and tells you how to
              fix it, rather than searching or applying unrecorded.
            </p>
            <CopyBlock label="macOS or Linux" code={SKILL_UNIX} />
            <CopyBlock label="Windows PowerShell" code={SKILL_WINDOWS} />
          </div>
        </section>

        <section className="card card-pad">
          <SectionHeading
            icon="world"
            title="4. Give it a browser"
            description="Listings are read and forms are filled in your assistant’s own browser."
          />
          <div className="setup-body">
            <p>
              For Claude, install the Claude in Chrome extension and sign in to
              LinkedIn and any employer sites yourself in Chrome. ChatGPT uses
              its own built-in browser. Your assistant never types your
              passwords and hands sign-in screens back to you.
            </p>
          </div>
        </section>

        <section className="card card-pad">
          <SectionHeading
            icon="check"
            title="5. Restart and try it"
            description="Restart your assistant so it picks up the new tools, then ask for something real."
          />
          <div className="setup-body">
            <p>
              Try: <em>“Use athena-jobs to find three roles that match my
              profile.”</em> The roles appear on your{" "}
              <Link href="/dashboard">overview</Link> as your assistant handles
              them. An application is marked Applied only after you have
              approved the submission and the employer has confirmed it.
            </p>
            <p>
              If the tools do not appear, the server says why when it starts: a
              missing token, a token this Athena rejected, or an address it
              cannot reach. Create a fresh token in Settings and try again.
            </p>
          </div>
        </section>
      </div>
    </>
  );
}
