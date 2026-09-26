// Home and album pages: filter songs by the language they are sung in and by album;
// remember the chosen UI language for the root redirect.
(function () {
  const save = (k, v) => { try { localStorage.setItem(k, v); } catch (_) { /* storage unavailable */ } };
  document.querySelectorAll("[data-ui-lang]").forEach((a) => {
    a.addEventListener("click", () => save("songbook.ui", a.dataset.uiLang));
  });

  const songItems = Array.from(document.querySelectorAll("#song-list li[data-sung]"));
  const sungFilter = document.getElementById("sung-filter");
  const albumFilter = document.getElementById("album-filter");
  if (!sungFilter && !albumFilter) return;

  let sung = "all";
  let album = "all";

  function apply() {
    songItems.forEach((li) => {
      const sungOk = sung === "all" || li.dataset.sung.split(" ").includes(sung);
      const albumOk = album === "all" || li.dataset.albumId === album;
      li.style.display = sungOk && albumOk ? "" : "none";
    });
    if (sungFilter) {
      sungFilter.querySelectorAll("[data-sung]").forEach((b) => b.classList.toggle("active", b.dataset.sung === sung));
    }
    if (albumFilter) {
      albumFilter.querySelectorAll("[data-album]").forEach((b) => b.classList.toggle("active", b.dataset.album === album));
    }
  }

  if (sungFilter) {
    sungFilter.querySelectorAll("[data-sung]").forEach((b) => {
      b.addEventListener("click", () => { sung = b.dataset.sung; apply(); });
    });
  }
  if (albumFilter) {
    albumFilter.querySelectorAll("[data-album]").forEach((b) => {
      b.addEventListener("click", () => { album = b.dataset.album; apply(); });
    });
  }

  // Old deep links: ?album=<id> filters the home page to that album
  const param = new URLSearchParams(location.search).get("album");
  if (param && albumFilter && albumFilter.querySelector(`[data-album="${CSS.escape(param)}"]`)) {
    album = param;
    apply();
  }
})();
