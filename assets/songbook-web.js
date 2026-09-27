// Web songbook: shows one song at a time (#song-id in the URL; no element has that id, so the page never jumps), fits it into the screen
// like its PDF sheet — two columns, three if long, smaller if still too long — and
// toggles the album menu. The music (chords, diagrams) is precomputed by the build.
(() => {
  const STORE = "songbook.nav";
  const load = () => { try { return localStorage.getItem(STORE); } catch (_) { return null; } };
  const save = (v) => { try { localStorage.setItem(STORE, v); } catch (_) { /* storage unavailable */ } };

  const body = document.body;
  const songs = [...document.querySelectorAll(".wsb-song")];
  const links = [...document.querySelectorAll(".wsb-nav a[data-song]")];
  const order = links.map((a) => a.dataset.song);
  const menu = document.getElementById("wsb-menu");
  const narrow = () => matchMedia("(max-width: 760px)").matches;
  if (!songs.length) return;
  let current = null;

  // Two columns; three if the song does not fit; then scale it down until it does
  function fit(song) {
    const flow = song.querySelector(".wsb-flow");
    const content = song.querySelector(".wsb-content");
    flow.classList.remove("cols-3");
    content.style.zoom = "";
    if (narrow()) return;
    const overflows = () => flow.scrollWidth > flow.clientWidth + 1;
    if (overflows()) flow.classList.add("cols-3");
    let zoom = 1;
    while (overflows() && zoom > 0.5) {
      zoom -= 0.04;
      content.style.zoom = zoom;
    }
  }

  function show(id, push = true) {
    const song = songs.find((s) => s.dataset.song === id) || songs.find((s) => s.dataset.song === order[0]) || songs[0];
    songs.forEach((s) => { s.hidden = s !== song; });
    links.forEach((a) => a.classList.toggle("on", a.dataset.song === song.dataset.song));
    current = song;
    fit(song);
    if (push && location.hash.slice(1) !== song.dataset.song) history.replaceState(null, "", `#${song.dataset.song}`);
    if (narrow()) {
      setNav(false);
      window.scrollTo(0, 0);
    } else {
      const active = links.find((a) => a.dataset.song === song.dataset.song);
      if (active) active.scrollIntoView({ block: "nearest" });   // inside the menu only: the page never scrolls
    }
  }

  function step(delta) {
    const i = order.indexOf(current.dataset.song);
    const next = order[(i + delta + order.length) % order.length];
    show(next);
  }

  function setNav(visible) {
    body.classList.toggle("nav-hidden", !visible);
    menu.setAttribute("aria-expanded", String(visible));
    if (current) fit(current);
  }

  menu.addEventListener("click", () => {
    const visible = body.classList.contains("nav-hidden");
    setNav(visible);
    if (!narrow()) save(visible ? "1" : "0");
  });
  document.getElementById("wsb-prev").addEventListener("click", () => step(-1));
  document.getElementById("wsb-next").addEventListener("click", () => step(1));
  links.forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); show(a.dataset.song); }));
  document.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") step(-1);
    if (e.key === "ArrowRight") step(1);
  });
  window.addEventListener("hashchange", () => show(location.hash.slice(1), false));
  let timer;
  window.addEventListener("resize", () => { clearTimeout(timer); timer = setTimeout(() => current && fit(current), 120); });
  document.querySelectorAll("[data-ui-lang]").forEach((a) => {
    a.addEventListener("click", () => { a.href = a.href.split("#")[0] + location.hash; });
  });

  setNav(narrow() ? false : load() !== "0");
  show(location.hash.slice(1), false);
  // Web fonts change line heights: fit again once they are in
  if (document.fonts) document.fonts.ready.then(() => current && fit(current));
})();
