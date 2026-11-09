#!/bin/bash
cd "$(dirname "$0")" || exit 1
printf '\nStarting Market Desk Reborn...\n\n'
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Python 3 is required. Install Python 3 from https://www.python.org/downloads/macos/'
  read -r -p 'Press Return to close...' answer
  exit 1
fi
python3 server.py
