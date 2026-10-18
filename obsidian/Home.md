---
tags: [athena, documentation]
---
# Athena documentation

Athena is an invite-only job-hunt platform with a web app, FastAPI API, MCP tools, ingestion worker, and self-hosted Supabase.

- [[Architecture]] — services and repository map
- [[Local Setup]] — configuration and first boot
- [[Data and Authentication]] — storage and permissions
- [[Invites and Administration]] — closed registration, roles, admin panel
- [[API and MCP]] — endpoints and agent connection
- [[Workflows]] — job search, applications, ingestion
- [[Operations]] — deployment, checks, troubleshooting

Open this `obsidian` folder using Obsidian's **Open folder as vault**. No community plugins are required. Start with this note.

Source links point outside the vault into the repository; use the project editor if Obsidian cannot open them. Reviewed against source on 2026-10-17. The invite gate, admin panel and one-call job tracking were exercised against a local stack on that date; nothing else was re-verified at runtime. Keep credentials, tokens, resumes, and personal answers out of these notes.

Sources of truth: [README](../README.md), [deployment guide](../DEPLOY.md), and source code. Update these notes alongside behavior changes.
