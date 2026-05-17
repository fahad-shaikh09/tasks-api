// Shared logic for login.html and signup.html. Talks to better-auth's
// /api/auth/* endpoints directly (no SDK to keep this dependency-free).

const params = new URLSearchParams(window.location.search);
// Where to send the user after a successful login/signup.
// Defaults to the agent UI if no ?redirect is supplied.
const REDIRECT =
  params.get("redirect") || window.__DEFAULT_REDIRECT__ || "/";

function setError(msg) {
  const el = document.getElementById("error");
  if (el) el.textContent = msg || "";
}

async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });
  let payload = null;
  try { payload = await res.json(); } catch { /* non-JSON */ }
  return { ok: res.ok, status: res.status, payload };
}

async function signInEmail(email, password) {
  setError("");
  const { ok, payload } = await postJson("/api/auth/sign-in/email", {
    email, password, callbackURL: REDIRECT,
  });
  if (!ok) {
    setError(payload?.message || "Sign-in failed.");
    return;
  }
  window.location.href = REDIRECT;
}

async function signUpEmail(name, email, password) {
  setError("");
  const { ok, payload } = await postJson("/api/auth/sign-up/email", {
    email, password, name, callbackURL: REDIRECT,
  });
  if (!ok) {
    setError(payload?.message || "Sign-up failed.");
    return;
  }
  window.location.href = REDIRECT;
}

async function signInSocial(provider) {
  setError("");
  const { ok, payload } = await postJson("/api/auth/sign-in/social", {
    provider,
    callbackURL: REDIRECT,
  });
  if (!ok) {
    setError(payload?.message || `${provider} sign-in unavailable.`);
    return;
  }
  // better-auth returns { url } to redirect the browser to the provider's
  // OAuth consent screen.
  if (payload?.url) {
    window.location.href = payload.url;
  }
}

window.AUTH = { signInEmail, signUpEmail, signInSocial };
