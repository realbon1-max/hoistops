// HOIST OPS 仙台版 service worker: keeps the app itself available offline.
// Map tiles are NOT cached here (the app's own "地図を端末に保存" handles that on request).
const VERSION = 'hoistops-sendai-20261026135044';
const APP = ['./', './index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png', './icon-maskable-512.png', './apple-touch-icon.png'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(APP)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== VERSION).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const u = new URL(e.request.url);
  if (e.request.method !== 'GET' || u.origin !== location.origin) return;   // GSI tiles etc. go straight to the network
  // app files: network first (to pick up updates), fall back to the cached copy when offline
  e.respondWith(fetch(e.request, {cache: 'no-cache'}).then(r => {
    if (r && r.ok) { const cp = r.clone(); caches.open(VERSION).then(c => c.put(e.request, cp)); }
    return r;
  }).catch(() => caches.match(e.request, {ignoreSearch: true}).then(m => m || caches.match('./index.html'))));
});
