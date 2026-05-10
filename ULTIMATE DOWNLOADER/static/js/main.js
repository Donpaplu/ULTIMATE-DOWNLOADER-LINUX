/* static/js/main.js */

"use strict";

// ── State ─────────────────────────────────────────────────────
let currentMode     = "best_vid";
let selectedFormats = [];
let isRunning       = false;
let destCount       = 0;
let isMediaTrack    = true;
let currentFilename = "";

const con = document.getElementById("console");

// ── Helpers ───────────────────────────────────────────────────
function getVal(id) {
  const el = document.getElementById(id);
  return el ? el.value.trim() : "";
}
function getCheck(id) {
  const el = document.getElementById(id);
  return el ? el.checked : false;
}
function consoleWrite(text) {
  con.textContent += text;
  con.scrollTop = con.scrollHeight;
}

// ── Boot: load saved config paths ─────────────────────────────
(async function boot() {
  try {
    const res = await fetch("/api/config");
    if (res.ok) {
      const c = await res.json();
      document.getElementById("s-vid").value    = c.outdir           || "";
      document.getElementById("s-pl").value     = c.pl_outdir        || "";
      document.getElementById("s-mus").value    = c.music_outdir     || "";
      document.getElementById("s-mus-pl").value = c.music_pl_outdir  || "";
      document.getElementById("s-ck").value     = c.cookies          || "";
    }
  } catch (e) { /* silently ignore */ }
})();

// ── Tab / Mode Switching ──────────────────────────────────────
function setMode(el) {
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  el.classList.add("active");
  currentMode = el.dataset.mode;
  const m = currentMode;

  document.getElementById("f-url")?.classList.toggle("hidden",   m === "batch");
  document.getElementById("f-batch")?.classList.toggle("hidden", m !== "batch");

  const isPlaylistMode = ["best_pl","custom_pl","audio_pl"].includes(m);
  document.getElementById("f-items")?.classList.toggle("hidden", !isPlaylistMode);

  const hasCustom = ["custom_vid","custom_pl","batch"].includes(m);
  document.getElementById("f-custom")?.classList.toggle("hidden", !hasCustom);

  const isAudio = ["audio","audio_pl"].includes(m);
  document.getElementById("f-subs-wrap")?.classList.toggle("hidden", isAudio);

  document.getElementById("f-rate-wrap")?.classList.toggle("hidden", false);

  const showAudio = ["audio","audio_pl"].includes(m);
  document.getElementById("f-audio")?.classList.toggle("hidden", !showAudio);

  document.getElementById("f-bmode")?.classList.toggle("hidden", m !== "batch");
}

// ── Progress Bar Reset ────────────────────────────────────────
function resetProgress(isAudioOnlyMode) {
  destCount    = 0;
  isMediaTrack = true;
  document.getElementById("sec-progress").classList.remove("hidden");
  document.getElementById("prog-status-text").textContent = "Status: Downloading...";
  document.getElementById("prog-filename").textContent    = "File: —";
  document.getElementById("prog-fill-vid").style.width   = "0%";
  document.getElementById("prog-fill-aud").style.width   = "0%";
  document.getElementById("prog-pct").textContent         = "0.0%";
  document.getElementById("prog-items").textContent       = "Files: —";
  document.getElementById("prog-speed").textContent       = "Speed: —";

  if (isAudioOnlyMode) {
    document.getElementById("track-2-wrap").classList.add("hidden");
    document.getElementById("track-1-label").textContent = "AUDIO TRACK";
  } else {
    document.getElementById("track-2-wrap").classList.remove("hidden");
    document.getElementById("track-1-label").textContent = "Video / Base Track";
  }
}

// ── Per-file reset (batch / playlist item) ────────────────────
function resetFileProgress() {
  destCount       = 0;
  isMediaTrack    = true;
  currentFilename = "";
  document.getElementById("prog-fill-vid").style.width    = "0%";
  document.getElementById("prog-fill-aud").style.width    = "0%";
  document.getElementById("prog-pct").textContent         = "0%";
  document.getElementById("prog-speed").textContent       = "Speed: —";
  document.getElementById("prog-filename").textContent    = "File: —";
  document.getElementById("prog-status-text").textContent = "Status: Downloading...";
}

