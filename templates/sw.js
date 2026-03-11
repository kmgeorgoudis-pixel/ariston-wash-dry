self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open('ariston-v1').then((cache) => {
      return cache.addAll([
        '/',
        '/templates/images/icon-192.png',
        '/templates/images/icon-512.png'
      ]);
    })
  );
});

self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then((response) => {
      return response || fetch(e.request);
    })
  );
});