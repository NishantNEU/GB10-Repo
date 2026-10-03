# Sanity Report: GB10 + Deploy Starter Kit

**Date:** 2026-10-03  **Host:** Dell Pro Max GB10 (`aarch64`, DGX OS 7.6.0 OTA / Ubuntu 24.04.5)
**Script:** [`scripts/sanity_check.sh`](scripts/sanity_check.sh) (read-only; rerun with `scripts/sanity_check.sh`, or `--no-checksums` to skip the ~1 min hashing)
**Result:** **33 PASS, 10 WARN, 2 FAIL**

## Summary

The hardware, OS, GPU, Python, toolchain and the kit itself are all in good shape. All 8 checksums match. Nothing from the NemoClaw stack is installed yet.

- **Only hard blocker:** your user can't use Docker. You're not in the `docker` group, so every Docker step fails, and that also kept the script from checking which images are loaded.
- **The OpenShell version mismatch isn't real.** The supervisor image named `…v0.0.130` actually contains OpenShell **0.0.116**, the exact version NemoClaw 0.0.130 requires (investigation A).
- **Managed vLLM won't fully use the kit's Qwen weights.** The kit's copy is a different Hugging Face revision from the one NemoClaw pins, and it's a plain folder, not the cache layout NemoClaw reuses (investigation B). For a fixed memory budget with no downloads, start vLLM yourself from the kit image and weights, then let NemoClaw attach to it.
- **This machine has internet.** github.com, huggingface.co and the npm registry respond, and nvcr.io and ghcr.io reply 401 (reachable, need login). So nothing here is fatal if the kit falls short; the cost is time and roughly 33 GB of downloads.

---

## 1. Check results

| # | Check | Status | Finding |
|---|---|---|---|
| 1 | Architecture | PASS | `aarch64` |
| 1 | OS | PASS | Ubuntu 24.04.5 LTS, kernel `7.0.0-1019-nvidia`, DGX SW build 7.2.3 / OTA 7.6.0 |
| 1 | Memory | PASS | 121 GiB total, 112 GiB available, 15 GiB swap |
| 1 | Disk | PASS | 3,388 GiB free on `/dev/nvme0n1p2`; `~` and the kit are on the same drive |
| 1 | GPU | PASS | `nvidia-smi` works: NVIDIA GB10, driver **580.178.04**, CUDA **13.0** (nvcc 13.0). The vLLM preset requires driver ≥ 580.65.06. |
| 2 | Docker installed / daemon | PASS | Docker 29.6.2, `docker.service` active |
| 2 | Docker without sudo | **FAIL** | `dell` isn't in group `docker` (the group has no members), and `/var/run/docker.sock` is `root:docker 660`, so `docker ps` gets permission denied |
| 2 | `/etc/docker/daemon.json` | INFO | Doesn't exist. **Fine:** NemoClaw 0.0.130 doesn't need cgroupns set, because OpenShell sets host cgroupns on its own container (`src/lib/onboard/preflight.ts:865-866`) |
| 2 | NVIDIA Container Toolkit / CDI | PASS | `nvidia-ctk` 1.20.1; `/var/run/cdi/nvidia.yaml` lists `nvidia.com/gpu=0`, `=all` and the GPU UUID |
| 2 | Loaded images + arch | WARN | Couldn't check without Docker access. **Read from the kit tarballs instead:** all three are `linux/arm64` (details in A and B) |
| 3 | Node / npm | WARN | Node **24.21.0** (from nvm; kit ships 22.22.1; NemoClaw needs ≥ 22.19, so OK); npm 11.19.0 |
| 4 | Ollama | WARN | Not installed; only needed if you use the Ollama path |
| 5 | vLLM | WARN | Couldn't check without Docker access. Nothing answers on `localhost:8000` |
| 6 | OpenShell | WARN | Not on PATH |
| 7 | NemoClaw / OpenClaw | WARN | `nemoclaw` not installed. `openclaw` isn't on the host, which is normal because it runs inside the sandbox. `~/.nemoclaw`, `~/.openclaw` and `~/.config/openshell` don't exist (clean slate) |
| 8 | Python | PASS | Python 3.12.3 at `/usr/bin/python3` (matches the kit's `cp312` wheels and NemoClaw's trusted path); pip 24.0; venv + ensurepip OK |
| 9 | git / tmux | PASS | git 2.43.0, tmux 3.4; also `zstd`, `strings`, `curl`, `jq`, `lsof` present (NemoClaw prerequisites) |
| 9 | Repo | WARN | `origin` = `git@github.com:NishantNEU/GB10-Repo.git`, branch `main`, **no commits yet** |
| 10 | Kit size / layout | PASS | 54 GB: `01_installers` 2.1G, `02_repos` 14G, `03_models` 28G, `04_container_images` 9.7G, `05_docs` 276K, `07_checksums` 36K, `08_demo_backup` empty |
| 10 | macOS `._*` files | WARN | 2,799 in the kit, **2,768 of them in the npm cache** (see below). The NemoClaw prepared tarball holds another **44,620** `._*` entries. The wheels folder and the Ollama store are clean |
| 10 | `08_demo_backup` | PASS | Empty, as expected |
| 10 | Checksums | PASS | All 8 match: the 4 in `07_checksums/`, the Node tarball against `SHASUMS256.txt`, and the 3 OpenShell tarballs against their `*-checksums-sha256.txt` |