// ── Control (Pause / Resume / Skip / Cancel) ──────────────────
async function controlDL(action) {
  if (!isRunning) return;
  try {
    const payload = {
      action,
      mode: currentMode,
      current_file: currentFilename,
      session_paths: {
        vid:    getVal("s-vid"),
        pl:     getVal("s-pl"),
        mus:    getVal("s-mus"),
        mus_pl: getVal("s-mus-pl"),
      }
    };
    const res  = await fetch("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (data.status) {
      document.getElementById("prog-status-text").textContent = `Status: ${data.status}`;
      consoleWrite(`\n[SYSTEM] ${data.status}\n`);
    } else if (data.error) {
      alert(data.error);
    }
  } catch (e) { console.error(e); }
}

// ── Streaming POST ────────────────────────────────────────────
async function streamPost(endpoint, payload) {
  if (isRunning) return alert("A process is already running.");
  isRunning = true;
  document.getElementById("dl-btn").disabled = true;
  con.textContent = "Starting process...\n";

  if (endpoint === "/api/download") {
    const isAudioOnly = ["audio","audio_pl"].includes(payload.mode)
      || (payload.mode === "batch" && payload.batch_mode === "audio");
    resetProgress(isAudioOnly);
  }

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const reader  = res.body.getReader();
    const decoder = new TextDecoder("utf-8");

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      consoleWrite(chunk);

      if (endpoint === "/api/download") {
        _parseProgress(chunk, payload);
      }
    }

    if (endpoint === "/api/download") {
      document.getElementById("prog-status-text").textContent = "Status: Finished!";
      document.getElementById("prog-fill-vid").style.width   = "100%";
      if (destCount > 1)
        document.getElementById("prog-fill-aud").style.width = "100%";
      document.getElementById("prog-pct").textContent = "100%";
    }

  } catch (err) {
    consoleWrite(`\n[ERROR] ${err}\n`);
    document.getElementById("prog-status-text").textContent = "Status: Error/Aborted";
  } finally {
    isRunning = false;
    document.getElementById("dl-btn").disabled = false;
  }
}

// ── Progress line parser ──────────────────────────────────────
function _parseProgress(chunk, payload) {
  const lines = chunk.split("\n");

  for (const line of lines) {
    // Batch item marker
    const mBatch = line.match(/\[BATCH_ITEM\]\s+(\d+)\s+of\s+(\d+)/);
    if (mBatch) {
      document.getElementById("prog-items").textContent = `File ${mBatch[1]} of ${mBatch[2]}`;
      resetFileProgress();
      continue;
    }

    // yt-dlp playlist item counter
    const mItem = line.match(/Downloading (?:video|item)\s+(\d+)\s+of\s+(\d+)/);
    if (mItem) {
      document.getElementById("prog-items").textContent = `File ${mItem[1]} of ${mItem[2]}`;
      resetFileProgress();
      continue;
    }

    // Destination / already downloaded
    const mDest = line.match(/\[download\] Destination: (.*)/)
                || line.match(/\[download\] (.*) has already been downloaded/);
    if (mDest) {
      const fname = mDest[1].split(/[/\\]/).pop();
      const isIgnored = /\.(jpg|jpeg|png|webp|mhtml|description|info\.json|vtt|srt|ass|ttml|srv\d|xml|annotations)$/i.test(fname);

      if (!isIgnored) {
        isMediaTrack    = true;
        currentFilename = fname;
        document.getElementById("prog-filename").textContent = "File: " + fname;
        if (line.includes("Destination:")) {
          destCount++;
          if (destCount === 1) {
            document.getElementById("prog-fill-vid").style.width = "0%";
            document.getElementById("prog-fill-aud").style.width = "0%";
          }
        }
      } else {
        isMediaTrack = false;
      }
      continue;
    }

    // Progress percentage
    const mStat = line.match(
      /\[download\]\s+([\d.]+)%\s+of\s+([^ ]+)(?:\s+at\s+([^ ]+))?(?:\s+ETA\s+([\d:]+))?/
    );
    if (mStat && isMediaTrack) {
      const pct   = mStat[1];
      const total = (mStat[2] || "").replace("~", "");
      const speed = mStat[3] || "—";
      const eta   = mStat[4] || "—";

      let statsStr = "";
      if (/[\d.]/.test(total)) {
        const numTotal   = parseFloat(total.replace(/[^0-9.]/g, ""));
        const unit       = total.replace(/[0-9.]/g, "");
        const downloaded = ((parseFloat(pct) / 100) * numTotal).toFixed(2);
        statsStr = `${downloaded}${unit} / ${total} | Speed: ${speed} | ETA: ${eta}`;
      } else {
        statsStr = `Speed: ${speed} | ETA: ${eta}`;
      }
      document.getElementById("prog-speed").textContent = statsStr;
      document.getElementById("prog-pct").textContent   = pct + "%";

      const pctVal = pct + "%";
      if (destCount <= 1) {
        document.getElementById("prog-fill-vid").style.width = pctVal;
      } else {
        document.getElementById("prog-fill-aud").style.width = pctVal;
      }
    }
  }
}

