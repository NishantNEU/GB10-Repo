# Deploy Starter Kit — Contents

**Location:** `/home/dell/Desktop/Deploy_starter_kit`
**Total size:** ~54 GB (4,899 files)
**Purpose:** An offline bundle for installing **NVIDIA NemoClaw** (with OpenClaw agents and the OpenShell sandbox) on a **Linux ARM64 NVIDIA GB10 / DGX Spark** machine without internet access. It includes local inference through vLLM (Qwen3.6-35B-A3B NVFP4) or Ollama (Qwen3.5 9B).

The checksum files show the bundle was copied from an external drive at `/Volumes/Extreme SSD/DELL_NVIDIA_HACKATHON_OFFLINE/`.

> **Note:** Files whose names start with `._` (for example, `._ollama`) are macOS AppleDouble metadata created during the copy from a Mac. They are not needed on Linux and can be ignored.

---

## At a glance

| Folder | Size | What's in it |
| --- | --- | --- |
| `01_installers/` | 2.1 GB | Offline installers: NemoClaw bootstrap, Node.js, npm caches, Ollama, OpenShell binaries, Python wheels |
| `02_repos/` | 14 GB | Git mirrors and source archives of NemoClaw, OpenClaw, OpenShell, plus a prepared NemoClaw v0.0.130 tarball |
| `03_models/` | 28 GB | Qwen3.6-35B-A3B-NVFP4 (Hugging Face format, for vLLM) and Qwen3.5 9B (Ollama store) |
| `04_container_images/` | 9.7 GB | Docker image tarballs: vLLM + Qwen server, OpenClaw sandbox, OpenShell supervisor |
| `05_docs/` | 276 KB | Offline copies of the NemoClaw docs (prerequisites, quickstart, vLLM/Ollama/Discord setup) |
| `07_checksums/` | 36 KB | SHA-256 checksums for the four main artifacts |
| `08_demo_backup/` | empty | Placeholder for demo backups, currently empty |

There is no `06_` folder; the numbering skips from 05 to 07.

---

## 01_installers/ — Offline installers (2.1 GB)

| Item | Size | Details |
| --- | --- | --- |
| `nemoclaw.sh` | 20 KB | NVIDIA's NemoClaw bootstrap installer (383 lines, Apache-2.0). By default it resolves the `lkg` (last-known-good) ref; set `NEMOCLAW_INSTALL_REF` / `NEMOCLAW_INSTALL_TAG` to pin a version. If `scripts/install.sh` sits next to it, it runs that local copy. |
| `node-v22.22.1-linux-arm64/` | 29 MB | Node.js 22.22.1 tarball (`.tar.xz`) and `SHASUMS256.txt`. NemoClaw requires Node 22.19 or later. |
| `npm-cache/` | 152 MB | Pre-populated npm cache (`_cacache`) for offline `npm install`. |
| `nemoclaw-v0.0.130-npm-cache/` | 176 MB | npm cache specific to NemoClaw v0.0.130. |
| `nemoclaw-v0.0.130-npm-packages/` | 56 MB | `openclaw-2026.9.2.tgz`, the OpenClaw npm package that NemoClaw v0.0.130 pins. |
| `npm-linux-arm64/` | 31 MB | `next-swc-linux-arm64-gnu-16.3.8.tgz`, the native Next.js SWC compiler for ARM64. |
| `ollama-v0.35.0-linux-arm64/` | 1.5 GB | Ollama 0.35.0 (`ollama-linux-arm64.tar.zst`) and the official `install.sh`. Extracting it needs `zstd`. |
| `openshell-v0.0.116-linux-arm64/` | 52 MB | OpenShell CLI, gateway, and sandbox binaries (`aarch64` gnu/musl tarballs), each with its `*-checksums-sha256.txt`. |
| `python-wheels-linux-arm64-py312/` | 77 MB | 48 Python 3.12 aarch64 wheels for offline `pip install` (list below). |

**Python wheels (48):**
aiohappyeyeballs 2.7.1, aiohttp 3.14.3, aiosignal 1.4.0, annotated_doc 0.0.5, annotated_types 0.8.0, anyio 4.15.1, attrs 26.1.0, certifi 2026.7.22, charset_normalizer 3.5.2, click 8.5.0, cloudpickle 3.1.2, **discord_py 2.7.1**, **fastapi 0.142.2**, frozenlist 1.8.0, h11 0.16.0, httpcore 1.0.9, **httpx 0.28.1**, idna 3.20, iniconfig 2.3.0, joblib 1.6.0, markdown_it_py 4.2.0, mdurl 0.1.2, multidict 6.9.1, narwhals 2.26.0, **numpy 2.5.3**, opentelemetry_api 1.45.0, packaging 26.3, **pandas 3.0.6**, pluggy 1.6.0, propcache 0.5.4, **pydantic 2.13.5**, pydantic_core 2.46.5, pygments 2.21.0, **pytest 9.1.1**, python_dateutil 2.9.0.post0, python_dotenv 1.2.4, **requests 2.34.2**, rich 15.0.0, **scikit_learn 1.9.1**, **scipy 1.18.1**, six 1.17.0, starlette 1.7.0, threadpoolctl 3.7.0, typing_extensions 4.16.0, typing_inspection 0.4.4, urllib3 2.8.0, **uvicorn 0.54.0**, yarl 1.25.1