**Where the `._*` files are that installers may trip on:**

```
2760  01_installers/nemoclaw-v0.0.130-npm-cache/_cacache/…   (inside the npm content cache)
   4  01_installers/nemoclaw-v0.0.130-npm-cache/_logs/
   3  01_installers/nemoclaw-v0.0.130-npm-cache/.__cacache, .__logs, .__update-notifier-last-checked
   1  01_installers/nemoclaw-v0.0.130-npm-packages/._openclaw-2026.9.2.tgz
```

npm checks cache entries by hash, so stray `._*` files in `_cacache` are probably ignored. But anything that globs `*.tgz` will pick up `._openclaw-2026.9.2.tgz`, which is a 4 KB AppleDouble file, not a tarball. When extracting the NemoClaw tarball, always pass `--exclude='._*'`, or you'll get 44,620 junk files in the source tree.

---

## A. OpenShell compatibility (NemoClaw 0.0.130 vs. the kit's OpenShell)

**Conclusion: compatible. NemoClaw v0.0.130 requires exactly OpenShell 0.0.116, and both the kit's binaries and its supervisor image are 0.0.116.** The "v0.0.130" in the supervisor's file name is the NemoClaw release it was bundled for, not an OpenShell version.

What NemoClaw v0.0.130 expects (tag `v0.0.130` = commit `a73099c773`, read with `git grep` in `02_repos/NemoClaw.git`):

| Evidence | File:line | Content |
|---|---|---|
| Blueprint version range | `nemoclaw-blueprint/blueprint.yaml:6-7` | `min_openshell_version: "0.0.116"` / `max_openshell_version: "0.0.116"` |
| Installer range | `scripts/install-openshell.sh:120,123,131` | `MIN_VERSION="0.0.116"`, `MAX_VERSION="0.0.116"`, `DEV_MIN_VERSION="0.0.116"` |
| Installer per-asset pins | `scripts/install-openshell.sh:223,232,241` | `v0.0.116:openshell-aarch64-unknown-linux-musl.tar.gz`, `…gateway-aarch64-unknown-linux-gnu…`, `…sandbox-aarch64-unknown-linux-musl…` (the same 3 files as in the kit) |
| SDK dependency | `package.json:129` | `"@nvidia/openshell-sdk": "0.0.116"` |
| Runtime constant | `nemoclaw/src/shared/openshell-external-target-boundary.cts:35` | `EXTERNAL_OPENSHELL_RELEASE = "0.0.116"` |
| Supervisor image pin | `src/lib/onboard/docker-driver-gateway-runtime.ts:50` | `"0.0.116": "sha256:c8c42aef16c2…ecead42"` |
| Supervisor image selection | `src/lib/onboard/docker-driver-gateway-runtime.ts:240-255` | Throws unless the version is exactly 0.0.116; uses `ghcr.io/nvidia/openshell/supervisor@<pinned digest>`; rejects any other `OPENSHELL_DOCKER_SUPERVISOR_IMAGE` override |
| Docs | `docs/reference/architecture.mdx:90` | "Managed installations require exact stable OpenShell 0.0.116" |

What the kit actually contains (read straight from the tarballs, no Docker needed):

| Kit artifact | Found |
|---|---|
| `openshell-v0.0.116-linux-arm64/*.tar.gz` | `openshell`, `openshell-gateway`, `openshell-sandbox` single binaries; sha256 matches the release checksum files |
| `openshell-supervisor-v0.0.130-arm64.tar.gz` | Tag `ghcr.io/nvidia/openshell/supervisor:nemoclaw-v0.0.130-arm64`. **OCI index digest `sha256:c8c42aef…ecead42`, the exact digest NemoClaw pins for 0.0.116.** The `/openshell-sandbox` binary inside contains the string `0.0.116`. Multi-arch index; the arm64 manifest is `sha256:34e0ba2b…` |
| `openclaw-sandbox-v0.0.130-arm64.tar.gz` | Tag `ghcr.io/nvidia/nemoclaw/openclaw-sandbox:v0.0.130`, `linux/arm64`, label `org.opencontainers.image.revision=a73099c7…` (= the v0.0.130 tag commit), built with Node 24.18.1. Its repository matches `src/lib/onboard/managed-image/contract.ts:53`. The release digest isn't pinned in source, which is expected because it's resolved at publish time |

