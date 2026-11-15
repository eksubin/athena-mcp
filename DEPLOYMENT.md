# Deploying Athena on AWS EC2 with a GoDaddy domain

A step-by-step walkthrough for putting Athena on one EC2 instance, with
HTTPS and Google sign-in, using subdomains managed in GoDaddy.
[DEPLOY.md](DEPLOY.md) is the short, provider-neutral version of the same
thing.

The examples use `yourdomain.com`. Replace it with your own domain
everywhere.

## What you end up with

Three hostnames, all pointing at the same server:

| Hostname | What answers there | Who calls it |
| --- | --- | --- |
| `athena.yourdomain.com` | The website | Browsers |
| `athena-api.yourdomain.com` | The Athena API | The website, and assistants through athena-mcp |
| `athena-db.yourdomain.com` | Sign-in (GoTrue) and the data gateway (PostgREST) | The website during login, and Google's redirect after sign-in |

Caddy listens on ports 80 and 443, gets certificates from Let's Encrypt
by itself, and routes each hostname to the right container. Nothing else
is exposed. Postgres is never reachable from the internet, despite the
`-db` name.

## 1. AWS

1. Launch an Ubuntu or Amazon Linux instance with at least 2 GB of memory (`t4g.small`
   or `t3.small`) and 20 GB of disk. The images used all publish arm64
   builds, so Graviton instances work.
2. Allocate an **Elastic IP** and associate it with the instance. The
   default public IP changes when the instance stops and starts.
3. In the instance's security group, allow inbound:

   | Port | Source |
   | --- | --- |
   | 22 | Your IP only |
   | 80 | Anywhere (`0.0.0.0/0`) |
   | 443 | Anywhere (`0.0.0.0/0`) |

## 2. GoDaddy DNS

Add three A records, all with the Elastic IP as the value:

| Type | Name | Value |
| --- | --- | --- |
| A | `athena` | Elastic IP |
| A | `athena-api` | Elastic IP |
| A | `athena-db` | Elastic IP |

Do this before starting the stack: Caddy requests a certificate for each
name on first start and needs all three to resolve. Check with:

```sh
nslookup athena.yourdomain.com
nslookup athena-api.yourdomain.com
nslookup athena-db.yourdomain.com
```

## 3. Google OAuth

In Google Cloud Console, open **APIs & Services → Credentials → your
OAuth client** and add this under **Authorized redirect URIs**:

```
https://athena-db.yourdomain.com/auth/v1/callback
```

It is the `-db` hostname, not the website's. The local-development entry
(`http://localhost:8001/auth/v1/callback`) can stay.

While the OAuth consent screen is in **Testing**, only the listed test
users can sign in. Publish it before inviting other people.

## 4. Prepare the server

SSH in (the user is `ubuntu` on Ubuntu and `ec2-user` on Amazon Linux),
install Docker, and add 2 GB of swap (the website build needs it on a
2 GB instance). The commands below are for Ubuntu; on Amazon Linux,
install Docker and the Compose plugin with `dnf` and the Docker
documentation instead of the first line.

```sh
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
exit
```

Log back in so the `docker` group applies.

## 5. Get the code onto the server

The folder must be called `athena`: the database commands below rely on
the container name `athena-db-1`, which comes from the folder name.

**If the server can read the repository** (public, or a deploy key is set
up):

```sh
git clone <repository URL> ~/athena && cd ~/athena
```

**If the repository is private and has no deploy key**, copy a snapshot
from your own machine instead. On your machine, in the repository:

```sh
git archive --format=tar.gz -o athena.tar.gz HEAD
scp -i /path/to/key.pem athena.tar.gz ubuntu@ELASTIC_IP:~
```

Then on the server:

```sh
mkdir -p ~/athena && tar -xzf ~/athena.tar.gz -C ~/athena && cd ~/athena
```

## 6. Create `.env`

`.env` holds the server's settings and secrets. This script writes the
whole file: it generates a fresh database password, the secret that signs
login sessions and the two API keys derived from it, and fills in the
three hostnames. Change the `ROOT=` value to your domain.

```sh
cd ~/athena
ROOT=yourdomain.com python3 - <<'EOF'
import base64, hashlib, hmac, json, os, secrets, time

root = os.environ["ROOT"]
app = f"athena.{root}"
api = f"athena-api.{root}"
db = f"athena-db.{root}"

secret = secrets.token_hex(32)
pg = secrets.token_hex(24)

def b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

def key(role):
    now = int(time.time())
    head = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = b64(json.dumps({"role": role, "iss": "supabase", "iat": now, "exp": now + 10*365*24*3600}).encode())
    sig = b64(hmac.new(secret.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest())
    return f"{head}.{body}.{sig}"

anon = key("anon")
service = key("service_role")

open(".env", "w").write(f"""POSTGRES_PASSWORD={pg}
JWT_SECRET={secret}
JWT_EXPIRY=3600
ANON_KEY={anon}
SERVICE_ROLE_KEY={service}
API_EXTERNAL_URL=https://{db}/auth/v1
GOOGLE_CLIENT_ID=
GOOGLE_SECRET=
SUPABASE_URL=http://gateway:8001
SUPABASE_ANON_KEY={anon}
SUPABASE_SERVICE_ROLE_KEY={service}
SUPABASE_JWT_SECRET={secret}
RESUME_STORAGE_DIR=/data/resumes
CORS_ORIGINS=["https://{app}"]
PUBLIC_API_URL=https://{api}
PUBLIC_SUPABASE_URL=https://{db}
PUBLIC_SITE_URL=https://{app}
ENABLE_TEST_LOGIN=false
ATHENA_DOMAIN={app}
ATHENA_API_DOMAIN={api}
ATHENA_DB_DOMAIN={db}
""")
print("Wrote .env")
EOF
chmod 600 .env
nano .env
```