// ── Start Download ────────────────────────────────────────────
function startDownload() {
  const m          = currentMode;
  const isPlaylist = ["best_pl","custom_pl","audio_pl","batch"].includes(m);
  const ctrlDiv    = document.getElementById("prog-controls");

  if (isPlaylist) {
    ctrlDiv.innerHTML = `
      <button class="btn btn-outline"  onclick="controlDL('pause')">⏸ Pause All</button>
      <button class="btn btn-outline"  onclick="controlDL('resume')">▶ Resume All</button>
      <button class="btn btn-warning"  onclick="controlDL('cancel_current')">⏭ Skip Current File</button>
      <button class="btn btn-danger"   onclick="controlDL('cancel_all')">✕ Cancel All</button>`;
  } else {
    ctrlDiv.innerHTML = `
      <button class="btn btn-outline"  onclick="controlDL('pause')">⏸ Pause</button>
      <button class="btn btn-outline"  onclick="controlDL('resume')">▶ Resume</button>
      <button class="btn btn-danger"   onclick="controlDL('cancel_all')">✕ Cancel</button>`;
  }

  const payload = {
    mode:       m,
    url:        getVal("url"),
    cust_path:  getVal("cust_path"),
    subs:       getCheck("subs"),
    rate:       getVal("rate"),
    vformat:    getVal("vformat"),
    extra:      getVal("extra"),
    batch_file: getVal("batch_file"),
    pl_items:   getVal("pl_items"),
    afmt:       document.getElementById("afmt")       ? document.getElementById("afmt").value       : "mp3",
    qual:       parseInt(getVal("qual")) || 0,
    batch_mode: document.getElementById("batch_mode") ? document.getElementById("batch_mode").value : "video",
    session_paths: {
      vid:    getVal("s-vid"),
      pl:     getVal("s-pl"),
      mus:    getVal("s-mus"),
      mus_pl: getVal("s-mus-pl"),
      ck:     getVal("s-ck"),
    }
  };

  if (m === "batch" && !payload.batch_file) return alert("Enter batch .txt file path.");
  if (m !== "batch" && !payload.url)        return alert("Enter a URL.");
  streamPost("/api/download", payload);
}

// ── Tools ──────────────────────────────────────────────────────
function runTool(tool) {
  const payload = {
    tool,
    url:  getVal("tool-url") || getVal("url"),
    session_paths: { ck: getVal("s-ck") }
  };
  streamPost("/api/tools", payload);
}

