const cacheName = "isbn-app-cache-v1";
const filesToCache = [
  "/",
  "/static/ISBNbookscanner.png",
  "/static/ISBNbookscanner2.png"
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(cacheName).then((cache) => cache.addAll(filesToCache))
  );
});

self.addEventListener("fetch", (e) => {
  e.respondWith(
    caches.match(e.request).then((res) => res || fetch(e.request))
  );
});

