from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request as URLRequest, urlopen

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse
from starlette.routing import Route

APP_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("AGENT_HQ_DB", str(APP_DIR / "data" / "agent-hq.sqlite3")))


def load_local_env() -> None:
    env_file = APP_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#") or "=" not in value:
            continue
        key, raw = value.split("=", 1)
        key, raw = key.strip(), raw.strip()
        if key and key.replace("_", "").isalnum():
            if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
                raw = raw[1:-1]
            os.environ.setdefault(key, raw)


load_local_env()
AGENTS = [
    {"id": "chief", "name": "Chief of Staff", "role": "Orchestrator", "color": "#7357e8"},
    {"id": "scamshield", "name": "ScamShield", "role": "Fraud evidence review", "color": "#ef6677"},
    {"id": "jobshield", "name": "JobShield", "role": "Jobs and recruiter checks", "color": "#df9d36"},
    {"id": "propertyshield", "name": "PropertyShield", "role": "Housing and deposit checks", "color": "#28a889"},
    {"id": "grc", "name": "GRC & Evidence", "role": "Governance and audit", "color": "#4c86d9"},
    {"id": "creative", "name": "Creative Pathways", "role": "Community pilot planning", "color": "#b354b9"},
    {"id": "studio", "name": "Faithfulord Studio", "role": "Brand and content work", "color": "#d37745"},
]
VALID_AGENT_IDS = {a["id"] for a in AGENTS}
VALID_NOTE_TYPES = {"knowledge", "memory", "rule"}
VALID_TASK_STATES = {"queued", "in_progress", "blocked", "complete"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, details TEXT NOT NULL DEFAULT '',
            agent_id TEXT NOT NULL, priority TEXT NOT NULL DEFAULT 'normal',
            status TEXT NOT NULL DEFAULT 'queued', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY, note_type TEXT NOT NULL, title TEXT NOT NULL,
            body TEXT NOT NULL, tags TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id TEXT PRIMARY KEY, kind TEXT NOT NULL, message TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS approvals (
            id TEXT PRIMARY KEY, recipient TEXT NOT NULL, body TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL,
            decided_at TEXT, sent_at TEXT
        );
        CREATE TABLE IF NOT EXISTS wa_messages (
            id TEXT PRIMARY KEY, wa_message_id TEXT UNIQUE, sender TEXT NOT NULL,
            body TEXT NOT NULL, received_at TEXT NOT NULL
        );
        """)


def add_notification(conn: sqlite3.Connection, kind: str, message: str) -> None:
    conn.execute(
        "INSERT INTO notifications(id,kind,message,created_at) VALUES(?,?,?,?)",
        (str(uuid.uuid4()), kind, message[:500], now_iso()),
    )


def json_error(message: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


def auto_assign(text: str) -> str:
    value = text.lower()
    if any(k in value for k in ("whatsapp", "scam", "fraud", "suspicious", "payment", "evidence")):
        return "scamshield"
    if any(k in value for k in ("job", "recruit", "sponsor", "cv", "interview")):
        return "jobshield"
    if any(k in value for k in ("rent", "property", "landlord", "deposit", "accommodation")):
        return "propertyshield"
    if any(k in value for k in ("policy", "audit", "governance", "compliance", "risk")):
        return "grc"
    if any(k in value for k in ("shirt", "shopify", "design", "instagram", "brand", "content")):
        return "studio"
    if any(k in value for k in ("pathway", "cic", "volunteer", "workshop", "community")):
        return "creative"
    return "chief"


def rows(conn: sqlite3.Connection, query: str, args: tuple = ()) -> list[dict]:
    return [dict(row) for row in conn.execute(query, args).fetchall()]


async def home(_: Request) -> HTMLResponse:
    return HTMLResponse(PAGE)


async def overview(_: Request) -> JSONResponse:
    with db() as conn:
        counts = {
            "queued": conn.execute("SELECT COUNT(*) FROM tasks WHERE status='queued'").fetchone()[0],
            "active": conn.execute("SELECT COUNT(*) FROM tasks WHERE status='in_progress'").fetchone()[0],
            "approvals": conn.execute("SELECT COUNT(*) FROM approvals WHERE status='pending'").fetchone()[0],
            "unread": conn.execute("SELECT COUNT(*) FROM notifications WHERE is_read=0").fetchone()[0],
            "messages": conn.execute("SELECT COUNT(*) FROM wa_messages").fetchone()[0],
        }
        tasks = rows(conn, "SELECT * FROM tasks ORDER BY created_at DESC LIMIT 8")
        notes_count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        notices = rows(conn, "SELECT * FROM notifications ORDER BY created_at DESC LIMIT 6")
    return JSONResponse({"counts": counts, "tasks": tasks, "notes_count": notes_count,
                         "notifications": notices, "agents": AGENTS,
                         "mode": "local_demo", "generated_at": now_iso()})


async def list_tasks(_: Request) -> JSONResponse:
    with db() as conn:
        result = rows(conn, "SELECT * FROM tasks ORDER BY CASE status WHEN 'in_progress' THEN 0 WHEN 'queued' THEN 1 WHEN 'blocked' THEN 2 ELSE 3 END, created_at DESC")
    return JSONResponse(result)


async def create_task(request: Request) -> JSONResponse:
    try:
        data = await request.json()
    except Exception:
        return json_error("Send a JSON request.")
    title = str(data.get("title", "")).strip()
    details = str(data.get("details", "")).strip()
    if not title or len(title) > 180 or len(details) > 4000:
        return json_error("Add a title under 180 characters and details under 4,000 characters.")
    agent_id = str(data.get("agent_id") or auto_assign(title + " " + details))
    if agent_id not in VALID_AGENT_IDS:
        return json_error("Choose a listed specialist.")
    priority = str(data.get("priority", "normal"))
    if priority not in {"low", "normal", "high"}:
        return json_error("Priority must be low, normal, or high.")
    task_id, stamp = "REQ-" + uuid.uuid4().hex[:8].upper(), now_iso()
    with db() as conn:
        conn.execute("INSERT INTO tasks(id,title,details,agent_id,priority,status,created_at,updated_at) VALUES(?,?,?,?,?,'queued',?,?)",
                     (task_id, title, details, agent_id, priority, stamp, stamp))
        agent_name = next(a["name"] for a in AGENTS if a["id"] == agent_id)
        add_notification(conn, "task", f"{agent_name} received a new request: {title}")
    return JSONResponse({"id": task_id, "title": title, "agent_id": agent_id, "status": "queued",
                         "message": "Request queued. This starter app does not run an LLM agent yet."}, status_code=201)


async def update_task(request: Request) -> JSONResponse:
    task_id = request.path_params["task_id"]
    try:
        data = await request.json()
    except Exception:
        return json_error("Send a JSON request.")
    status = str(data.get("status", ""))
    if status not in VALID_TASK_STATES:
        return json_error("Use queued, in_progress, blocked, or complete.")
    with db() as conn:
        found = conn.execute("SELECT title FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not found:
            return json_error("Request not found.", 404)
        conn.execute("UPDATE tasks SET status=?,updated_at=? WHERE id=?", (status, now_iso(), task_id))
        add_notification(conn, "status", f"{task_id} · {found['title']} moved to {status.replace('_',' ')}.")
    return JSONResponse({"id": task_id, "status": status})


async def list_notes(_: Request) -> JSONResponse:
    with db() as conn:
        result = rows(conn, "SELECT * FROM notes ORDER BY created_at DESC")
    for item in result:
        item["tags"] = [x for x in item["tags"].split(",") if x]
    return JSONResponse(result)


async def create_note(request: Request) -> JSONResponse:
    try:
        data = await request.json()
    except Exception:
        return json_error("Send a JSON request.")
    note_type = str(data.get("note_type", "knowledge"))
    title = str(data.get("title", "")).strip()
    body = str(data.get("body", "")).strip()
    tags = data.get("tags", [])
    if note_type not in VALID_NOTE_TYPES or not title or not body:
        return json_error("Choose knowledge, memory, or rule and provide a title and note.")
    if len(title) > 160 or len(body) > 8000:
        return json_error("Title or note is too long.")
    if isinstance(tags, str):
        tags = tags.split(",")
    tags_text = ",".join(dict.fromkeys(re.sub(r"[^a-zA-Z0-9 _-]", "", str(t)).strip().lower()[:32] for t in tags if str(t).strip()))
    note_id = "NOTE-" + uuid.uuid4().hex[:8].upper()
    with db() as conn:
        conn.execute("INSERT INTO notes(id,note_type,title,body,tags,created_at) VALUES(?,?,?,?,?,?)",
                     (note_id, note_type, title, body, tags_text, now_iso()))
        add_notification(conn, "brain", f"New {note_type} note saved: {title}")
    return JSONResponse({"id": note_id, "title": title, "note_type": note_type}, status_code=201)


async def list_notifications(_: Request) -> JSONResponse:
    with db() as conn:
        result = rows(conn, "SELECT * FROM notifications ORDER BY created_at DESC LIMIT 100")
    return JSONResponse(result)


async def mark_notification(request: Request) -> JSONResponse:
    note_id = request.path_params["notification_id"]
    with db() as conn:
        conn.execute("UPDATE notifications SET is_read=1 WHERE id=?", (note_id,))
    return JSONResponse({"ok": True})


async def list_approvals(_: Request) -> JSONResponse:
    with db() as conn:
        result = rows(conn, "SELECT * FROM approvals ORDER BY CASE status WHEN 'pending' THEN 0 WHEN 'approved' THEN 1 ELSE 2 END, created_at DESC")
    return JSONResponse(result)


async def create_approval(request: Request) -> JSONResponse:
    try:
        data = await request.json()
    except Exception:
        return json_error("Send a JSON request.")
    recipient = re.sub(r"[^0-9]", "", str(data.get("recipient", "")))
    body = str(data.get("body", "")).strip()
    if not re.fullmatch(r"[1-9][0-9]{7,14}", recipient):
        return json_error("Enter a WhatsApp number in international format, digits only after cleaning.")
    if not body or len(body) > 4096:
        return json_error("Write a message of 1 to 4,096 characters.")
    approval_id = "APR-" + uuid.uuid4().hex[:8].upper()
    with db() as conn:
        conn.execute("INSERT INTO approvals(id,recipient,body,status,created_at) VALUES(?,?,?,'pending',?)",
                     (approval_id, recipient, body, now_iso()))
        add_notification(conn, "approval", f"WhatsApp draft to +{recipient} is waiting for your review.")
    return JSONResponse({"id": approval_id, "status": "pending"}, status_code=201)


async def decide_approval(request: Request) -> JSONResponse:
    approval_id = request.path_params["approval_id"]
    try:
        data = await request.json()
    except Exception:
        return json_error("Send a JSON request.")
    decision = data.get("decision")
    if decision not in {"approved", "rejected"}:
        return json_error("Decision must be approved or rejected.")
    with db() as conn:
        item = conn.execute("SELECT status FROM approvals WHERE id=?", (approval_id,)).fetchone()
        if not item:
            return json_error("Approval not found.", 404)
        if item["status"] != "pending":
            return json_error("This draft has already been decided.", 409)
        conn.execute("UPDATE approvals SET status=?,decided_at=? WHERE id=?",
                     (decision, now_iso(), approval_id))
        add_notification(conn, "approval", f"{approval_id} was {decision}.")
    return JSONResponse({"id": approval_id, "status": decision})


def whatsapp_config() -> dict:
    return {
        "access_token": os.getenv("WHATSAPP_ACCESS_TOKEN", ""),
        "phone_number_id": os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""),
        "api_version": os.getenv("WHATSAPP_API_VERSION", ""),
        "verify_token": os.getenv("WHATSAPP_VERIFY_TOKEN", ""),
        "app_secret": os.getenv("WHATSAPP_APP_SECRET", ""),
        "allowed": {re.sub(r"[^0-9]", "", x) for x in os.getenv("WHATSAPP_ALLOWED_RECIPIENTS", "").split(",") if x.strip()},
    }


async def whatsapp_status(_: Request) -> JSONResponse:
    cfg = whatsapp_config()
    return JSONResponse({
        "mode": "credentials_configured" if all(cfg[k] for k in ("access_token", "phone_number_id", "api_version", "verify_token", "app_secret")) else "not_configured",
        "credentials_present": {k: bool(cfg[k]) for k in ("access_token", "phone_number_id", "api_version", "verify_token", "app_secret")},
        "approved_recipients": len(cfg["allowed"]),
        "outbound_policy": "human approval + recipient allowlist + recent inbound conversation",
    })


async def webhook_verify(request: Request) -> PlainTextResponse:
    cfg = whatsapp_config()
    params = request.query_params
    if (params.get("hub.mode") == "subscribe" and cfg["verify_token"]
            and hmac.compare_digest(params.get("hub.verify_token", ""), cfg["verify_token"])):
        return PlainTextResponse(params.get("hub.challenge", ""))
    return PlainTextResponse("Webhook verification failed", status_code=403)


async def webhook_receive(request: Request) -> JSONResponse:
    cfg = whatsapp_config()
    if not cfg["app_secret"]:
        return json_error("WhatsApp webhook is not configured.", 503)
    raw = await request.body()
    signature = request.headers.get("x-hub-signature-256", "")
    expected = "sha256=" + hmac.new(cfg["app_secret"].encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return json_error("Webhook signature check failed.", 401)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return json_error("Invalid webhook JSON.")
    stored = 0
    with db() as conn:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for message in value.get("messages", []):
                    message_id = str(message.get("id", ""))
                    sender = re.sub(r"[^0-9]", "", str(message.get("from", "")))
                    text_body = str(message.get("text", {}).get("body", "")).strip()
                    if not message_id or not sender or not text_body:
                        continue
                    try:
                        conn.execute("INSERT INTO wa_messages(id,wa_message_id,sender,body,received_at) VALUES(?,?,?,?,?)",
                                     (str(uuid.uuid4()), message_id, sender, text_body[:4096], now_iso()))
                        add_notification(conn, "whatsapp", f"New WhatsApp message from +{sender}. Review it before replying.")
                        stored += 1
                    except sqlite3.IntegrityError:
                        pass
    return JSONResponse({"ok": True, "messages_stored": stored})


async def list_messages(_: Request) -> JSONResponse:
    with db() as conn:
        result = rows(conn, "SELECT * FROM wa_messages ORDER BY received_at DESC LIMIT 100")
    return JSONResponse(result)


async def send_approved(request: Request) -> JSONResponse:
    try:
        data = await request.json()
    except Exception:
        return json_error("Send a JSON request.")
    approval_id = str(data.get("approval_id", ""))
    cfg = whatsapp_config()
    if not all(cfg[k] for k in ("access_token", "phone_number_id", "api_version", "app_secret")):
        return json_error("WhatsApp sending is disabled until Meta Cloud API credentials are configured.", 503)
    with db() as conn:
        approval = conn.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)).fetchone()
        if not approval:
            return json_error("Approval not found.", 404)
        if approval["status"] != "approved" or approval["sent_at"]:
            return json_error("Only an approved, unsent draft can be sent.", 409)
        recipient = approval["recipient"]
        if recipient not in cfg["allowed"]:
            return json_error("Recipient is not on the explicit consent allowlist.", 403)
        latest = conn.execute("SELECT received_at FROM wa_messages WHERE sender=? ORDER BY received_at DESC LIMIT 1", (recipient,)).fetchone()
        if not latest:
            return json_error("No incoming conversation exists for this recipient. Use a reviewed template flow or wait for them to message first.", 403)
        try:
            recent = datetime.fromisoformat(latest["received_at"]).timestamp() > time.time() - 24 * 60 * 60
        except ValueError:
            recent = False
        if not recent:
            return json_error("The recipient’s last incoming message is outside the 24-hour reply window. This starter supports replies only.", 403)
        body = approval["body"]
        changed = conn.execute(
            "UPDATE approvals SET status='sending' WHERE id=? AND status='approved' AND sent_at IS NULL",
            (approval_id,),
        ).rowcount
        if changed != 1:
            return json_error("This draft is already being sent or has changed state.", 409)
    endpoint = f"https://graph.facebook.com/{cfg['api_version']}/{cfg['phone_number_id']}/messages"
    payload = json.dumps({"messaging_product": "whatsapp", "recipient_type": "individual",
                          "to": recipient, "type": "text", "text": {"preview_url": False, "body": body}}).encode()
    req = URLRequest(endpoint, data=payload, headers={
        "Authorization": "Bearer " + cfg["access_token"],
        "Content-Type": "application/json",
    }, method="POST")
    try:
        with urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode())
    except HTTPError as exc:
        exc.read(1024)
        with db() as conn:
            conn.execute("UPDATE approvals SET status='approved' WHERE id=? AND status='sending'", (approval_id,))
        return json_error("Meta rejected the send request. Review the WhatsApp account and draft before retrying.", 502)
    except (URLError, TimeoutError) as exc:
        # A timeout can happen after the provider accepted the message. Keep the
        # draft locked in 'sending' so a retry cannot accidentally duplicate it.
        return json_error(f"WhatsApp provider could not be reached: {exc.reason if isinstance(exc, URLError) else 'timeout'}.", 502)
    with db() as conn:
        conn.execute("UPDATE approvals SET sent_at=?,status='sent' WHERE id=? AND status='sending' AND sent_at IS NULL", (now_iso(), approval_id))
        add_notification(conn, "whatsapp", f"Approved WhatsApp reply sent to +{recipient}.")
    return JSONResponse({"ok": True, "provider_result": result})


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Palm92 Agent HQ</title>
<style>
:root{--bg:#0c1421;--panel:#121e2d;--panel2:#172638;--line:#26384c;--ink:#eff5fb;--muted:#9aadc2;--aqua:#43e0d1;--blue:#5591ff;--purple:#9b80ff;--good:#4dc99a;--gold:#f1b64d;--red:#fa7581}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 78% -10%,#1d3850 0,#0c1421 42%);color:var(--ink);font:14px/1.45 Inter,system-ui,Segoe UI,sans-serif}
button,input,select,textarea{font:inherit}button{cursor:pointer}.shell{display:grid;grid-template-columns:238px 1fr;min-height:100vh}.side{padding:22px 15px;border-right:1px solid var(--line);background:#0b1320e8;position:sticky;top:0;height:100vh}
.brand{display:flex;align-items:center;gap:11px;padding:3px 9px 22px}.logo{width:38px;height:38px;border-radius:12px;display:grid;place-items:center;background:linear-gradient(145deg,#39ddce,#557cf9);color:#071521;font-weight:900;font-size:18px}.brand strong{display:block;font-size:14px}.brand small{color:var(--muted);font-size:11px}
.navtitle{font-size:10px;text-transform:uppercase;letter-spacing:1.5px;color:#70859d;padding:14px 10px 6px}.nav{display:block;border:0;background:none;color:#aebed0;width:100%;text-align:left;padding:10px 12px;border-radius:10px;margin:2px 0}.nav:hover,.nav.on{background:#1b2b40;color:white}.nav.on{box-shadow:inset 3px 0 var(--aqua)}.nav i{display:inline-block;width:26px;font-style:normal;color:#7fa0c0}.sidefoot{position:absolute;bottom:18px;left:25px;right:25px;color:#8ca1b8;font-size:11px;border-top:1px solid var(--line);padding-top:13px}
main{padding:26px clamp(18px,3vw,42px);max-width:1500px;width:100%;margin:auto}.topbar{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:25px}.crumb{color:var(--muted);font-size:12px}.topbar h1{font-size:25px;margin:4px 0 0;letter-spacing:-.5px}.topright{display:flex;align-items:center;gap:10px}.mode{border:1px solid #38516a;background:#142539;border-radius:999px;padding:7px 10px;color:#bcd0e5;font-size:11px}.avatar{width:36px;height:36px;border-radius:12px;background:#e8e8ff;color:#273064;display:grid;place-items:center;font-weight:800}
.hero{display:flex;align-items:center;justify-content:space-between;gap:15px;margin:0 0 18px;padding:20px 22px;border:1px solid #2a4459;border-radius:16px;background:linear-gradient(110deg,#142a3b,#17243b 70%,#211c3b)}.hero h2{font-size:18px;margin:0 0 4px}.hero p{margin:0;color:#a8bbd0}.hero .spark{font-size:28px;color:var(--aqua)}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}.card{background:linear-gradient(160deg,#142233,#111d2b);border:1px solid var(--line);border-radius:15px;padding:17px;box-shadow:0 14px 40px #00000014}.metric{font-size:11px;text-transform:uppercase;letter-spacing:.8px;color:#9fb2c6}.metric strong{display:block;font-size:28px;color:#fff;margin:8px 0 1px}.metric small{font-size:11px;color:#8499b0}
.cols{display:grid;grid-template-columns:1.2fr .8fr;gap:14px}.panel{background:#111d2b;border:1px solid var(--line);border-radius:15px;padding:18px;margin-bottom:14px}.panelhead{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:13px}.panelhead h3{font-size:15px;margin:0}.sub{font-size:11px;color:var(--muted);margin-top:3px}.btn{border:1px solid #31475f;background:#192a3e;color:#dbe8f5;border-radius:9px;padding:8px 11px;font-size:12px;font-weight:650}.btn.primary{background:var(--aqua);color:#09202a;border-color:var(--aqua)}.btn.purple{background:#8770ed;color:#fff;border-color:#8770ed}.btn.good{color:var(--good);border-color:#317b69}.btn.danger{color:var(--red);border-color:#73404a}.btn.sm{padding:5px 8px;font-size:11px}
.agentgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:9px}.agent{display:flex;align-items:center;gap:10px;background:#162538;border:1px solid #26394d;border-radius:11px;padding:11px}.dot{width:10px;height:10px;border-radius:50%;box-shadow:0 0 10px currentColor}.agent b{display:block;font-size:12px}.agent small{display:block;color:var(--muted);font-size:10px}.state{margin-left:auto;color:var(--good);font-size:10px}
.task{display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:start;padding:12px 0;border-bottom:1px solid #243447}.task:last-child{border:0}.taskid{color:#728ba4;font-size:10px}.task b{font-size:12px}.task small{display:block;color:var(--muted);font-size:11px;margin-top:3px}.status{font-size:10px;border-radius:999px;padding:4px 7px;background:#203247;color:#a9bfd6;white-space:nowrap}.status.queued{color:var(--gold)}.status.in_progress{color:var(--blue)}.status.complete{color:var(--good)}.status.blocked{color:var(--red)}
.row{display:flex;gap:9px;align-items:center;padding:10px 0;border-bottom:1px solid #243447}.row:last-child{border:0}.row .body{flex:1;min-width:0}.row b{font-size:12px}.row small{display:block;color:var(--muted);font-size:10px}.unread{width:8px;height:8px;border-radius:50%;background:var(--aqua)}
.page{display:none}.page.active{display:block}.field{margin:10px 0}.field label{display:block;font-size:11px;color:#a8bbd0;margin-bottom:5px}.field input,.field textarea,.field select{width:100%;border:1px solid #2d4259;background:#0d1825;color:var(--ink);border-radius:9px;padding:10px}.field textarea{min-height:78px;resize:vertical}.formrow{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.note{border:1px solid #2b4357;background:#142437;border-radius:11px;padding:12px;color:#a9bed3;font-size:11px}.tag{display:inline-block;border-radius:999px;padding:3px 7px;background:#1c3045;color:#9db4cb;font-size:10px;margin:5px 3px 0 0}
.approval{border:1px solid #3a4a60;border-radius:11px;padding:13px;margin:9px 0;background:#142234}.approval p{white-space:pre-wrap;color:#c8d5e3;font-size:12px;margin:8px 0}.empty{padding:24px;text-align:center;color:var(--muted);border:1px dashed #32475e;border-radius:12px;font-size:12px}.split{display:flex;gap:8px}.split>*{flex:1}.callout{border-left:3px solid var(--gold);padding:10px 12px;background:#231f18;color:#d7c49a;font-size:11px;border-radius:0 8px 8px 0}
.toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:#e9f7f4;color:#0b2a2b;padding:10px 15px;border-radius:10px;box-shadow:0 8px 32px #0008;display:none;z-index:10}.toast.show{display:block}
@media(max-width:950px){.shell{grid-template-columns:74px 1fr}.side{padding:18px 9px}.brand{padding:0 7px 18px}.brandtxt,.nav span,.navtitle,.sidefoot{display:none}.nav{text-align:center;padding:12px 4px}.nav i{width:auto}.cards{grid-template-columns:repeat(2,1fr)}.cols{grid-template-columns:1fr}}
@media(max-width:600px){.shell{display:block}.side{height:auto;position:sticky;z-index:5;top:0;display:flex;overflow:auto;border:0;border-bottom:1px solid var(--line);padding:7px;background:#0b1320}.brand{display:none}.nav{width:auto;min-width:43px;margin:0;padding:9px}.nav i{font-size:15px}.topbar h1{font-size:21px}main{padding:17px 13px}.hero{padding:15px}.cards{gap:8px}.card{padding:12px}.metric strong{font-size:23px}.agentgrid{grid-template-columns:1fr 1fr}.formrow{grid-template-columns:1fr}.topright .mode{display:none}}
</style></head>
<body><div class="shell"><aside class="side">
<div class="brand"><div class="logo">P</div><div class="brandtxt"><strong>PALM92 AGENT HQ</strong><small>AI investigates. Humans decide.</small></div></div>
<div class="navtitle">Workspace</div>
<button class="nav on" data-view="overview"><i>⌂</i><span>Overview</span></button>
<button class="nav" data-view="requests"><i>⇄</i><span>Requests</span></button>
<button class="nav" data-view="brain"><i>◈</i><span>Company brain</span></button>
<button class="nav" data-view="approvals"><i>✓</i><span>Approvals</span></button>
<button class="nav" data-view="whatsapp"><i>◉</i><span>WhatsApp</span></button>
<button class="nav" data-view="notifications"><i>♧</i><span>Notifications</span></button>
<div class="navtitle">Specialists</div><button class="nav" data-view="agents"><i>✣</i><span>Agent directory</span></button>
<div class="sidefoot">LOCAL STARTER · MESSAGES OFF BY DEFAULT</div></aside>
<main><div class="topbar"><div><div class="crumb">Palm92 / <span id="crumb">Overview</span></div><h1 id="title">Agent HQ</h1></div><div class="topright"><span class="mode">● LOCAL MODE · AI PROVIDER OFF</span><div class="avatar">FW</div></div></div>
<section class="page active" id="overview"><div class="hero"><div><h2>Your work, in one command room.</h2><p>Capture a request, route it to a specialist, and keep every decision visible.</p></div><div class="spark">✦</div></div>
<div class="cards"><div class="card metric">QUEUED REQUESTS<strong id="nQueued">0</strong><small>Waiting for an agent</small></div><div class="card metric">IN PROGRESS<strong id="nActive">0</strong><small>Work currently moving</small></div><div class="card metric">NEEDS YOUR REVIEW<strong id="nApproval">0</strong><small>Human decision required</small></div><div class="card metric">NEW NOTIFICATIONS<strong id="nUnread">0</strong><small>Updates in your workspace</small></div></div>
<div class="cols"><div><div class="panel"><div class="panelhead"><div><h3>Specialist team</h3><div class="sub">Role directory and routing targets</div></div><button class="btn" data-jump="agents">View team</button></div><div class="agentgrid" id="agentCards"></div></div>
<div class="panel"><div class="panelhead"><div><h3>Recent requests</h3><div class="sub">One shared queue, specialist ownership</div></div><button class="btn" data-jump="requests">Open queue</button></div><div id="recentTasks"></div></div></div>
<div><div class="panel"><div class="panelhead"><div><h3>Notification feed</h3><div class="sub">Agent and connector updates</div></div><button class="btn" data-jump="notifications">See all</button></div><div id="recentNotices"></div></div>
<div class="panel"><div class="panelhead"><div><h3>Four primitives. One engine.</h3></div></div><div class="note"><b>Notes</b> hold rules and project knowledge.<br><b>Memory</b> keeps approved context and history.<br><b>Skills</b> define repeatable workflows.<br><b>Pages</b> show queues, reports, and decisions.<br><br>This local app stores notes and requests in SQLite. It does not call an AI model yet.</div></div></div></div></section>
<section class="page" id="requests"><div class="cols"><div><div class="panel"><div class="panelhead"><div><h3>Request inbox</h3><div class="sub">Write naturally. The dispatcher suggests a specialist.</div></div></div>
<form id="taskForm"><div class="field"><label>What would you like done?</label><input name="title" maxlength="180" required placeholder="Example: Review this job offer for warning signs"></div><div class="field"><label>Context or voice-note transcript</label><textarea name="details" maxlength="4000" placeholder="Add background, what you noticed, and the result you want."></textarea></div><div class="formrow"><div class="field"><label>Send to</label><select name="agent_id"><option value="auto">Let the dispatcher choose</option></select></div><div class="field"><label>Priority</label><select name="priority"><option>normal</option><option>high</option><option>low</option></select></div></div><button class="btn primary" type="submit">＋ Add to request queue</button></form></div>
<div class="panel"><div class="panelhead"><div><h3>Request status</h3><div class="sub">Update work manually while the AI provider is off.</div></div></div><div id="taskList"></div></div></div>
<div><div class="panel"><h3>How routing works</h3><p class="sub">The starter uses transparent keyword rules to suggest a specialist. A human can change the assignment before saving.</p><div class="callout">Requests are queued only. No shell commands, external messages, payments, or account changes run from this app.</div></div></div></div></section>
<section class="page" id="brain"><div class="cols"><div><div class="panel"><div class="panelhead"><div><h3>Company brain</h3><div class="sub">Save the context agents need to stay consistent.</div></div></div>
<form id="noteForm"><div class="formrow"><div class="field"><label>Record type</label><select name="note_type"><option value="knowledge">Knowledge</option><option value="memory">Memory</option><option value="rule">Shared rule</option></select></div><div class="field"><label>Tags</label><input name="tags" placeholder="palm92, whatsapp, consent"></div></div><div class="field"><label>Title</label><input name="title" required maxlength="160" placeholder="A clear label for this note"></div><div class="field"><label>Note</label><textarea name="body" required maxlength="8000" placeholder="Capture a decision, stable fact, or reusable instruction."></textarea></div><button class="btn primary" type="submit">Save to shared brain</button></form></div></div>
<div><div class="panel"><h3>Memory boundaries</h3><div class="note">Store only information you intend to reuse. Keep health information, passwords, access tokens, and other sensitive details out of this shared business brain. A saved rule is visible to the team but does not automatically change an agent’s system permissions.</div></div><div class="panel"><div class="panelhead"><div><h3>Saved context</h3><div class="sub">Newest first</div></div></div><div id="noteList"></div></div></div></div></section>
<section class="page" id="approvals"><div class="cols"><div class="panel"><div class="panelhead"><div><h3>Human approval queue</h3><div class="sub">Review a draft before any outbound action.</div></div></div><div id="approvalList"></div></div><div class="panel"><h3>Approval rule</h3><div class="note">Approving records your decision. Sending is a separate action and is disabled until official WhatsApp credentials, an allowlisted recipient, and a recent incoming conversation are present.</div></div></div></section>
<section class="page" id="whatsapp"><div class="cols"><div><div class="panel"><div class="panelhead"><div><h3>WhatsApp Intelligence</h3><div class="sub">Official WhatsApp Business Cloud API adapter</div></div><span class="mode" id="waMode">CHECKING</span></div><div class="note" id="waStatus"></div>
<form id="waForm"><div class="field"><label>Recipient number</label><input name="recipient" required inputmode="tel" placeholder="44 7700 900000"></div><div class="field"><label>Draft a reply</label><textarea name="body" maxlength="4096" required placeholder="Write a reply to a recent incoming message."></textarea></div><button class="btn primary" type="submit">Submit draft for approval</button></form></div>
<div class="panel"><div class="panelhead"><div><h3>Recent incoming messages</h3><div class="sub">Messages are saved for manual review. No automatic replies.</div></div></div><div id="messageList"></div></div></div>
<div><div class="panel"><h3>Connector setup</h3><p class="sub">Add credentials to your local environment file. Never paste access tokens into chat or the browser form.</p><div class="note">Required settings:<br><b>WHATSAPP_ACCESS_TOKEN</b><br><b>WHATSAPP_PHONE_NUMBER_ID</b><br><b>WHATSAPP_API_VERSION</b><br><b>WHATSAPP_VERIFY_TOKEN</b><br><b>WHATSAPP_APP_SECRET</b><br><b>WHATSAPP_ALLOWED_RECIPIENTS</b></div><p class="sub">Webhook route: <code>/webhook</code>. Meta requires a public HTTPS callback for live delivery.</p></div>
<div class="panel"><div class="panelhead"><div><h3>Outgoing safeguards</h3></div></div><div class="note">• Each draft waits for a human decision.<br>• Recipient must appear on your consent allowlist.<br>• This version sends text replies only within 24 hours of an incoming message.<br>• Business initiated templates are not implemented.<br>• No inbound message triggers a reply.</div></div></div></div></section>
<section class="page" id="notifications"><div class="panel"><div class="panelhead"><div><h3>Notifications</h3><div class="sub">Queue events, review requests, and connector status.</div></div></div><div id="allNotices"></div></div></section>
<section class="page" id="agents"><div class="hero"><div><h2>Specialist directory</h2><p>These are routing roles. AI execution is not connected in this starter build.</p></div><div class="spark">✦</div></div><div class="agentgrid" id="allAgents"></div><div class="panel" style="margin-top:14px"><h3>Three workstreams, safely separated</h3><p class="sub">The app records task ownership and review state. Parallel code agents should use isolated Git worktrees or branches; this UI does not start local processes.</p></div></section>
</main></div><div class="toast" id="toast"></div>
<script>
const agentNames={chief:"Chief of Staff",scamshield:"ScamShield",jobshield:"JobShield",propertyshield:"PropertyShield",grc:"GRC & Evidence",creative:"Creative Pathways",studio:"Faithfulord Studio"};
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const stamp=s=>{try{return new Date(s).toLocaleString(undefined,{month:"short",day:"numeric",hour:"numeric",minute:"2-digit"})}catch{return ""}};
function toast(s){const e=document.getElementById("toast");e.textContent=s;e.classList.add("show");setTimeout(()=>e.classList.remove("show"),2300)}
async function api(path,options={}){const r=await fetch(path,{headers:{"Content-Type":"application/json"},...options});const d=await r.json();if(!r.ok)throw new Error(d.error||"Request failed");return d}
function nav(id){document.querySelectorAll(".page").forEach(x=>x.classList.toggle("active",x.id===id));document.querySelectorAll(".nav").forEach(x=>x.classList.toggle("on",x.dataset.view===id));const label={overview:"Overview",requests:"Requests",brain:"Company brain",approvals:"Approvals",whatsapp:"WhatsApp Intelligence",notifications:"Notifications",agents:"Agent directory"}[id]||"Overview";document.getElementById("title").textContent=id==="overview"?"Agent HQ":label;document.getElementById("crumb").textContent=label;refresh(id)}
document.querySelectorAll(".nav").forEach(b=>b.onclick=()=>nav(b.dataset.view));document.querySelectorAll("[data-jump]").forEach(b=>b.onclick=()=>nav(b.dataset.jump));
function taskCard(t){return '<div class="task"><div><div class="taskid">'+esc(t.id)+'</div></div><div><b>'+esc(t.title)+'</b><small>'+esc(agentNames[t.agent_id]||t.agent_id)+' · '+stamp(t.created_at)+'</small></div><select class="status '+esc(t.status)+'" onchange="setTask(\\''+esc(t.id)+'\\',this.value)"><option '+(t.status==="queued"?"selected":"")+' value="queued">Queued</option><option '+(t.status==="in_progress"?"selected":"")+' value="in_progress">In progress</option><option '+(t.status==="blocked"?"selected":"")+' value="blocked">Blocked</option><option '+(t.status==="complete"?"selected":"")+' value="complete">Complete</option></select></div>'}
async function setTask(id,status){try{await api("/api/tasks/"+encodeURIComponent(id),{method:"PATCH",body:JSON.stringify({status})});toast("Request status updated");refresh("requests")}catch(e){toast(e.message)}}
function renderAgents(agents){const html=agents.map(a=>'<div class="agent"><span class="dot" style="color:'+esc(a.color)+';background:'+esc(a.color)+'"></span><div><b>'+esc(a.name)+'</b><small>'+esc(a.role)+'</small></div><span class="state">ROLE</span></div>').join("");document.getElementById("agentCards").innerHTML=html;document.getElementById("allAgents").innerHTML=html;const sel=document.querySelector('#taskForm [name="agent_id"]');if(sel.options.length===1)agents.forEach(a=>sel.insertAdjacentHTML("beforeend",'<option value="'+esc(a.id)+'">'+esc(a.name)+'</option>'))}
async function renderOverview(){const d=await api("/api/overview");renderAgents(d.agents);document.getElementById("nQueued").textContent=d.counts.queued;document.getElementById("nActive").textContent=d.counts.active;document.getElementById("nApproval").textContent=d.counts.approvals;document.getElementById("nUnread").textContent=d.counts.unread;document.getElementById("recentTasks").innerHTML=d.tasks.length?d.tasks.map(taskCard).join():'<div class="empty">Your request queue is empty. Add a first task when ready.</div>';document.getElementById("recentNotices").innerHTML=d.notifications.length?d.notifications.map(noticeRow).join():'<div class="empty">No notifications yet.</div>'}
function noticeRow(n){return '<div class="row"><span class="'+(n.is_read?"":"unread")+'"></span><div class="body"><b>'+esc(n.message)+'</b><small>'+stamp(n.created_at)+'</small></div>'+(n.is_read?"":'<button class="btn sm" onclick="readNotice(\\''+esc(n.id)+'\\')">Mark read</button>')+'</div>'}
async function readNotice(id){try{await api("/api/notifications/"+encodeURIComponent(id)+"/read",{method:"POST"});refresh("notifications")}catch(e){toast(e.message)}}
async function renderRequests(){const d=await api("/api/tasks");document.getElementById("taskList").innerHTML=d.length?d.map(taskCard).join():'<div class="empty">No requests yet.</div>'}
async function renderNotes(){const d=await api("/api/notes");document.getElementById("noteList").innerHTML=d.length?d.map(n=>'<div class="row"><div class="body"><b>'+esc(n.title)+' · '+esc(n.note_type)+'</b><small>'+esc(n.body)+'</small><div>'+n.tags.map(t=>'<span class="tag">'+esc(t)+'</span>').join("")+'</div></div></div>').join():'<div class="empty">Your shared brain is empty. Start with a project rule or stable fact.</div>'}
async function renderApprovals(){const d=await api("/api/approvals");document.getElementById("approvalList").innerHTML=d.length?d.map(a=>'<div class="approval"><b>'+esc(a.id)+' · +'+esc(a.recipient)+'</b><span class="status '+esc(a.status)+'">'+esc(a.status)+'</span><p>'+esc(a.body)+'</p><small class="sub">'+stamp(a.created_at)+(a.sent_at?" · sent "+stamp(a.sent_at):"")+'</small><div class="split" style="margin-top:10px">'+(a.status==="pending"?'<button class="btn good" onclick="decide(\\''+esc(a.id)+'\\',\\'approved\\')">Approve draft</button><button class="btn danger" onclick="decide(\\''+esc(a.id)+'\\',\\'rejected\\')">Reject</button>':a.status==="approved"&&!a.sent_at?'<button class="btn primary" onclick="sendApproved(\\''+esc(a.id)+'\\')">Send approved reply</button>':'')+'</div></div>').join():'<div class="empty">No drafts waiting for review.</div>'}
async function decide(id,decision){try{await api("/api/approvals/"+encodeURIComponent(id)+"/decision",{method:"POST",body:JSON.stringify({decision})});toast("Decision saved");refresh("approvals")}catch(e){toast(e.message)}}
async function sendApproved(id){if(!confirm("Send this approved reply through WhatsApp?"))return;try{await api("/api/whatsapp/send",{method:"POST",body:JSON.stringify({approval_id:id})});toast("Reply sent");refresh("approvals")}catch(e){toast(e.message)}}
async function renderNotifications(){const d=await api("/api/notifications");document.getElementById("allNotices").innerHTML=d.length?d.map(noticeRow).join():'<div class="empty">No notifications yet.</div>'}
async function renderWhatsapp(){const s=await api("/api/whatsapp/status");document.getElementById("waMode").textContent=s.mode==="credentials_configured"?"● CREDENTIALS CONFIGURED":"○ NOT CONFIGURED";document.getElementById("waStatus").innerHTML=s.mode==="credentials_configured"?"Credentials are present. Confirm the public HTTPS webhook is subscribed in Meta before expecting messages. Sends still require an approved draft, an allowlisted recipient, and a recent incoming message.":"The connector is safely offline. Add Meta Cloud API environment settings and a public HTTPS webhook before live use.";const m=await api("/api/whatsapp/messages");document.getElementById("messageList").innerHTML=m.length?m.map(x=>'<div class="row"><span class="unread"></span><div class="body"><b>+'+esc(x.sender)+'</b><small>'+esc(x.body)+'</small><small>'+stamp(x.received_at)+'</small></div><button class="btn sm" onclick="draftReply(\\''+esc(x.sender)+'\\')">Draft reply</button></div>').join():'<div class="empty">No incoming messages. Connect a verified Cloud API webhook to receive them.</div>'}
function draftReply(number){document.querySelector('#waForm [name="recipient"]').value=number;document.querySelector('#waForm [name="body"]').focus()}
async function refresh(id){try{if(id==="overview")await renderOverview();if(id==="requests")await renderRequests();if(id==="brain")await renderNotes();if(id==="approvals")await renderApprovals();if(id==="notifications")await renderNotifications();if(id==="whatsapp")await renderWhatsapp();if(id==="agents"){const d=await api("/api/overview");renderAgents(d.agents)}}catch(e){toast(e.message)}}
document.getElementById("taskForm").onsubmit=async e=>{e.preventDefault();const f=new FormData(e.target),body={title:f.get("title"),details:f.get("details"),priority:f.get("priority")};if(f.get("agent_id")!=="auto")body.agent_id=f.get("agent_id");try{const d=await api("/api/tasks",{method:"POST",body:JSON.stringify(body)});toast("Queued for "+(agentNames[d.agent_id]||"review"));e.target.reset();refresh("requests")}catch(x){toast(x.message)}};
document.getElementById("noteForm").onsubmit=async e=>{e.preventDefault();const f=new FormData(e.target);try{await api("/api/notes",{method:"POST",body:JSON.stringify({note_type:f.get("note_type"),title:f.get("title"),body:f.get("body"),tags:f.get("tags")})});toast("Saved to company brain");e.target.reset();refresh("brain")}catch(x){toast(x.message)}};
document.getElementById("waForm").onsubmit=async e=>{e.preventDefault();const f=new FormData(e.target);try{await api("/api/approvals",{method:"POST",body:JSON.stringify({recipient:f.get("recipient"),body:f.get("body")})});toast("Draft sent to approval queue");e.target.reset();refresh("whatsapp")}catch(x){toast(x.message)}};
refresh("overview");
</script></body></html>"""


routes = [
    Route("/", home, methods=["GET"]),
    Route("/api/overview", overview, methods=["GET"]),
    Route("/api/tasks", list_tasks, methods=["GET"]),
    Route("/api/tasks", create_task, methods=["POST"]),
    Route("/api/tasks/{task_id}", update_task, methods=["PATCH"]),
    Route("/api/notes", list_notes, methods=["GET"]),
    Route("/api/notes", create_note, methods=["POST"]),
    Route("/api/notifications", list_notifications, methods=["GET"]),
    Route("/api/notifications/{notification_id}/read", mark_notification, methods=["POST"]),
    Route("/api/approvals", list_approvals, methods=["GET"]),
    Route("/api/approvals", create_approval, methods=["POST"]),
    Route("/api/approvals/{approval_id}/decision", decide_approval, methods=["POST"]),
    Route("/api/whatsapp/status", whatsapp_status, methods=["GET"]),
    Route("/api/whatsapp/messages", list_messages, methods=["GET"]),
    Route("/api/whatsapp/send", send_approved, methods=["POST"]),
    Route("/webhook", webhook_verify, methods=["GET"]),
    Route("/webhook", webhook_receive, methods=["POST"]),
]

@asynccontextmanager
async def lifespan(_: Starlette):
    init_db()
    yield


app = Starlette(debug=False, routes=routes, lifespan=lifespan)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PORT", "3870")))
