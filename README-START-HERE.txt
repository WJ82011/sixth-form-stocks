MARKET DESK REBORN 4.0.0 — MAC
Background market collection and local forecast evaluation

PUBLIC PORTFOLIO DEMO (VERCEL)
The live sixth-form URL is a static admissions demo. It loads site/demo/snapshot.json
and cloud-host.js serves read-only /api responses without your Mac. Labels say
PORTFOLIO DEMO. Finnhub keys, SEC refresh and live research still need server.py
locally. Regenerate the bundle with: python3 tools/export-demo-snapshot.py
Test the same mode locally with ?demo=1 on any static server (not port 8765).

NEW IN V4.0
Market Desk now collects prices in the local server. Close the tab and leave
the server running, or enable the optional macOS login service. Open All tools
→ Learning & offline to see collection status and evaluate a company forecast.
Read V4.0-QUICK-GUIDE.txt before enabling background startup.

NEW IN V3.9
On a company chart, choose a daily price range and click Focus on purple line.
The main view shows the trend scenario with its illustrative range. The focus
view lets you read smaller movements in the centre of that scenario.
Live Tape adds observed 1-minute and 5-minute candles, a trade size filter,
direct directory stock switching and a saved date selector with time scrubbing.
Read V3.9-QUICK-GUIDE.txt and V3.9-VERIFICATION.md.

NEW IN V3.8
Open All tools → Crypto to view Bitcoin and Ethereum in USD. Coinbase Exchange
provides public historical candles and live trades. Charts cover 1 hour,
24 hours, 1 week, 30 days and 1 year. Previously loaded ranges are saved locally.
In a US company chart, open Understand this chart → Load last available US date
to see split-adjusted minute prices from Massive for the latest eligible date.
Read V3.8-QUICK-GUIDE.txt for opening and usage instructions.

NEW IN V3.7
All tools → Market Heatmap. Choose 1 day, 3 days or 1 week of completed US
trading sessions. History loads across the 221-company directory using six
shared daily market files from your existing free Massive connection.
Every company opens directly, without joining your watchlist. The chart uses
the exact heatmap dates. Your watchlist and its feed limits stay separate.
Pause/resume, small history lines, rise/fall sorting, saved map preferences,
CSV export and optional company-follow controls are included. Older market
value cards and the size map remain in expandable sections below the map.
Read V3.7-QUICK-GUIDE.txt and V3.7-VERIFICATION.md before using the new data.


NEW IN V3.6
Open All tools → Market Heatmap for dated market-value cards, sourced CSV
imports/exports and opt-in top-right notifications. Browse 221 listed stocks,
including 55 new verified entries. The heatmap opens the full directory.
The live tape has more starter choices and keeps its existing feed limits.
Charts distinguish the plotted range from the provider previous-close return
and the latest saved completed-session comparison. Explicit daily-price
refresh now bypasses the provider cache. Actual missing data stays missing.
Read V3.6-QUICK-GUIDE.txt and V3.6-VERIFICATION.md for coverage and checks.

NEW IN V3.5
All tools → Market Desk Intelligence. A guided company research screen brings
saved evidence together. Preview user-chosen what-ifs with optional local AI
help, approve them explicitly and see a reconciled profit chart. Recover
unfinished company forms. Record new five-session forecasts before outcomes
are known and check actual saved prices later against an unchanged baseline.
Read V3.5-QUICK-GUIDE.txt, V3.5-METHODOLOGY.md and V3.5-VERIFICATION.md.
Earlier features and saved research remain available. No new model download,
paid AI requirement or cloud fallback is added. Nothing learns while Mac is off.

OPEN THE WEBSITE
1. Export a full research backup in the old app's Settings.
2. Stop the old app's Terminal window with Control+C.
3. Extract MarketDesk-Reborn-v4.0.0-Mac.zip.
4. Double-click Start Market Desk.command inside the new folder.
5. Keep its Terminal window open. Visit http://127.0.0.1:8765.
If needed: type python3 and a space in Terminal, drag the new server.py
into that window and press Return. Python 3 comes from python.org.

The new version reuses your existing private data folder and browser origin.
Keep ~/.marketdesk-reborn; do not remove your saved keys or database.
No keys, model weights or personal research are included in this ZIP.

