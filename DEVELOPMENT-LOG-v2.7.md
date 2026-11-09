# Market Desk Reborn v2.7 — development record

Date: 4 November 2026. Starting point: v2.6.1.

## Problem and intended experience

The project owner asked for a modern black-and-blue website with rounded
surfaces, clear graphs and simple wording. The next agreed improvements were
a clearer stock overview, better history controls and a readable daily briefing.
The goal was to help an unfamiliar visitor understand the evidence without
having to interpret a large table of figures first.

## Decisions

- Keep the existing detailed workspaces available through an explicit choice.
  Reuse the chart canvas so sources, interactions and the original tools remain.
- Make a briefing from dated saved quotes and publisher headline links. Describe
  available watchlist moves; do not present it as an index or explain causation
  from price changes alone. The wording is deterministic and inspectable.
- Show source coverage before a user chooses a chart range. Keep actual dates,
  missing years and gaps visible. Let saved provider history work offline.
- Let users review and export imported histories. Store small source metadata
  alongside imports so ordinary briefing reads stay light.
- Keep the project's original visual system and logo. No competitor screenshots,
  layouts or design assets were copied into this release.

## Evidence and limits

The release includes offline regression tests and a QA report. Browser checks
used an isolated database with genuine previously saved market snapshots and
two genuine headline requests. No keys were exposed to the preview browser;
the user's existing research database was not modified by those checks.

The source limits remain material: free Massive history is about two years,
company/news coverage varies, imported files are not independently verified,
and old quote times can differ between stocks. Sixteen default companies have
written background descriptions. Other companies can fall back to a saved
industry field or a clear missing-description state.

A new-user usability session has NOT been carried out. USER-TEST-GUIDE.txt is a
blank protocol for the project owner to use; it is not evidence of participants
or results. No claims of improved user comprehension have been measured yet.

## AI assistance and project ownership

The project owner supplied the product direction, requested changes and
application context. Codex assisted with implementation, explanatory wording,
test creation, debugging and packaging for this update. This record does not
claim the project owner wrote every implementation line unaided.

To discuss the work confidently, inspect the source and explain the trade-offs:
why a missing price is not zero, why a five-year label is not five years of data,
why headlines do not establish causation, and how local/offline operation changes
what the app can know. Record any later personal changes and test results with
their actual dates.

## Next review

Run the short usability protocol, record where someone hesitates and address
those points before expanding the feature list. Company statements and an
earnings calendar remain possible future work, depending on source access.
