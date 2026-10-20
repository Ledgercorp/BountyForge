"""Verify and join the six BountyForge Google Drive model chunks.

Requires only Python 3.11+ and the original manifest.json.
Never downloads, executes or modifies the original Drive GGUF.
"""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

MODEL = "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
SIZE = 1117320768
SHA256 = "cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046"
CHUNK = 2 * 1024 * 1024

def reassemble(folder: Path, target: Path) -> dict:
    folder = Path(folder).resolve(strict=True)
    target = Path(target)
    if target.exists() or target.is_symlink():
        raise ValueError("Output already exists, refusing overwrite")
    manifest_path = folder / "manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError("Missing or linked manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("model"), manifest.get("source_bytes"), manifest.get("expected_sha256")) != (MODEL, SIZE, SHA256):
        raise ValueError("Wrong model manifest")
    parts = manifest.get("parts")
    if not isinstance(parts, list) or len(parts) != 6:
        raise ValueError("Expected exactly 6 model parts")
    temp = target.with_suffix(target.suffix + ".partial")
    target.parent.mkdir(parents=True, exist_ok=True)
    if temp.exists():
        raise ValueError("Partial output exists")
    full_hash = hashlib.sha256()
    written = 0
    try:
        with temp.open("xb") as output:
            for idx, part in enumerate(parts, 1):
                name = f"{MODEL}.part{idx:03}"
                if not isinstance(part, dict) or part.get("name") != name:
                    raise ValueError(f"Invalid part {idx} entry")
                path = folder / name
                if path.is_symlink() or not path.is_file():
                    raise ValueError(f"Missing or linked part {idx}")
                size = path.stat().st_size
                if size != part.get("bytes") or not 0 < size <= 200 * 1024 * 1024:
                    raise ValueError(f"Wrong part {idx} length")
                digest = hashlib.sha256()
                with path.open("rb") as stream:
                    for block in iter(lambda: stream.read(CHUNK), b""):
                        digest.update(block)
                        full_hash.update(block)
                        output.write(block)
                if digest.hexdigest() != part.get("sha256"):
                    raise ValueError(f"Part {idx} checksum mismatch")
                written += size
        if written != SIZE or full_hash.hexdigest() != SHA256:
            raise ValueError("Final model size or SHA256 mismatch")
        temp.rename(target)
        return {"path": str(target), "bytes": written, "sha256": full_hash.hexdigest(), "verified": True}
    except BaseException:
        temp.unlink(missing_ok=True)
        raise

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python scripts/reassemble_model.py <parts_directory> <output.gguf>")
    try:
        print(json.dumps(reassemble(Path(sys.argv[1]), Path(sys.argv[2])), indent=2))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Model transfer failed verification: {exc}") from exc
