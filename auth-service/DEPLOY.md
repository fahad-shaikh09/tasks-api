# Deploying auth-service + wiring auth across the rest of the stack

This is the **one-time** setup to make the new auth-service work end-to-end.
After this, only the usual `oc start-build` + `oc rollout restart` cycle is needed.

## 1. Database reset (REQUIRED — schema changed)

`task` and `notification` records gained a `user_id` column. Existing
rows can't be back-filled (we don't know who owned them), so the
table needs to be dropped. Connect to your Postgres and run:

```sql
DROP TABLE IF EXISTS task;
```

The MCP server recreates `task` via `SQLModel.metadata.create_all()` on startup.
The auth-service runs `CREATE TABLE IF NOT EXISTS` for its own tables
(`user`, `session`, `account`, `verification`) on every boot — no manual
migration needed.

## 2. Generate secrets

```bash
# better-auth signing secret
openssl rand -hex 32

# Chainlit auth secret (separate, required by Chainlit to enable header_auth_callback)
openssl rand -hex 32
```

## 3. Build images

```bash
# One-time BuildConfig
oc new-build --binary --strategy=docker --name=auth-service -n tasks-app

# Build
oc start-build auth-service --from-dir=auth-service --follow -n tasks-app
oc start-build mcp-server   --from-dir=.              --follow -n tasks-app
oc start-build agent        --from-dir=agent          --follow -n tasks-app
oc start-build notification --from-dir=notification   --follow -n tasks-app
```

## 4. Install/upgrade helm charts

```bash
BETTER_AUTH_SECRET=<from step 2>
CHAINLIT_AUTH_SECRET=<from step 2>
DB_URL='postgresql://user:pass@host:5432/dbname?sslmode=require'

helm upgrade --install auth-service ./auth-service/helm -n tasks-app \
  --set secrets.betterAuthSecret="$BETTER_AUTH_SECRET" \
  --set secrets.databaseUrl="$DB_URL" \
  --set secrets.googleClientId="$GOOGLE_CLIENT_ID" \
  --set secrets.googleClientSecret="$GOOGLE_CLIENT_SECRET" \
  --set secrets.githubClientId="$GITHUB_CLIENT_ID" \
  --set secrets.githubClientSecret="$GITHUB_CLIENT_SECRET"

helm upgrade --install agent ./agent/helm -n tasks-app \
  --set env.openaiApiKey="$OPENAI_API_KEY" \
  --set env.chainlitAuthSecret="$CHAINLIT_AUTH_SECRET"

# Re-roll the others so they pick up new env vars + new image
helm upgrade --install mcp-server   ./backend-mcp/helm -n tasks-app \
  --set secrets.databaseUrl="$DB_URL" \
  --set secrets.secretKey="$CHAINLIT_AUTH_SECRET"
helm upgrade --install notification ./notification/helm -n tasks-app \
  --set secrets.databaseUrl="$DB_URL"

oc rollout restart deploy/auth-service deploy/mcp-server deploy/agent deploy/notification -n tasks-app
```

## 5. OAuth setup (optional but recommended)

### Google
1. Go to https://console.cloud.google.com/apis/credentials
2. Create OAuth 2.0 Client ID → Web application
3. Authorized redirect URI:
   ```
   http://auth-service-tasks-app.apps-crc.testing/api/auth/callback/google
   ```
4. Copy Client ID + Client Secret, pass via `--set secrets.googleClientId=...` above.

### GitHub
1. Go to https://github.com/settings/developers → New OAuth App
2. Authorization callback URL:
   ```
   http://auth-service-tasks-app.apps-crc.testing/api/auth/callback/github
   ```
3. Copy Client ID + Client Secret, pass via `--set secrets.githubClientId=...` above.

If you skip OAuth, the buttons appear but `/api/auth/sign-in/social` returns an error.
Email + password works regardless.

## 6. Cookie scope

The default values set `BETTER_AUTH_COOKIE_DOMAIN=.apps-crc.testing` so
the session cookie is sent to every `*.apps-crc.testing` route — agent,
mcp-server, notification, etc. If you serve any of these from a
different parent domain, change `auth-service/helm/values.yaml`
`cookieDomain` accordingly.

`cookieSecure` defaults to `"false"` since OpenShift CRC routes are
HTTP by default. Flip to `"true"` once you put real TLS in front.

## 7. Verify

```bash
# Login page
curl -sI http://auth-service-tasks-app.apps-crc.testing/login | head

# Agent should redirect unauthenticated to /login on auth-service
curl -sI http://agent-tasks-app.apps-crc.testing/ | grep -i location
```

Open the agent URL in a browser → you should land on the login page,
sign up with email+password, then bounce back into the chat as that user.
Tasks/notifications you create are visible only to your account.