START EXPLORING
Home: arrange five cards and keep a research question in focus.
Companies: charts and the retained financial-health view, plus expanded
income, balance-sheet and cash-flow research with exact filing inputs.
All tools: all 19 earlier tools plus Home, Company calendar and Sources.
Practice Portfolio: a new sourced cash/holding ledger, fees, dividends,
splits, explicit FX, checkpoints and benchmark review. The original V2
practice tool is retained in a folded section; migration is explicit.
Stock Browser: official SEC listing search alongside the existing directory.
Stock Screener: filter saved standardized annual accounts.
Market Heatmap: an optional source-qualified market-cap area map.
Compare Companies: saved daily-price charts rebased on shared actual dates.
Economy Overview: four dated official FRED series with explicit updates.
Customise: the existing appearance, rounded design and motion controls.

Read V3.0-QUICK-GUIDE.txt, V3.0-METHODOLOGY.txt and V3.0-RELEASE-NOTES.txt.
The older guides below remain useful for retained V2 tools.

USING INTELLIGENCE
- In Overview, press 1hr or 24hrs. The chart and its Intelligence paragraph
  use timestamped local Finnhub observations for the selected ticker.
- In Market Desk Intelligence, check saved data for a stock to inspect both windows and
  the Model Results. Nothing is fetched from a provider by this action.
- Press Get company details & news for Finnhub profile, metrics and dated headlines.
  Ask a question or use the topic buttons. Unsupported questions are declined.
- Download research data saves the loaded research data and model results, no keys.
- To populate daily model training data, load a 1Y chart using your Massive
  key, then return to Intelligence and check saved data again. At least 90 valid daily
  closes are required. Model fitting happens locally on each analysis request.

WHAT THIS CAN AND CANNOT DO
Market Desk AI now uses an installed local Ollama language model for questions
and research drafts. Read AI-START-HERE.txt. The older Quick data questions
box remains a topic router with evidence templates and works without Ollama.
No paid OpenAI account is required. Ollama is an optional separate installation.
The learning model fits next-session daily log returns, not hour-ahead prices.
It does not learn from news or company variables. It reports out-of-sample
error, baseline comparison, empirical interval coverage and learned coefficients.
Missing history withholds results. No guarantee of predictive value is made.

Intraday data is partial and recorded only while the app/feed is running.
Mac sleep, browser closure, provider disconnects and retention can leave gaps.
The hourly/daily-window returns compare available endpoints, not necessarily
the exact window boundaries. Occupied minute slots are a sampling measure,
not proof of complete coverage. Daily bars never backfill intraday charts.
No collection, training or continuous learning occurs while the Mac is off.
Company data can be old, news is publisher claims, and price correlation is
not causation. Free plan restrictions and the existing request budgets apply.

TESTS
Python: python3 tests/run_all.py
JavaScript (if Node installed): run each tests/test_*.cjs with node.
See V2.6.0-QA-REPORT.txt, AI-METHODOLOGY.txt and INTELLIGENCE-METHODOLOGY.txt.
Legacy QA/release notes describe earlier releases, not this release's results.

2.1.0 WORDING UPDATE
Menus, buttons, help text, chart summaries and model results use simpler English.
This is a wording update. Price calculations and model rules are unchanged.

TAKE-TWO UPDATE
TTWO is included for new watchlists. Existing watchlists stay as you set them.
Open Stock Browser and press Add / open Take-Two to add it to yours.
Search Take Two, Rockstar or GTA VI in Stock Browser or Live Tape to find TTWO.
Rockstar Games is part of Take-Two, not a separate listed stock.

EXPANDED STOCK DIRECTORY
Open Stock Browser to browse 221 stocks, choose a category or search by name.
Use Add to watchlist for the companies you want to follow. Your existing list
is kept. Browsing does not request prices. Prices depend on your provider plan.
See V2.1-RELEASE-NOTES.txt for that directory update.

V2.1.1 — QUICK GUIDE
Open Stock Browser: My watchlist now appears first. Use Explore stocks to
browse the directory. Open a watched company to go straight to its chart,
then choose Company details or Ask Intelligence for research on that stock.
Price time and last check are separate. Next-check times are estimates.
See V2.1.1-RELEASE-NOTES.txt and V2.1.1-QA-REPORT.txt for that earlier update.

V2.2 — PRICE ALERTS
Open Price Alerts, choose a watched stock and set an at-or-above or at-or-below
price. Save and arm it. Keep Market Desk open and connected. Alerts trigger once
on a new recent price, then wait for you to re-arm them. They do not monitor
while the Mac is off, and missed moves are not filled in. Messages are in-app.
Targets and trigger history are saved privately in the local price database.
Research JSON backups exclude alerts; Download alert records creates a separate
readable copy. Keep the private data folder when upgrading.
Read V2.2-RELEASE-NOTES.txt and V2.2-QA-REPORT.txt for the alerts release.
Read V2.6.0-QA-REPORT.txt for the current checks.
