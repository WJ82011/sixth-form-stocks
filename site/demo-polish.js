/* Public demo: replace contradictory Mac/local copy and tune peripheral chrome. */
(function () {
  'use strict';

  function isDemo() {
    return document.documentElement.dataset.demoMode === 'true' || Boolean(window.MarketDeskHost?.demoMode);
  }

  const EXACT = new Map([
    ['.desk-local', 'Portfolio demo · bundled snapshot'],
    ['#preferences-state', 'DEMO · BROWSER ONLY'],
    ['#v3-global-status', null],
    ['#view-learning .page-title > div > p', 'Sample training results from the bundle. Live collection needs server.py on your Mac.'],
    ['#view-markets .page-title .eyebrow', 'PORTFOLIO DEMO / BUNDLED QUOTES'],
    ['#view-tape .page-title .eyebrow', 'PORTFOLIO DEMO / BUNDLED TRADES'],
    ['#view-tape .page-title > div > p', 'Replay labelled sample trades from the demo bundle. Live Finnhub sockets run on your Mac.'],
    ['#view-reports .page-title .eyebrow', 'INVESTMENT RESEARCH / DEMO BROWSER'],
  ]);

  const SUBTREE_PHRASES = [
    ['Private workspace · saved on this Mac', 'Portfolio demo · bundled snapshot'],
    ['Private research workspace ·', 'Portfolio demo ·'],
    ['saved on this Mac', 'in this demo bundle'],
    ['on this Mac', 'on the public demo host'],
    ['this Mac has saved', 'the demo bundle includes'],
    ['Saved data stays on this Mac.', 'Saved data on the public demo stays in your browser only.'],
    ['while the Mac is awake', 'while server.py runs on your Mac'],
    ['Enable Background at Login.command in the Mac folder.', 'On your Mac, use Enable Background at Login.command for overnight collection.'],
    ['Nothing is collected while this Mac is off.', 'This public host does not run overnight collectors.'],
    ['Nothing is collected while your Mac is off.', 'This public host does not run overnight collectors.'],
    ['Files saved on this Mac', 'Files in the full Mac workspace'],
    ['BACKED UP LOCALLY', 'DEMO · BROWSER ONLY'],
    ['Settings are saved automatically on this Mac.', 'Settings are saved in your browser on this demo.'],
    ['backed up on this Mac', 'saved in your browser on this demo'],
    ['LOCAL RESEARCH TERMINAL', 'PORTFOLIO DEMO'],
    ['LOCAL WORKSTATION', 'PORTFOLIO DEMO'],
    ['FEED OFFLINE', 'DEMO DATA'],
    ['LIVE TERMINAL / FINNHUB', 'PORTFOLIO DEMO / BUNDLED QUOTES'],
    ['RECORDED FINNHUB TRADES', 'BUNDLED DEMO TRADES'],
    ['See the trades Finnhub sends to your app.', 'Replay labelled sample trades from the demo bundle.'],
    ['Uses data saved on this Mac.', 'Uses the labelled demo snapshot on this host.'],
    ['SAVED ON YOUR MAC', 'SAVED IN THIS BROWSER'],
    ['PRIVATE & LOCAL', 'DEMO · BROWSER ONLY'],
    ['Connecting to Finnhub…', 'Sample watchlist quotes from the bundled snapshot'],
    ['Finnhub market feed', 'Demo bundle · not a live Finnhub feed'],
    ['Waiting for Finnhub trades. Prices are never made up.', 'Bundled demo trades · not a live Finnhub socket.'],
    ['Watchlist prices will appear here when Finnhub supplies them.', 'Sample watchlist quotes from the bundled snapshot.'],
    ['search for a stock on Finnhub', 'search the bundled demo directory'],
    ['with the same Finnhub data and research tools', 'with the same bundled demo tools'],
    ['Your browser needs this key to receive Finnhub’s live feed.', 'Provider keys are not used on this public demo host.'],
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
      if (selector === '#v3-global-status' && el.textContent.startsWith('Private research workspace')) {
        const date = new Date().toLocaleDateString('en-GB', {
          weekday: 'long',
          day: 'numeric',
          month: 'long',
        });
        const next = 'Portfolio demo · ' + date + ' · source dates stay visible.';
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
      '#view-overview, #view-home, #view-learning, #view-settings, #view-alerts, #view-reports, #view-markets, #view-tape, #view-intelligence, #view-news, #view-sources'
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
    if (typeof window.Desk !== 'undefined') return;
    window.Desk = {
      selected() {},
      memory() {},
      reload() {},
      historyChanged() {},
      chartMount() {
        return document.getElementById('desk-chart-mount');
      },
    };
  }

  function onViewChange() {
    if (!isDemo() || polishing) return;
    polishing = true;
    try {
      polishTextRoots();
      polishTapeChrome();
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
