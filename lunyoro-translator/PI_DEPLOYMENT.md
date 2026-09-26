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

## Deploying the Ollama chat LLM

The chat endpoint uses **qwen2.5:1.5b** (986 MB Q4_K_M) running inside Ollama on the Pi.
It must be set up once and thereafter starts automatically on every boot.

### Boot sequence

```
boot
 └─ ollama.service          (installed by Ollama's install.sh, starts the server on :11434)
     └─ ollama-pull.service  (one-shot: pulls qwen2.5:1.5b if not already cached)
         └─ lunyoro-sidecar.service  (Python FastAPI — waits for model to be ready)
```

### First-time setup (run on the Pi, needs sudo)

```bash
# 1. Install Ollama — registers ollama.service to start at boot automatically
curl -fsSL https://ollama.com/install.sh | sh
systemctl is-active ollama   # should print: active

# 2. Install the model-pull service
sudo cp /home/pi/lunyoro-sidecar/ollama-pull.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ollama-pull

# 3. Do the initial pull now (one-time, ~986 MB)
sudo systemctl start ollama-pull
journalctl -u ollama-pull -f    # watch until "Pull complete."

# 4. Install / update the sidecar service (also done by deploy.sh step 3)
sudo cp /home/pi/lunyoro-sidecar/lunyoro-sidecar.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable lunyoro-sidecar
sudo systemctl restart lunyoro-sidecar
```

### What runs automatically after this

On every subsequent boot, systemd brings up services in this order automatically:

1. **ollama.service** — Ollama server, no user action needed
2. **ollama-pull.service** — checks if model is cached; skips the download if already present (fast)
3. **lunyoro-translator.service** — C++ NLLB backend (NLLB only — MarianMT removed)
4. **lunyoro-sidecar.service** — Python sidecar, starts after all the above are ready

No manual intervention is needed after the first-time setup.

### Updating the model

To swap to a different model (e.g. a future `qwen2.5:3b`):

```bash
# On the Pi:
ollama pull qwen2.5:3b
# Edit /etc/systemd/system/lunyoro-sidecar.service:
#   Environment=OLLAMA_MODEL=qwen2.5:3b
sudo systemctl daemon-reload && sudo systemctl restart lunyoro-sidecar
```

### Verifying the chat is working

```bash
curl -s -X POST http://localhost/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "How are you?"}' | python3 -m json.tool
# Expected: "reply": "Ndyoho, webale muno.\n\n(English: I am fine, thank you.)"
```

---

## Deploying a model update

Only when models are retrained. Requires the PyTorch checkpoints in `backend/model/`:

```bash
cd lunyoro-translator/backend
python export_nllb_onnx.py
python export_onnx_int8.py --prune-fp32  # NLLB → INT8
python verify_pi_models.py --all         # check output before shipping

PI=pi@<ip>
rsync -a model/nllb_en2lun_pi/ $PI:/home/pi/lunyoro-translator-cpp/models/v3/nllb_en2lun/
rsync -a model/nllb_lun2en_pi/ $PI:/home/pi/lunyoro-translator-cpp/models/v3/nllb_lun2en/
```

Then have someone restart the service (below).

#### Fixing external-data references after quantization

After quantizing NLLB models to INT8 the `.onnx` protobuf header still records the old
`*_quantized.onnx.data` filename rather than the renamed `*.onnx.data` file. Running
inference against a mismatched filename causes a load error.
`backend/model/patch_ext_refs.py` fixes this without touching the `.data` file itself:

```bash
# Run inside the pi-sim-backend container (or any environment with the onnx package)
python3 /models/patch_ext_refs.py
```

The script:
- Covers **all** tensor locations in the protobuf — `graph.initializer`, `node.attribute`
  tensors (e.g. Constant nodes), and subgraphs inside `If`/`Loop`/`Scan` nodes recursively
- Derives the correct target filename dynamically from each model's own base name
  (`encoder_model_quantized.onnx.data` → `encoder_model.onnx.data`, etc.)
- Rewrites only the protobuf header (`SerializeToString`) — the `.data` weight file is
  **never modified**, so no data is duplicated or lost
