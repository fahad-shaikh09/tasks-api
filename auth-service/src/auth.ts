// Better-auth instance configuration.
//
// Database: reuses the same Postgres that the Python services use.
// better-auth creates its own tables (user, session, account, verification)
// in the schema set via DATABASE_URL — keep them isolated from the
// app's `task` and `notification` tables.

import { betterAuth } from "better-auth";
import { Pool } from "pg";

const required = (name: string): string => {
  const v = process.env[name];
  if (!v) throw new Error(`Missing required env var: ${name}`);
  return v;
};

const optional = (name: string): string | undefined => process.env[name];

const pool = new Pool({ connectionString: required("DATABASE_URL") });

// Domain to scope the session cookie. For OpenShift CRC, set to
// ".apps-crc.testing" so the cookie is shared between auth/agent/etc.
const COOKIE_DOMAIN = optional("BETTER_AUTH_COOKIE_DOMAIN");

const socialProviders: Record<string, unknown> = {};

if (optional("GOOGLE_CLIENT_ID") && optional("GOOGLE_CLIENT_SECRET")) {
  socialProviders.google = {
    clientId: required("GOOGLE_CLIENT_ID"),
    clientSecret: required("GOOGLE_CLIENT_SECRET"),
  };
}

if (optional("GITHUB_CLIENT_ID") && optional("GITHUB_CLIENT_SECRET")) {
  socialProviders.github = {
    clientId: required("GITHUB_CLIENT_ID"),
    clientSecret: required("GITHUB_CLIENT_SECRET"),
  };
}

// Comma-separated list of origins allowed to call this service.
// e.g. "http://agent-tasks-app.apps-crc.testing,http://frontend-tasks-app.apps-crc.testing"
const trustedOrigins = (optional("TRUSTED_ORIGINS") ?? "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

export const auth = betterAuth({
  database: pool,
  secret: required("BETTER_AUTH_SECRET"),
  baseURL: required("BETTER_AUTH_URL"),
  trustedOrigins,
  emailAndPassword: {
    enabled: true,
    autoSignIn: true,
  },
  socialProviders: socialProviders as never,
  advanced: COOKIE_DOMAIN
    ? {
        defaultCookieAttributes: {
          domain: COOKIE_DOMAIN,
          sameSite: "lax",
          // For OpenShift CRC HTTP routes; flip to true behind HTTPS.
          secure: optional("BETTER_AUTH_COOKIE_SECURE") === "true",
        },
      }
    : undefined,
});
