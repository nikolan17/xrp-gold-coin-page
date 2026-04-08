/**
 * Affiliate Tracker
 * - Reads ?ref=CODE from the URL
 * - Looks up that affiliate from Supabase
 * - Replaces every .aff-link button/anchor on the page with their store link
 * - Logs pageviews and CTA clicks to Supabase
 */
(function () {

  const CLICKS_KEY = 'xrp_clicks';

  const SB_URL = 'https://wyxlodcpzbzgcwolfzbu.supabase.co';
  const SB_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind5eGxvZGNwemJ6Z2N3b2xmemJ1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU0NTY5MzYsImV4cCI6MjA5MTAzMjkzNn0.lbnIqkDSvFrD5KIu7j5YebWKwKmiBR75BUByc9_VZkQ';

  function sbInsert(table, row) {
    fetch(SB_URL + '/rest/v1/' + table, {
      method: 'POST',
      headers: {
        'apikey': SB_KEY,
        'Authorization': 'Bearer ' + SB_KEY,
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
      },
      body: JSON.stringify(row)
    }).catch(function() {});
  }

  // 1. Read ?ref= from URL
  var code = new URLSearchParams(window.location.search).get('ref');

  // 2. Fetch affiliate from Supabase then wire everything up
  function init(affiliate) {

    // 3. Swap all .aff-link elements to use this affiliate's store link
    if (affiliate && affiliate.store_link) {
      var storeLink = affiliate.store_link;
      if (!/^https?:\/\//i.test(storeLink)) {
        storeLink = 'https://' + storeLink;
      }
      document.querySelectorAll('.aff-link').forEach(function(el) {
        el.href = storeLink;
      });

      // 4. Log CTA clicks
      document.querySelectorAll('.aff-link').forEach(function(el) {
        el.addEventListener('click', function() {
          var page    = window.location.pathname || window.location.href;
          var clickTs = new Date().toISOString();

          try {
            var clicks = JSON.parse(localStorage.getItem(CLICKS_KEY) || '{}');
            clicks[affiliate.code] = (clicks[affiliate.code] || 0) + 1;
            localStorage.setItem(CLICKS_KEY, JSON.stringify(clicks));
          } catch(e) {}

          sbInsert('events', {
            type:           'cta_click',
            affiliate_code: affiliate.code,
            page:           page,
            url:            window.location.href,
            ts:             clickTs
          });
        });
      });
    }

    // 5. Log pageview
    var pvTs   = new Date().toISOString();
    var pvPage = window.location.pathname || window.location.href;

    sbInsert('events', {
      type:           'pageview',
      affiliate_code: affiliate ? affiliate.code : null,
      page:           pvPage,
      url:            window.location.href,
      ts:             pvTs
    });

    // Expose for debugging
    window.AffiliateTracker = {
      code:      code,
      affiliate: affiliate
    };
  }

  console.log('[AffTracker] ref code from URL:', code);

  if (code) {
    var url = SB_URL + '/rest/v1/affiliates?code=eq.' + encodeURIComponent(code.toUpperCase()) + '&limit=1';
    console.log('[AffTracker] fetching:', url);
    // Fetch matching affiliate from Supabase
    fetch(url, {
      headers: { 'apikey': SB_KEY, 'Authorization': 'Bearer ' + SB_KEY }
    })
    .then(function(res) {
      console.log('[AffTracker] response status:', res.status);
      return res.ok ? res.json() : [];
    })
    .then(function(rows) {
      console.log('[AffTracker] rows returned:', rows);
      init(rows.length ? rows[0] : null);
    })
    .catch(function(err) {
      console.error('[AffTracker] fetch error:', err);
      init(null);
    });
  } else {
    console.log('[AffTracker] no ref in URL — running without affiliate');
    init(null);
  }

})();
