// Service worker Paris ASF : affiche les notifications push, sans mise en cache.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));

self.addEventListener("push", e => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (_) { d = { body: e.data && e.data.text() }; }
  e.waitUntil(self.registration.showNotification(d.title || "Paris ASF", {
    body: d.body || "",
    icon: "icon-192.png",
    badge: "icon-192.png",
    data: { url: d.url || "./" },
  }));
});

// Un clic ouvre l'app sur le match concerné (lien ./?match=<id>) :
// si l'app est déjà ouverte on lui envoie un message, sinon on ouvre une nouvelle fenêtre.
self.addEventListener("notificationclick", e => {
  e.notification.close();
  const url = new URL((e.notification.data && e.notification.data.url) || "./", self.registration.scope).href;
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(list => {
    for (const c of list) {
      if (c.url.startsWith(self.registration.scope) && "focus" in c) {
        c.postMessage({ type: "navigate", url });
        return c.focus();
      }
    }
    return self.clients.openWindow(url);
  }));
});
