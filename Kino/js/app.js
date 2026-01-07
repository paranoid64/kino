fetch("library.json")
  .then(r => r.json())
  .then(data => render(data.movies));

function playVideo(file) {
  // Alle anderen Videos stoppen (außer dem Player)
  document.querySelectorAll("video").forEach(v => {
    if (v.id !== "main-video") v.pause();
  });

  // Hole den bestehenden Player
  let video = document.getElementById("main-video");

  // Wenn Player noch nicht existiert, erstellen
  if (!video) {
    const playerDiv = document.getElementById("video-player");
    video = document.createElement("video");
    video.id = "main-video";
    video.controls = true;
    video.autoplay = true;
    video.style.width = "100%";

    // Fehler abfangen
    video.onerror = (e) =>
      console.warn("Video konnte nicht geladen werden oder wurde abgebrochen", e);

    playerDiv.appendChild(video);
  }

  // Neues Video laden
  video.src = file;
  video.currentTime = 0;
  video.play().catch((e) => console.warn("Play fehlgeschlagen:", e));

  // Scrollen, damit Video sichtbar ist
  video.scrollIntoView({ behavior: "smooth", block: "start" });
}

function formatDuration(sec) {
  if (!sec) return "";
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  return h > 0 ? `${h}h ${m}min` : `${m} min`;
}

function render(movies) {
  const content = document.getElementById("content");

  // Alle Kategorien sammeln
  const categories = {};
  movies.forEach(m => {
    if (!categories[m.category]) categories[m.category] = [];
    categories[m.category].push(m);
  });

  // Für jede Kategorie ein Grid bauen
  for (const [catName, films] of Object.entries(categories)) {
    const h2 = document.createElement("h2");
    h2.textContent = catName;
    content.appendChild(h2);

    const grid = document.createElement("div");
    grid.className = "grid";

    films.forEach(film => {
      const card = document.createElement("div");
      card.className = "card";

      const img = document.createElement("img");
      img.className = "poster";

      const thumbs = film.thumbnails;
      let currentSlide = Math.floor(thumbs.length / 2);
      img.src = thumbs[currentSlide];

      const title = document.createElement("h3");
      title.textContent = film.title;

    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = formatDuration(film.duration);

    card.appendChild(meta);

      card.appendChild(img);
      card.appendChild(title);
      grid.appendChild(card);

      // --- Slider pro Film ---
      let timer = null;

      function showSlide(n) {
        currentSlide = (n + thumbs.length) % thumbs.length;
        img.src = thumbs[currentSlide];
      }

      // --- Video-Click ---
      card.addEventListener("click", () => playVideo(film.file));

      // Slider starten/stoppen
      card.addEventListener("mouseenter", () => {
        timer = setInterval(() => {
          showSlide(currentSlide + 1);
        }, 600);
      });

      card.addEventListener("mouseleave", () => {
        clearInterval(timer);
        timer = null;
        currentSlide = Math.floor(thumbs.length / 2);
        img.src = thumbs[currentSlide];
      });

    });

    content.appendChild(grid);
  }
}
