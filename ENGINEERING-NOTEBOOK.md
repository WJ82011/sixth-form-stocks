ENGINEERING NOTEBOOK
Dates are the days the note was written. Status is completed, proposed or pending.

2026-11-14 · completed
The purple chart line was drawn in the browser from a damped 5/20/60-session curve, sometimes blended with older matching paths. V6.1 stops using that curve for the chart. The line now comes from the chronological price model. A horizon is included only when it beats an unchanged price on a later block. That later block is not used to fit the line. The band is the middle range of earlier misses, and the later dates report how often the close fell inside it. A recent-average move is scored as a second comparison and does not replace the unchanged-price rule. Sessions between drawn horizons are a straight join. The check uses daily closes only. News and accounts are not inputs. Each distinct result is kept. Reading the check does not replace an issued forecast. Tests: tests/test_learning40.py and tests/test_forecast61.py.

2026-11-14 · completed
A saved scan card opened the overview page and lost the chart window. The card now opens the company chart and keeps the scanned dates. Checked in the running app with the saved scan “V6 investigation”.

2026-11-14 · completed
V2.7 recorded a full-screen check: desktop 1280 by 720, panel from 20,20 to 1260,700, and a phone width of 390 with no sideways overflow. That file records measurements. It does not record an open navigation defect. V2.4.1 grouped the sidebar into six entries. Source: V2.7-QA-REPORT.txt and V2.4.1-RELEASE-NOTES.txt.

2026-11-15 · completed
V6.8 groups the existing screens into My Desk, Explore, Investigate and My Research. Forecast Lab and Forecast Results were left separate because one checks a model and the other stores issued forecasts. No new tester result was received. The five V6.8 tasks are written and still pending.

2026-11-15 · completed
V6.7 adds decision practice on the saved tape. The server answer includes only records at or before the replay clock. A reflection does not replace the original decision. No new tester result was received.

2026-11-15 · completed
V6.6 retrieved Take-Two SEC company facts for CIK 0000946581 and labelled event relevance. No new tester result was received.

2026-11-14 · pending
Five tester tasks are written. No tester has returned a result. The feedback list stays empty until someone records one.

Proposed
Keep the unchanged-price baseline whenever a horizon fails its later test. Do not draw a curve to make the forecast look busier.
