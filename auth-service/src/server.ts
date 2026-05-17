// Express host for better-auth.
//
// Routes:
//   /api/auth/*    — better-auth's own handlers (sign-in, sign-up, session, OAuth callbacks)
//   /login         — login page (HTML)
//   /signup        — signup page (HTML)
//   /config.js     — injects per-deploy config (default redirect URL) into the auth pages
//   /              — redirects to /login
//   /healthz       — liveness probe

import express from "express";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Pool } from "pg";
import { toNodeHandler } from "better-auth/node";
import { auth } from "./auth.js";
import { ensureBetterAuthSchema } from "./schema.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PUBLIC_DIR = path.resolve(__dirname, "../public");

// Where the browser should land after a successful sign-in/sign-up when no
// ?redirect= is supplied. Defaults to "/" of this service, which just bounces
// back to /login — so set this in helm to the agent's public URL.
const DEFAULT_REDIRECT_URL = process.env.DEFAULT_REDIRECT_URL ?? "/";

const app = express();

// IMPORTANT: better-auth's handler must be mounted BEFORE express.json()
// because it reads the raw request stream itself.
app.all("/api/auth/*", toNodeHandler(auth));

app.use(express.json());
app.use("/static", express.static(PUBLIC_DIR, { maxAge: "1h" }));

app.get("/config.js", (_req, res) => {
  res.type("application/javascript").send(
    `window.__DEFAULT_REDIRECT__ = ${JSON.stringify(DEFAULT_REDIRECT_URL)};`,
  );
});

app.get("/healthz", (_req, res) => {
  res.status(200).json({ status: "ok" });
});

app.get("/login", (_req, res) => {
  res.sendFile(path.join(PUBLIC_DIR, "login.html"));
});

app.get("/signup", (_req, res) => {
  res.sendFile(path.join(PUBLIC_DIR, "signup.html"));
});

app.get("/", (_req, res) => {
  res.redirect("/login");
});

const PORT = Number(process.env.PORT ?? 8003);
const HOST = process.env.HOST ?? "0.0.0.0";

// Ensure the better-auth tables exist before accepting requests. Without this
// the very first sign-up call 500s with "relation 'user' does not exist".
const schemaPool = new Pool({ connectionString: process.env.DATABASE_URL });
ensureBetterAuthSchema(schemaPool)
  .then(() => {
    app.listen(PORT, HOST, () => {
      console.log(`auth-service listening on http://${HOST}:${PORT}`);
    });
  })
  .catch((err) => {
    console.error("Failed to ensure better-auth schema:", err);
    process.exit(1);
  });
