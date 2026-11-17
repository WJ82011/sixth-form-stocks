/* Public demo: replace contradictory Mac/local copy and tune peripheral chrome. */
(function () {
  'use strict';

  function isDemo() {
    if (document.documentElement.dataset.demoMode === 'true') return true;
    if (window.MarketDeskHost?.demoMode) return true;
    return Boolean(window.MarketDeskPublicHost?.resolve?.(location)?.demoMode);
  }

  const EXACT = new Map([
    ['.desk-local', 'Public portfolio · labelled snapshot'],
    ['#preferences-state', 'DEMO · BROWSER ONLY'],
    ['#v3-global-status', null],
    ['#overview-chart-source', 'BUNDLED DEMO OBSERVATIONS'],
    ['#view-learning .page-title > div > p', 'Sample training results from the bundle. Live collection needs server.py on your Mac.'],
    // Markets eyebrow is owned by demo-wiring assertDemoChrome (LIVE vs SNAPSHOT).
    ['#view-markets .page-title .eyebrow', null],
    ['#view-tape .page-title .eyebrow', 'PUBLIC PORTFOLIO / BUNDLED TRADES'],
    ['#view-tape .page-title > div > p', 'Replay labelled sample trades from the demo bundle. Live Finnhub sockets run on your Mac.'],
    ['#view-forecast .page-title .eyebrow', 'PRICE ESTIMATES / DEMO DATA'],
    ['#view-forecast .forecast-banner p', 'This public portfolio uses bundled daily closes. Calculate shows a labelled learned or withheld path — no Massive key on this host.'],
    ['#view-reports .page-title .eyebrow', 'INVESTMENT RESEARCH / DEMO BROWSER'],
    ['#view-research .page-title .eyebrow', 'YOUR RESEARCH / PUBLIC PORTFOLIO'],
    ['#view-portfolio .page-title .eyebrow', 'PRACTICE / PUBLIC PORTFOLIO'],
    ['#view-screener .v3-card .desk-eyebrow', 'DEMO TTM RATIOS / ACCOUNTS SAMPLE'],
    ['#view-intelligence .ai-heading p', 'Sample assistant chrome on this host. Full local AI runs with server.py on your Mac.'],
  ]);

  const SUBTREE_PHRASES = [
    ['Private workspace · saved on this Mac', 'Public portfolio · labelled snapshot'],
    ['Private research workspace ·', 'Public portfolio ·'],
    [
      'Private research projects · saved on this Mac and included in your full research backup.',
      'Demo sample research · labelled synthetic project in this browser.',
    ],
    ['Private research projects · saved on this Mac', 'Demo sample research · labelled synthetic'],
    [
      'Your saved V3 records are ready. All trades are hypothetical.',
      'Demo sample ledger ready. All trades are hypothetical · labelled synthetic.',
    ],
    ['Opening or rereading this view only reads local snapshots.', 'Opening or rereading this view only reads the public portfolio snapshot.'],
    ['Alerts are stored in the private price database on this Mac', 'Alerts on this public host stay in your browser only'],
    ['Drafts remain on this Mac, with a private local backup.', 'Drafts on this public host stay in your browser only.'],
    ['Practice trades are saved on this Mac and included in your private research backup.', 'Practice trades on this public host stay in your browser only.'],
    ['Excerpts stay on this Mac and are used as unverified source material', 'Excerpts stay in this browser on the public host'],
    ['A real language model running on your Mac', 'Sample assistant chrome on this public host'],
    ['saved on this Mac', 'in this demo bundle'],
    ['on this Mac', 'on the public portfolio host'],
    ['this Mac has saved', 'the demo bundle includes'],
    ['Saved data stays on this Mac.', 'Saved data on the public portfolio stays in your browser only.'],
    ['while the Mac is awake', 'while server.py runs on your Mac'],
    ['Enable Background at Login.command in the Mac folder.', 'On your Mac, use Enable Background at Login.command for overnight collection.'],
    ['Nothing is collected while this Mac is off.', 'This public host does not run overnight collectors.'],
    ['Nothing is collected while your Mac is off.', 'This public host does not run overnight collectors.'],
    ['No data is collected while your Mac is off.', 'This public host does not run overnight collectors.'],
    ['Files saved on this Mac', 'Files in the full Mac workspace'],
    ['BACKED UP LOCALLY', 'DEMO · BROWSER ONLY'],
    ['Settings are saved automatically on this Mac.', 'Settings are saved in your browser on this demo.'],
    ['backed up on this Mac', 'saved in your browser on this demo'],
    ['LOCAL RESEARCH TERMINAL', 'PUBLIC PORTFOLIO'],
    ['LOCAL WORKSTATION', 'PUBLIC PORTFOLIO'],
    ['FEED OFFLINE', 'SNAPSHOT · DEMO DATA'],
    ['LIVE TERMINAL / FINNHUB', 'PUBLIC PORTFOLIO / BUNDLED QUOTES'],
    ['LOCALLY RECORDED FINNHUB OBSERVATIONS', 'BUNDLED DEMO OBSERVATIONS'],
    ['RECORDED FINNHUB OBSERVATIONS', 'BUNDLED DEMO OBSERVATIONS'],
    ['RECORDED FINNHUB TRADES', 'BUNDLED DEMO TRADES'],
    ['Add a Massive key for US daily history on Stocks Basic. Finnhub history depends on your plan.', 'Bundled daily closes only on this host. Try TTWO for a shown path or AMD for a withheld example.'],
    ['Check your Massive plan and request limit in Settings.', 'No provider key is used here — pick TTWO or AMD from the demo bundle.'],
    ['See the trades Finnhub sends to your app.', 'Replay labelled sample trades from the demo bundle.'],
    ['Uses data saved on this Mac.', 'Uses the labelled demo snapshot on this host.'],
    ['SAVED ON YOUR MAC', 'SAVED IN THIS BROWSER'],
    ['PRIVATE & LOCAL', 'DEMO · BROWSER ONLY'],
    ['Connecting to Finnhub…', 'Sample watchlist quotes from the bundled snapshot'],
    ['Finnhub market feed', 'Public portfolio · bundled snapshot · not a live Finnhub feed'],
    ['Waiting for Finnhub trades. Prices are never made up.', 'Bundled demo trades · not a live Finnhub socket.'],
    ['Watchlist prices will appear here when Finnhub supplies them.', 'Sample watchlist quotes from the bundled snapshot.'],
    ['search for a stock on Finnhub', 'search the bundled demo directory'],
    ['with the same Finnhub data and research tools', 'with the same bundled demo tools'],
    ['Your browser needs this key to receive Finnhub’s live feed.', 'Provider keys are not used on this public portfolio host.'],
  ];

  const LEARNING_CARD =
    'Background collection is part of the Mac install. This public demo shows bundled prices and charts only — no overnight collector runs here.';

  let v3StatusStamp = '';
  let polishing = false;
  let polishTimer = 0;

  function replaceInTextNode(node) {
    let text = node.textContent;
    let changed = false;
    for (const [from, to] of SUBTREE_PHRASES) {
      if (text.includes(from)) {
        text = text.split(from).join(to);
        changed = true;
      }
    }
    if (changed) node.textContent = text;
  }

  function polishTextRoots() {
    for (const [selector, value] of EXACT) {
      const el = document.querySelector(selector);
      if (!el) continue;
      if (value !== null) {
        if (el.textContent !== value) el.textContent = value;
        continue;
      }
      if (selector === '#view-markets .page-title .eyebrow') {
        const live = window.MarketDeskHost?.quoteSource === 'live';
        const next = live
          ? 'PUBLIC PORTFOLIO / LIVE QUOTES (CACHED)'
          : 'PUBLIC PORTFOLIO / SNAPSHOT QUOTES';
        if (el.textContent !== next) el.textContent = next;
        continue;
      }
      if (
        selector === '#v3-global-status' &&
        (el.textContent.startsWith('Private research workspace') || el.textContent.startsWith('Portfolio demo'))
      ) {
        const date = new Date().toLocaleDateString('en-GB', {
          weekday: 'long',
          day: 'numeric',
          month: 'long',
        });
        const next = 'Public portfolio · ' + date + ' · source dates stay visible.';
        if (el.textContent !== next) el.textContent = next;
      }
    }
    const learningCard = document.querySelector('#view-learning article.v3-card');
    if (learningCard) {
      const paras = learningCard.querySelectorAll('p');
      if (paras[0] && !paras[0].dataset.demoPolish) {
        paras[0].dataset.demoPolish = '1';
        paras[0].textContent = LEARNING_CARD;
      }
    }
    const roots = document.querySelectorAll(
      '#view-overview, #view-home, #view-learning, #view-settings, #view-alerts, #view-reports, #view-markets, #view-tape, #view-intelligence, #view-news, #view-sources, #view-research, #view-portfolio, #view-forecast, #view-screener, #p32-projects, #v3-portfolio'
    );
    for (const root of roots) {
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      let n;
      while ((n = walker.nextNode())) {
        if (!n.textContent.trim() || n.parentElement?.closest('script, style')) continue;
        if (n.parentElement?.closest('#showcase61-stage, #showcase61-log, #diag-message')) continue;
        replaceInTextNode(n);
      }
    }
  }

  function polishTapeChrome() {
    const pill = document.getElementById('tape-feed-pill');
    if (pill && document.querySelector('.view.active')?.id === 'view-tape') {
      pill.textContent = '● DEMO RECORDING · BUNDLED TRADES';
    }
    const reco = document.getElementById('tape-reconnect');
    if (reco && !reco.dataset.demoPolish) {
      reco.dataset.demoPolish = '1';
      reco.title = 'Replay bundled demo trades (not a live Finnhub socket).';
    }
  }

  function deskStub() {
    const stub = {
      open() {},
      selected() {},
      memory() {},
      reload() {},
      historyChanged() {},
      chartMount() {
        return document.getElementById('desk-chart-mount');
      },
      revealSelected() {},
    };
    if (typeof window.Desk === 'undefined') {
      window.Desk = stub;
      return;
    }
    for (const key of Object.keys(stub)) {
      if (typeof window.Desk[key] !== 'function') window.Desk[key] = stub[key];
    }
  }

  function polishTapeNav() {
    document.querySelectorAll('.nav-btn[data-view="tape"] span:nth-child(2)').forEach((el) => {
      if (el.textContent.trim() === 'Live Tape') el.textContent = 'Demo Tape';
    });
  }

  function onViewChange() {
    if (!isDemo() || polishing) return;
    polishing = true;
    try {
      polishTextRoots();
      polishTapeChrome();
      polishTapeNav();
    } finally {
      polishing = false;
    }
  }

  function schedulePolish() {
    if (!isDemo() || polishing) return;
    clearTimeout(polishTimer);
    polishTimer = setTimeout(onViewChange, 80);
  }

  function watchDynamicCopy() {
    const status = document.getElementById('v3-global-status');
    if (!status) return;
    new MutationObserver(() => {
      if (polishing || status.textContent === v3StatusStamp) return;
      v3StatusStamp = status.textContent;
      schedulePolish();
    }).observe(status, { childList: true, characterData: true, subtree: true });
  }

  function bindNav() {
    document.getElementById('nav')?.addEventListener('click', () => setTimeout(schedulePolish, 120));
    window.addEventListener('marketdesk:ready', () => {
      deskStub();
      onViewChange();
      watchDynamicCopy();
    });
    // Only react to view class toggles — never to our own text rewrites.
    new MutationObserver((records) => {
      if (polishing) return;
      const relevant = records.some(
        (r) =>
          r.type === 'attributes' &&
          r.attributeName === 'class' &&
          (r.target.classList?.contains('view') || r.target.classList?.contains('nav-btn'))
      );
      if (relevant) schedulePolish();
    }).observe(document.body, {
      subtree: true,
      attributes: true,
      attributeFilter: ['class'],
    });
  }

  function boot() {
    if (!isDemo()) return;
    document.documentElement.dataset.demoMode = 'true';
    deskStub();
    polishTextRoots();
    bindNav();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

  window.MarketDeskDemoPolish = { refresh: onViewChange };
})();
