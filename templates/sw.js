self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open('ariston-v1').then((cache) => {
      return cache.addAll([
        '/',
        '/images/icon-192.png',
        '/images/icon-512.png',
        '/manifest.json'
      ]).catch(err => console.log("Service Worker Cache Error:", err));
    })
  );
  self.skipWaiting();
});

self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then((response) => {
      return response || fetch(e.request);
    })
  );
});