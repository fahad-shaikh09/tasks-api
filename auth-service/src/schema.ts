// Idempotent migration for better-auth's required tables.
//
// better-auth doesn't auto-create its schema on first connect — its docs
// expect you to run `@better-auth/cli migrate` ahead of time. For this
// monorepo we'd rather not gate every deploy on a separate Job, so we
// CREATE TABLE IF NOT EXISTS at startup using the same Postgres pool.
//
// Column names are quoted because better-auth uses camelCase identifiers
// (emailVerified, userId, createdAt) and Postgres lowercases unquoted ones.
// Keep these definitions in lockstep with better-auth's expected schema —
// see https://www.better-auth.com/docs/concepts/database#schema.

import type { Pool } from "pg";

const STATEMENTS: string[] = [
  `CREATE TABLE IF NOT EXISTS "user" (
    "id"            text         PRIMARY KEY,
    "name"          text         NOT NULL,
    "email"         text         NOT NULL UNIQUE,
    "emailVerified" boolean      NOT NULL DEFAULT false,
    "image"         text,
    "createdAt"     timestamptz  NOT NULL DEFAULT NOW(),
    "updatedAt"     timestamptz  NOT NULL DEFAULT NOW()
  )`,

  `CREATE TABLE IF NOT EXISTS "session" (
    "id"         text         PRIMARY KEY,
    "userId"     text         NOT NULL REFERENCES "user"("id") ON DELETE CASCADE,
    "token"      text         NOT NULL UNIQUE,
    "expiresAt"  timestamptz  NOT NULL,
    "ipAddress"  text,
    "userAgent"  text,
    "createdAt"  timestamptz  NOT NULL DEFAULT NOW(),
    "updatedAt"  timestamptz  NOT NULL DEFAULT NOW()
  )`,

  `CREATE INDEX IF NOT EXISTS "session_userId_idx" ON "session"("userId")`,

  `CREATE TABLE IF NOT EXISTS "account" (
    "id"                     text         PRIMARY KEY,
    "userId"                 text         NOT NULL REFERENCES "user"("id") ON DELETE CASCADE,
    "accountId"              text         NOT NULL,
    "providerId"             text         NOT NULL,
    "accessToken"            text,
    "refreshToken"           text,
    "idToken"                text,
    "accessTokenExpiresAt"   timestamptz,
    "refreshTokenExpiresAt"  timestamptz,
    "scope"                  text,
    "password"               text,
    "createdAt"              timestamptz  NOT NULL DEFAULT NOW(),
    "updatedAt"              timestamptz  NOT NULL DEFAULT NOW()
  )`,

  `CREATE INDEX IF NOT EXISTS "account_userId_idx" ON "account"("userId")`,
  `CREATE UNIQUE INDEX IF NOT EXISTS "account_provider_account_idx" ON "account"("providerId","accountId")`,

  `CREATE TABLE IF NOT EXISTS "verification" (
    "id"          text         PRIMARY KEY,
    "identifier"  text         NOT NULL,
    "value"       text         NOT NULL,
    "expiresAt"   timestamptz  NOT NULL,
    "createdAt"   timestamptz  NOT NULL DEFAULT NOW(),
    "updatedAt"   timestamptz  NOT NULL DEFAULT NOW()
  )`,

  `CREATE INDEX IF NOT EXISTS "verification_identifier_idx" ON "verification"("identifier")`,
];

export async function ensureBetterAuthSchema(pool: Pool): Promise<void> {
  const client = await pool.connect();
  try {
    for (const sql of STATEMENTS) {
      await client.query(sql);
    }
    console.log("better-auth schema verified (user, session, account, verification)");
  } finally {
    client.release();
  }
}