**Remaining risk:** NemoClaw refers to the supervisor by **digest** (`…/supervisor@sha256:c8c42aef…`). Docker 29 uses the containerd image store, which should keep the index digest after `docker load`. But if `docker image inspect ghcr.io/nvidia/openshell/supervisor@sha256:c8c42aef16c200063e32cbf72e553e4ead027085427b555efafd95063ecead42` fails after loading, NemoClaw will just pull it from ghcr.io. That works here because there's internet. The check is in the commands section.

---

## B. vLLM memory settings for Qwen3.6-35B-A3B-NVFP4

### Where NemoClaw sets them

Managed vLLM is driven by catalog YAML. A **preset** (which hosts qualify, plus a priority) points to a **recipe** (container image and `vllm serve` arguments).

| What | File:line (NemoClaw `v0.0.130`) | Value |
|---|---|---|
| Default preset on this host | `managed-inference/presets/vllm.dgx-spark-gb10.single.qwen3-6-35b-a3b-nvfp4.yaml:16-18,111` | `selection: automatic`, `priority: 550` → recipe `vllm.qwen3-6-35b-a3b-nvfp4.spark-single.v1` |
| **Context length** | `managed-inference/recipes/vllm.qwen3-6-35b-a3b-nvfp4.spark-single.v1.yaml:50-51` | `--max-model-len 262144` (the 262K setting) |
| **GPU memory utilization** | same file `:52-53` | `--gpu-memory-utilization 0.4` |
| Concurrency / batch | same file `:64-67` | `--max-num-seqs 4`, `--max-num-batched-tokens 8192` |
| Other arguments | same file `:54-77` | `--quantization modelopt`, `--kv-cache-dtype fp8`, `--attention-backend flashinfer`, `--moe-backend marlin`, chunked prefill, `--async-scheduling`, prefix caching, `--enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3`, `--load-format fastsafetensors` |
| Runtime image | same file `:16` | `nvcr.io/nvidia/vllm@sha256:9204569b17ee…c659e2`; recipe needs ≥ 64 GB (`:20`) |
| Smaller sibling preset | `managed-inference/presets/vllm.dgx-spark-gb10.single-64gb.qwen3-6-35b-a3b-nvfp4.yaml:10,16-18,112` | `supportState: experimental`, `priority: 549` → recipe `…spark-single-64gb.v1` |
| Smaller sibling recipe | `managed-inference/recipes/vllm.qwen3-6-35b-a3b-nvfp4.spark-single-64gb.v1.yaml:21,51-54,65-68` | min memory 60 GB; **`--max-model-len 32768`, `--gpu-memory-utilization 0.5`**, `--max-num-seqs 1`, `--max-num-batched-tokens 4096` |
| Which preset wins | `src/lib/inference/serving/resolver.ts:426-447` + priorities | Both presets fit 121 GB; the higher priority (550, the full 262K recipe) is picked automatically |
| Model definition | `managed-inference/models/vllm.qwen3-6-35b-a3b-nvfp4.v1.yaml:10-12,16` | `nvidia/Qwen3.6-35B-A3B-NVFP4`, **revision `491c2f1ea524…`**, env slug `qwen3.6-35b-a3b-nvfp4`, 23.5 GB download |

### How to override each setting

