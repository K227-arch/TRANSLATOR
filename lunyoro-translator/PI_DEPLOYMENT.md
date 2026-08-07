# Deploying updates to the Raspberry Pi

How to take a new commit from this repo and get it running on the Runyoro translator Pi.

There is one physical device. Everyone deploying from this repo is updating **the same Pi**, so
coordinate before restarting the service — a restart takes it offline for about 45 seconds.

---

## What runs on the Pi

| Piece | Location on the Pi | How it updates | Root needed |
|---|---|---|---|
| Frontend (static Next.js export) | `~/lunyoro-translator-cpp/frontend/out/` | directory swap | no |
| Backend binary (C++) | `~/lunyoro-translator-cpp/build_v3/translator_v2` | rebuild on the Pi, restart service | yes, to restart |
| Models (ONNX) | `~/lunyoro-translator-cpp/models/v3/` | rsync, restart service | yes, to restart |

Most repo updates are frontend-only: no root, no downtime.

**The C++ source is not in this repo** — it lives only on the Pi at `~/lunyoro-translator-cpp/`
and on the maintainer's machine. From a clone of this repo you can deploy frontend and model
updates; backend changes require access to that source.

---

## Prerequisites

**Find the Pi.** Its address is assigned by DHCP and moves — it has been `192.168.100.63` and
`192.168.100.86`. ICMP is blocked, so `ping` fails even when the device is healthy; don't use it
as a liveness test.

```bash
arp -a | grep -i "d8:3a:dd"     # d8:3a:dd:f4:3c:16 = eth0, ...:15 = wlan0 (hotspot)
nc -z <ip> 22 && echo reachable
```

On its own hotspot (SSID `Lunyoro-Translator`) the Pi is always `192.168.4.1`.

**SSH access.** Install your key once — the account is `pi`:

```bash
ssh-copy-id -i ~/.ssh/id_rsa.pub pi@<ip>
```

Use a key **without a passphrase**, or load it into `ssh-agent` first; scripted (`BatchMode`) SSH
cannot prompt for one.

**`sudo` needs a password.** Anything touching `/etc` or `systemctl` must be typed by a person and
cannot be scripted.

---

## Deploying a frontend update

The scripted path — builds, runs pre-flight checks, and refuses to ship a broken bundle:

```bash
./lunyoro-translator/deploy-pi-frontend.sh <pi-ip>
```

<details>
<summary>Doing it manually</summary>

```bash
git pull --ff-only origin main
cd lunyoro-translator/frontend

# Both variables are required:
#   STATIC_EXPORT=1        -> emits out/ instead of a server build
#   NEXT_PUBLIC_API_URL="" -> API calls become same-origin, so they reach the Pi
rm -rf out
STATIC_EXPORT=1 NEXT_PUBLIC_API_URL="" npx next build

# All three must hold before deploying:
grep -rl 'localhost:8000' out/_next/static/chunks/*.js | wc -l   # 0
grep -rl 'googleapis'     out/                          | wc -l   # 0
ls -l out/fonts/material-symbols.woff2                            # exists, ~312K

# Stage then swap — never scp over the live directory
PI=pi@<ip>
ssh $PI 'rm -rf ~/lunyoro-translator-cpp/frontend/out.new && mkdir -p ~/lunyoro-translator-cpp/frontend/out.new'
scp -r out/. $PI:/home/pi/lunyoro-translator-cpp/frontend/out.new/
ssh $PI 'cd ~/lunyoro-translator-cpp/frontend && rm -rf out.bak-old && mv out.bak-prev out.bak-old 2>/dev/null; mv out out.bak-prev && mv out.new out'
```

</details>

No service restart is needed — the server reads the directory from disk on each request.

### Why those two environment variables matter

`NEXT_PUBLIC_API_URL=""` makes the app call `/translate` rather than an absolute URL, so requests
go to whatever host served the page. Omit it and the bundle calls `http://localhost:8000`, which
works on your laptop and fails on every phone.

This relies on components reading the variable with `??`, not `||` — an empty string is falsy, so
`||` would discard it and fall back to localhost. If you add a component that calls the API, copy
the existing pattern:

```ts
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
```

### Why the icon font is committed

`public/fonts/material-symbols.woff2` is checked in and referenced by an `@font-face` in
`app/globals.css`. The Pi runs as an offline hotspot, so a `fonts.googleapis.com` stylesheet never
loads there and all 75 icons render as literal text (`swap_horiz`, `thumb_up`, …). Do not
reintroduce the external stylesheet: it also *overrides* the local `@font-face`, because it loads
after Next's CSS.

---

## Deploying a model update

Only when models are retrained. Requires the PyTorch checkpoints in `backend/model/`:

