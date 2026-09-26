// Songbook layout (print page only): place every song on one A5 half or on both halves
// of one A4 sheet — never across sheets — number the pages and fill in the contents.
(() => {
  const MM = 96 / 25.4;                       // CSS px per millimetre
  const style = getComputedStyle(document.documentElement);
  const mm = (name) => parseFloat(style.getPropertyValue(name));
  const halfHeight = (mm("--sheet-h") - 2 * mm("--pad-y")) * MM;
  const sheets = document.querySelector(".sb-sheets");
  const songs = [...document.querySelectorAll(".sb-source .sb-song")];

  let open = null;                            // sheet whose right half is still free
  const pageOf = {};

  function newSheet(cls = "") {
    const sheet = document.createElement("section");
    sheet.className = `sb-sheet ${cls}`.trim();
    sheets.appendChild(sheet);
    return sheet;
  }

  for (const song of songs) {
    let height = song.getBoundingClientRect().height;
    if (height > 2 * halfHeight) {             // too long even for a whole sheet: scale it down
      const zoom = Math.max(0.6, (2 * halfHeight * 0.96) / height);
      song.style.zoom = zoom;
      height *= zoom;
    }
    if (height <= halfHeight) {
      if (open) {                              // fill the free right half
        const half = document.createElement("div");
        half.className = "half";
        half.appendChild(song);
        open.appendChild(half);
        open = null;
      } else {
        const sheet = newSheet();
        const half = document.createElement("div");
        half.className = "half";
        half.appendChild(song);
        sheet.appendChild(half);
        open = sheet;
      }
    } else {                                   // both halves of a fresh sheet; a free right half stays empty
      if (open) open = null;
      const sheet = newSheet("span");
      const flow = document.createElement("div");
      flow.className = "flow";
      flow.appendChild(song);
      sheet.appendChild(flow);
      // Column breaks waste space: shrink until nothing spills into a third column
      let zoom = parseFloat(song.style.zoom || "1");
      while (flow.scrollWidth > flow.clientWidth + 1 && zoom > 0.45) {
        zoom -= 0.03;
        song.style.zoom = zoom;
      }
    }
  }

  // Page numbers: two per sheet (left, right); the title sheet is pages 1-2
  document.querySelectorAll(".sb-sheets .sb-sheet").forEach((sheet, i) => {
    ["left", "right"].forEach((side, j) => {
      const no = document.createElement("div");
      no.className = `page-no ${side}`;
      no.textContent = String(i * 2 + j + 1);
      sheet.appendChild(no);
    });
    sheet.querySelectorAll(".sb-song").forEach((song) => {
      const firstHalf = sheet.classList.contains("span") || song.closest(".half") === sheet.firstElementChild;
      pageOf[song.id] = i * 2 + (firstHalf ? 1 : 2);
    });
  });
  document.querySelectorAll(".sb-toc li[data-song]").forEach((li) => {
    li.querySelector(".toc-page").textContent = pageOf[li.dataset.song] || "";
  });

  document.body.dataset.layout = "done";
})();
