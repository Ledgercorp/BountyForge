#!/usr/bin/env bash
# Explicit opt-in only. Linux host, CPU inference, loopback network.
set -euo pipefail
if ! command -v llama-server >/dev/null 2>&1; then
  echo "Install a trusted llama-server binary from the official llama.cpp releases first." >&2
  exit 1
fi
if ! command -v curl >/dev/null 2>&1 || ! command -v sha256sum >/dev/null 2>&1; then
  echo "Requires curl and sha256sum on Linux." >&2
  exit 1
fi
if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This project is configured for a Linux cloud host; no local Mac access." >&2
  exit 1
fi
model_dir="${BOUNTYFORGE_MODEL_DIR:-${HOME}/.cache/bountyforge/models}"
mkdir -p "${model_dir}"
model="${model_dir}/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
expected="cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046"
url="https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
if [[ ! -s "${model}" ]]; then
  echo "Downloading the official ~1.12 GB open-weight model, no inference API."
  curl --fail --location --retry 2 --connect-timeout 20 -o "${model}.part" "${url}"
  echo "${expected}  ${model}.part" | sha256sum --check --status || { rm -f "${model}.part"; echo "Model SHA-256 mismatch" >&2; exit 1; }
  mv "${model}.part" "${model}"
fi
echo "${expected}  ${model}" | sha256sum --check --status || { echo "Model SHA-256 mismatch" >&2; exit 1; }
echo "Verified official model SHA-256. Serving only at 127.0.0.1:8080."
exec llama-server -m "${model}" --host 127.0.0.1 --port 8080 -c 4096