- Backs up each `.onnx` file to `<file>.bak` on first run (skips if backup already exists)
- Prints a per-model count of references fixed and a final verification pass showing any
  remaining old-style references

Models patched: `nllb_en2lun_int8` and `nllb_lun2en_int8`, both encoder and decoder.

**NLLB must be quantized.** Unquantized it is ~6.8 GB per direction, 13.6 GB for both — it cannot
load on the Pi's 8 GB. INT8 brings it to ~1.19 GB per direction (~2.4 GB total). MarianMT has
been removed — only NLLB is used for translation.

**NLLB language token: `run_Latn` (Rundi proxy, ID 256146).** Use `run_Latn` as
`forced_bos_token_id` for all NLLB INT8 ONNX inference on the Pi — both en→lun and lun→en.

**Why not `nyo_Latn`?** `nyo_Latn` (ID 256205) is the custom Runyoro-Rutooro token baked into the
FP32 PyTorch model during fine-tuning. INT8 quantization distorts its embedding because it sits at
the very end of the vocabulary matrix as a custom-added token with limited training exposure. In
practice, every quantized model tested outputs Luganda (`muli kurungi`) or garbage when
`nyo_Latn` is the forced BOS, and correct Runyoro when `run_Latn` is used instead.

**`model_config.json` pin.** Each `nllb_*_pi` directory now contains:
```json
{"runyoro_lang_code": "run_Latn"}
```
This file is rsynced to the Pi alongside the model weights and is read by any Python inference
layer (`pi-sim`, sidecar patches). The C++ backend reads its token from the compiled binary and
**must be updated separately** — see the C++ fix section below.

**If the Pi is still outputting Luganda (`muli kurungi`) or wrong-language text**, the C++ binary
is compiled with the old token. Fix:

```cpp
// In translator_v2.cpp (or wherever NLLB_TGT_LANG / NLLB_SRC_LANG are defined):

// OLD — causes Luganda output from INT8 models:
// const std::string NLLB_LANG_LUN = "nyk_Latn";   // was: Nyankore placeholder → <unk>
// const std::string NLLB_LANG_LUN = "lug_Latn";   // was: Luganda proxy
// const std::string NLLB_LANG_LUN = "nyo_Latn";   // was: custom token, distorted by INT8

// CORRECT — use this:
const std::string NLLB_LANG_LUN = "run_Latn";       // Rundi proxy, ID 256146, works with INT8
```

After editing, rebuild and restart the service:
```bash
ssh pi@<ip>
cd ~/lunyoro-translator-cpp
make -j4
sudo systemctl restart lunyoro-translator
sleep 45
curl -s -X POST localhost/translate -H 'Content-Type: application/json' \
  -d '{"text":"How are you?"}' | python3 -m json.tool
# Expected: "translation": "Oroho ota?" or "Oirirwe ota" — Runyoro, not Luganda
```

---

## Restarting the service

Needed after a model or backend change. A person must type the password:

```bash
ssh pi@<ip> 'sudo systemctl restart lunyoro-translator && sleep 45 && systemctl is-active lunyoro-translator'
```

Allow ~30 seconds — it loads two NLLB INT8 models (~2.4 GB). Memory use after startup is roughly 2.4 GB for models + OS/sidecar overhead.

---

## Verifying a deploy

```bash
IP=<ip>
curl -s $IP/health
curl -s -X POST $IP/translate         -H 'Content-Type: application/json' -d '{"text":"Good morning, my friend."}'
curl -s -X POST $IP/translate-reverse -H 'Content-Type: application/json' -d '{"text":"Webale muno"}'
ssh pi@$IP 'systemctl is-active lunyoro-translator; free -h | head -2'
```

Known-good answers: `Good morning, my friend.` → `Oraire ota mugenziwe.` (NLLB);
`Webale muno` → `Thank you very much`; `How are you?` → `Oroho ota?` or `Oirirwe ota`.
If NLLB returns Luganda (`muli kurungi`) the C++ binary is using the wrong language token —
see the C++ fix instructions in the model update section above.

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
