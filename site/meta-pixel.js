// Meta Pixel loader — shared across site.
// Reads window.META_PIXEL_ID. If it's missing or still the build-time placeholder,
// the loader no-ops so the page works fine before the Pixel ID is provisioned.
//
// Usage in each page <head>:
//   <script>window.META_PIXEL_ID = '__META_PIXEL_ID__';</script>
//   <script src="/meta-pixel.js"></script>
//
// On Netlify deploy, replace __META_PIXEL_ID__ with the real Pixel ID before
// publishing (or post-deploy via a one-line find/replace + redeploy).

(function () {
  var id = window.META_PIXEL_ID;
  if (!id || /^__/.test(id)) {
    // Provide harmless stubs so call sites can still invoke them.
    window.fbq = window.fbq || function () {};
    window.trackLead = function () {};
    return;
  }

  // Standard Meta Pixel base code
  !function (f, b, e, v, n, t, s) {
    if (f.fbq) return;
    n = f.fbq = function () {
      n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments);
    };
    if (!f._fbq) f._fbq = n;
    n.push = n; n.loaded = !0; n.version = '2.0'; n.queue = [];
    t = b.createElement(e); t.async = !0; t.src = v;
    s = b.getElementsByTagName(e)[0]; s.parentNode.insertBefore(t, s);
  }(window, document, 'script', 'https://connect.facebook.net/en_US/fbevents.js');

  window.fbq('init', id);
  window.fbq('track', 'PageView');

  // Lead helper — pass an eventID to dedup against server-side Conversions API.
  window.trackLead = function (eventID, custom) {
    try {
      window.fbq('track', 'Lead', custom || {}, eventID ? { eventID: eventID } : undefined);
    } catch (_) {}
  };
})();
