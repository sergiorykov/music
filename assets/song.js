// Song page interactions: capo mode, transposition, chord popover, chord panel.
// All music logic (names, keys, diagrams) is precomputed by the build; this only swaps text.
(() => {
  const data = JSON.parse(document.getElementById("song-data").textContent);
  const STORE = "songbook.mode";
  const state = { mode: "shape", t: 0 };
  try {
    if (localStorage.getItem(STORE) === "sound" && data.capo) state.mode = "sound";
  } catch (_) { /* storage unavailable */ }

  const chordEls = document.querySelectorAll(".ch[data-i]");
  const cards = document.querySelectorAll(".dg-card");
  const keyName = document.getElementById("key-name");
  const keyShift = document.getElementById("key-shift");
  const keyReset = document.getElementById("key-reset");
  const pop = document.getElementById("pop");

  const idx = () => ((state.t % 12) + 12) % 12;
  const names = () => data.names[state.mode][idx()];
  const svgFor = (name) => data.diagrams[name] || '<span class="dg-none">?</span>';

  function apply() {
    const row = names();
    chordEls.forEach((el) => { el.textContent = row[+el.dataset.i]; });
    cards.forEach((card) => {
      const name = row[+card.dataset.card];
      card.querySelector(".dg-name").textContent = name;
      card.querySelector(".dg-img").innerHTML = svgFor(name);
    });
    keyName.textContent = data.keys[state.mode][idx()];
    keyShift.textContent = state.t ? (state.t > 0 ? "+" : "−") + Math.abs(state.t) : "";
    keyReset.hidden = state.t === 0;
    document.querySelectorAll("[data-mode]").forEach((b) => {
      b.classList.toggle("on", b.dataset.mode === state.mode);
    });
    hidePop();
  }

  document.querySelectorAll("[data-mode]").forEach((b) => {
    b.addEventListener("click", () => {
      state.mode = b.dataset.mode;
      try { localStorage.setItem(STORE, state.mode); } catch (_) { /* ignore */ }
      apply();
    });
  });

  document.querySelectorAll("[data-step]").forEach((b) => {
    b.addEventListener("click", () => {
      state.t = Math.max(-6, Math.min(6, state.t + +b.dataset.step));
      apply();
    });
  });
  keyReset.addEventListener("click", () => { state.t = 0; apply(); });

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

  chordEls.forEach((el) => {
    el.addEventListener("click", (e) => {
      e.stopPropagation();
      if (popFor === el) hidePop(); else showPop(el);
    });
  });
  document.addEventListener("click", (e) => { if (!pop.contains(e.target)) hidePop(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") hidePop(); });
  window.addEventListener("resize", hidePop);

  // ── Chord panel: highlight every occurrence of the chord ──
  cards.forEach((card) => {
    card.addEventListener("click", () => {
      const i = card.dataset.card;
      const hits = document.querySelectorAll(`.ch[data-i="${i}"]`);
      hits.forEach((el) => el.classList.add("hl"));
      setTimeout(() => hits.forEach((el) => el.classList.remove("hl")), 1400);
    });
  });

  if (state.mode !== "shape") apply();
})();
