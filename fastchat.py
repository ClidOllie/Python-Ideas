import requests, threading, os, re, getpass, time, hashlib, hmac, json
from datetime import datetime, timezone
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# ── Pusher Config ─────────────────────────────────────────────────────────────
PASSWORD  = 'chat123'
APP_ID    = "2150965"
KEY       = "404d8f54ccb40251ca17"
SECRET    = "3957573b1ec6a0b53f80"
CLUSTER   = "us2"
CHANNEL   = "global-chat"

# JSONBin is only used for message history + presence (read rarely)
BIN_ID    = "69f4040aaaba8821975a1456"
BIN_KEY   = "$2a$10$vKt9uIjp7/5nLq0NPM.oUe6Dtmtqo941CNDojDsijC1DNZ..iBBbG"
BIN_URL   = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
BIN_HDR   = {"Content-Type": "application/json", "X-Master-Key": BIN_KEY}

PRESENCE_TTL  = 60
MAX_HISTORY   = 200

console = Console()

# ── Pusher HTTP trigger ───────────────────────────────────────────────────────
# We use Pusher's REST API to trigger events — no SDK needed, just requests.

def pusher_trigger(event, data):
    """Send an event to Pusher channel instantly via their HTTP API."""
    body    = json.dumps({"name": event, "channel": CHANNEL, "data": json.dumps(data)}, separators=(',', ':'))
    now_ts  = str(int(time.time()))
    to_sign = "\n".join(["POST", f"/apps/{APP_ID}/events", f"auth_key={KEY}&auth_timestamp={now_ts}&auth_version=1.0&body_md5={hashlib.md5(body.encode()).hexdigest()}"])
    sig     = hmac.new(SECRET.encode(), to_sign.encode(), hashlib.sha256).hexdigest()

    url = (
        f"https://api-{CLUSTER}.pusher.com/apps/{APP_ID}/events"
        f"?auth_key={KEY}&auth_timestamp={now_ts}&auth_version=1.0"
        f"&body_md5={hashlib.md5(body.encode()).hexdigest()}"
        f"&auth_signature={sig}"
    )
    r = requests.post(url, data=body, headers={"Content-Type": "application/json"}, timeout=5)
    r.raise_for_status()

# ── Pusher HTTP subscription (long-poll fallback) ─────────────────────────────
# True WebSocket needs a library. Instead we poll Pusher's channel info API
# to get who's online, and poll JSONBin at a slow rate for history.
# Incoming messages come via Pusher triggers stored in JSONBin.
# This gives us ~1-2s delivery with no SDK.

POLL_INTERVAL = 2   # fast poll since JSONBin is only for history now

# ── JSONBin helpers ───────────────────────────────────────────────────────────

def bin_get():
    r = requests.get(f"{BIN_URL}/latest", headers=BIN_HDR, timeout=8)
    r.raise_for_status()
    return r.json().get("record", {})

def bin_put(record):
    r = requests.put(BIN_URL, json=record, headers=BIN_HDR, timeout=8)
    r.raise_for_status()

# ── Time ──────────────────────────────────────────────────────────────────────

def utc_now():
    return datetime.now(timezone.utc)

def parse_iso(s):
    try:
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None

# ── Formatting ────────────────────────────────────────────────────────────────

MSG_RE = re.compile(r"^\[(\d{2}:\d{2})\]\s+(.+?):\s+(.+)$")

def fmt(raw):
    m = MSG_RE.match(raw.strip())
    if m:
        return f"[dim]{m.group(1)}[/dim]  [bold cyan]{m.group(2)}:[/bold cyan] {m.group(3)}"
    return f"[dim]{raw}[/dim]"

# ── Presence via Pusher channel info ─────────────────────────────────────────

def get_presence():
    """Ask Pusher who is subscribed to the channel right now."""
    try:
        now_ts  = str(int(time.time()))
        path    = f"/apps/{APP_ID}/channels/{CHANNEL}/users"
        to_sign = "\n".join(["GET", path, f"auth_key={KEY}&auth_timestamp={now_ts}&auth_version=1.0"])
        sig     = hmac.new(SECRET.encode(), to_sign.encode(), hashlib.sha256).hexdigest()
        url     = (
            f"https://api-{CLUSTER}.pusher.com{path}"
            f"?auth_key={KEY}&auth_timestamp={now_ts}&auth_version=1.0&auth_signature={sig}"
        )
        r = requests.get(url, timeout=5)
        if r.ok:
            return [u["id"] for u in r.json().get("users", [])]
    except Exception:
        pass
    return []

# ── Send message ──────────────────────────────────────────────────────────────

def send_message(name, text):
    ts   = datetime.now().strftime("%H:%M")
    line = f"[{ts}] {name}: {text}"

    # 1. Trigger Pusher event (instant delivery to web clients)
    try:
        pusher_trigger("message", {"line": line})
    except Exception:
        pass

    # 2. Also save to JSONBin for history (best-effort)
    try:
        rec  = bin_get()
        msgs = rec.get("messages", [])
        if line not in msgs:
            msgs.append(line)
            rec["messages"] = msgs[-MAX_HISTORY:]
            bin_put(rec)
    except Exception:
        pass  # history save failed — message still delivered via Pusher

# ── Heartbeat ─────────────────────────────────────────────────────────────────

def heartbeat(name, stop_event):
    while not stop_event.is_set():
        try:
            rec = bin_get()
            p   = rec.get("presence", {})
            p[name] = utc_now().isoformat()
            rec["presence"] = p
            bin_put(rec)
        except Exception:
            pass
        stop_event.wait(20)