Together these cover a FastAPI/uvicorn web service, a Discord bot, HTTP clients, data science (numpy/pandas/scipy/scikit-learn), and testing (pytest).

```bash
pip install --no-index --find-links /home/dell/Desktop/Deploy_starter_kit/01_installers/python-wheels-linux-arm64-py312 fastapi uvicorn discord.py
```

---

## 02_repos/ — Source code (14 GB)

Bare git mirrors, snapshotted on 2026-10-02:

| Repo | Size | Upstream | Latest commit on `main` | Recent tags |
| --- | --- | --- | --- | --- |
| `NemoClaw.git` | 446 MB | github.com/NVIDIA/NemoClaw | `fcce93c721` (2026-10-02) — *test(config): cover policy export semantics* | up to v0.0.13x |
| `OpenClaw.git` | 13 GB | github.com/openclaw/openclaw | `aac001b30b` (2026-10-02) — *fix(qa): run Telegram plugin source…* | v2026.9.5 – v2026.9.7 |
| `OpenShell.git` | 174 MB | github.com/NVIDIA/OpenShell | `ec49209da` (2026-10-02) — *fix(providers): stabilize provider environment revisions* | v0.1.3-pre.x |

Other files:

- **`NemoClaw-v0.0.130-prepared-linux-arm64.tar.gz`** (179 MB): an extracted, pre-built NemoClaw v0.0.130 tree for linux-arm64 (contains `NemoClaw/`, including `spark-install.md`). **This is the main install payload.**
- **`source_archives/`** (220 MB): `NemoClaw-main.tar.gz`, `OpenClaw-main.tar.gz`, `OpenShell-main.tar.gz`, which are plain source snapshots of `main`.

To get a working copy from a mirror:

```bash
git clone /home/dell/Desktop/Deploy_starter_kit/02_repos/NemoClaw.git ~/NemoClaw
```

---

## 03_models/ — Model weights (28 GB)

### Qwen3.6-35B-A3B-NVFP4 (22 GB) — for vLLM

The Hugging Face checkpoint `nvidia/Qwen3.6-35B-A3B-NVFP4`, which is **NemoClaw's default managed vLLM model on DGX Spark**.

| Property | Value |
| --- | --- |
| Architecture | `Qwen3_5MoeForConditionalGeneration` (`qwen3_5_moe`), multimodal (vision + video preprocessors) |
| Size | 35B total params, ~3B active (Mixture-of-Experts) |
| Layers / hidden size | 40 / 2048 |
| Experts | 256 total, 8 active per token |
| Max context | 262,144 tokens |
| Quantization | NVIDIA ModelOpt 0.44.0, `MIXED_PRECISION`: MoE experts in **W4A16 NVFP4** (group 16), linear-attention projections in FP8, **KV cache in FP8**; vision tower not quantized |
| Weight files | 3 safetensors shards (10.0 GB + 10.0 GB + 3.4 GB) |
| Also includes | `config.json`, `tokenizer.json`, `vocab.json`, `chat_template.jinja`, `generation_config.json`, `hf_quant_config.json`, `.quant_summary.txt` |

### ollama/ (6.2 GB) — for Ollama

An Ollama model store in the standard `manifests/` and `blobs/` layout, containing a single model:

| Property | Value |
| --- | --- |
| Model tag | **`qwen3.5:9b`** |
| Parameters | ~9.65B |
| Architecture | `qwen35`: hybrid attention + SSM, 32 blocks, multimodal (vision encoder) |
| Context | 262,144 tokens |
| Built with | Ollama 0.35.0 |

To use it offline, point `OLLAMA_MODELS` at this directory or copy it into `~/.ollama/models`.

---

## 04_container_images/ — Docker images (9.7 GB)

Image tarballs saved with `docker save` and gzipped. Load them with `docker load -i <file>`.

| File | Size | Role |
| --- | --- | --- |
| `nemoclaw-vllm-qwen36-gb10-arm64.tar.gz` | 9.0 GB | vLLM inference server image for GB10 (arm64), used to serve Qwen3.6-35B-A3B-NVFP4 |
| `openclaw-sandbox-v0.0.130-arm64.tar.gz` | 752 MB | OpenClaw agent sandbox image that NemoClaw v0.0.130 runs agents in |
| `openshell-supervisor-v0.0.130-arm64.tar.gz` | 16 MB | OpenShell supervisor that runs inside the sandbox and enforces policy and network egress |

```bash
for f in /home/dell/Desktop/Deploy_starter_kit/04_container_images/[!.]*.tar.gz; do docker load -i "$f"; done
```

> On this machine, the current user can't reach the Docker socket yet (`permission denied`). Add the user to the `docker` group (`sudo usermod -aG docker $USER`, then log out and back in) or use `sudo`.

---

## 05_docs/ — Offline documentation (276 KB)