In `nano`, paste the Google OAuth client ID and secret after
`GOOGLE_CLIENT_ID=` and `GOOGLE_SECRET=` (no spaces, no quotes), then
save with `Ctrl+O`, `Enter`, and exit with `Ctrl+X`.

**Run the script once.** The database stores `POSTGRES_PASSWORD` the first
time it starts. Running the script again afterwards writes a new password
that the database does not know; see
[Troubleshooting](#sign-in-returns-502-bad-gateway) if that happens.

To check the file without showing secrets: `cut -d= -f1 .env`.

## 7. Build and start

Always pass both compose files. Plain `docker compose up` starts the
local-development layout on ports 3000, 8000 and 8001, without Caddy.

```sh
cd ~/athena
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

The first build takes several minutes.

## 8. Load the schema (first deploy only)

Before running these, make sure the first administrator's address in
`supabase/migrations/0002_invites_and_admin.sql` is the Google account
you will sign in with. Athena is invite-only, and that file creates the
one admin invite that lets the first person in.

Once `db` shows `healthy`:

```sh
docker exec -i athena-db-1 psql -U postgres -d postgres < supabase/migrations/0001_init.sql
docker exec -i athena-db-1 psql -U postgres -d postgres < supabase/migrations/0002_invites_and_admin.sql
docker exec -i athena-db-1 psql -U postgres -d postgres < supabase/migrations/0003_profile_identity.sql
docker exec -i athena-db-1 psql -U postgres -d postgres < supabase/seed.sql
```

## 9. Check it

```sh
curl https://athena-api.yourdomain.com/health
curl https://athena-db.yourdomain.com/auth/v1/health
```

The first returns `{"status":"ok",...}` and the second returns GoTrue's
name and version. Then open `https://athena.yourdomain.com` and sign in
with Google on the administrator address. **Administration** should
appear in the sidebar.

## 10. Connect an assistant

The server has its own database, so tokens from a local instance do not
work here.

1. Sign in on the live site and create a token under **Settings**.
2. Open **Set up assistant**. Its commands already contain this
   deployment's API address (`https://athena-api.yourdomain.com`).
3. Run the command for your assistant, install the skill, and restart the
   assistant.

## Updating

Get the new code onto the server (`git pull`, or repeat the snapshot copy
from step 5), then:

```sh
cd ~/athena
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Do not rerun the `.env` script or the schema commands. Certificates and
data live in Docker volumes and survive rebuilds. Never use `down -v`: it
deletes the database, uploaded resumes and the certificates.

## Backups

All user data is on the instance: the database in the `athena_db_data`
volume and uploaded resumes in `athena_resumes`. `scripts/backup.sh`
copies both to S3; cron runs it every night.

### Set it up once

The examples use the bucket name `athena-backups-yourname`; replace it
with yours everywhere, including inside the policy.

**1. Create a bucket.** In S3, create a private bucket in the same region
as the instance. Leave "Block all public access" on.

**2. Expire old backups.** In the bucket, **Management → Lifecycle rules →
Create rule**: apply to all objects, and expire current versions after
30 days (or however long you want to keep them).

**3. Create an IAM role for the instance.** The role is what lets the
server write to the bucket, so no access keys are stored on it.

1. Go to **IAM → Roles → Create role**.
2. Trusted entity: **AWS service**; use case: **EC2**. Click Next.
3. Skip the permissions list (Next), name the role `athena-backup-role`,
   and create it.
4. Open the new role, then **Add permissions → Create inline policy →
   JSON**, and paste:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": ["s3:PutObject", "s3:GetObject"],
         "Resource": "arn:aws:s3:::athena-backups-yourname/*"
       },
       {
         "Effect": "Allow",
         "Action": "s3:ListBucket",
         "Resource": "arn:aws:s3:::athena-backups-yourname"
       }
     ]
   }
   ```

5. Name the policy `athena-backup-s3` and save.

**4. Attach the role to the instance.** In **EC2 → Instances**, select the
instance, then **Actions → Security → Modify IAM role**, choose
`athena-backup-role`, and click **Update IAM role**. No restart is
needed.

**5. Install the AWS CLI and cron on the server.**

Amazon Linux usually has the AWS CLI already (`aws --version`), but not
cron, and it has no `snap`:

```sh
sudo dnf install -y awscli cronie
sudo systemctl enable --now crond
```

Ubuntu has cron already:

```sh
sudo snap install aws-cli --classic
```

**6. Check the server can see the role:**

```sh
aws sts get-caller-identity
```

It should print an ARN containing `athena-backup-role`.

**7. Run a backup by hand:**

```sh
cd ~/athena
BACKUP_BUCKET=athena-backups-yourname bash scripts/backup.sh
aws s3 ls s3://athena-backups-yourname/athena/ --recursive
```

The script should end with a `backup ok` line, and the listing should
show `db.dump` and `resumes.tar.gz`. Do not schedule it until this works;
cron would fail the same way.

**8. Schedule it.** This adds a nightly job at 02:00 UTC without opening
an editor. Run it once only, or the line is added twice. The home folder
is `/home/ec2-user` on Amazon Linux and `/home/ubuntu` on Ubuntu; adjust
both paths to match.

```sh
(crontab -l 2>/dev/null; echo '0 2 * * * BACKUP_BUCKET=athena-backups-yourname PATH=/snap/bin:/usr/local/bin:/usr/bin:/bin bash /home/ec2-user/athena/scripts/backup.sh >> /home/ec2-user/athena-backup.log 2>&1') | crontab -
crontab -l
```

`crontab -l` should show the line. To change or remove it later, run
`crontab -e`, which opens `vi`: press `i` to edit, then `Esc`, `:wq` and
`Enter` to save.

`~/athena-backup.log` gets one line per run. A night with no `backup ok`
line is a failed backup; the error is in the same file.

Each run writes two files under `athena/<date>/`: `db.dump` (accounts,
profiles, jobs, answers, tokens) and `resumes.tar.gz`. `.env` is not
backed up. Keep a copy of it somewhere safe yourself, because sessions
and tokens depend on its secrets.

### Restoring

On a server set up through step 8 (same `.env`, schema loaded), fetch a
backup and load it over the empty schema:

```sh
cd ~/athena
aws s3 cp s3://athena-backups-yourname/athena/<date>/db.dump .
aws s3 cp s3://athena-backups-yourname/athena/<date>/resumes.tar.gz .
docker exec -i athena-db-1 pg_restore -U supabase_admin -d postgres --clean --if-exists < db.dump
docker run --rm -i -v athena_resumes:/data alpine tar -xzf - -C /data < resumes.tar.gz
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart auth rest api
```

Try a restore on a throwaway instance before you rely on it.

### If a backup fails

- **`Unable to locate credentials`** - no IAM role is attached to the
  instance (steps 3 and 4). The dump itself worked; only the upload
  failed. Do not fix this with `aws configure` and access keys.
- **`AccessDenied`** - the role is attached, but its policy names a
  different bucket from the one in `BACKUP_BUCKET`.
- **`snap: command not found`** - the server is Amazon Linux; use the
  `dnf` command in step 5.
- **Nothing in `~/athena-backup.log` the next morning** - cron is not
  running (`systemctl status crond`), or the paths in the cron line do
  not match the home folder.

## Troubleshooting

All commands run from `~/athena`.

### The site does not load at all

- Ports 80 and 443 are not open to `0.0.0.0/0` in the security group.
- The stack was started without `-f docker-compose.prod.yml`, so Caddy is
  not running. `ps` should list a `caddy` container.
- A DNS record is missing or still propagating. Caddy's log says which
  name failed:

  ```sh
  docker compose -f docker-compose.yml -f docker-compose.prod.yml logs caddy
  ```

### Sign-in returns 502 Bad Gateway

The website loads but **Continue with Google** ends on a 502 from the
`-db` hostname, and `ps` shows `auth` and `rest` as `Restarting`. Check
their logs:

```sh
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail 15 auth rest
```

If they say `password authentication failed`, the database was created
with a different `POSTGRES_PASSWORD` from the one now in `.env`. Set the
database's service passwords to the current value, then restart the two
services:

```sh
PW=$(grep '^POSTGRES_PASSWORD=' .env | cut -d= -f2)
docker exec -i athena-db-1 psql -U supabase_admin -d postgres -v pw="$PW" <<'SQL'
ALTER USER authenticator WITH PASSWORD :'pw';
ALTER USER pgbouncer WITH PASSWORD :'pw';
ALTER USER supabase_auth_admin WITH PASSWORD :'pw';
ALTER USER supabase_storage_admin WITH PASSWORD :'pw';
SQL
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart auth rest
```

You should see `ALTER ROLE` four times, and `auth` and `rest` as `Up`.

### Google says `redirect_uri_mismatch`

`https://athena-db.yourdomain.com/auth/v1/callback` is missing from the
OAuth client's Authorized redirect URIs (step 3).

### "Athena is invite-only, and this address hasn't been invited yet"

Either the schema has not been loaded (step 8), or you signed in with a
Google account other than the administrator address in
`0002_invites_and_admin.sql`.

### Other people cannot sign in with Google

The OAuth consent screen is still in Testing, or the person has not been
invited from **My profile → Invite someone in** or **Administration →
Invites**.

### The build is killed or the server freezes while building

The instance ran out of memory. Confirm swap is on with `free -h`
(step 4), then run the build again.