| Mechanism | Evidence | Notes |
|---|---|---|
| **Env `NEMOCLAW_VLLM_EXTRA_ARGS_JSON`** (JSON array of `vllm serve` tokens) | Parsed in `src/lib/inference/vllm-models.ts:578,678-712`; appended after the recipe arguments at `:1010-1015`; documented in `05_docs/04-vllm-setup.md:691-724` | vLLM uses the **last** value, so `["--gpu-memory-utilization","0.5","--max-model-len","65536"]` overrides both. NemoClaw also uses the last `--gpu-memory-utilization` value for its free-memory preflight (`04-vllm-setup.md:695`). Allowed for the Qwen Spark recipe because `fixedArguments: false` (recipe `:46`). Must be paired with `NEMOCLAW_PROVIDER=install-vllm` and `NEMOCLAW_VLLM_MODEL=qwen3.6-35b-a3b-nvfp4`; **can't** be combined with `--profile` or `NEMOCLAW_SERVING_PRESET` (`src/lib/inference/serving/host-local-vllm-selection.ts:192-205`) |
| **Onboarding flag `--profile <id>`** | `05_docs/04-vllm-setup.md:121-135` | `nemoclaw onboard --profile vllm.dgx-spark-gb10.single-64gb.qwen3-6-35b-a3b-nvfp4` gives exactly **0.5 / 32K**, but it's *experimental* and uses `--max-num-seqs 1`. The docs explain that a second sequence is what lets a context-compaction summary run while the agent is answering (`04-vllm-setup.md` around line 384), so 1 can stall long agent sessions. Run `nemoclaw profiles list` first to confirm it shows as compatible |
| **Env `NEMOCLAW_CONTEXT_WINDOW`** | `src/lib/inference/vllm-runtime-context.ts:90-108` | This is what OpenClaw is *told*, not what vLLM allocates. By default onboarding reads `max_model_len` from vLLM's `/v1/models`, so lowering `--max-model-len` carries through automatically. Set this only to make the agent use less than the server allows |
| Config file | — | No user config file overrides recipe arguments; the recipes ship inside the NemoClaw source tree. Editing `managed-inference/recipes/*.yaml` in your NemoClaw checkout would work but changes the catalog fingerprint (`04-vllm-setup.md:206`). Not recommended |

### Catch: the kit's model files don't match what managed vLLM expects

- NemoClaw pins revision **`491c2f1ea524c639598bf8fa787a93fed5a6fbce`** and passes `--revision` to vLLM (`vllm-models.ts:1006`). The kit's weights were downloaded at revision **`1355db6a052410cfd62085d94b58866fd0f2c3c5`** (`03_models/Qwen3.6-35B-A3B-NVFP4/.cache/huggingface/download/*.metadata`).
- Managed vLLM mounts `~/.cache/huggingface` as the HF cache (`src/lib/inference/vllm.ts:204-213,247-256`). That directory doesn't exist yet, and the kit's model is a `--local-dir` copy, not cache layout.
- **Result:** the managed path will download ~23.5 GB from Hugging Face. It will also pull the vLLM image from nvcr.io unless `nvcr.io/nvidia/vllm@sha256:9204569b…` resolves locally. The kit's vLLM tarball **has exactly that digest**, but it's named `nemoclaw-vllm:qwen36-gb10-arm64`.

### Recommendation: run vLLM yourself, then attach NemoClaw

This uses the kit image and weights as-is, downloads nothing, and puts the memory knobs on your own command line, which suits a memory-pressure demo. NemoClaw supports attaching to an already-running server (`05_docs/04-vllm-setup.md:38-80`). It reads `/v1/models` and sets the context window from `max_model_len`. The `docker run` command is in step 5 below.

Memory budget: `0.5 × ~121 GiB ≈ 60 GiB` for vLLM. About 22 GiB of that is weights and the rest is FP8 KV cache, which is plenty for 64K tokens and 2 sequences. That leaves about 60 GiB of unified memory for the OS, the OpenShell gateway, the sandbox and your memory-pressure scenario. NemoClaw's docs warn that on Spark, running out of unified memory can show up as `NV_ERR_NO_MEMORY`, lost SSH or a hard host freeze (`04-vllm-setup.md:74-80`). Keep the pressure scenario bounded, for example with a cgroup or `docker run --memory`, not unbounded host allocation.

---

## Component table

| Component | Expected version | Found | Status |
|---|---|---|---|
| CPU arch | aarch64 | aarch64 | PASS |
| OS | Ubuntu 24.04 / DGX OS | Ubuntu 24.04.5, DGX OS 7.6.0 OTA | PASS |
| NVIDIA driver | ≥ 580.65.06 (Qwen preset) | 580.178.04 | PASS |
| CUDA | 13.x | 13.0 (driver + nvcc) | PASS |
| GPU memory (unified) | ≥ 64 GB (Qwen recipe) | 121 GiB | PASS |
| Docker | Docker Engine, usable without sudo | 29.6.2, **no access for `dell`** | **FAIL** |
| NVIDIA Container Toolkit / CDI | present (preset requirement) | 1.20.1, 3 CDI GPU devices | PASS |
| Node.js | ≥ 22.19 (kit: 22.22.1) | 24.21.0 (nvm) | WARN (OK) |
| npm | ≥ 10 | 11.19.0 | PASS |
| Python | 3.12 (kit wheels cp312) | 3.12.3, pip 24.0, venv OK | PASS |
| Ollama | 0.35.0 (kit) | not installed | WARN (optional) |
| OpenShell CLI / gateway | **exactly 0.0.116** | not installed (kit has 0.0.116, checksums OK) | WARN |
| OpenShell supervisor image | digest `c8c42aef…` (0.0.116) | kit tarball has the same digest; not loaded | WARN |
| NemoClaw | 0.0.130 | not installed (kit tarball OK) | WARN |
| OpenClaw | 2026.9.2 (npm pin) / sandbox image v0.0.130 | in kit; not loaded | WARN |
| vLLM image | `nvcr.io/nvidia/vllm@sha256:9204569b…` | kit tarball has the same digest, named `nemoclaw-vllm:qwen36-gb10-arm64`; not loaded | WARN |
| Qwen3.6-35B-A3B-NVFP4 weights | HF revision `491c2f1e…` | kit has revision `1355db6a…` (local-dir layout) | WARN |
| Kit checksums | match | 8/8 match | PASS |
| git / tmux | present | 2.43.0 / 3.4 | PASS |

