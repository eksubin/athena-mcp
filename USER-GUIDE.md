# Using Athena

Athena is a quieter place to run a job search. It keeps every role you are
considering in one pipeline, remembers the things you end up typing into
application forms over and over, and turns your progress into a small patch
of land in a world you share with the other people here.

It is also built to be driven by an AI assistant. You can use Athena entirely
by hand, but the point of it is that your assistant keeps the record up to
date while you get on with the actual applying.

This guide is for using Athena. If you are setting up or running a
deployment, see [README.md](README.md) and [DEPLOY.md](DEPLOY.md) instead.

---

## 1. Getting in

**Athena is invite-only.** You cannot sign up on your own — someone already
inside has to add your email address first, and then you create an account
on *that exact address*.

Nothing is emailed to you automatically. Whoever invited you sends you the
link themselves.

1. Go to the Athena address you were given.
2. Choose **Sign in to Athena**, then **Continue with Google**.
3. Use the address you were invited on.

If you see *"Athena is invite-only, and this address hasn't been invited
yet"*, the address you signed in with is not the one that was invited. Check
for a different account — a personal address instead of a work one, for
instance — or ask whoever invited you to add the one you actually want to
use.

If you get in and later see *"This account's access to Athena has been
withdrawn"*, an administrator has suspended the account. Your data is still
there; speak to them.

---

## 2. Set yourself up

Everything here lives under **My profile**.

### How you appear

Pick the name and face other people see in the shared world. Neither is your
real name — your real name, resume, answers and applications are private to
you, whatever you choose here.

- **Your name in the world** — lowercase letters, numbers and single
  hyphens, starting with a letter, 3–24 characters. You get a randomly
  generated one when you join (`quiet-meadow-76`) and can change it whenever
  you like, as long as nobody else has taken it.
- **Choose your look** — one of five: fox, owl, cat, bear or fawn.

### Your resume

Upload a PDF, DOCX or TXT. Athena pulls out contact details and recognizable
skills and lists them under **Your extracted details**, each with a
confidence. These are what your assistant uses to fill forms, so it is worth
glancing over them — a fact extracted with low confidence is one your
assistant should be asking you about rather than relying on.

Upload a newer resume at any time; the latest upload wins.

### The right fit

Three preferences, and they do real work — they decide which roles get
ranked highest when you or your assistant search:

| Preference | What it does |
| --- | --- |
| **Target roles** | Comma-separated titles. Matching is by words, not exact strings, so "backend engineer" also matches "Senior Backend Engineer, Platform". Worth 45 of 100. |
| **Minimum annual salary** | A listing at or above it scores full marks; below it scores nothing. Leave blank to see every salary. Worth 30 of 100. |
| **Prioritize remote opportunities** | Worth 25 of 100. |

Age then pulls a score down, but never to zero: a listing keeps full credit
for its first two weeks and tapers off over about three months. A
six-month-old listing that matches you perfectly still beats a fresh one
that matches nothing.

### Your answer library

The questions every application asks — notice period, work authorization,
why this company — answered once, in your words, ready to reuse.

Mark anything **sensitive** (salary expectations, visa status, anything you
would want to think about before sending). Your assistant still sees these,
but it is instructed to confirm them with you each time rather than reusing
them silently.

---

## 3. Your pipeline

**Overview** is the board. Every role you are tracking sits in one of six
columns:

| Column | What it means |
| --- | --- |
| **Saved** | You are considering it. Nothing has been sent. |
| **Applied** | You submitted an application and saw the employer confirm it. |
| **Pending** | You followed up, or you are waiting on them. |
| **Interview** | A conversation is scheduled or has happened. |
| **Offer** | They made you an offer. |
| **Closed** | It ended — rejection, or you withdrew. |

Each card links straight back to the original listing, and shows the
company, location, salary range, where it came from and when it was posted.
The button on the right moves a role to the next stage. **Board view** gives
you the columns; **List view** lays everything out in one grid; the search
box filters by role, company or location.

---

## 4. Connect your assistant

This is where Athena earns its keep. Once connected, your assistant can
search your ranked roles, open the real listing in a browser, prepare an
application from what Athena already knows about you, and keep the pipeline
current — without you having to tell it to file anything.

### Setting it up

There is nothing to download or install by hand. Athena's assistant side
is a small package called **athena-mcp** that your assistant fetches and
runs itself; all you provide is one block of configuration.

1. Go to **Settings → Personal access tokens**.
2. Name the connection something you will recognize ("Claude on my laptop")
   and create a token.
3. **Copy it now** — it is shown once and never again. If you lose it,
   revoke it and make another.
