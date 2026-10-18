# Google sign-in

[[Home]] · [[Local Setup]] · [[Invites and Administration]] · [[Operations]]

Google is the sign-in path for a real deployment; the email/password form on
/login is a local testing convenience that the production overlay turns off.
GoTrue performs the whole OAuth exchange — the web app only asks it to start
one and then exchanges the code it returns for a session.

The provider is enabled unconditionally in Compose. Enabled without
credentials, `/auth/v1/authorize?provider=google` answers `400
validation_failed`, which the login page reports as "Google sign-in is
unavailable right now".

## The two callbacks

The one thing worth getting right first, because the names are nearly
identical and only one of them belongs to Google:

| URL | Whose | Where it is configured |
| --- | --- | --- |
| `{API_EXTERNAL_URL}/callback`, e.g. `http://localhost:8001/auth/v1/callback` | GoTrue's | **Google's** authorized redirect URIs, and `GOTRUE_EXTERNAL_GOOGLE_REDIRECT_URI` |
| `{PUBLIC_SITE_URL}/auth/callback`, e.g. `http://localhost:3000/auth/callback` | The web app's | `GOTRUE_URI_ALLOW_LIST`, and the `redirectTo` the login page sends |

Google redirects the browser to the first; GoTrue then forwards it to the
second with a code, which [the callback
route](../frontend/src/app/auth/callback/route.ts) exchanges for a session.
Registering the web app's URL with Google instead of GoTrue's is the usual
cause of `redirect_uri_mismatch`.

Compose derives both from `.env`, so they stay consistent as long as
`API_EXTERNAL_URL` and `PUBLIC_SITE_URL` are correct for the deployment.

## Setting it up

1. In the Google Cloud Console, create or select a project.
2. **APIs & Services → OAuth consent screen**: External. The default
   `email`, `profile` and `openid` scopes are all Athena uses.
3. While that screen is in **Testing**, only addresses listed under **Test
   users** can sign in at all — a restriction separate from, and on top of,
   Athena's own invite gate. Add them, or publish the app.
4. **Credentials → Create credentials → OAuth client ID → Web application**.
5. Under **Authorized redirect URIs**, add GoTrue's callback from the table
   above — not the web app's.
6. Put the client ID and secret in `.env` as `GOOGLE_CLIENT_ID` and
   `GOOGLE_SECRET`.
7. `docker compose up -d auth`. These are plain environment variables, so no
   image rebuild is needed.

## Who can actually get in

OAuth working is necessary but not sufficient: Athena is invite-only, and an
address with no live invite is refused by the database when GoTrue tries to
create the account. The refusal surfaces as a generic provider error, which
[the callback route](../frontend/src/app/auth/callback/route.ts) translates
into the invite-only message. See [[Invites and Administration]].

So a new administrator's first sign-in needs both: the address listed as a
Google test user if the consent screen is unpublished, and a pending admin
invite in the database.

## Verifying

```sh
curl -s -o /dev/null -w "%{http_code}\n" \
  "http://localhost:8001/auth/v1/authorize?provider=google&redirect_to=http://localhost:3000/auth/callback"
```

`302` means GoTrue is redirecting to Google and the credentials are loaded.
`400` means they are not.

## Moving to a real domain

Three things change together, and missing the third is a quiet failure:

1. `API_EXTERNAL_URL` and `PUBLIC_SITE_URL` in `.env` become the real HTTPS
   addresses.
2. The new `{API_EXTERNAL_URL}/callback` is added to the same Google client.
3. **The web image is rebuilt.** `NEXT_PUBLIC_SITE_URL` is a build argument
   baked into the client bundle, so changing `.env` alone leaves the old
   address in the browser's `redirectTo`.

`localhost` redirect URIs are exempt from Google's HTTPS requirement, which
is why local development works over plain HTTP; a real domain is not.

Sources: [Compose auth service](../docker-compose.yml), [environment
template](../.env.example), [login page](../frontend/src/app/login/page.tsx),
[callback route](../frontend/src/app/auth/callback/route.ts), [deployment
guide](../DEPLOY.md).
