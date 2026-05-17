// Notification bell injected into the Chainlit UI.
// Lives in a fixed-position root attached to <body> so it survives any
// React re-renders inside the Chainlit app.

(function () {
  if (window.__notifBellMounted) return;
  window.__notifBellMounted = true;

  const POLL_MS = 5000;

  const mount = () => {
    const root = document.createElement("div");
    root.id = "notif-bell-root";
    root.innerHTML = `
      <button id="notif-bell-btn" aria-label="Notifications">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
          <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
        </svg>
        <span id="notif-bell-badge"></span>
      </button>
      <div id="notif-bell-panel" role="dialog" aria-label="Notifications">
        <div class="notif-bell-header">
          <span>Notifications</span>
          <button class="notif-bell-clear" id="notif-bell-clear">Clear all</button>
        </div>
        <div class="notif-bell-body" id="notif-bell-body">
          <div class="notif-bell-empty">No notifications</div>
        </div>
      </div>
    `;
    document.body.appendChild(root);

    const btn = root.querySelector("#notif-bell-btn");
    const badge = root.querySelector("#notif-bell-badge");
    const panel = root.querySelector("#notif-bell-panel");
    const body = root.querySelector("#notif-bell-body");
    const clearBtn = root.querySelector("#notif-bell-clear");

    const setBadge = (n) => {
      if (n > 0) {
        badge.textContent = n > 99 ? "99+" : String(n);
        badge.style.display = "flex";
      } else {
        badge.style.display = "none";
      }
    };

    const timeAgo = (ts) => {
      const diff = (Date.now() - new Date(ts).getTime()) / 1000;
      if (!isFinite(diff)) return "";
      if (diff < 60) return "just now";
      if (diff < 3600) return Math.floor(diff / 60) + "m ago";
      if (diff < 86400) return Math.floor(diff / 3600) + "h ago";
      return Math.floor(diff / 86400) + "d ago";
    };

    const escapeHtml = (s) =>
      String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");

    const dotClass = (t) =>
      t === "task-created" ? "created" :
      t === "task-updated" ? "updated" :
      t === "task-deleted" ? "deleted" : "unknown";

    const renderList = (items) => {
      if (!items || !items.length) {
        body.innerHTML = `<div class="notif-bell-empty">No notifications</div>`;
        return;
      }
      body.innerHTML = items
        .map((n) => `
          <div class="notif-bell-item">
            <span class="notif-bell-dot notif-bell-dot--${dotClass(n.event_type)}"></span>
            <div class="notif-bell-content">
              <div class="notif-bell-msg">${escapeHtml(n.message || "")}</div>
              <div class="notif-bell-time">${escapeHtml(timeAgo(n.timestamp))}</div>
            </div>
          </div>
        `)
        .join("");
    };

    const loadList = async () => {
      try {
        const r = await fetch("/api/notifications", { cache: "no-store" });
        const items = r.ok ? await r.json() : [];
        renderList(items);
        setBadge(items.length);
      } catch {
        body.innerHTML = `<div class="notif-bell-empty">Failed to load</div>`;
      }
    };

    const pollCount = async () => {
      try {
        const r = await fetch("/api/notifications/count", { cache: "no-store" });
        if (!r.ok) return;
        const data = await r.json();
        setBadge(data.count || 0);
      } catch {
        /* ignore transient errors */
      }
    };

    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const open = panel.classList.toggle("open");
      if (open) loadList();
    });

    document.addEventListener("click", (e) => {
      if (!root.contains(e.target)) panel.classList.remove("open");
    });

    clearBtn.addEventListener("click", async (e) => {
      e.stopPropagation();
      try {
        await fetch("/api/notifications", { method: "DELETE" });
      } catch { /* ignore */ }
      renderList([]);
      setBadge(0);
    });

    pollCount();
    setInterval(pollCount, POLL_MS);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount, { once: true });
  } else {
    mount();
  }
})();
