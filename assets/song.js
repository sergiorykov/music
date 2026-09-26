// Song page: lyrics switch (original / translations), "with chords" toggle, capo mode,
// transposition, chord popover and chord panel.
// All music logic (names, keys, diagrams) is precomputed by the build; this only swaps text.
(() => {
  const STORE = { mode: "songbook.mode", chords: "songbook.chords", ui: "songbook.ui" };
  const load = (k) => { try { return localStorage.getItem(k); } catch (_) { return null; } };
  const save = (k, v) => { try { localStorage.setItem(k, v); } catch (_) { /* storage unavailable */ } };

  const body = document.body;
  const blocks = [...document.querySelectorAll(".lyrics-block")];
  if (!blocks.length) return;
  const data = new Map(blocks.map((b) => [b.dataset.lyrics, JSON.parse(b.querySelector(".lyrics-data").textContent)]));
  let active = blocks.find((b) => !b.hidden) || blocks[0];

  const state = { mode: load(STORE.mode) === "sound" ? "sound" : "shape", t: 0, chords: load(STORE.chords) === "1" };
  // Links from song lists open the page in a given view: #lyrics or #chords
  if (location.hash === "#chords") state.chords = true;
  if (location.hash === "#lyrics") state.chords = false;

  const $ = (sel) => document.querySelector(sel);
  const keyName = $(".key-name");
  const keyShift = $(".key-shift");
  const keyReset = $(".key-reset");
  const chordsToggle = $("#chords-toggle");
  const pdfLink = $(".toolbar .pdf");
  const pop = $("#pop");

  const current = () => data.get(active.dataset.lyrics);
  const idx = () => ((state.t % 12) + 12) % 12;
  const modeFor = (d) => (d.capo ? state.mode : "shape");
  const svgFor = (name) => current().diagrams[name] || '<span class="dg-none">?</span>';

  function apply() {
    const d = current();
    const mode = modeFor(d);
    const row = d.names[mode][idx()];
    active.querySelectorAll(".ch[data-i]").forEach((el) => { el.textContent = row[+el.dataset.i]; });
    active.querySelectorAll(".dg-card").forEach((card) => {
      const name = row[+card.dataset.card];
      card.querySelector(".dg-name").textContent = name;
      card.querySelector(".dg-img").innerHTML = svgFor(name);
    });
    if (keyName) keyName.textContent = d.keys[mode][idx()];
    if (keyShift) keyShift.textContent = state.t ? (state.t > 0 ? "+" : "−") + Math.abs(state.t) : "";
    if (keyReset) keyReset.hidden = state.t === 0;
    document.querySelectorAll("[data-mode]").forEach((b) => b.classList.toggle("on", b.dataset.mode === state.mode));
    document.querySelectorAll(".toolbar [data-lyrics]").forEach((b) => {
      b.classList.toggle("on", b.dataset.lyrics === active.dataset.lyrics);
    });
    // Lyrics translations are lyrics only: chords are off and the toggle says so
    const original = active.dataset.original === "1";
    const chords = state.chords && original;
    body.classList.toggle("mode-chords", chords);
    body.classList.toggle("mode-lyrics", !chords);
    if (chordsToggle) {
      chordsToggle.disabled = !original;
      chordsToggle.textContent = original ? chordsToggle.dataset.labelChords : chordsToggle.dataset.labelLyricsOnly;
      chordsToggle.setAttribute("aria-pressed", String(chords));
      chordsToggle.classList.toggle("on", chords);
    }
    if (pdfLink && active.dataset.pdf) {
      pdfLink.href = active.dataset.pdf;
      pdfLink.textContent = `PDF ${active.dataset.lyrics.toUpperCase()}`;
    }
    hidePop();
  }

  // ── Controls ──
  document.querySelectorAll(".toolbar [data-lyrics]").forEach((b) => {
    b.addEventListener("click", () => {
      blocks.forEach((block) => { block.hidden = block.dataset.lyrics !== b.dataset.lyrics; });
      active = blocks.find((block) => !block.hidden);
      apply();
    });
  });
  if (chordsToggle) {
    chordsToggle.addEventListener("click", () => {
      state.chords = !state.chords;
      save(STORE.chords, state.chords ? "1" : "0");
      apply();
    });
  }
  document.querySelectorAll("[data-mode]").forEach((b) => {
    b.addEventListener("click", () => {
      state.mode = b.dataset.mode;
      save(STORE.mode, state.mode);
      apply();
    });
  });
  document.querySelectorAll("[data-step]").forEach((b) => {
    b.addEventListener("click", () => {
      state.t = Math.max(-6, Math.min(6, state.t + +b.dataset.step));
      apply();
    });
  });
  if (keyReset) keyReset.addEventListener("click", () => { state.t = 0; apply(); });

  // SoundCloud player before the lyrics, shown by default
  const player = document.getElementById("player");
  const playerToggle = document.getElementById("player-toggle");
  if (player && playerToggle) {
    playerToggle.addEventListener("click", () => {
      player.hidden = !player.hidden;
      playerToggle.setAttribute("aria-pressed", String(!player.hidden));
      playerToggle.classList.toggle("on", !player.hidden);
    });
  }
  document.querySelectorAll("[data-ui-lang]").forEach((a) => {
    a.addEventListener("click", () => save(STORE.ui, a.dataset.uiLang));
  });

  // ── Popover ──
  let popFor = null;
  function hidePop() {
    pop.hidden = true;
    popFor = null;
  }
  function showPop(el) {
    const name = el.textContent;
    pop.innerHTML = `<span class="dg-name">${name}</span>${svgFor(name)}`;
    pop.hidden = false;
    const r = el.getBoundingClientRect();
    const w = pop.offsetWidth;
    const left = Math.min(Math.max(8, r.left + window.scrollX + r.width / 2 - w / 2),
                          window.scrollX + document.documentElement.clientWidth - w - 8);
    pop.style.left = `${left}px`;
    pop.style.top = `${r.bottom + window.scrollY + 6}px`;
    popFor = el;
  }
  document.querySelectorAll(".ch[data-i]").forEach((el) => {
    el.addEventListener("click", (e) => {
      e.stopPropagation();
      if (popFor === el) hidePop(); else showPop(el);
    });
  });
  document.addEventListener("click", (e) => { if (!pop.contains(e.target)) hidePop(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") hidePop(); });
  window.addEventListener("resize", hidePop);

  // ── Chord panel: highlight every occurrence of the chord ──
  document.querySelectorAll(".dg-card").forEach((card) => {
    card.addEventListener("click", () => {
      const block = card.closest(".lyrics-block");
      const hits = block.querySelectorAll(`.ch[data-i="${card.dataset.card}"]`);
      hits.forEach((el) => el.classList.add("hl"));
      setTimeout(() => hits.forEach((el) => el.classList.remove("hl")), 1400);
    });
  });

  apply();
})();
