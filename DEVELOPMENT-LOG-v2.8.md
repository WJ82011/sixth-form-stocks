# Market Desk Reborn 2.8

Integrated the approved local design study into the existing Python/JavaScript
app. AI assisted implementation and checks. The original data, chart, model
and research modules remain; this is an interface release.

Two new local assets (`design.js`, `design.css`) supply the shell and motion.
Existing DOM identifiers and chart mounting are preserved. Navigation commits
only the latest requested destination; cancelling motion resolves promises.
Reduce Motion and hidden-tab behaviour are explicit. No interpolation of
market values is introduced. Preferences are bounded, whitelist validated,
backed up and compatible with earlier workstation choices.

Validation: full Python suite, JavaScript regression suites, new cancellation
and settings tests, real browser desktop/phone checks, saved price history
and full-screen geometry checks. QA used a temporary database and read-only
copies of genuine saved provider snapshots; no credentials or user research
were put in the release. No new provider requests were needed for visual QA.
