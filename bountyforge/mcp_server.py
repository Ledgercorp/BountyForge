"""BountyForge MCP stdio, read-only and owned-fixture only.

No remote listener, arbitrary file/tool execution, payment, inference or delivery.
Run from the trusted BountyForge checkout using python -m bountyforge.mcp_server.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

PROTOCOL = "2025-11-25"
SUPPORTED = {"2025-03-26", "2025-06-18", PROTOCOL}
NAME = "bountyforge-owned-review"
VERSION = "0.1.0"
MAX_REQUEST = 8192
MAX_REQUESTS = 100
ROOT = Path(__file__).resolve().parents[1]

# This adapter never has authority to use inherited provider or repository tokens.
for _name in ("GROQ_API_KEY", "OPENAI_API_KEY", "STRIPE_SECRET_KEY",
              "GITHUB_TOKEN", "GH_TOKEN", "RUNPOD_API_KEY"):
    os.environ.pop(_name, None)


def _tool(name, description, properties=None, required=None):
    return {
        "name": name, "description": description,
        "inputSchema": {
            "type": "object", "properties": properties or {},
            "required": required or [], "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False,
                        "idempotentHint": True, "openWorldHint": False},
    }


TOOLS = (
    _tool("bountyforge_status", "Recorded engineering/admission state. Not live operational readiness."),
    _tool("list_owned_calibration", "List four public, authored calibration defects. NOT a hidden benchmark."),
    _tool("inspect_owned_calibration", "Inspect one exact public owned defect without its reference solution.",
          {"case_id": {"type": "string", "maxLength": 64}}, ["case_id"]),
    _tool("verify_owned_reference", "Recheck an exact authored reference repair; not an AI-generated repair score.",
          {"case_id": {"type": "string", "maxLength": 64}}, ["case_id"]),
    _tool("preview_owned_review_package", "Inspect only the static owned patch-review manifest, no files written."),
)
BY_NAME = {t["name"]: t for t in TOOLS}


class Rejected(ValueError):
    """Sanitized tool refusal. Never include caller input in error messages."""


def _no_duplicates(pairs):
    result = {}
    for k, value in pairs:
        if k in result:
            raise ValueError("Duplicate JSON field")
        result[k] = value
    return result


def _load(raw):
    return json.loads(raw, object_pairs_hook=_no_duplicates,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


def _schema_args(name, args):
    tool = BY_NAME.get(name)
    if tool is None:
        raise Rejected("Unknown tool")
    schema = tool["inputSchema"]
    if type(args) is not dict or set(args) != set(schema["required"]):
        raise Rejected("Tool arguments must match the published schema exactly")
    if "case_id" in args and (type(args["case_id"]) is not str
                              or len(args["case_id"]) > 64):
        raise Rejected("Invalid owned case identifier")
    return args


def _case(case_id):
    from bountyforge.phase7_calibration import CASES
    matching = [item for item in CASES if item["id"] == case_id]
    if len(matching) != 1:
        raise Rejected("Unknown owned calibration case")
    return matching[0]


def _receipt():
    # Only read a fixed, recorded, non-private public artifact. No file paths
    # are accepted from clients; missing or tampered evidence fails closed.
    path = ROOT / "evidence" / "phase6" / "actual_python_image_layers.json"
    try:
        if path.is_symlink() or path.stat().st_size > 8192:
            raise Rejected("Recorded image evidence unavailable")
        info = _load(path.read_bytes())
        if (type(info) is not dict or info.get("kind") !=
                "bountyforge_phase6_actual_pinned_runtime_layer_integrity"
                or info.get("layers_verified") != 4
                or info.get("private_execution_admitted") is True):
            raise Rejected("Recorded image evidence not accepted")
        return {"recorded_content_integrity": True,
                "publisher_signature_verified": False,
                "private_execution_admitted": False,
                "evidence_kind": info["kind"],
                "pinned_manifest_digest": info["pinned_manifest_digest"]}
    except (OSError, TypeError, KeyError, ValueError):
        raise Rejected("Recorded image evidence unavailable") from None


def call_tool(name, args):
    _schema_args(name, args)
    if name == "bountyforge_status":
        return {"kind": "bountyforge_mcp_status", "scope": "recorded_owned_only",
                "status": "ENGINEERING_READY_FOR_REVIEW",
                "private_execution_admitted": False,
                "commercial_launch_authorized": False,
                "customer_source_accepted": False,
                "payment_verified": False, "delivery_authorized": False,
                "live_model_accuracy": None, "model_calls": 0,
                "runtime": _receipt()}
    if name == "list_owned_calibration":
        from bountyforge.phase7_calibration import manifest
        record = manifest()
        return {"kind": "public_owned_calibration_list", "cases": [
            {"id": r["id"], "source_sha256": r["source_sha256"],
             "vectors": r["vectors"]} for r in record["cases"]],
            "unseen_model_evaluation": False, "model_calls": 0}
    if name == "inspect_owned_calibration":
        case = _case(args["case_id"])
        raw = case["source"].encode("utf-8")
        if len(raw) > 4096:
            raise Rejected("Owned source too large")
        return {"kind": "owned_public_defect", "case_id": case["id"],
                "defect": case["defect"], "target_symbol": case["symbol"],
                "source": case["source"],
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "reference_solution_disclosed": False,
                "customer_source": False, "model_calls": 0}
    if name == "verify_owned_reference":
        from bountyforge.phase7_calibration import replay_one
        case = _case(args["case_id"])
        report = replay_one(case["id"], case["source"].encode(),
                            case["fixed"].encode())
        return {**report, "authorship": "preauthored_reference_only",
                "ai_generated_patch": False, "private_execution_admitted": False}
    if name == "preview_owned_review_package":
        from bountyforge.patch_review_service import _expected_files, _receipt as receipt
        files = _expected_files()
        report = receipt(files)
        return {**report, "preview_only": True, "files_written": 0,
                "customer_source_accepted": False,
                "private_execution_admitted": False,
                "delivery_authorized": False, "model_calls": 0}
    raise Rejected("Unknown tool")


def _reply(id_value, *, result=None, error=None):
    base = {"jsonrpc": "2.0", "id": id_value}
    if error is not None:
        base["error"] = error
    else:
        base["result"] = result
    return base


def _fail(id_value, code, message):
    return _reply(id_value, error={"code": code, "message": message})


def handle(packet, state):
    """Return JSON-RPC response, or None for client notifications."""
    if type(packet) is not dict or packet.get("jsonrpc") != "2.0":
        return _fail(None, -32600, "Invalid JSON-RPC request")
    method = packet.get("method")
    if type(method) is not str or len(method) > 80:
        return _fail(None, -32600, "Invalid JSON-RPC method")
    if "id" not in packet:
        if method == "notifications/initialized" and state["initialized"]:
            state["ready"] = True
        return None
    id_value = packet["id"]
    if (type(id_value) not in (str, int)
            or (type(id_value) is str and len(id_value) > 96)):
        return _fail(None, -32600, "Invalid request identifier")
    if method == "initialize":
        if state["initialized"]:
            return _fail(id_value, -32600, "Already initialized")
        params = packet.get("params")
        if (type(params) is not dict or type(params.get("protocolVersion")) is not str
                or type(params.get("capabilities")) is not dict
                or type(params.get("clientInfo")) is not dict):
            return _fail(id_value, -32602, "Invalid initialization")
        state["initialized"] = True
        proposed = params["protocolVersion"]
        version = proposed if proposed in SUPPORTED else PROTOCOL
        return _reply(id_value, result={"protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": NAME, "version": VERSION},
            "instructions": "Owned-only read-only engineering records. No private execution, model inference, customer intake, payments or delivery."})
    if not state["ready"]:
        return _fail(id_value, -32000, "MCP handshake incomplete")
    if method == "ping":
        return _reply(id_value, result={})
    if method == "tools/list":
        params = packet.get("params", {})
        # MCP RequestParams permits inert _meta (Codex uses progressToken).
        # It is not a tool argument, pagination cursor or authorization record.
        if (type(params) is not dict or set(params) - {"_meta"}
                or ("_meta" in params and type(params["_meta"]) is not dict)):
            return _fail(id_value, -32602, "No tool pagination supported")
        return _reply(id_value, result={"tools": list(TOOLS)})
    if method == "tools/call":
        params = packet.get("params")
        if (type(params) is not dict or set(params) - {"name", "arguments", "_meta"}
                or ("_meta" in params and type(params["_meta"]) is not dict)
                or type(params.get("name")) is not str):
            return _fail(id_value, -32602, "Invalid tool call")
        name = params["name"]
        if name not in BY_NAME:
            return _fail(id_value, -32602, "Unknown tool")
        try:
            output = call_tool(name, params.get("arguments", {}))
            return _reply(id_value, result={
                "content": [{"type": "text", "text": json.dumps(output, sort_keys=True,
                            separators=(",", ":"), allow_nan=False)}], "isError": False})
        except (Rejected, ValueError, TypeError, OSError, KeyError, RuntimeError):
            return _reply(id_value, result={"content": [{"type": "text",
                "text": "Owned-only tool request rejected"}], "isError": True})
    return _fail(id_value, -32601, "Method not found")


def main():
    state = {"initialized": False, "ready": False}
    for counter in range(MAX_REQUESTS):
        raw = sys.stdin.buffer.readline(MAX_REQUEST + 1)
        if not raw:
            return 0
        if len(raw) > MAX_REQUEST or not raw.endswith(b"\n"):
            # Quit rather than desynchronize on partial/oversized untrusted data.
            return 2
        try:
            packet = _load(raw)
        except (ValueError, UnicodeError, RecursionError):
            reply = _fail(None, -32700, "Invalid JSON")
        else:
            reply = handle(packet, state)
        if reply is not None:
            sys.stdout.write(json.dumps(reply, sort_keys=True, separators=(",", ":"),
                                        allow_nan=False) + "\n")
            sys.stdout.flush()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
