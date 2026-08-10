#!/usr/bin/env bash
# Build the static frontend and deploy it to the Pi.
#
# Covers the common case: a repo update that only touches the frontend. Needs no
# root and causes no downtime — the server reads the directory from disk.
#
#   ./lunyoro-translator/deploy-pi-frontend.sh 192.168.100.86
#
# See PI_DEPLOYMENT.md for model updates, verification and rollback.

set -euo pipefail

PI_IP="${1:-}"
if [[ -z "$PI_IP" ]]; then
    echo "usage: $0 <pi-ip>" >&2
    echo "  find it with: arp -a | grep -i d8:3a:dd" >&2
    exit 1
fi

# This script lives in lunyoro-translator/, so its own directory is the project root.
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND="$PROJECT_DIR/frontend"
REMOTE="/home/pi/lunyoro-translator-cpp/frontend"
PI="pi@$PI_IP"

echo "==> Checking the Pi is reachable (ICMP is blocked, so test the port)"
nc -z -G 5 -w 5 "$PI_IP" 22 || { echo "cannot reach $PI_IP:22" >&2; exit 1; }
ssh -o BatchMode=yes -o ConnectTimeout=10 "$PI" 'true' || { echo "ssh key auth failed" >&2; exit 1; }

cd "$FRONTEND"

echo "==> Re-applying the same-origin API fix (harmless if already applied)"
# Upstream ships `|| "http://localhost:8000"`, which is falsy-tested and so ignores
# NEXT_PUBLIC_API_URL="". `??` keeps the empty string, giving same-origin URLs.
grep -rl 'NEXT_PUBLIC_API_URL || "http://localhost:8000"' components/ app/ 2>/dev/null | while read -r f; do
    perl -pi -e 's/NEXT_PUBLIC_API_URL \|\| "http:\/\/localhost:8000"/NEXT_PUBLIC_API_URL ?? "http:\/\/localhost:8000"/' "$f"
    echo "    patched $f"
done

if [[ ! -f public/fonts/material-symbols.woff2 ]]; then
    echo "!! public/fonts/material-symbols.woff2 is missing — icons will render as text." >&2
    echo "   git checkout -- public/fonts/material-symbols.woff2" >&2
    exit 1
fi

echo "==> Building static export"
rm -rf out
STATIC_EXPORT=1 NEXT_PUBLIC_API_URL="" npx next build

echo "==> Verifying the bundle before shipping"
fail=0
if grep -rql 'localhost:8000' out/_next/static/chunks/*.js 2>/dev/null; then
    echo "    FAIL: bundle still points at localhost:8000" >&2; fail=1
fi
if grep -rql 'googleapis' out/ 2>/dev/null; then
    echo "    FAIL: bundle references fonts.googleapis.com (unreachable offline)" >&2; fail=1
fi
if [[ ! -f out/fonts/material-symbols.woff2 ]]; then
    echo "    FAIL: icon font missing from build output" >&2; fail=1
fi
[[ $fail -eq 0 ]] || { echo "aborting, nothing deployed" >&2; exit 1; }
echo "    same-origin OK, no external fonts, icon font present"

echo "==> Uploading to a staging directory"
ssh -o BatchMode=yes "$PI" "rm -rf $REMOTE/out.new && mkdir -p $REMOTE/out.new"
scp -q -o BatchMode=yes -r out/. "$PI:$REMOTE/out.new/"

echo "==> Swapping in (previous build kept as out.bak-prev)"
ssh -o BatchMode=yes "$PI" "cd $REMOTE && rm -rf out.bak-old && mv out.bak-prev out.bak-old 2>/dev/null; mv out out.bak-prev && mv out.new out"

echo "==> Verifying the live site"
code=$(curl -s -m 20 -o /dev/null -w '%{http_code}' "http://$PI_IP/")
font=$(curl -s -m 20 -o /dev/null -w '%{http_code}' "http://$PI_IP/fonts/material-symbols.woff2")
echo "    index: HTTP $code    icon font: HTTP $font"
[[ "$code" == "200" && "$font" == "200" ]] || { echo "    deploy looks wrong — roll back with: ssh $PI 'cd $REMOTE && mv out out.broken && mv out.bak-prev out'" >&2; exit 1; }

echo
echo "Done. Anyone who loaded the site before the cache fix shipped needs one hard"
echo "reload (Cmd/Ctrl+Shift+R); after that it self-corrects on every deploy."