Snapshots of docs.nvidia.com/nemoclaw:

| File | Lines | Covers |
| --- | --- | --- |
| `01-prerequisites.md` | 131 | Hardware (min 4 vCPU / 8 GB RAM / 20 GB disk), software (Node ≥ 22.19, npm ≥ 10, Python 3, Docker or rootless Podman, `zstd`, `binutils`), platforms, DGX Station and Windows/WSL prep |
| `02-quickstart.md` | 781 | Installing NemoClaw and launching the first OpenClaw sandbox, with both a coding-agent starter prompt and the interactive installer; troubleshooting |
| `03-local-inference-options.md` | 182 | Comparison of Ollama, managed vLLM, the fixed vLLM profile (DGX Spark Express option 2), llama.cpp, and NVIDIA NIM |
| `04-vllm-setup.md` | 731 | Existing vs. managed vLLM, serving profiles, GPU selection, HF auth, non-interactive onboarding, and the **DGX Spark Qwen recipe** |
| `05-ollama-setup.md` | 331 | Installing Ollama, Linux install modes, the authenticated proxy, Docker bridge firewall, freeing GPU memory |
| `06-discord-setup.md` | 39 | Discord bot channel: `DISCORD_BOT_TOKEN`, `DISCORD_SERVER_ID`, `DISCORD_REQUIRE_MENTION`, `DISCORD_USER_ID` |
| `nemoclaw-doc-index.txt` | 308 | Index of every NemoClaw doc page with its URL (inference providers, policies, channels, troubleshooting, etc.) |

### DGX Spark Qwen recipe (from `04-vllm-setup.md`)

NemoClaw picks the recipe automatically from the detected unified memory:

| Detected memory | Context | Concurrent seqs | Batched tokens | GPU mem util |
| --- | --- | --- | --- | --- |
| ≥ 60 GB and < 64 GB | 32,768 | 1 | 4,096 | 0.5 |
| **≥ 64 GB** | **262,144** | **4** | **8,192** | **0.4** |

This GB10 reports **121 GB** of memory, so it gets the **full 262K-context recipe**. Async scheduling is on; MTP speculative decoding is off.

---

## 07_checksums/ — Integrity checks

All four checksums were **verified on 2026-10-03 and match**:

| Artifact | SHA-256 | Status |
| --- | --- | --- |
| `02_repos/NemoClaw-v0.0.130-prepared-linux-arm64.tar.gz` | `b2454dac09c251781b73949691fe00b656cebec4628e39dac6dda081b470dd04` | ✅ match |
| `04_container_images/openclaw-sandbox-v0.0.130-arm64.tar.gz` | `4ec53858aa6af1c557df21fafe0e4e80cd1cc197be74d1a90655a191ebf52a58` | ✅ match |
| `04_container_images/openshell-supervisor-v0.0.130-arm64.tar.gz` | `a9ce64c6db96ba7e5d605d6d2c7c7eeee6195e43150af96f2b6562c14cbc42ef` | ✅ match |
| `04_container_images/nemoclaw-vllm-qwen36-gb10-arm64.tar.gz` | `9dce826dd24813dd70d883f9938be7f824de8efc4f80e7d98fe5725a98b2f899` | ✅ match |

The `.sha256` files contain macOS source paths, so `sha256sum -c` won't work on them directly. Compare the hashes by hand:

```bash
cd /home/dell/Desktop/Deploy_starter_kit
sha256sum 04_container_images/nemoclaw-vllm-qwen36-gb10-arm64.tar.gz
awk '{print $1}' 07_checksums/vllm-container.sha256
```

---

## How the pieces fit together

```
NemoClaw CLI (Node 22 + npm, installed from 01_installers + 02_repos tarball)
   │  onboards / manages
   ▼
OpenShell gateway (01_installers/openshell-*)  ──►  sandbox container
   │                                               (openclaw-sandbox image + openshell-supervisor)
   │  routes inference (credentials stay on host)        │ runs
   ▼                                                     ▼
Local inference server                              OpenClaw agent (openclaw-2026.9.2)
 ├─ vLLM image  + 03_models/Qwen3.6-35B-A3B-NVFP4        │ optional channel
 └─ Ollama 0.35 + 03_models/ollama (qwen3.5:9b)          ▼
                                                     Discord bot (06-discord-setup.md)
```

## Things to watch

1. **OpenShell versions differ:** the host binaries are **v0.0.116**, but the supervisor image is **v0.0.130**. Check that NemoClaw v0.0.130 accepts the v0.0.116 CLI/gateway; otherwise build OpenShell from `02_repos/OpenShell.git`.
2. **Docker access:** the current user isn't in the `docker` group yet, which managed vLLM and the sandbox need.
3. **Prerequisites:** NemoClaw needs `zstd` (for the Ollama archive) and `binutils` (`strings`, to verify the OpenShell binary).
4. **`08_demo_backup/` is empty:** there's nothing in it to restore.
5. **Disk space:** fine. `/` has ~3.4 TB free, and loading the images plus unpacking the models needs roughly 60–80 GB.