4. Make sure [uv](https://docs.astral.sh/uv/) is installed on the machine
   your assistant runs on. That is the only prerequisite.
5. Add this to wherever your assistant keeps its MCP servers, filling in
   the address of your Athena instance and the token from step 3:

```json
{
  "mcpServers": {
    "athena": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/<owner>/athena-mcp", "athena-mcp"],
      "env": {
        "ATHENA_API_URL": "https://api.athena.example.com",
        "ATHENA_TOKEN": "athena_pat_..."
      }
    }
  }
}
```

6. Restart your assistant so it picks up the new tools. You should see ten
   of them.

Treat the token like a password — it can read your resume, your answers and
your whole history. Create a separate one per device, and revoke any you are
no longer using; revoking takes effect immediately.

If the tools do not appear, athena-mcp says why in its startup message:
a missing token, a token this instance rejected (revoked, from a different
instance, or your access withdrawn), a copy of athena-mcp too old for this
instance, or an address it cannot reach. Its
[README](https://github.com/<owner>/athena-mcp) has the rest, including
Codex and how to update to a newer version.

### What it can do

| You might ask | What happens |
| --- | --- |
| "Find me some roles" | Returns your highest-ranked listings, with links |
| "Tell me more about the second one" | Fetches the full description |
| "I'm looking at this job — <link>" | Records it against your pipeline as **Saved** |
| "Help me apply to this one" | Pulls together the listing, your verified facts and your answer library, then works the employer's form in a browser with you watching |
| "I got an interview for the Acme role" | Moves it to **Interview** |
| "What am I waiting on?" | Lists everything by status |

You do not have to ask it to save or log anything. Your assistant is
instructed to record every role it handles as it handles it, with whatever
status is actually true at that moment. Mentioning a job twice does not
create it twice.

### What it will not do

Athena stores your job-search data. **It does not submit applications.**
Forms are filled in a real browser, with you watching, and the final button
is yours to press.

Your assistant is also instructed to:

- leave an application **Saved** when you asked only for a review — never
  mark it Applied;
- record **Applied** only after an authorized submission *and* a visible
  confirmation from the employer;
- ask you about facts it does not have, or has only with low confidence,
  rather than guessing;
- confirm anything you marked sensitive before reusing it;
- never invent a qualification you do not have.

If an assistant ever tells you it has applied to something on your behalf
without you pressing anything, treat that as wrong and check the employer's
site yourself.

---

## 5. Your world

**My world** is the shared map. Everyone here has a plot of land, and
every step forward puts something on it:

| What you did | What appears |
| --- | --- |
| Saved a role | A sapling |
| Applied, or followed up | A tree |
| Got an interview | A house |
| Received an offer | A monument |
| An application closed | A stump — with something already growing back |

Your own land is the one with the coloured kerb and your name on it; your
neighbours' plots sit alongside, with open ground between them. Drag to look
around, scroll to zoom. It updates itself every few seconds, so you will see
other people's worlds grow while you watch.

Only your username and your avatar are visible to anyone else. Nobody can
see which companies you applied to, what you wrote, or what is in your
resume — a house on your land says you got an interview, not who with.

---

## 6. Inviting people

Athena only grows by invitation, and you get three invites.

From **My profile → Invite someone in**, add an email address and an
optional note to remind you who it was. That address can then create its own
account.

**Nothing is emailed.** Send them the link yourself, and tell them to sign in
with that exact address.

An invite you have sent but nobody has used yet can be withdrawn, which
gives you the slot back. Once somebody has joined on it, only an
administrator can take their access away. If you run out and need more, ask
an administrator to raise your allowance.

---

## 7. If you are an administrator

**Administration** appears in the sidebar for administrators only.

**Accounts** lists everyone: their email, name, avatar, how many invites
they have used, how many applications they are tracking, and when they were
last seen. From here you can:

- change somebody's **role** between member and administrator;
- change their **invite allowance**;
- **withdraw** access, which suspends the account immediately — every
  request it makes is refused, including from any assistant connected with
  its tokens. Nothing is deleted, and **Restore** puts it back.

**Invites** shows every invite anyone has sent, who sent it, and whether it
is waiting, used or withdrawn. You can invite directly from here with no
allowance limit, including inviting somebody as an administrator.
Withdrawing an invite that has already been used also suspends the account
it let in.

Two things are deliberately refused: changing your own role or access, and
removing the last active administrator. Ask another administrator.

---

## 8. What is private

| Private to you | Visible to others |
| --- | --- |
| Your real name | Your username |
| Your resume and everything extracted from it | Your avatar |
| Your answer library | The shape of your land — how much is on it |
| Every job you saved, applied to or heard back from | |
| Your preferences and target salary | |
| Your email address (administrators can see it) | |

A monument on your plot tells people you got an offer. It does not tell them
from whom, for what, or when.

---

## Common questions

**I was invited but it says my address hasn't been.**
The address you signed in with is not the one that was invited. Google
accounts in particular can surprise you here — check which account you are
signed into, or ask for an invite for the address you actually want.

**My assistant can't see my jobs.**
Its token is missing, wrong or revoked. Create a fresh one in **Settings**
and restart the assistant — a token is shown only once, so a half-copied one
is a common cause.

**My assistant doesn't have the newer tools.**
Restart it. Assistants read the available tools once when they connect.

**A role I'm tracking shows up twice.**
It shouldn't — Athena recognizes the same listing through different link
shapes. If it happens anyway, the two links genuinely pointed at different
listings.

**I changed my username and my old one is gone.**
Names are freed when you leave them, so somebody else can take one you
stopped using. Nothing else about your account changes.

**My world looks out of date.**
It refreshes every few seconds while the page is open and visible. Switch
back to the tab, or reload.
