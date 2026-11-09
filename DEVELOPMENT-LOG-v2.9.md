# Market Desk Reborn 2.9

AI assisted implementation and testing of a bounded Financial Health release.
The existing v2.8 source was copied into its own version folder; the prior
release, private research and saved data were preserved.

## Implementation

- New pure extraction module validates exact periods, units, issuer identity,
  filing versions, same-day conflicts and missing facts. Annual durations and
  quarters stay separate; YTD cash flow is never mistaken for a quarter.
- New SEC client validates ticker/CIK against submissions, uses fixed verified
  HTTPS endpoints and a paced single update, and stores only selected facts.
- Financial health, per-filing sources and dated comparison use the existing
  company and comparison pages. Provider profiles load when their section
  is opened. All 19 tools and the v2.8 motion/design remain.
- Saved SEC facts feed deterministic Intelligence summaries and optional local
  language-model evidence. The price model and its backtests are unchanged.

## Findings during validation

Direct Python HTTPS initially needed the app's established macOS trust-root
helper. It now uses that helper while retaining certificate and hostname
verification. No TLS check was disabled.

Live local-model drafts exposed two presentation/validation issues: ISO date
parts and negative loss amounts were being rendered in ordinary English by
the model, while the numeric validator expects those exact numbers to be in
its sources. The evidence now includes equivalent readable dates and exact
signed/absolute loss and million-USD representations. No numeric check was
relaxed. These generated representations are explicitly not filing quotations.

Manual review also caught incorrect claims that known filing dates and prior
years were missing. A targeted consistency check rejects those claims, and
answer sizes are bounded in the output schema. This remains a narrow check;
it does not prove semantic correctness. A final real local-model answer passed
all checks and manual comparison with the supplied Take-Two facts.

A narrow phone layout initially overflowed at the old provider-profile button.
Moving that control into its retained provider section and wrapping the
company selector fixed the overflow. Data views remain source driven.

## Scope limits

Selected US-GAAP USD facts, not full financial statements. IFRS, custom tags,
complete debt/lease normalization, TTM, segments and point-in-time fundamentals
remain future work. Source coverage and unavailable figures are visible.
