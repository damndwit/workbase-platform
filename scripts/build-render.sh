#!/usr/bin/env bash
# Old build helper, still keeping it around.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
python -m pip install -r backend/requirements.txt
cd frontend
npm install
npm run build
