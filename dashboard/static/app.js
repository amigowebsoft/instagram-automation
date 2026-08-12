/* ================================================================
   AI Instagram Automation Dashboard — JavaScript
   Real-time polling, UI updates, modal, pipeline trigger
   ================================================================ */

const POLL_INTERVAL = 15000; // 15 seconds

// ── Init ─────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  refreshAll();
  setInterval(refreshStatus, POLL_INTERVAL);
  setInterval(refreshLog, POLL_INTERVAL * 2);
  setInterval(updateCountdown, 1000);
});

async function refreshAll() {
  await Promise.allSettled([
    refreshStatus(),
    refreshNews(),
    refreshPosts(),
    refreshLog(),
    refreshAnalytics(),
  ]);
}

// ── Status ───────────────────────────────────────────────────────
async function refreshStatus() {
  try {
    const data = await fetchJSON("/api/status");

    // Nav
    setText("accountBadge", data.ig_account || "—");
    setText("liveLabel", data.ig_connected ? "Connected" : "Disconnected");

    // Stats
    animateValue("statNewsVal", data.today_stats?.news_fetched ?? "—");
    animateValue("statSelectedVal", data.today_stats?.news_selected ?? "—");
    animateValue("statPublishedVal", data.today_stats?.posts_published ?? "—");
    animateValue("statReachVal", formatNum(data.analytics?.total_reach));
    animateValue(
      "statEngVal",
      (data.analytics?.avg_engagement ?? 0).toFixed(1) + "%",
    );

    // Countdown
    if (data.schedule) {
      window._nextRunSeconds = data.schedule.seconds_remaining;
      updateCountdown();
    }

    // Live mode badge
    const dot = document.querySelector(".mode-dot");
    const label = document.getElementById("modeLabel");
    if (data.live_mode) {
      dot?.classList.add("live");
      if (label) label.textContent = "LIVE MODE — posting to Instagram";
    } else {
      dot?.classList.remove("live");
      if (label) label.textContent = "DRY RUN MODE — no actual posts";
    }
  } catch (e) {
    console.error("Status error:", e);
  }
}

// ── Analytics ────────────────────────────────────────────────────-
async function refreshAnalytics() {
  try {
    const data = await fetchJSON("/api/analytics");
    const s = data.summary || {};
    setText("mLikes", formatNum(s.total_likes ?? 0));
    setText("mComments", formatNum(s.total_comments ?? 0));
    setText("mSaves", formatNum(s.total_saves ?? 0));
    setText("mReach", formatNum(s.total_reach ?? 0));
  } catch (e) {
    /* silent */
  }
}

// ── News ─────────────────────────────────────────────────────────
async function refreshNews() {
  try {
    const items = await fetchJSON("/api/news");
    const list = document.getElementById("newsList");
    const badge = document.getElementById("newsCount");
    if (!list) return;

    badge && (badge.textContent = `${items.length} articles`);

    if (!items.length) {
      list.innerHTML =
        '<div class="empty-state">No AI news fetched yet today.</div>';
      return;
    }

    // Show selected (top 5) first, then rest
    const selected = items.filter((n) => n.is_selected);
    const rest = items.filter((n) => !n.is_selected).slice(0, 5);
    const display = [...selected, ...rest].slice(0, 10);

    list.innerHTML = display
      .map((item, idx) => {
        const rank = item.selection_rank || idx + 1;
        const viral = (item.viral_score || 0).toFixed(0);
        const useful = (item.usefulness_score || 0).toFixed(0);
        const innov = (item.innovation_score || 0).toFixed(0);
        const src = escHtml(item.source || "");
        const title = escHtml(item.title || "");
        const url = item.url
          ? `href="${escHtml(item.url)}" target="_blank"`
          : "";
        return `
        <div class="news-item">
          <div class="news-rank">${rank}</div>
          <div class="news-body">
            <div class="news-title" title="${title}">
              ${url ? `<a ${url} style="color:inherit;text-decoration:none">${title}</a>` : title}
            </div>
            <div class="news-meta">${src} · Score: ${(parseFloat(viral) + parseFloat(useful) + parseFloat(innov)).toFixed(0)}/30</div>
          </div>
          <div class="news-scores">
            <span class="score-pill score-viral"  title="Viral">🔥 ${viral}</span>
            <span class="score-pill score-use"    title="Useful">💡 ${useful}</span>
            <span class="score-pill score-innov"  title="Innovation">⚡ ${innov}</span>
          </div>
        </div>
      `;
      })
      .join("");
  } catch (e) {
    console.error("News error:", e);
  }
}

// ── Posts ─────────────────────────────────────────────────────────
async function refreshPosts() {
  try {
    const posts = await fetchJSON("/api/posts");
    const grid = document.getElementById("postsGrid");
    const badge = document.getElementById("postsCount");
    if (!grid) return;

    badge && (badge.textContent = `${posts.length} posts`);

    if (!posts.length) {
      grid.innerHTML =
        '<div class="empty-state" style="grid-column:1/-1">No posts generated yet. Run the pipeline to start.</div>';
      return;
    }

    grid.innerHTML = posts
      .map((post) => {
        const status = post.status || "pending";
        const topic = escHtml((post.topic || "AI Update").substring(0, 80));
        const thumb = post.thumbnail;
        const thumbEl = thumb
          ? `<img class="post-thumb" src="${thumb}" alt="Slide preview" />`
          : `<div class="post-thumb-placeholder">🤖</div>`;

        return `
        <div class="post-card" onclick="openPostModal(${post.id})">
          ${thumbEl}
          <div class="post-info">
            <div class="post-topic">${topic}</div>
            <span class="post-status status-${status}">${status}</span>
          </div>
        </div>
      `;
      })
      .join("");
  } catch (e) {
    console.error("Posts error:", e);
  }
}

