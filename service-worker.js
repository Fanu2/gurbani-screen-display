const CACHE_NAME = "gurbani-cache-v1";
const urlsToCache = [
  "/",
  "/index.html",
  "/assets/fonts/AnmolLipiSG.ttf",
  "/assets/fonts/GurbaniAkharHeavyTrue.ttf",
  "/assets/css/bundle.css",
  "/assets/js/app.js"
];

// Install service worker
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(urlsToCache);
    })
  );
});

// Fetch requests
self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});

// Update cache
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) =>
      Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            return caches.delete(cache);
          }
        })
      )
    )
  );
});
