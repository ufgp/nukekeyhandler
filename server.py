import os
import sqlite3
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask, request, jsonify, session, redirect
from markupsafe import Markup

from pathlib import Path

env_path = Path(__file__).parent / "login_info"
load_dotenv(env_path)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")


DB = "licenses.db"

def init_db():
    with sqlite3.connect(DB) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                key        TEXT PRIMARY KEY,
                hwid       TEXT,
                activated  INTEGER DEFAULT 0,
                key_type   TEXT DEFAULT 'lifetime',
                expires_at TEXT,
                created_at TEXT
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                key        TEXT,
                key_type   TEXT,
                cost       REAL,
                created_at TEXT,
                notes      TEXT
            )
        """)
        con.commit()


def get_db():
    return sqlite3.connect(DB)


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated


def badge(key_type):
    mapping = {
        "lifetime": ("badge-life",  "Lifetime"),
        "30days":   ("badge-30",    "30 Days"),
        "90days":   ("badge-90",    "90 Days"),
    }
    cls, label = mapping.get(key_type, ("badge-life", key_type))
    return f'<span class="badge {cls}">{label}</span>'


CSS = """
<style>
:root {
  --bg:      #080808;
  --surface: #0f0f0f;
  --border:  #1c1c1c;
  --accent:  #c8ff00;
  --red:     #ff3c3c;
  --text:    #e8e8e8;
  --muted:   #555;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:var(--bg);color:var(--text);font-family:'Space Mono',monospace;font-size:13px}
::-webkit-scrollbar{width:4px}::-webkit-scrollbar-track{background:var(--bg)}::-webkit-scrollbar-thumb{background:var(--border)}
a{color:inherit;text-decoration:none}

.shell{display:flex;min-height:100vh}
.sidebar{width:210px;min-height:100vh;background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;position:sticky;top:0}
.logo{font-family:'Syne',sans-serif;font-weight:800;font-size:22px;color:var(--accent);letter-spacing:-1px;padding:28px 24px;border-bottom:1px solid var(--border)}
.nav{display:flex;flex-direction:column;padding:12px 0;flex:1}
.nav a{display:flex;align-items:center;gap:10px;padding:11px 24px;color:var(--muted);font-size:11px;letter-spacing:.08em;text-transform:uppercase;transition:all .15s;border-left:2px solid transparent}
.nav a:hover,.nav a.active{color:var(--accent);border-left-color:var(--accent);background:rgba(200,255,0,.03)}
.sidebar-footer{padding:20px 24px;border-top:1px solid var(--border)}
.btn-logout{display:block;text-align:center;padding:9px;border:1px solid var(--border);color:var(--muted);font-size:11px;letter-spacing:.08em;text-transform:uppercase;transition:all .15s;border-radius:3px}
.btn-logout:hover{border-color:var(--red);color:var(--red)}

.main{flex:1;padding:40px 48px;overflow-y:auto}
.page-header{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:32px;padding-bottom:24px;border-bottom:1px solid var(--border)}
.page-title{font-family:'Syne',sans-serif;font-weight:800;font-size:26px;letter-spacing:-1px}
.page-title span{color:var(--accent)}
.page-sub{color:var(--muted);font-size:11px;margin-top:4px}

.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:32px}
.stat{background:var(--surface);border:1px solid var(--border);padding:20px 24px;border-radius:3px}
.stat-val{font-family:'Syne',sans-serif;font-size:30px;font-weight:800;color:var(--accent)}
.stat-label{color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.1em;margin-top:4px}

.table-wrap{background:var(--surface);border:1px solid var(--border);border-radius:3px;overflow:hidden}
table{width:100%;border-collapse:collapse}
th{text-align:left;padding:12px 18px;font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);border-bottom:1px solid var(--border);background:rgba(255,255,255,.01)}
td{padding:13px 18px;border-bottom:1px solid var(--border);vertical-align:middle}
tr:last-child td{border-bottom:none}
tr:hover td{background:rgba(255,255,255,.015)}
.mono{font-family:'Space Mono',monospace;font-size:11px;color:var(--accent)}

