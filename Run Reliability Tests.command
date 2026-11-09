#!/bin/bash
cd "$(dirname "$0")" || exit 1
printf '\nMarket Desk V3.3 reliability checks\nUses temporary test data. No keys or paid services required.\n\n'
python3 tests/run_reliability.py
result=$?
printf '\nFinished. The JSON report is in this folder.\n'
read -r -p 'Press Return to close...' answer
exit "$result"