# ── Watcher ───────────────────────────────────────────────────────────────────

def watch(name, stop_event, ready_event):
    seen       = set()
    confirmed  = set()
    absence    = {}
    own_prefix = f"] {name.lower()}:"

    # Pre-load history silently
    for _ in range(5):
        try:
            rec = bin_get()
            for m in rec.get("messages", []):
                seen.add(m)
            for u, ts in rec.get("presence", {}).items():
                if u != name:
                    dt = parse_iso(ts)
                    if dt and (utc_now() - dt).total_seconds() < PRESENCE_TTL:
                        confirmed.add(u)
            break
        except Exception:
            time.sleep(2)

    ready_event.set()

    while not stop_event.is_set():
        try:
            rec    = bin_get()
            msgs   = rec.get("messages", [])
            now_on = set()

            for u, ts in rec.get("presence", {}).items():
                if u == name:
                    continue
                dt = parse_iso(ts)
                if dt and (utc_now() - dt).total_seconds() < PRESENCE_TTL:
                    now_on.add(u)

            # New messages
            for m in msgs:
                if m not in seen:
                    seen.add(m)
                    if own_prefix not in m.lower():
                        console.print("")
                        console.print(fmt(m))

            # Joins
            for u in now_on - confirmed:
                absence.pop(u, None)
                confirmed.add(u)
                console.print(f"\n[dim]  --> {u} joined[/dim]")

            # Leaves
            for u in list(confirmed - now_on):
                absence[u] = absence.get(u, 0) + 1
                if absence[u] >= 3:
                    confirmed.discard(u)
                    absence.pop(u, None)
                    console.print(f"\n[dim]  <-- {u} left[/dim]")

            for u in now_on:
                absence.pop(u, None)

        except Exception:
            pass

        stop_event.wait(POLL_INTERVAL)

# ── Commands ──────────────────────────────────────────────────────────────────

def do_command(cmd, name):
    if cmd == "/clear":
        try:
            rec = bin_get()
            rec["messages"] = []
            bin_put(rec)
            console.print("[bold red]Cleared.[/bold red]")
        except Exception:
            console.print("[bold red]Failed.[/bold red]")

    elif cmd == "/history":
        try:
            msgs = bin_get().get("messages", [])
            if msgs:
                for m in msgs: console.print(fmt(m))
            else:
                console.print("[dim]No messages yet.[/dim]")
        except Exception:
            console.print("[bold red]Could not fetch.[/bold red]")

    elif cmd == "/online":
        users = get_presence()
        if users:
            console.print("  " + "  ".join(f"[bold green]● {u}[/bold green]" for u in users))
        else:
            console.print("[dim]  No one else online.[/dim]")

    elif cmd == "/quit":
        return False

    elif cmd == "/help":
        console.print("\n  /clear  /history  /online  /quit  /help\n")

    else:
        console.print(f"[bold red]Unknown: {cmd}[/bold red]")

    return True

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    os.system("clear" if os.name == "posix" else "cls")

    console.print(Panel(
        Text("GLOBAL CHAT", style="bold white", justify="center"),
        border_style="blue",
        subtitle="[dim]private · password required[/dim]",
        expand=False,
    ))

    for attempt in range(3):
        pwd = getpass.getpass("Password: ")
        if pwd == PASSWORD:
            console.print("[bold green]✓ Access granted[/bold green]\n")
            break
        left = 2 - attempt
        if left:
            console.print(f"[bold red]Wrong. {left} attempt{'s' if left>1 else ''} left.[/bold red]")
        else:
            console.print("[bold red]Too many attempts. Exiting.[/bold red]")
            return

    name = console.input("[bold cyan]Enter your handle: [/bold cyan]").strip()
    if not name:
        console.print("[bold red]Handle cannot be empty.[/bold red]")
        return

    stop_event  = threading.Event()
    ready_event = threading.Event()

    threading.Thread(target=heartbeat, args=(name, stop_event), daemon=True).start()
    threading.Thread(target=watch, args=(name, stop_event, ready_event), daemon=True).start()

    ready_event.wait(timeout=10)

    try:
        rec   = bin_get()
        users = [u for u, ts in rec.get("presence", {}).items()
                 if u != name and (dt := parse_iso(ts)) and (utc_now()-dt).total_seconds() < PRESENCE_TTL]
        console.print(f"[dim]Joined as [bold]{name}[/bold].[/dim]")
        if users:
            console.print("  " + "  ".join(f"[bold green]● {u}[/bold green]" for u in sorted(users)))
        else:
            console.print("[dim]  No one else is online.[/dim]")
        console.print("")
    except Exception:
        console.print(f"[dim]Joined as {name}.[/dim]\n")

    try:
        while True:
            try:
                msg = console.input(f"[bold cyan]{name}: [/bold cyan]").strip()
            except EOFError:
                break
            if not msg:
                continue
            if msg.startswith("/"):
                if not do_command(msg.lower(), name):
                    break
            else:
                send_message(name, msg)

    except KeyboardInterrupt:
        console.print("\n[bold yellow]Bye![/bold yellow]")
    finally:
        try:
            rec = bin_get()
            rec.setdefault("presence", {}).pop(name, None)
            bin_put(rec)
        except Exception:
            pass
        stop_event.set()

if __name__ == "__main__":
    main()