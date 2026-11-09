#!/bin/bash
cd "$(dirname "$0")" || exit 1
python3 login40.py disable
read -r -p 'Press Return to close… ' answer
