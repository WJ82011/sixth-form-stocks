/* Shared public-host detection for Vercel / tmp.now / production portfolio URL.
 * Loaded before cloud-host.js. Safe on Mac localhost (no auto demo). */
(function (root) {
  'use strict';

  function isLoopbackHost(hostname) {
    const host = String(hostname || '').toLowerCase();
    return host === 'localhost' || host === '127.0.0.1' || host === '[::1]';
  }

  function isPublicPortfolioHost(hostname) {
    const host = String(hostname || '').toLowerCase();
    if (!host || isLoopbackHost(host)) return false;
    // Production project host + anonymous Vercel preview / legacy now hosts.
    if (host.endsWith('.vercel.app')) return true;
    if (host.endsWith('.tmp.now')) return true;
    if (host.endsWith('.now.sh')) return true;
    // Project name in hostname (custom domain or preview alias).
    if (host.includes('sixth-form-stocks')) return true;
    return false;
  }

  /**
   * Resolve whether the static public portfolio (snapshot) mode should run.
   * Rules:
   * - Auto-on for vercel.app / tmp.now / now.sh / sixth-form-stocks hosts (no ?demo=1).
   * - ?demo=1 / ?demo=cloud force-on (static local servers for admissions checks).
   * - Port 8765 on loopback = Mac server.py → never auto demo.
   * - ?demo=local only forces Mac-shaped static on loopback; ignored on public hosts.
   */
  function resolvePublicHostMode(loc) {
    const locationLike = loc || {};
    const host = String(locationLike.hostname || '');
    const port = String(locationLike.port || '');
    let search = String(locationLike.search || '');
    if (search.startsWith('?')) search = search.slice(1);
    const params = new URLSearchParams(search);
    const loopback = isLoopbackHost(host);
    const localPython = loopback && port === '8765';
    const forceDemo = params.get('demo') === '1' || params.get('demo') === 'cloud';
    const wantsLocal = params.get('demo') === 'local';
    // Never let ?demo=local disable the admissions URL on a public host.
    const forceLocal = wantsLocal && loopback && !isPublicPortfolioHost(host);
    const publicHost = isPublicPortfolioHost(host);
    const demoMode = (forceDemo || publicHost) && !localPython && !forceLocal;
    return {
      demoMode,
      publicHost,
      localPython,
      forceDemo,
      forceLocal,
      wantsLocal,
      loopback,
      host,
      port,
    };
  }

  const api = {
    resolve: resolvePublicHostMode,
    isPublicPortfolioHost,
    isLoopbackHost,
  };

  root.MarketDeskPublicHost = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
