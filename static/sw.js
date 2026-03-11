// Το όνομα της μνήμης (cache) της εφαρμογής σου
const CACHE_NAME = 'ariston-cache-v1';

// Αρχεία που θέλουμε να αποθηκεύονται για γρήγορο φόρτωμα
const urlsToCache = [
  '/',
  '/static/ai/ai.css'
];

// Εγκατάσταση του Service Worker
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache);
      })
  );
});

// Λειτουργία Fetch (απαραίτητη για να θεωρηθεί PWA)
self.addEventListener('fetch', event => {
  event.respondWith(
    fetch(event.request).catch(() => {
      return caches.match(event.request);
    })
  );
});