---

## Blockers, in the order to fix them

1. **Docker access (FAIL):** add `dell` to the `docker` group and start a new login session. Everything else depends on this.
2. **Confirm GPU-in-Docker works:** CDI is present, but no container has actually been run yet.
3. **Load the kit images and make NemoClaw's digest references resolve locally:** load all three, tag the vLLM image under `nvcr.io/nvidia/vllm`, and confirm both digest lookups work.
4. **Install OpenShell 0.0.116, then NemoClaw 0.0.130.** Install the OpenShell binaries from the kit first, so NemoClaw's version check passes without downloading.
5. **Start vLLM with your memory settings** (0.5 / 64K), **block port 8000 from the venue network**, and **check that tool calling works** before onboarding.
6. **Onboard NemoClaw against local vLLM only** (no cloud provider), then record the memory baseline.
7. *(Optional)* **Ollama:** only if you want the `qwen3.5:9b` fallback path.
8. *(Hygiene)* Always extract kit tarballs with `--exclude='._*'`. Don't glob `*.tgz` in `nemoclaw-v0.0.130-npm-packages/`.

## Commands to run

Nothing below has been run. Lines starting with `sudo` need your password.

**Before you start:** run everything from step 2 onward inside tmux, so a disconnect doesn't kill the model load or the install. Start tmux *after* step 1's re-login, not before (see the note in step 1).

