let allMovies = [];

const version = new Date().getTime();

// Fetch mit Timestamp gegen den Cache
fetch(`library.json?v=${new Date().getTime()}`)
  .then(r => r.json())
  .then(data => {
    // 1. Im JS nach ID sortieren (Größte ID = Neuester Film)
    allMovies = data.movies.sort((a, b) => b.id - a.id);

    renderCategories();

    // 2. Die 12 neuesten für die Startansicht
    render(allMovies.slice(0, 12), "Neu hinzugefuegt");
  });

function renderCategories() {
  const bar = document.getElementById("category-bar");
  bar.innerHTML = "";

  // Startseiten-Button
  const homeBtn = document.createElement("button");
  homeBtn.textContent = "Startseite";
  homeBtn.onclick = () => render(allMovies.slice(0, 12), "Neu hinzugefuegt");
  bar.appendChild(homeBtn);

  // Kategorien sammeln (alphabetisch für das Menü)
  const categories = [...new Set(allMovies.map(m => m.category))].sort();

  categories.forEach(cat => {
    const btn = document.createElement("button");
    btn.textContent = cat;
    btn.onclick = () => {
      // Filtert die bereits sortierten allMovies
      const filtered = allMovies.filter(m => m.category === cat);
      render(filtered, cat);
    };
    bar.appendChild(btn);
  });
}

function render(movies, titleText) {
  const content = document.getElementById("content");
  content.innerHTML = ""; // Alten Inhalt löschen

  const h2 = document.createElement("h2");
  h2.textContent = titleText;
  content.appendChild(h2);

  const grid = document.createElement("div");
  grid.className = "grid";

  movies.forEach(film => {
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

    // Slider-Logik
    let timer = null;
    function showSlide(n) {
      currentSlide = (n + thumbs.length) % thumbs.length;
      img.src = thumbs[currentSlide];
    }

    card.addEventListener("click", () => playVideo(film.file));

    card.addEventListener("mouseenter", () => {
      timer = setInterval(() => showSlide(currentSlide + 1), 600);
    });

    card.addEventListener("mouseleave", () => {
      clearInterval(timer);
      currentSlide = Math.floor(thumbs.length / 2);
      img.src = thumbs[currentSlide];
    });
  });

  content.appendChild(grid);
}

function playVideo(file) {
  document.querySelectorAll("video").forEach(v => { if (v.id !== "main-video") v.pause(); });
  let video = document.getElementById("main-video");
  if (!video) {
    const playerDiv = document.getElementById("video-player");
    video = document.createElement("video");
    video.id = "main-video";
    video.controls = video.autoplay = true;
    video.style.width = "100%";
    playerDiv.appendChild(video);
  }
  video.src = file;
  video.currentTime = 0;
  video.play().catch(e => console.warn(e));
  video.scrollIntoView({ behavior: "smooth", block: "start" });
}

function formatDuration(sec) {
  if (!sec) return "";
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  return h > 0 ? `${h}h ${m}min` : `${m} min`;
}
