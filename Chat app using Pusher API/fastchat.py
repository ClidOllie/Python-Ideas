import requests, threading, os, re, getpass, time, hashlib, hmac, json
from datetime import datetime, timezone
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# ── Config ────────────────────────────────────────────────────────────────────
# Password is stored as a SHA-256 hash — the real password is never in the code
PASSWORD_HASH   = "22be099338be394c7100e87181c44d8be5dd72f4e24d9356f418aed88f17131c"
APP_ID          = "2150965"
KEY             = "404d8f54ccb40251ca17"
SECRET          = "3957573b1ec6a0b53f80"
CLUSTER         = "us2"
CHANNEL         = "global-chat"
BIN_ID          = "69f4040aaaba8821975a1456"
BIN_KEY         = "$2a$10$vKt9uIjp7/5nLq0NPM.oUe6Dtmtqo941CNDojDsijC1DNZ..iBBbG"
BIN_URL         = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
BIN_HDR         = {"Content-Type": "application/json", "X-Master-Key": BIN_KEY}
PRESENCE_TTL    = 60
POLL_INTERVAL   = 2
MAX_HISTORY     = 200

console = Console()

# ── Password check ────────────────────────────────────────────────────────────

def check_password(attempt):
    hashed = hashlib.sha256(attempt.encode()).hexdigest()
    return hashed == PASSWORD_HASH

# ── Pusher HTTP trigger ───────────────────────────────────────────────────────

def pusher_trigger(event, data):
    body    = json.dumps({"name": event, "channel": CHANNEL, "data": json.dumps(data)}, separators=(',', ':'))
    now_ts  = str(int(time.time()))
    md5     = hashlib.md5(body.encode()).hexdigest()
    to_sign = "\n".join(["POST", f"/apps/{APP_ID}/events", f"auth_key={KEY}&auth_timestamp={now_ts}&auth_version=1.0&body_md5={md5}"])
    sig     = hmac.new(SECRET.encode(), to_sign.encode(), hashlib.sha256).hexdigest()
    url     = (f"https://api-{CLUSTER}.pusher.com/apps/{APP_ID}/events"
               f"?auth_key={KEY}&auth_timestamp={now_ts}&auth_version=1.0&body_md5={md5}&auth_signature={sig}")
    r = requests.post(url, data=body, headers={"Content-Type": "application/json"}, timeout=5)
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

# ── JSONBin ───────────────────────────────────────────────────────────────────

def bin_get():
    r = requests.get(f"{BIN_URL}/latest", headers=BIN_HDR, timeout=10)
    r.raise_for_status()
    return r.json().get("record", {})

def bin_put(record):
    r = requests.put(BIN_URL, json=record, headers=BIN_HDR, timeout=10)
    r.raise_for_status()

# ── Formatting ────────────────────────────────────────────────────────────────

MSG_RE = re.compile(r"^\[(\d{2}:\d{2})\]\s+(.+?):\s+(.+)$")

def fmt(raw):
    m = MSG_RE.match(raw.strip())
    if m:
        return f"[dim]{m.group(1)}[/dim]  [bold cyan]{m.group(2)}:[/bold cyan] {m.group(3)}"
    return f"[dim]{raw}[/dim]"

# ── Presence ──────────────────────────────────────────────────────────────────

def online_users(presence, exclude):
    now = utc_now()
    return sorted(u for u, ts in presence.items()
                  if u != exclude and (dt := parse_iso(ts))
                  and (now - dt).total_seconds() < PRESENCE_TTL)

# ── Send ──────────────────────────────────────────────────────────────────────

def send_message(name, text):
    ts   = datetime.now().strftime("%H:%M")
    line = f"[{ts}] {name}: {text}"

    # Trigger Pusher (instant delivery to web)
    try:
        pusher_trigger("message", {"line": line})
    except Exception:
        pass

    # Save to JSONBin for history
    for attempt in range(4):
        try:
            rec  = bin_get()
            msgs = rec.get("messages", [])
            if line not in msgs:
                msgs.append(line)
                rec["messages"] = msgs[-MAX_HISTORY:]
                bin_put(rec)
            return
        except Exception:
            if attempt < 3:
                time.sleep(1 * (attempt + 1))
    console.print("[bold red]Could not save message — try again.[/bold red]")

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

    for _ in range(5):
        try:
            rec = bin_get()
            for m in rec.get("messages", []):
                seen.add(m)
            for u in online_users(rec.get("presence", {}), name):
                confirmed.add(u)
            break
        except Exception:
            time.sleep(2)

    ready_event.set()

    while not stop_event.is_set():
        try:
            rec    = bin_get()
            msgs   = rec.get("messages", [])
            now_on = set(online_users(rec.get("presence", {}), name))

            for m in msgs:
                if m not in seen:
                    seen.add(m)
                    if own_prefix not in m.lower():
                        console.print("")
                        console.print(fmt(m))

            for u in now_on - confirmed:
                absence.pop(u, None)
                confirmed.add(u)
                console.print(f"\n[dim]  --> {u} joined[/dim]")

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
        try:
            rec   = bin_get()
            users = online_users(rec.get("presence", {}), name)
            if users:
                console.print("  " + "  ".join(f"[bold green]● {u}[/bold green]" for u in users))
            else:
                console.print("[dim]  No one else online.[/dim]")
        except Exception:
            console.print("[bold red]Could not fetch.[/bold red]")

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

    # Password — 3 attempts, checked against hash
    for attempt in range(3):
        pwd = getpass.getpass("Password: ")
        if check_password(pwd):
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
        users = online_users(rec.get("presence", {}), name)
        console.print(f"[dim]Joined as [bold]{name}[/bold].[/dim]")
        if users:
            console.print("  " + "  ".join(f"[bold green]● {u}[/bold green]" for u in users))
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
