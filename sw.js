// シンプルな Service Worker。
// - アプリ本体(HTML/CSS/JS): cache-first（オフラインでも起動）
// - データJSON: network-first（常に最新を取りに行き、失敗時のみキャッシュ）
const CACHE = "nvda-dash-v1";
const SHELL = [
  "./",
  "./index.html",
  "./styles.css",
  "./app.js",
  "./manifest.webmanifest",
  "./icons/icon-192.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const { request } = e;
  if (request.method !== "GET") return;
  const url = new URL(request.url);

  // データは network-first
  if (url.pathname.includes("/data/")) {
    e.respondWith(
      fetch(request)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(request, copy));
          return res;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // 外部CDN(チャートライブラリ)も stale-while-revalidate 的に
  if (url.origin !== self.location.origin) {
    e.respondWith(
      caches.match(request).then((cached) => {
        const net = fetch(request).then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(request, copy));
          return res;
        }).catch(() => cached);
        return cached || net;
      })
    );
    return;
  }

  // アプリ本体は cache-first
  e.respondWith(caches.match(request).then((cached) => cached || fetch(request)));
});
