"""BountyForge MCP stdio, restricted owned-fixture operations only.

No remote listener, arbitrary file/tool execution, payment or delivery.
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
VERSION = "0.3.0"
MAX_REQUEST = 8192
MAX_REQUESTS = 100
ROOT = Path(__file__).resolve().parents[1]

def _isolate_environment():
    # Deny all inherited credentials, not just a list of known provider names.
    # Docker is installed in /usr/local/bin in the managed Linux environment.
    os.environ.clear()
    os.environ['PATH']='/usr/local/bin:/usr/bin:/bin'


def _tool(name, description, properties=None, required=None, *, stateful=False):
    return {
        "name": name, "description": description,
        "inputSchema": {
            "type": "object", "properties": properties or {},
            "required": required or [], "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": not stateful, "destructiveHint": False,
                        "idempotentHint": not stateful, "openWorldHint": False},
    }


TOOLS = (
    _tool("bountyforge_status", "Recorded engineering/admission state. Not live operational readiness."),
    _tool("list_owned_calibration", "List four public, authored calibration defects. NOT a hidden benchmark."),
    _tool("inspect_owned_calibration", "Inspect one exact public owned defect without its reference solution.",
          {"case_id": {"type": "string", "maxLength": 64}}, ["case_id"]),
    _tool("verify_owned_reference", "Recheck an exact authored reference repair; not an AI-generated repair score.",
          {"case_id": {"type": "string", "maxLength": 64}}, ["case_id"]),
    _tool("preview_owned_review_package", "Inspect only the static owned patch-review manifest, no files written."),
    _tool("list_repair_engines", "Select Autonomous Qwen or session-driven Codex Agent; no provider fallback."),
    _tool("list_owned_repair_tasks", "List fixed owned DEVELOPMENT tasks, not a hidden evaluation."),
    _tool("prepare_owned_repair", "Reproduce an exact owned defect, then hand off source and authorized AST edit units. No tests or answers are returned.",
          {"case_id":{"type":"string","maxLength":64},
           "model_profile":{"type":"string","enum":["QWEN_1_5B","QWEN_7B"]},
           "engine":{"type":"string","enum":["QWEN_LOCAL","CODEX_AGENT"]}},
          ["case_id","engine"], stateful=True),
    _tool("submit_owned_repair", "Verify a Codex-session candidate with existing validators and two isolated Docker observations. No delivery.",
          {"task_id":{"type":"string","maxLength":32},
           "revision":{"type":"integer","minimum":0,"maximum":1},
           "proposal":{"type":"object","properties":{"changes":{"type":"array","minItems":1,"maxItems":3,
             "items":{"type":"object","properties":{"line":{"type":"integer","minimum":1,"maximum":200},
             "new":{"type":"string","maxLength":400}},"required":["line","new"],"additionalProperties":False}}},
             "required":["changes"],"additionalProperties":False}},
          ["task_id","revision","proposal"], stateful=True),
    _tool("run_owned_qwen", "Run at most two autonomous requests to the pinned local Qwen runtime for a QWEN_LOCAL task only.",
          {"task_id":{"type":"string","maxLength":32},
           "revision":{"type":"integer","minimum":0,"maximum":1}},
          ["task_id","revision"], stateful=True),
)
QUEUE_LEASE = {'batch_id':{'type':'string','maxLength':48},
               'job_id':{'type':'string','maxLength':32},
               'lease_token':{'type':'string','maxLength':32}}
PROPOSAL = TOOLS[8]['inputSchema']['properties']['proposal']
TOOLS += (
    _tool('create_owned_queue','Idempotently enqueue up to five fixed owned tasks. Four batches per store; no scheduling or customer intake.',
          {'batch_id':{'type':'string','maxLength':48},'engine':{'type':'string','enum':['CODEX_AGENT','QWEN_LOCAL']},
           'model_profile':{'type':'string','enum':['QWEN_1_5B','QWEN_7B']},
           'case_ids':{'type':'array','minItems':1,'maxItems':5,'items':{'type':'string','maxLength':64}}},
          ['batch_id','engine','case_ids'],stateful=True),
    _tool('claim_owned_queue','Lease one owned task globally and reproduce its baseline. Codex must remain active to generate a patch.',
          {'batch_id':{'type':'string','maxLength':48}},['batch_id'],stateful=True),
    _tool('submit_owned_queue','Submit a Codex candidate under its live lease and revision. Durable two-attempt budget; never bypasses verification.',
          {**QUEUE_LEASE,'revision':{'type':'integer','minimum':0,'maximum':1},'proposal':PROPOSAL},
          [*QUEUE_LEASE,'revision','proposal'],stateful=True),
    _tool('run_owned_queue_qwen','Execute only the selected QWEN_LOCAL queue job with at most two local requests; no provider fallback.',
          QUEUE_LEASE,list(QUEUE_LEASE),stateful=True),
    _tool('heartbeat_owned_queue','Renew a live lease up to its absolute ten-minute job deadline.',
          QUEUE_LEASE,list(QUEUE_LEASE),stateful=True),
    _tool('release_owned_queue','Release a lease after interruption. A second claim requires fresh admission and baseline reproduction.',
          QUEUE_LEASE,list(QUEUE_LEASE),stateful=True),
    _tool('owned_queue_status','Read bounded local SQLite progress without exposing lease capabilities.',
          {'batch_id':{'type':'string','maxLength':48}},['batch_id'],stateful=True),
    _tool('stop_owned_queue','Irreversibly stop a batch and revoke its leases. In-flight bounded work may finish but cannot commit success.',
          {'batch_id':{'type':'string','maxLength':48}},['batch_id'],stateful=True),
)
BY_NAME = {t["name"]: t for t in TOOLS}
_REPAIRS = None
_QUEUE = None


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
    def validate(value, spec):
        kind=spec['type']
        if kind=='object':
            if (type(value) is not dict or not set(spec['required'])<=set(value)
                    or set(value)-set(spec['properties'])):
                raise Rejected('Tool arguments must match the published schema exactly')
            for key,child in value.items(): validate(child,spec['properties'][key])
        elif kind=='string':
            if type(value) is not str or len(value)>spec.get('maxLength',4096):
                raise Rejected('Invalid string argument')
            if 'enum' in spec and value not in spec['enum']: raise Rejected('Unknown engine')
        elif kind=='integer':
            if type(value) is not int or not spec.get('minimum',0)<=value<=spec.get('maximum',200):
                raise Rejected('Invalid integer argument')
        elif kind=='array':
            if type(value) is not list or not spec['minItems']<=len(value)<=spec['maxItems']:
                raise Rejected('Invalid bounded array')
            for child in value: validate(child,spec['items'])
    validate(args,schema)
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
    global _REPAIRS, _QUEUE
    _schema_args(name, args)
    if name in {'create_owned_queue','claim_owned_queue','submit_owned_queue','run_owned_queue_qwen',
                'heartbeat_owned_queue','release_owned_queue','owned_queue_status','stop_owned_queue'}:
        from bountyforge.owned_repair_queue import OwnedRepairQueue
        from bountyforge.repair_engines import RepairRejected
        if _QUEUE is None:_QUEUE=OwnedRepairQueue()
        methods={'create_owned_queue':'create','claim_owned_queue':'claim','submit_owned_queue':'submit',
                 'run_owned_queue_qwen':'run_qwen','heartbeat_owned_queue':'heartbeat',
                 'release_owned_queue':'release','owned_queue_status':'status','stop_owned_queue':'stop'}
        try:return getattr(_QUEUE,methods[name])(**args)
        except RepairRejected as exc:
            import re
            code=str(exc)
            if not re.fullmatch('[A-Z_]{1,80}',code):code='OWNED_QUEUE_REQUEST_REJECTED'
            return {'state':'REJECTED','outcome':code,'paid_fallback':False,'delivery_authorized':False}
    if name in {'list_repair_engines','list_owned_repair_tasks','prepare_owned_repair',
                'submit_owned_repair','run_owned_qwen'}:
        from bountyforge.repair_engines import RepairService, RepairUnavailable, engine_inventory, task_inventory
        if name=='list_repair_engines': return {'engines':engine_inventory(),'paid_fallback':False}
        if name=='list_owned_repair_tasks': return {'tasks':task_inventory(),'independent_evaluation':False}
        if _REPAIRS is None: _REPAIRS=RepairService()
        try:
            if name=='prepare_owned_repair': return _REPAIRS.prepare(**args)
            if name=='submit_owned_repair': return _REPAIRS.submit(**args)
            return _REPAIRS.run_qwen(**args)
        except RepairUnavailable as exc:
            outcome=str(exc) if str(exc) in {'SANDBOX_ADMISSION_UNAVAILABLE','BASELINE_OBSERVATION_UNAVAILABLE'} else 'SANDBOX_UNAVAILABLE'
            return {'state':'BLOCKED','outcome':outcome,
                    'private_execution_admitted':False,'delivery_authorized':False}
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
            "instructions": "Restricted owned DEVELOPMENT tasks only. Original five tools remain read-only. Codex candidates require explicit task and revision; Qwen requires explicit QWEN_LOCAL selection. No customer source, arbitrary commands, payments or delivery. No unattended Codex backend or paid fallback."})
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
    _isolate_environment()
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