```bash
cd lunyoro-translator/backend
python export_onnx_all.py                # PyTorch -> ONNX
python export_onnx_int8.py --prune-fp32  # NLLB -> INT8
python export_marian_tokenizer.py        # Unigram data the C++ Marian path needs
python verify_pi_models.py --all         # check output before shipping

PI=pi@<ip>
rsync -a --exclude 'decoder_with_past_model.onnx' model/en2lun_onnx/ $PI:/home/pi/lunyoro-translator-cpp/models/v3/marian_en2lun/
rsync -a --exclude 'decoder_with_past_model.onnx' model/lun2en_onnx/ $PI:/home/pi/lunyoro-translator-cpp/models/v3/marian_lun2en/
rsync -a model/nllb_en2lun_pi/ $PI:/home/pi/lunyoro-translator-cpp/models/v3/nllb_en2lun/
rsync -a model/nllb_lun2en_pi/ $PI:/home/pi/lunyoro-translator-cpp/models/v3/nllb_lun2en/
```

Then have someone restart the service (below).

**NLLB must be quantized.** Unquantized it is ~6.8 GB per direction, 13.6 GB for both — it cannot
load on the Pi's 8 GB. INT8 brings it to ~1.19 GB per direction with no measurable quality loss
(4/5 exact output parity against fp32 on our probes). MarianMT stays fp32 at ~550 MB per direction.

**Keep `model_config.json` in each NLLB directory.** It pins the Runyoro language token to
`256146`. Without it the loader falls back to the key `nyk_Latn`, which is not a real NLLB token
and silently resolves to UNK, degrading output.

---

## Restarting the service

Needed after a model or backend change. A person must type the password:

```bash
ssh pi@<ip> 'sudo systemctl restart lunyoro-translator && sleep 45 && systemctl is-active lunyoro-translator'
```

Allow ~45 seconds — it loads four models. Expect roughly 3.6 GB of the 7.9 GB in use afterwards.

---

## Verifying a deploy

```bash
IP=<ip>
curl -s $IP/health
curl -s -X POST $IP/translate         -H 'Content-Type: application/json' -d '{"text":"Good morning, my friend."}'
curl -s -X POST $IP/translate-reverse -H 'Content-Type: application/json' -d '{"text":"Webale muno"}'
ssh pi@$IP 'systemctl is-active lunyoro-translator; free -h | head -2'
```

Known-good answers: `Good morning, my friend.` → `Oraire ota mugenziwe.` (NLLB) and
`Oraire ota, mukwangu.` (Marian); `Webale muno` → `Thank you very much`.

Live request log, useful when something silently fails:

```bash
ssh pi@<ip> 'journalctl -u lunyoro-translator -f' | grep -E '\[(GET|POST)'
```

---

## Rolling back

Each layer is independent.

```bash
# Frontend — the previous build is kept next to the live one
ssh pi@<ip> 'cd ~/lunyoro-translator-cpp/frontend && rm -rf out.broken && mv out out.broken && mv out.bak-prev out'

# Backend binary / model flags (needs sudo)
ssh pi@<ip> 'sudo cp /home/pi/override-v2-backup.conf /etc/systemd/system/lunyoro-translator.service.d/override.conf && sudo systemctl daemon-reload && sudo systemctl restart lunyoro-translator'

# Captive portal
ssh pi@<ip> 'sudo rm /etc/NetworkManager/dnsmasq-shared.d/captive-portal.conf && sudo nmcli connection down Lunyoro-Translator && sudo nmcli connection up Lunyoro-Translator'
```

---

## Traps that have already cost time

1. **A user reports the UI looks broken after your deploy.** Next names chunks by content hash, so
   a browser holding a stale `index.html` requests files the new build deleted; they 404, the
   stylesheet among them, and the page renders unstyled. The server now sends `Cache-Control:
   no-cache` on HTML, but anyone who loaded the site before that shipped needs one hard reload
   (Cmd/Ctrl+Shift+R).
2. **Forgetting `NEXT_PUBLIC_API_URL=""`** produces a bundle that works on your laptop and fails
   on every phone. The deploy script checks for this.
3. **Never `systemctl restart NetworkManager`** on the Pi — it drops the eth0 SSH session and you
   lose access. Use `nmcli connection down/up Lunyoro-Translator`.
4. **`iw` lives in `/usr/sbin`**, not on `pi`'s PATH, so `iw dev wlan0 station dump` reports
   "command not found" — which reads exactly like "no clients connected". Use the full path.
5. **Don't leave a test instance running.** Two full instances exhaust the 8 GB of RAM and risk
   the OOM killer taking down the live service on port 80.

---

## Known gaps

The frontend calls 15 endpoints; the Pi's C++ server implements 12. Missing: `/classify-image`
(Lens "Identify"), `/summarize-pdf`, `/translate-batch`, `/translate-batch-file`,
`/language-rules/*`. Those tabs render but do not function on the Pi. They work against the Python
backend.

Live camera preview cannot work on the Pi: browsers restrict `getUserMedia` to HTTPS, and a device
on a private IP with no internet cannot obtain a valid certificate. Lens therefore hands off to the
device's native camera app instead of showing a live viewfinder.
