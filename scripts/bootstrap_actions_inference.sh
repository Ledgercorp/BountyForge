#!/usr/bin/env bash
# BountyForge pinned, loopback-only CPU inference bootstrap for trusted Linux hosts.
# Safe to prepare before account-level GitHub Actions spending controls are verified.
set -euo pipefail
if [[ "$(uname -s)" != Linux ]]; then
  echo 'Linux-only; the local Mac is prohibited.' >&2
  exit 2
fi
for binary in curl sha256sum tar; do
  command -v "$binary" >/dev/null || { echo "Missing $binary" >&2; exit 2; }
done
mode="${1:---verify-only}"
port="${BOUNTYFORGE_PORT:-8080}"
if [[ "$port" != 8080 && "$port" != 18080 ]]; then echo "Unsupported inference port" >&2; exit 2; fi
if [[ "$mode" != '--verify-only' && "$mode" != '--serve' ]]; then
  echo 'Use --verify-only or --serve' >&2; exit 2
fi
expected_model='cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046'
expected_runtime='152e33221c9c9d37816a8ee9943f8d87339199197c80cb692559c9756b2027d8'
model_dir="${BOUNTYFORGE_MODEL_DIR:-${HOME}/.cache/bountyforge/models}"
runtime_dir="${BOUNTYFORGE_RUNTIME_DIR:-${HOME}/.cache/bountyforge/runtime}"
mkdir -p "$model_dir" "$runtime_dir"
model="$model_dir/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
archive="${BOUNTYFORGE_LLAMA_ARCHIVE:-$runtime_dir/llama-b11750-bin-ubuntu-x64.tar.gz}"
model_url='https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf'
archive_url='https://github.com/ggml-org/llama.cpp/releases/download/b11750/llama-b11750-bin-ubuntu-x64.tar.gz'
check() { printf '%s  %s\n' "$1" "$2" | sha256sum --check --status; }
if [[ ! -s "$model" ]]; then
  echo 'Downloading pinned public Qwen GGUF; no paid inference API.'
  curl --fail --location --retry 2 --connect-timeout 20 --max-time 1200 -o "$model.part" "$model_url"
  check "$expected_model" "$model.part" || { rm -f "$model.part"; echo 'Model checksum mismatch' >&2; exit 2; }
  mv -- "$model.part" "$model"
fi
check "$expected_model" "$model" || { echo 'Model checksum mismatch' >&2; exit 2; }
if [[ ! -s "$archive" ]]; then
  echo 'Downloading pinned llama.cpp b11750 CPU runtime.'
  curl --fail --location --retry 2 --connect-timeout 20 --max-time 300 -o "$archive.part" "$archive_url"
  check "$expected_runtime" "$archive.part" || { rm -f "$archive.part"; echo 'Runtime checksum mismatch' >&2; exit 2; }
  mv -- "$archive.part" "$archive"
fi
check "$expected_runtime" "$archive" || { echo 'Runtime checksum mismatch' >&2; exit 2; }
echo 'Verified model and runtime SHA-256 checksums.'
if [[ "$mode" == '--verify-only' ]]; then exit 0; fi
# The verified release archive has a fixed layout. No host credentials enter the process.
if [[ ! -x "$runtime_dir/llama-b11750/llama-server" ]]; then
  tar -xzf "$archive" -C "$runtime_dir" --no-same-owner --no-same-permissions
fi
[[ -x "$runtime_dir/llama-b11750/llama-server" ]] || { echo 'Trusted llama-server absent' >&2; exit 2; }
export LD_LIBRARY_PATH="$runtime_dir/llama-b11750"
unset GITHUB_TOKEN GH_TOKEN GITLAB_TOKEN OPENAI_API_KEY ANTHROPIC_API_KEY GROQ_API_KEY STRIPE_SECRET_KEY
exec "$runtime_dir/llama-b11750/llama-server" \
  -m "$model" --host 127.0.0.1 --port "$port" -t 2 -c 2048 -np 1