.badge{display:inline-block;padding:3px 8px;border-radius:2px;font-size:10px;text-transform:uppercase;letter-spacing:.08em;font-weight:700}
.badge-life{background:rgba(200,255,0,.1);color:var(--accent)}
.badge-30{background:rgba(255,160,0,.1);color:#ffa000}
.badge-90{background:rgba(100,160,255,.1);color:#64a0ff}
.badge-yes{background:rgba(200,255,0,.1);color:var(--accent)}
.badge-no{background:rgba(255,60,60,.1);color:var(--red)}

.form-card{background:var(--surface);border:1px solid var(--border);border-radius:3px;padding:32px;max-width:520px}
.form-row{margin-bottom:18px}
label{display:block;font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin-bottom:7px}
input,select,textarea{width:100%;background:var(--bg);border:1px solid var(--border);color:var(--text);padding:10px 13px;font-family:'Space Mono',monospace;font-size:13px;border-radius:3px;outline:none;transition:border .15s}
input:focus,select:focus,textarea:focus{border-color:var(--accent)}
select option{background:var(--surface)}
textarea{resize:vertical;min-height:80px}

.btn{display:inline-flex;align-items:center;gap:8px;padding:10px 22px;font-family:'Space Mono',monospace;font-size:12px;font-weight:700;letter-spacing:.04em;border:none;cursor:pointer;border-radius:3px;transition:all .15s}
.btn-primary{background:var(--accent);color:#000}
.btn-primary:hover{background:#d4ff1a}
.btn-danger{background:transparent;border:1px solid var(--red);color:var(--red);font-size:11px;padding:5px 12px}
.btn-danger:hover{background:rgba(255,60,60,.1)}

.flash{padding:12px 18px;border-radius:3px;margin-bottom:24px;font-size:12px}
.flash-ok{background:rgba(200,255,0,.07);border:1px solid rgba(200,255,0,.2);color:var(--accent)}
.flash-err{background:rgba(255,60,60,.07);border:1px solid rgba(255,60,60,.2);color:var(--red)}

.empty{text-align:center;padding:40px;color:var(--muted);font-size:12px}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:28px;align-items:start}
.section-title{font-family:'Syne',sans-serif;font-weight:700;font-size:15px;margin-bottom:16px}

.login-wrap{min-height:100vh;display:flex;align-items:center;justify-content:center}
.login-box{width:360px}
.login-logo{font-family:'Syne',sans-serif;font-weight:800;font-size:34px;color:var(--accent);margin-bottom:6px;letter-spacing:-2px}
.login-sub{color:var(--muted);font-size:11px;margin-bottom:28px}
</style>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
"""


def page(title, body, active=""):
    nav_links = [
        ("/",            "dashboard", "◈", "Dashboard"),
        ("/keys",        "keys",      "⌗", "Keys"),
        ("/generate",    "generate",  "+", "Generate Key"),
        ("/orders",      "orders",    "▤", "Orders"),
        ("/orders/new",  "new_order", "✦", "New Order"),
    ]
    nav_html = ""
    for href, name, icon, label in nav_links:
        cls = "active" if active == name else ""
        nav_html += f'<a href="{href}" class="{cls}"><span>{icon}</span>{label}</a>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Black Horizon — {title}</title>{CSS}</head>
<body>
<div class="shell">
  <aside class="sidebar">
    <div class="logo">Black Horizon<span style="color:var(--muted);font-weight:400">.</span></div>
    <nav class="nav">{nav_html}</nav>
    <div class="sidebar-footer"><a href="/logout" class="btn-logout">Sign Out</a></div>
  </aside>
  <main class="main">{body}</main>
</div>
</body></html>"""


def login_page(error=""):
    err_html = f'<div class="flash flash-err">{error}</div>' if error else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Black Horizon — Login</title>{CSS}</head>
<body>
<div class="login-wrap">
  <div class="login-box">
    <div class="login-logo">Black Horizon.</div>
    <div class="login-sub">License Management Panel</div>
    {err_html}
    <form method="POST">
      <div class="form-row"><label>Username</label><input type="text" name="username" autofocus></div>
      <div class="form-row"><label>Password</label><input type="password" name="password"></div>
      <button class="btn btn-primary" style="width:100%;justify-content:center" type="submit">Enter Panel</button>
    </form>
  </div>
</div>
</body></html>"""


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == ADMIN_USERNAME and request.form.get("password") == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect("/")
        return login_page("Invalid credentials.")
    return login_page()


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/")
@login_required
def dashboard():
    with get_db() as con:
        total_keys   = con.execute("SELECT COUNT(*) FROM licenses").fetchone()[0]
        active_keys  = con.execute("SELECT COUNT(*) FROM licenses WHERE activated=1").fetchone()[0]
        total_orders = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        revenue      = con.execute("SELECT SUM(cost) FROM orders").fetchone()[0] or 0
        recent_keys  = con.execute("SELECT key, key_type, activated, created_at FROM licenses ORDER BY created_at DESC LIMIT 5").fetchall()
        recent_ord   = con.execute("SELECT key, key_type, cost, created_at FROM orders ORDER BY created_at DESC LIMIT 5").fetchall()

    k_rows = ""
    for r in recent_keys:
        act = '<span class="badge badge-yes">Yes</span>' if r[2] else '<span class="badge badge-no">No</span>'
        k_rows += f"<tr><td class='mono'>{r[0]}</td><td>{badge(r[1])}</td><td>{act}</td><td style='color:var(--muted)'>{r[3] or '—'}</td></tr>"
    if not k_rows:
        k_rows = "<tr><td colspan='4' class='empty'>No keys yet</td></tr>"

    o_rows = ""
    for r in recent_ord:
        o_rows += f"<tr><td class='mono'>{r[0] or '—'}</td><td>{badge(r[1])}</td><td style='color:var(--accent)'>£{r[2]:.2f}</td><td style='color:var(--muted)'>{r[3]}</td></tr>"
    if not o_rows:
        o_rows = "<tr><td colspan='4' class='empty'>No orders yet</td></tr>"

    body = f"""
    <div class="page-header">
      <div><div class="page-title">Dashboard <span>↗</span></div><div class="page-sub">Overview of your license panel</div></div>
    </div>
    <div class="stats">
      <div class="stat"><div class="stat-val">{total_keys}</div><div class="stat-label">Total Keys</div></div>
      <div class="stat"><div class="stat-val">{active_keys}</div><div class="stat-label">Activated</div></div>
      <div class="stat"><div class="stat-val">{total_orders}</div><div class="stat-label">Orders</div></div>
      <div class="stat"><div class="stat-val">£{revenue:.2f}</div><div class="stat-label">Revenue</div></div>
    </div>
    <div class="two-col">
      <div>
        <div class="section-title">Recent Keys</div>
        <div class="table-wrap"><table>
          <tr><th>Key</th><th>Type</th><th>Activated</th><th>Created</th></tr>
          {k_rows}
        </table></div>
      </div>
      <div>
        <div class="section-title">Recent Orders</div>
        <div class="table-wrap"><table>
          <tr><th>Key</th><th>Type</th><th>Cost</th><th>Date</th></tr>
          {o_rows}
        </table></div>
      </div>
    </div>"""
    return page("Dashboard", body, "dashboard")


@app.route("/keys")
@login_required
def keys():
    with get_db() as con:
        rows = con.execute("SELECT key, key_type, activated, hwid, created_at, expires_at FROM licenses ORDER BY created_at DESC").fetchall()

    rows_html = ""
    for r in rows:
        act  = '<span class="badge badge-yes">Yes</span>' if r[2] else '<span class="badge badge-no">No</span>'
        hwid = f'<span style="color:var(--muted);font-size:10px">{r[3][:20]}…</span>' if r[3] else '<span style="color:var(--muted)">—</span>'
        exp  = r[5] if r[5] else "Never"
        rows_html += f"""<tr>
          <td class="mono">{r[0]}</td>
          <td>{badge(r[1])}</td>
          <td>{act}</td>
          <td>{hwid}</td>
          <td style="color:var(--muted)">{r[4] or '—'}</td>
          <td style="color:var(--muted)">{exp}</td>
          <td>
            <form method="POST" action="/keys/revoke" style="display:inline">
              <input type="hidden" name="key" value="{r[0]}">
              <button class="btn btn-danger" onclick="return confirm('Revoke this key?')">Revoke</button>
            </form>
          </td>
        </tr>"""
    if not rows_html:
        rows_html = "<tr><td colspan='7' class='empty'>No keys generated yet.</td></tr>"

    body = f"""
    <div class="page-header">
      <div><div class="page-title">Keys <span>⌗</span></div><div class="page-sub">{len(rows)} total keys</div></div>
      <a href="/generate" class="btn btn-primary">+ Generate Key</a>
    </div>
    <div class="table-wrap"><table>
      <tr><th>Key</th><th>Type</th><th>Activated</th><th>HWID</th><th>Created</th><th>Expires</th><th></th></tr>
      {rows_html}
    </table></div>"""
    return page("Keys", body, "keys")


@app.route("/keys/revoke", methods=["POST"])
@login_required
def revoke_key():
    key = request.form.get("key")
    with get_db() as con:
        con.execute("DELETE FROM licenses WHERE key = ?", (key,))
        con.commit()
    return redirect("/keys")


@app.route("/generate", methods=["GET", "POST"])
@login_required
def generate():
    flash_html = ""
    if request.method == "POST":
        key_type = request.form.get("key_type", "lifetime")
        raw      = uuid.uuid4().hex.upper()
        key      = f"{raw[:5]}-{raw[5:10]}-{raw[10:15]}-{raw[15:20]}"
        now      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if key_type == "30days":
            expires = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        elif key_type == "90days":
            expires = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S")
        else:
            expires = None

        with get_db() as con:
            con.execute(
                "INSERT INTO licenses (key, key_type, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (key, key_type, now, expires)
            )
            con.commit()

        flash_html = f'<div class="flash flash-ok">Key generated: <strong>{key}</strong> &nbsp;·&nbsp; Type: {key_type} &nbsp;·&nbsp; Expires: {expires or "Never"}</div>'

    body = f"""
    <div class="page-header">
      <div><div class="page-title">Generate Key <span>+</span></div><div class="page-sub">Create a new license key</div></div>
    </div>
    {flash_html}
    <div class="form-card">
      <form method="POST">
        <div class="form-row">
          <label>Key Type</label>
          <select name="key_type">
            <option value="lifetime">Lifetime</option>
            <option value="30days">30 Days</option>
            <option value="90days">90 Days</option>
          </select>
        </div>
        <button class="btn btn-primary" type="submit">Generate Key</button>
      </form>
    </div>"""
    return page("Generate Key", body, "generate")


@app.route("/orders")
@login_required
def orders():
    with get_db() as con:
        rows = con.execute("SELECT id, key, key_type, cost, created_at, notes FROM orders ORDER BY created_at DESC").fetchall()

    total     = sum(r[3] for r in rows) if rows else 0
    rows_html = ""
    for r in rows:
        rows_html += f"""<tr>
          <td style="color:var(--muted)">{r[0]}</td>
          <td class="mono">{r[1] or '—'}</td>
          <td>{badge(r[2])}</td>
          <td style="color:var(--accent)">£{r[3]:.2f}</td>
          <td style="color:var(--muted)">{r[4]}</td>
          <td style="color:var(--muted);font-size:11px">{r[5] or '—'}</td>
          <td>
            <form method="POST" action="/orders/delete" style="display:inline">
              <input type="hidden" name="id" value="{r[0]}">
              <button class="btn btn-danger" onclick="return confirm('Delete this order?')">Delete</button>
            </form>
          </td>
        </tr>"""
    if not rows_html:
        rows_html = "<tr><td colspan='7' class='empty'>No orders recorded yet.</td></tr>"

    body = f"""
    <div class="page-header">
      <div><div class="page-title">Orders <span>▤</span></div><div class="page-sub">{len(rows)} orders &nbsp;·&nbsp; £{total:.2f} total revenue</div></div>
      <a href="/orders/new" class="btn btn-primary">+ New Order</a>
    </div>
    <div class="table-wrap"><table>
      <tr><th>#</th><th>Key</th><th>Type</th><th>Cost</th><th>Date</th><th>Info</th><th></th></tr>
      {rows_html}
    </table></div>"""
    return page("Orders", body, "orders")


@app.route("/orders/delete", methods=["POST"])
@login_required
def delete_order():
    oid = request.form.get("id")
    with get_db() as con:
        con.execute("DELETE FROM orders WHERE id = ?", (oid,))
        con.commit()
    return redirect("/orders")


@app.route("/orders/new", methods=["GET", "POST"])
@login_required
def new_order():
    flash_html = ""
    if request.method == "POST":
        key      = request.form.get("key", "").strip()
        key_type = request.form.get("key_type", "lifetime")
        cost     = float(request.form.get("cost") or 0)
        notes    = request.form.get("notes", "").strip()
        now      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with get_db() as con:
            con.execute(
                "INSERT INTO orders (key, key_type, cost, created_at, notes) VALUES (?, ?, ?, ?, ?)",
                (key, key_type, cost, now, notes)
            )
            con.commit()
        flash_html = '<div class="flash flash-ok">Order recorded successfully.</div>'

    with get_db() as con:
        all_keys = con.execute("SELECT key, key_type FROM licenses ORDER BY created_at DESC").fetchall()

    key_options = '<option value="">— Select a key —</option>'
    for k in all_keys:
        key_options += f'<option value="{k[0]}">{k[0]} ({k[1]})</option>'

    body = f"""
    <div class="page-header">
      <div><div class="page-title">New Order <span>✦</span></div><div class="page-sub">Record a new sale</div></div>
    </div>
    {flash_html}
    <div class="form-card">
      <form method="POST">
        <div class="form-row">
          <label>License Key (optional)</label>
          <select name="key">{key_options}</select>
        </div>
        <div class="form-row">
          <label>Key Type</label>
          <select name="key_type">
            <option value="lifetime">Lifetime</option>
            <option value="30days">30 Days</option>
            <option value="90days">90 Days</option>
          </select>
        </div>
        <div class="form-row">
          <label>Cost (£)</label>
          <input type="number" name="cost" step="0.01" min="0" placeholder="0.00">
        </div>
        <div class="form-row">
          <label>Info</label>
          <textarea name="notes" placeholder="Buyer username, platform, etc."></textarea>
        </div>
        <button class="btn btn-primary" type="submit">Record Order</button>
      </form>
    </div>"""
    return page("New Order", body, "new_order")


@app.route("/validate", methods=["POST"])
def validate():
    data = request.json or {}
    key  = data.get("key", "").strip().upper()
    hwid = data.get("hwid", "").strip()

    if not key or not hwid:
        return jsonify({"valid": False, "reason": "Missing key or HWID"})

    with get_db() as con:
        row = con.execute(
            "SELECT hwid, activated, key_type, expires_at FROM licenses WHERE key = ?", (key,)
        ).fetchone()

    if not row:
        return jsonify({"valid": False, "reason": "Invalid key"})

    stored_hwid, activated, key_type, expires_at = row

    if expires_at:
        if datetime.now() > datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S"):
            return jsonify({"valid": False, "reason": "Key has expired"})

    if activated and stored_hwid != hwid:
        return jsonify({"valid": False, "reason": "Key already activated on another device"})

    if not activated:
        with get_db() as con:
            con.execute("UPDATE licenses SET hwid=?, activated=1 WHERE key=?", (hwid, key))
            con.commit()

    return jsonify({"valid": True, "key_type": key_type})


if __name__ == "__main__":
    init_db()
    print("\n  Black Horizon License Panel → http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)