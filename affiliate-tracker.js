/**
 * Affiliate Tracker (robust)
 * - Reads ?ref=CODE from URL (or remembers last one via localStorage)
 * - Fetches affiliate from Supabase (with short localStorage cache)
 * - Rewrites every .aff-link to the affiliate's store_link
 * - Intercepts clicks BEFORE fetch resolves — queues the redirect so no
 *   click is ever lost to a race condition
 * - Falls back to appending ?ref=CODE to the original href if the
 *   affiliate row or store_link is missing, so attribution still survives
 * - Uses event delegation so dynamically-added buttons also work
 */
(function () {
  'use strict';

  var CLICKS_KEY = 'xrp_clicks';
  var REF_KEY    = 'xrp_ref';        // sticky ref code across pages/reloads
  var AFF_KEY    = 'xrp_aff_cache';  // cached affiliate row (short TTL)
  var CACHE_TTL  = 10 * 60 * 1000;   // 10 minutes

  var SB_URL = 'https://wyxlodcpzbzgcwolfzbu.supabase.co';
  var SB_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind5eGxvZGNwemJ6Z2N3b2xmemJ1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU0NTY5MzYsImV4cCI6MjA5MTAzMjkzNn0.lbnIqkDSvFrD5KIu7j5YebWKwKmiBR75BUByc9_VZkQ';

  function sbHeaders() {
    return {
      'apikey':        SB_KEY,
      'Authorization': 'Bearer ' + SB_KEY,
      'Content-Type':  'application/json'
    };
  }

  function sbInsert(table, row) {
    try {
      fetch(SB_URL + '/rest/v1/' + table, {
        method:    'POST',
        headers:   Object.assign({ 'Prefer': 'return=minimal' }, sbHeaders()),
        body:      JSON.stringify(row),
        keepalive: true // fires even if the page is navigating away
      }).catch(function () {});
    } catch (e) {}
  }

  // ---- ref code resolution --------------------------------------------------
  // 1. from ?ref= in URL (fresh click through an affiliate link)
  // 2. otherwise from localStorage (sticky — survives internal navigation)
  var urlCode = null;
  try {
    urlCode = new URLSearchParams(window.location.search).get('ref');
  } catch (e) {}

  if (urlCode) {
    urlCode = urlCode.toUpperCase();
    try { localStorage.setItem(REF_KEY, urlCode); } catch (e) {}
  }

  var code = urlCode;
  if (!code) {
    try { code = localStorage.getItem(REF_KEY); } catch (e) {}
  }
  if (code) code = code.toUpperCase();

  // ---- affiliate state (Promise so clicks can await it) --------------------
  var affiliate = null;
  var affReady  = false;

  function loadCachedAff() {
    try {
      var raw = localStorage.getItem(AFF_KEY);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      if (!parsed || parsed.code !== code) return null;
      if (Date.now() - parsed.ts > CACHE_TTL) return null;
      return parsed.data;
    } catch (e) { return null; }
  }

  function saveCachedAff(data) {
    try {
      localStorage.setItem(AFF_KEY, JSON.stringify({
        code: code, ts: Date.now(), data: data
      }));
    } catch (e) {}
  }

  function fetchAffiliate() {
    if (!code) return Promise.resolve(null);

    var cached = loadCachedAff();
    if (cached) return Promise.resolve(cached);

    var url = SB_URL + '/rest/v1/affiliates?code=eq.' +
              encodeURIComponent(code) + '&limit=1';

    return fetch(url, { headers: sbHeaders() })
      .then(function (res) { return res.ok ? res.json() : []; })
      .then(function (rows) {
        var row = rows.length ? rows[0] : null;
        if (row) saveCachedAff(row);
        return row;
      })
      .catch(function () { return null; });
  }

  var affPromise = fetchAffiliate().then(function (row) {
    affiliate = row;
    affReady  = true;
    applyAffiliateToButtons();
    return row;
  });

  // ---- URL helpers ---------------------------------------------------------
  function normalizeUrl(u) {
    if (!u) return u;
    if (!/^https?:\/\//i.test(u)) u = 'https://' + u;
    return u;
  }

  function appendRef(base, refCode) {
    if (!base || !refCode) return base;
    try {
      var u = new URL(base, window.location.origin);
      u.searchParams.set('ref', refCode);
      return u.toString();
    } catch (e) {
      var sep = base.indexOf('?') >= 0 ? '&' : '?';
      return base + sep + 'ref=' + encodeURIComponent(refCode);
    }
  }

  function originalHref(el) {
    var orig = el.getAttribute('data-orig-href');
    if (orig == null) {
      orig = el.getAttribute('href') || '';
      el.setAttribute('data-orig-href', orig);
    }
    return orig;
  }

  function resolveDestination(el) {
    var base = originalHref(el);
    // 1. Affiliate has a real store_link → use it
    if (affiliate && affiliate.store_link) {
      return normalizeUrl(affiliate.store_link);
    }
    // 2. We have a ref code but no store_link → append ?ref=CODE to default
    if (code && base) {
      return appendRef(base, code);
    }
    // 3. No ref at all → default href
    return base;
  }

  function applyAffiliateToButtons() {
    var els = document.querySelectorAll('.aff-link');
    for (var i = 0; i < els.length; i++) {
      originalHref(els[i]); // snapshot original before we overwrite
      els[i].href = resolveDestination(els[i]);
    }
  }

  // Do an early swap (adds ?ref=CODE fallback) as soon as the DOM is ready,
  // even before the Supabase fetch resolves.
  function earlySwap() { applyAffiliateToButtons(); }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', earlySwap);
  } else {
    earlySwap();
  }

  // ---- click handling (event delegation, capture phase) --------------------
  function logClick(dest) {
    var page = window.location.pathname || window.location.href;
    var ts   = new Date().toISOString();
    var key  = (affiliate && affiliate.code) || code || null;

    try {
      var clicks = JSON.parse(localStorage.getItem(CLICKS_KEY) || '{}');
      var localKey = key || '_anon';
      clicks[localKey] = (clicks[localKey] || 0) + 1;
      localStorage.setItem(CLICKS_KEY, JSON.stringify(clicks));
    } catch (e) {}

    sbInsert('events', {
      type:           'cta_click',
      affiliate_code: key,
      page:           page,
      url:            dest || window.location.href,
      ts:             ts
    });
  }

  document.addEventListener('click', function (ev) {
    var el = ev.target && ev.target.closest && ev.target.closest('.aff-link');
    if (!el) return;
    if (ev.defaultPrevented) return;

    // Let modified clicks (cmd/ctrl/shift/middle) behave natively
    if (ev.button !== 0) return;
    if (ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;

    if (affReady) {
      // Fetch done — href is already correct. Just log and let browser navigate.
      logClick(el.href);
      return;
    }

    // Fetch not done yet — block navigation, wait, then redirect.
    ev.preventDefault();
    var target = (el.getAttribute('target') || '').toLowerCase();

    // Open placeholder tab synchronously to keep popup-blocker happy
    var newWin = null;
    if (target === '_blank') {
      try { newWin = window.open('about:blank', '_blank'); } catch (e) {}
    }

    affPromise.then(function () {
      var dest = resolveDestination(el);
      el.href  = dest;
      logClick(dest);

      if (newWin && !newWin.closed) {
        try { newWin.location.href = dest; return; } catch (e) {}
      }
      window.location.href = dest;
    });
  }, true);

  // ---- pageview ------------------------------------------------------------
  affPromise.then(function () {
    sbInsert('events', {
      type:           'pageview',
      affiliate_code: (affiliate && affiliate.code) || code || null,
      page:           window.location.pathname || window.location.href,
      url:            window.location.href,
      ts:             new Date().toISOString()
    });

    window.AffiliateTracker = {
      code:      code,
      affiliate: affiliate,
      ready:     true
    };
  });

  console.log('[AffTracker] ref:', code || '(none)');
})();