// ── Format Picker Modal ───────────────────────────────────────
async function openFormatPicker() {
  const m         = currentMode;
  let   url       = getVal("url");
  const batchFile = getVal("batch_file");

  if (m === "batch") {
    if (!batchFile) {
      alert("Enter the Batch .txt file path first.");
      document.getElementById("batch_file")?.focus();
      return;
    }
  } else if (!url) {
    alert("Paste a URL in the Target URL field first.");
    document.getElementById("url")?.focus();
    return;
  }

  const modal = document.getElementById("format-modal");
  modal.classList.add("open");
  document.getElementById("fmt-loading").style.display = "block";
  document.getElementById("fmt-loading").textContent   = "Fetching formats… please wait.";
  document.getElementById("fmt-table").classList.add("hidden");
  document.getElementById("btn-apply").disabled        = true;
  document.getElementById("fmt-selected").textContent  = "None";
  selectedFormats = [];

  try {
    const res  = await fetch("/api/get_formats", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({
        url:        m === "batch" ? "" : url,
        batch_file: batchFile,
        pl_items:   getVal("pl_items"),
        session_paths: { ck: getVal("s-ck") }
      }),
    });
    const data = await res.json();

    if (data.error) {
      document.getElementById("fmt-loading").textContent = `[Error] ${data.error}`;
      return;
    }

    const tbody = document.getElementById("fmt-tbody");
    tbody.innerHTML = "";

    const formats = data.formats.slice().reverse();

    formats.forEach(f => {
      const tr = document.createElement("tr");
      tr.setAttribute("data-fmt-id", f.id);

      const langHtml = f.language
        ? `<span class="lang-badge">${f.language}</span>`
        : "";

      tr.innerHTML = `
        <td style="font-weight:600; color:var(--warning)">${f.id} ${langHtml}</td>
        <td>${f.ext}</td>
        <td>${f.resolution}</td>
        <td>${f.vcodec}</td>
        <td>${f.acodec}</td>
        <td style="color:var(--info); font-size:11px">${f.language || ""}</td>
        <td style="color:var(--text-dim); font-size:11px">${f.note || ""}</td>
        <td style="color:var(--text-dim)">${f.filesize}</td>`;

      tr.addEventListener("click", () => {
        const id = f.id;
        if (selectedFormats.includes(id)) {
          selectedFormats = selectedFormats.filter(x => x !== id);
          tr.classList.remove("selected");
        } else {
          if (selectedFormats.length >= 2) {
            const oldest = selectedFormats.shift();
            document.querySelector(`tr[data-fmt-id="${oldest}"]`)?.classList.remove("selected");
          }
          selectedFormats.push(id);
          tr.classList.add("selected");
        }
        const joined = selectedFormats.join("+");
        document.getElementById("fmt-selected").textContent = joined || "None";
        document.getElementById("btn-apply").disabled       = selectedFormats.length === 0;
      });

      tr.addEventListener("dblclick", applyFormat);
      tbody.appendChild(tr);
    });

    document.getElementById("fmt-loading").style.display = "none";
    document.getElementById("fmt-table").classList.remove("hidden");

  } catch (err) {
    document.getElementById("fmt-loading").textContent = "[Error] Could not connect to backend.";
  }
}

function closeFormatPicker() {
  document.getElementById("format-modal").classList.remove("open");
}
function applyFormat() {
  if (selectedFormats.length > 0) {
    document.getElementById("vformat").value = selectedFormats.join("+");
    closeFormatPicker();
  }
}

document.getElementById("format-modal").addEventListener("click", function(e) {
  if (e.target === this) closeFormatPicker();
});

// ── Server Shutdown ───────────────────────────────────────────
async function shutdownServer() {
  if (!confirm("Stop the server? The page will become unreachable until you run start.sh again.")) return;
  try {
    await fetch("/api/shutdown", { method: "POST" });
    document.body.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:center;height:100vh;
        background:#0F172A;color:#94A3B8;font-family:Inter,sans-serif;text-align:center;gap:12px;flex-direction:column;">
        <div style="font-size:24px;color:#10B981;font-weight:700;">Server Stopped</div>
        <div>Run <code style="color:#F59E0B">./start.sh</code> again to restart.</div>
      </div>`;
  } catch (e) {
    alert("Server shut down (connection lost — that's expected).");
  }
}