```bash
KIT=~/Desktop/Deploy_starter_kit

# 1. Docker access ---------------------------------------------------------
sudo usermod -aG docker "$USER"
# Then log out and back in (or reboot). `newgrp docker` only fixes the current shell.
# tmux: a running tmux *server* keeps the groups it started with, and so does every new
# session/window it creates. So after re-login, restart the server, not just the session:
tmux kill-server 2>/dev/null               # no tmux server was running at check time, but be sure
tmux new -s setup
id -nG | tr ' ' '\n' | grep -x docker      # should print: docker
docker ps                                  # should work without sudo

# 3. Load kit images (do this before step 2: it gives step 2 a local image to test with)
for f in "$KIT"/04_container_images/[!.]*.tar.gz; do docker load -i "$f"; done
docker images --digests
docker image inspect --format '{{.RepoTags}} {{.Architecture}}' \
  nemoclaw-vllm:qwen36-gb10-arm64 \
  ghcr.io/nvidia/openshell/supervisor:nemoclaw-v0.0.130-arm64 \
  ghcr.io/nvidia/nemoclaw/openclaw-sandbox:v0.0.130          # all should say arm64

# Give the vLLM image the repository name NemoClaw's recipe uses
docker tag nemoclaw-vllm:qwen36-gb10-arm64 nvcr.io/nvidia/vllm:26.05.post1-py3

# Check that NemoClaw's pinned digest references resolve offline (each should print an ID, not an error)
docker image inspect --format '{{.Id}}' \
  ghcr.io/nvidia/openshell/supervisor@sha256:c8c42aef16c200063e32cbf72e553e4ead027085427b555efafd95063ecead42
docker image inspect --format '{{.Id}}' \
  nvcr.io/nvidia/vllm@sha256:9204569b17ee4c0eff75194b8e6e458479c8aee18953b5ab9cf359fcdac659e2
# If either fails, NemoClaw will pull that image from the registry instead (internet works here).

# 2. GPU inside a container -------------------------------------------------
docker run --rm --gpus all --entrypoint nvidia-smi nemoclaw-vllm:qwen36-gb10-arm64

# 4. OpenShell 0.0.116 from the kit (user-local, no sudo) -------------------
mkdir -p ~/.local/bin
for t in openshell-aarch64-unknown-linux-musl openshell-gateway-aarch64-unknown-linux-gnu \
         openshell-sandbox-aarch64-unknown-linux-musl; do
  tar xzf "$KIT/01_installers/openshell-v0.0.116-linux-arm64/$t.tar.gz" -C ~/.local/bin
done
export PATH="$HOME/.local/bin:$PATH"       # add to ~/.bashrc if it isn't already on PATH
openshell --version                        # expect 0.0.116

# 4b. NemoClaw 0.0.130 from the kit's prepared tarball
tar xzf "$KIT/02_repos/NemoClaw-v0.0.130-prepared-linux-arm64.tar.gz" -C ~ --exclude='._*'
ls -d ~/NemoClaw*                          # the tarball's top folder is NemoClaw/ (checked), so expect ~/NemoClaw
cd ~/NemoClaw && bash install.sh           # uses the local scripts/install.sh payload; may prompt for sudo
# Online alternative, pinned to the same release:
#   NEMOCLAW_INSTALL_TAG=v0.0.130 bash "$KIT/01_installers/nemoclaw.sh"
nemoclaw --version
nemoclaw profiles list                     # confirm the Qwen Spark profiles show as compatible
# If the installer goes straight into onboarding, cancel it with Ctrl+C, do step 5, then run step 5b.

# 5. vLLM with your memory budget (kit image + kit weights, no downloads) ---
docker run -d --name pitcrew-vllm --restart unless-stopped \
  --gpus all --ipc=host --ulimit memlock=-1 --ulimit stack=67108864 \
  -p 8000:8000 \
  -v "$KIT/03_models/Qwen3.6-35B-A3B-NVFP4":/models/qwen:ro \
  -e HF_HUB_OFFLINE=1 \
  nemoclaw-vllm:qwen36-gb10-arm64 \
  vllm serve /models/qwen \
    --served-model-name nvidia/Qwen3.6-35B-A3B-NVFP4 \
    --host 0.0.0.0 --port 8000 \
    --gpu-memory-utilization 0.5 \
    --max-model-len 65536 \
    --max-num-seqs 2 --max-num-batched-tokens 4096 \
    --dtype auto --quantization modelopt --kv-cache-dtype fp8 \
    --attention-backend flashinfer --moe-backend marlin \
    --enable-chunked-prefill --enable-prefix-caching \
    --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3
docker logs -f pitcrew-vllm                # wait for "Application startup complete" (a few minutes)
curl -s localhost:8000/v1/models | jq '.data[] | {id, max_model_len}'   # expect 65536

# 5a. Block port 8000 from the venue network ---------------------------------
# ufw does NOT block ports that Docker publishes: Docker's own iptables rules route that
# traffic before ufw sees it. Use Docker's DOCKER-USER chain instead.
IFACE=$(ip route get 8.8.8.8 | awk '{for(i=1;i<=NF;i++) if($i=="dev") print $(i+1)}')   # wlP9s9 (Wi-Fi) at check time
sudo iptables -I DOCKER-USER -i "$IFACE" -p tcp --dport 8000 -j DROP
sudo iptables -I DOCKER-USER -i enP7s7 -p tcp --dport 8000 -j DROP      # Ethernet: down now, covered if you plug in
# IPv6: the Wi-Fi only has a link-local address, but docker-proxy may still listen on [::]:8000.
# That traffic goes through INPUT, not DOCKER-USER, so block it there:
sudo ip6tables -I INPUT -i "$IFACE" -p tcp --dport 8000 -j DROP
curl -s localhost:8000/v1/models | jq .    # still works locally
sudo iptables -L DOCKER-USER -n --line-numbers                         # confirm the DROP rules are on top
# From another laptop on the venue network (should time out):  curl -m 3 http://172.20.65.95:8000/v1/models
# These rules don't survive a reboot or a Docker restart; re-run 5a after either.
# The sandbox still reaches vLLM through Docker's internal bridge, which these rules don't touch.
# If `nemoclaw <sandbox> status` later shows inferenceHealth failing, list the rules and
# remove the matching one with `sudo iptables -D DOCKER-USER <num>`.

# 5b. Check that tool calling works before onboarding -----------------------
# The whole agent depends on this.
curl -s localhost:8000/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model":"nvidia/Qwen3.6-35B-A3B-NVFP4",
  "messages":[{"role":"user","content":"Check current machine memory usage."}],
  "tools":[{"type":"function","function":{"name":"get_metrics","description":"Get current CPU, memory, disk and GPU metrics","parameters":{"type":"object","properties":{}}}}]
}' | jq '.choices[0].message.tool_calls'
# Expect a get_metrics call. If you get null, look for tool-parser errors in
# `docker logs pitcrew-vllm` before going any further.

# 5c. Attach NemoClaw to the running server ---------------------------------
nemoclaw onboard                           # choose "Local vLLM"; it reads max_model_len from /v1/models
# Or non-interactive:  NEMOCLAW_PROVIDER=vllm nemoclaw onboard --non-interactive   (provider value per 04-vllm-setup.md:41)
# If onboarding offers NVIDIA cloud models or asks for an API key, don't take that path:
# it would put a cloud LLM in the agent's runtime path.

# 5d. Record the memory baseline --------------------------------------------
free -h
# Before vLLM, 9 GiB was in use. 0.5 x ~121 GiB adds about 60 GiB, so expect roughly 65-70 GiB "used".
# The ~22 GiB of weights read from disk also show up under buff/cache; the kernel can reclaim that,
# so don't count it as pressure. Set the demo's alert thresholds from this measured
# baseline, not from defaults.

# --- Alternative to steps 5/5b: let NemoClaw manage vLLM with overrides --------------------
# Downloads ~23.5 GB of weights at revision 491c2f1e unless ~/.cache/huggingface already has them.
#   NEMOCLAW_PROVIDER=install-vllm \
#   NEMOCLAW_VLLM_MODEL=qwen3.6-35b-a3b-nvfp4 \
#   NEMOCLAW_VLLM_EXTRA_ARGS_JSON='["--gpu-memory-utilization","0.5","--max-model-len","65536","--max-num-seqs","2","--max-num-batched-tokens","4096"]' \
#   nemoclaw onboard --non-interactive
# Or the built-in experimental 0.5 / 32K profile (max-num-seqs 1):
#   nemoclaw onboard --profile vllm.dgx-spark-gb10.single-64gb.qwen3-6-35b-a3b-nvfp4

# 6. Optional: Ollama 0.35.0 from the kit (installs a system service; needs sudo)
#   cd "$KIT/01_installers/ollama-v0.35.0-linux-arm64" && sudo sh install.sh
#   Then serve the kit model store: OLLAMA_MODELS="$KIT/03_models/ollama" ollama serve
```

