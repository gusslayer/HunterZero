#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
git -C "$APP_DIR" pull --ff-only
sudo systemctl restart hunterzero.service
sudo systemctl --no-pager --full status hunterzero.service