// ── Log ───────────────────────────────────────────────────────────
async function refreshLog() {
  try {
    const entries = await fetchJSON("/api/log");
    const container = document.getElementById("logContainer");
    if (!container) return;

    if (!entries.length) {
      container.innerHTML =
        '<div class="empty-state">No log entries yet.</div>';
      return;
    }

    container.innerHTML = entries
      .map((e) => {
        const ts = formatTs(e.logged_at);
        const cls =
          e.status === "success"
            ? "success"
            : e.status === "failed"
              ? "failed"
              : "started";
        const topic = escHtml((e.topic || "Pipeline").substring(0, 50));
        const msg = escHtml((e.message || "").substring(0, 80));
        return `
        <div class="log-entry ${cls}">
          <span class="log-ts">${ts}</span>
          <span class="log-badge ${cls}">${escHtml(e.status)}</span>
          <span class="log-topic">${topic}</span>
          <span class="log-msg">${msg}</span>
        </div>
      `;
      })
      .join("");
  } catch (e) {
    console.error("Log error:", e);
  }
}

// ── Countdown ─────────────────────────────────────────────────────
function updateCountdown() {
  const el = document.getElementById("countdownTimer");
  if (!el) return;
  if (window._nextRunSeconds === undefined) return;

  if (window._nextRunSeconds > 0) {
    window._nextRunSeconds--;
  }

  const total = window._nextRunSeconds;
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  el.textContent = `${pad(h)}:${pad(m)}:${pad(s)}`;
}

// ── Pipeline Trigger ──────────────────────────────────────────────
async function triggerPipeline(live = false) {
  const btn = document.getElementById(live ? "btnLive" : "btnDryRun");
  const status = document.getElementById("runStatus");
  if (!status) return;

  const confirmed = live
    ? confirm("⚠️ This will PUBLISH LIVE to Instagram. Are you sure?")
    : true;
  if (!confirmed) return;

  btn && (btn.disabled = true);
  status.className = "run-status";
  status.textContent = "⏳ Starting pipeline...";

  try {
    const res = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ live }),
    });
    const data = await res.json();
    status.className = "run-status ok";
    status.textContent = `✅ ${data.message || "Pipeline started"}`;
    setTimeout(() => {
      refreshAll();
    }, 5000);
  } catch (e) {
    status.className = "run-status err";
    status.textContent = `❌ Error: ${e.message}`;
  } finally {
    setTimeout(() => {
      btn && (btn.disabled = false);
    }, 3000);
  }
}

// ── Modal ──────────────────────────────────────────────────────────
async function openPostModal(postId) {
  const modal = document.getElementById("slideModal");
  if (!modal) return;

  try {
    const post = await fetchJSON(`/api/posts/${postId}/slides`);

    setText("modalTitle", post.topic || "Post Preview");

    // Slides
    const viewer = document.getElementById("slidesViewer");
    if (viewer) {
      viewer.innerHTML = post.slides
        .map((src, i) =>
          src
            ? `<img class="slide-preview-img" src="${src}" alt="Slide ${i + 1}" />`
            : `<div class="slide-preview-img" style="display:flex;align-items:center;justify-content:center;font-size:32px">🤖</div>`,
        )
        .join("");
    }

    // Caption
    const capEl = document.getElementById("modalCaption");
    if (capEl) capEl.textContent = post.caption || "No caption generated.";

    // Hashtags
    const tagsEl = document.getElementById("modalHashtags");
    if (tagsEl) {
      const tags = Array.isArray(post.hashtags) ? post.hashtags : [];
      tagsEl.innerHTML = tags
        .map((t) => `<span class="tag-chip">${escHtml(t)}</span>`)
        .join("");
    }

    modal.classList.add("open");
  } catch (e) {
    console.error("Modal error:", e);
  }
}

function closeModal(e) {
  if (e && e.target !== document.getElementById("slideModal")) return;
  document.getElementById("slideModal")?.classList.remove("open");
}

// ESC key closes modal
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape")
    document.getElementById("slideModal")?.classList.remove("open");
});

// ── Utils ──────────────────────────────────────────────────────────
async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val ?? "—";
}

function animateValue(id, val) {
  const el = document.getElementById(id);
  if (!el) return;
  el.style.animation = "none";
  el.offsetHeight; // reflow
  el.style.animation = "";
  el.textContent = val ?? "—";
}

function formatNum(n) {
  const num = Number(n) || 0;
  if (num >= 1e6) return (num / 1e6).toFixed(1) + "M";
  if (num >= 1e3) return (num / 1e3).toFixed(1) + "K";
  return num.toString();
}

function pad(n) {
  return String(n).padStart(2, "0");
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatTs(ts) {
  if (!ts) return "—";
  try {
    const d = new Date(ts.replace(" ", "T"));
    return d.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return ts.substring(11, 19) || "—";
  }
}
