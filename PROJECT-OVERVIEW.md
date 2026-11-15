PROJECT OVERVIEW
Market Desk is a local research app for a Mac. It does not send the saved database anywhere. This page is meant to be edited before it is shown to someone else.

MY ROLE
William, student.
[Write what you designed, what you decided, and what you checked yourself.]

HELP FROM AI TOOLS
ChatGPT and Cursor were used while the app was built. The code, tests and saved records are on this Mac.
[Write, in your own words, which parts you directed and which parts an AI tool drafted.]

WHAT THE APP USES
Python and its standard library. The browser files are part of this project. No new paid package was added for V6.1.
Market data comes from Finnhub, Massive Stocks Basic, the public Coinbase Exchange API, SEC company facts and FRED. Each source has its own terms. Missing figures stay missing.

WHAT IT DOES NOT DO
A forecast is not a promise. The purple line is withheld when the price model does not beat an unchanged price on later dates, when history is short, when a one-day jump looks like a split, or when the last close is stale. News does not move that line. A typed company scenario is separate. The guided demo uses labelled sample numbers and does not write them into your price database.

CHECKED
The path rules are in tests/test_forecast61.py. Take-Two, AMD and Apple were read from the saved closes on this Mac when V6.1 was checked. The numbers from that check belong in V6.1-VERIFICATION.md, not in this overview, because they change when new closes are saved.
