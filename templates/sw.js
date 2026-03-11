self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open('ariston-v1').then((cache) => {
      return cache.addAll([
        '/',
        '/static/images/icon-192.png',
        '/static/images/icon-512.png',
        '/manifest.json'
      ]).catch(err => console.log("Service Worker Cache Error:", err));
    })
  );
  self.skipWaiting();
});