#!/usr/bin/env bash
set -euo pipefail
mkdir -p social/audit
BROWSER="$(command -v google-chrome || command -v google-chrome-stable || command -v chromium || true)"
if [[ -z "$BROWSER" ]]; then
  echo "Chrome/Chromium missing; installing chromium-browser via package manager"
  sudo apt-get update -qq && sudo apt-get install -y chromium-browser
  BROWSER="$(command -v chromium-browser)"
fi
echo "Browser: $BROWSER"
python3 -m http.server 8462 >/tmp/chef-site.log 2>&1 &
server_pid=$!
trap 'kill $server_pid 2>/dev/null || true' EXIT
sleep 2
"$BROWSER" --headless --no-sandbox --disable-gpu --disable-dev-shm-usage \
 --hide-scrollbars --disable-background-timer-throttling --window-size=1440,1050 \
 --virtual-time-budget=18000 --screenshot="social/audit/luxury-desktop.png" \
 "http://127.0.0.1:8462/"
"$BROWSER" --headless --no-sandbox --disable-gpu --disable-dev-shm-usage \
 --hide-scrollbars --disable-background-timer-throttling --window-size=440,1000 \
 --virtual-time-budget=18000 --screenshot="social/audit/luxury-mobile.png" \
 "http://127.0.0.1:8462/"
for p in social/audit/luxury-desktop.png social/audit/luxury-mobile.png; do
  test -s "$p"
  file "$p"
done