Notes on step 5:
- `-p 8000:8000` publishes an **unauthenticated** vLLM API on every interface, including the hackathon LAN, and **ufw won't stop it**. Step 5a closes it with `DOCKER-USER` rules while leaving the Docker bridge open for the sandbox. A `127.0.0.1:8000:8000` binding isn't the fix, because it may also cut off the sandbox. For the pitch: Pitcrew's own model API isn't exposed to the network.
- `--max-num-seqs 2` follows NemoClaw's own reasoning that a second sequence lets context compaction run alongside a response. `--async-scheduling` is left off, as in the docs' "bounded resource" example (`04-vllm-setup.md:715-720`).
- To change the memory budget for the demo, `docker rm -f pitcrew-vllm` and rerun step 5 with new values. NemoClaw reads the new `max_model_len` the next time it probes. Set `NEMOCLAW_CONTEXT_WINDOW` only if you want the agent to use less than the server allows.

---

<details>
<summary>Raw output of <code>scripts/sanity_check.sh</code></summary>

```

== 1. System ==
  PASS  arch: aarch64
  INFO  OS: Ubuntu 24.04.5 LTS  kernel: 7.0.0-1019-nvidia
  PASS  Ubuntu 24.04
  INFO  DGX OS: DGX_SWBUILD_VERSION="7.2.3" DGX_OTA_VERSION="7.6.0" 
                       total        used        free      shared  buff/cache   available
        Mem:           121Gi       9.0Gi        50Gi       164Mi        62Gi       112Gi
        Swap:           15Gi          0B        15Gi
  PASS  memory: 121 GiB total
  PASS  disk free in ~: 3388 GiB
  PASS  disk free on kit drive (/dev/nvme0n1p2): 3388 GiB
  PASS  nvidia-smi works
  INFO  GPU, driver: NVIDIA GB10, 580.178.04
  INFO  CUDA (driver-supported): 13.0
  PASS  GPU is GB10
  INFO  nvcc: release 13.0

== 2. Docker ==
  PASS  docker installed: Docker version 29.6.2, build dfc4efb
  PASS  docker daemon: active (systemd)
  FAIL  user dell is NOT in the docker group
  FAIL  docker ps without sudo: permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
  INFO  /etc/docker/daemon.json does not exist (defaults; cgroupns not required by NemoClaw 0.0.130)
  PASS  nvidia container toolkit: 1.20.1
  PASS  CDI spec lists 3 nvidia.com/gpu device(s)
  WARN  skipping image list/arch check (no docker access)

== 3. Node and npm ==
  WARN  node 24.21.0 (kit ships 22.22.1; >=22.19 is OK)
  INFO  node path: /home/dell/.nvm/versions/node/v24.21.0/bin/node
  PASS  npm 11.19.0

== 4. Ollama ==
  WARN  ollama not installed (kit ships 0.35.0; only needed for the Ollama path)

== 5. vLLM ==
  WARN  cannot check vLLM image/containers (no docker access)

== 6. OpenShell ==
  WARN  openshell not on PATH (kit binaries: 01_installers/openshell-v0.0.116-linux-arm64)

== 7. NemoClaw and OpenClaw ==
  WARN  nemoclaw not installed (kit: 02_repos/NemoClaw-v0.0.130-prepared-linux-arm64.tar.gz)
  INFO  openclaw not on host PATH (normal: NemoClaw runs it inside the sandbox image)
  INFO  /home/dell/.nemoclaw: absent
  INFO  /home/dell/.openclaw: absent
  INFO  /home/dell/.config/openshell: absent
  INFO  /home/dell/.openshell: absent

== 8. Python ==
  PASS  python3 3.12.3 (matches kit wheels cp312)
  INFO  python3 path: /usr/bin/python3
  PASS  /usr/bin/python3 exists (NemoClaw sanitizer trusted path)
  PASS  pip: pip 24.0
  PASS  venv + ensurepip available

== 9. git, tmux, repo ==
  PASS  git 2.43.0
  PASS  tmux 3.4
  PASS  zstd present
  PASS  strings present
  PASS  curl present
  PASS  jq present
  PASS  lsof present
  INFO  repo: /home/dell/GB10-Repo
  INFO  remote: git@github.com:NishantNEU/GB10-Repo.git
  INFO  branch: main
  WARN  repo has no commits yet

== 10. Kit ==
  PASS  kit found: /home/dell/Desktop/Deploy_starter_kit
  INFO  total size: 54G
  INFO  layout:
        2.1G	01_installers/
        14G	02_repos/
        28G	03_models/
        9.7G	04_container_images/
        276K	05_docs/
        36K	07_checksums/
        4.0K	08_demo_backup/
  WARN  2799 macOS ._* AppleDouble files in kit
  WARN  2768 ._* files inside wheel/npm-cache/ollama-store folders (installers may choke)
  INFO  count by folder:
              1 01_installers/nemoclaw-v0.0.130-npm-cache/.__cacache
           2760 01_installers/nemoclaw-v0.0.130-npm-cache/_cacache
              1 01_installers/nemoclaw-v0.0.130-npm-cache/.__logs
              4 01_installers/nemoclaw-v0.0.130-npm-cache/_logs
              1 01_installers/nemoclaw-v0.0.130-npm-cache/.__update-notifier-last-checked
              1 01_installers/nemoclaw-v0.0.130-npm-packages/._openclaw-2026.9.2.tgz
  INFO  examples:
        01_installers/nemoclaw-v0.0.130-npm-cache/.__logs
        01_installers/nemoclaw-v0.0.130-npm-cache/.__update-notifier-last-checked
        01_installers/nemoclaw-v0.0.130-npm-cache/.__cacache
        01_installers/nemoclaw-v0.0.130-npm-cache/_logs/._2026-10-03T03_07_38_304Z-debug-0.log
        01_installers/nemoclaw-v0.0.130-npm-cache/_logs/._2026-10-03T03_06_20_233Z-debug-0.log
        01_installers/nemoclaw-v0.0.130-npm-cache/_logs/._2026-10-03T03_07_40_930Z-debug-0.log
        01_installers/nemoclaw-v0.0.130-npm-cache/_logs/._2026-10-03T03_06_17_725Z-debug-0.log
        01_installers/nemoclaw-v0.0.130-npm-packages/._openclaw-2026.9.2.tgz
  WARN  NemoClaw prepared tarball contains 44620 ._* entries (extract with --exclude='._*')
  PASS  08_demo_backup is empty (as expected)
  PASS  sha256 OK: 02_repos/NemoClaw-v0.0.130-prepared-linux-arm64.tar.gz
  PASS  sha256 OK: 04_container_images/openclaw-sandbox-v0.0.130-arm64.tar.gz
  PASS  sha256 OK: 04_container_images/openshell-supervisor-v0.0.130-arm64.tar.gz
  PASS  sha256 OK: 04_container_images/nemoclaw-vllm-qwen36-gb10-arm64.tar.gz
  PASS  sha256 OK: node tarball
  PASS  sha256 OK: openshell/openshell-aarch64-unknown-linux-musl.tar.gz
  PASS  sha256 OK: openshell/openshell-gateway-aarch64-unknown-linux-gnu.tar.gz
  PASS  sha256 OK: openshell/openshell-sandbox-aarch64-unknown-linux-musl.tar.gz

== Summary ==
  PASS 33   WARN 10   FAIL 2
```

</details>
