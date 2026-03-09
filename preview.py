#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["jinja2"]
# ///
"""
Local template preview renderer for The Local Synapse templates.

Usage:
    uv run preview.py           # Render all templates and open index
    uv run preview.py clean     # Delete rendered/ directory
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import jinja2
from markupsafe import Markup

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent
TEMPLATES_DIR = ROOT / "templates"
RENDERED_DIR = ROOT / "rendered"

if len(sys.argv) > 1 and sys.argv[1] == "clean":
    import shutil
    shutil.rmtree(RENDERED_DIR, ignore_errors=True)
    print("Cleaned rendered/")
    sys.exit(0)

RENDERED_DIR.mkdir(exist_ok=True)

# ── Jinja2 environment ────────────────────────────────────────────────────────

loader = jinja2.FileSystemLoader(str(TEMPLATES_DIR))
env = jinja2.Environment(
    loader=loader,
    autoescape=jinja2.select_autoescape(["html"]),  # txt templates not escaped
)

# Mock Synapse filters
def mxc_to_http(mxc_url, width=480, height=360, mode="scale"):
    """Converts mxc:// URLs to a placeholder image URL."""
    return f"https://via.placeholder.com/{width}x{height}/e0dbd3/8a8299?text=Image"

def format_ts(ts, fmt="%b %d %H:%M"):
    """Formats a millisecond timestamp."""
    if not ts:
        return ""
    return datetime.fromtimestamp(ts / 1000).strftime(fmt)

env.filters["mxc_to_http"] = mxc_to_http
env.filters["format_ts"] = format_ts

# ── Mock contexts ─────────────────────────────────────────────────────────────

now_ms = int(datetime.now().timestamp() * 1000)

LINK = "https://matrix.thelocal.chat/_matrix/client/v3/account/password/email/requestToken/submit?token=preview_token_abc123&client_secret=preview_secret"

NOTIF_CONTEXT = {
    "user_display_name": "Sam",
    "summary_text": "You have 3 new messages in The Local.",
    "unsubscribe_link": "https://matrix.thelocal.chat/_matrix/push/v1/notify",
    "reason": {
        "room_name": "dm-general",
        "now": now_ms,
        "received_at": now_ms - 5000,
        "delay_before_mail_ms": 120000,
        "last_sent_ts": now_ms - 7200000,
        "throttle_ms": 600000,
    },
    "rooms": [
        {
            "title": "#dm-general:thelocal.chat",
            "link": "https://thelocal.chat/#/room/#dm-general:thelocal.chat",
            "invite": False,
            "notifs": [
                {
                    "link": "https://thelocal.chat/#/room/!xyz:thelocal.chat/$event1",
                    "messages": [
                        {
                            "sender_name": "Travis",
                            "event_type": "m.room.message",
                            "msgtype": "m.text",
                            "body_text_html": Markup("Hey, can you review the governance proposal? I think we're ready to vote on Thursday."),
                            "body_text_plain": "Hey, can you review the governance proposal? I think we're ready to vote on Thursday.",
                            "image_url": None,
                        },
                        {
                            "sender_name": "Travis",
                            "event_type": "m.room.message",
                            "msgtype": "m.text",
                            "body_text_html": Markup("I'll share the draft in #dm-assembly shortly."),
                            "body_text_plain": "I'll share the draft in #dm-assembly shortly.",
                            "image_url": None,
                        },
                    ],
                },
                {
                    "link": "https://thelocal.chat/#/room/!xyz:thelocal.chat/$event2",
                    "messages": [
                        {
                            "sender_name": "Chris",
                            "event_type": "m.room.message",
                            "msgtype": "m.text",
                            "body_text_html": Markup("Sounds good. I'll read it tonight."),
                            "body_text_plain": "Sounds good. I'll read it tonight.",
                            "image_url": None,
                        },
                    ],
                },
            ],
        },
        {
            "title": "#dm-assembly:thelocal.chat",
            "link": "https://thelocal.chat/#/room/#dm-assembly:thelocal.chat",
            "invite": True,
            "notifs": [],
        },
    ],
}

# (template_name, output_name, context)
HTML_TEMPLATES = [
    ("password_reset.html",         "password_reset.html",         {"link": LINK}),
    ("registration.html",           "registration.html",           {"link": LINK}),
    ("add_threepid.html",           "add_threepid.html",           {"link": LINK}),
    ("add_threepid_success.html",   "add_threepid_success.html",   {}),
    ("add_threepid_failure.html",   "add_threepid_failure.html",   {"failure_reason": "The link has expired. Please request a new verification email."}),
    ("password_reset_success.html", "password_reset_success.html", {}),
    ("password_reset_failure.html", "password_reset_failure.html", {"failure_reason": "The link has expired or already been used. Please request a new password reset."}),
    ("registration_token.html",     "registration_token.html",     {"myurl": "#", "session": "session_abc123"}),
    ("registration_token.html",     "registration_token_error.html", {"myurl": "#", "session": "session_abc123", "error": "Invalid or expired token. Please try again."}),
    ("registration_failure.html",   "registration_failure.html",   {"failure_reason": "This username is already taken. Please choose another."}),
    ("invalid_token.html",          "invalid_token.html",          {}),
    ("already_in_use.html",         "already_in_use.html",         {}),
    ("notif_mail.html",             "notif_mail.html",             NOTIF_CONTEXT),
]

TXT_TEMPLATES = [
    ("password_reset.txt",  "password_reset.txt",  {"link": LINK}),
    ("registration.txt",    "registration.txt",    {"link": LINK}),
    ("add_threepid.txt",    "add_threepid.txt",    {"link": LINK}),
    ("already_in_use.txt",  "already_in_use.txt",  {}),
    ("notif_mail.txt",      "notif_mail.txt",      NOTIF_CONTEXT),
]

# ── Render ────────────────────────────────────────────────────────────────────

rendered_html = []
errors = []

print("\nRendering HTML templates:")
for template_name, out_name, context in HTML_TEMPLATES:
    try:
        template = env.get_template(template_name)
        output = template.render(**context)
        out_path = RENDERED_DIR / out_name
        out_path.write_text(output, encoding="utf-8")
        rendered_html.append((out_name, out_path))
        print(f"  ✓ {out_name}")
    except Exception as e:
        errors.append((out_name, str(e)))
        print(f"  ✗ {out_name}: {e}")

print("\nRendering text templates:")
for template_name, out_name, context in TXT_TEMPLATES:
    try:
        template = env.get_template(template_name)
        output = template.render(**context)
        out_path = RENDERED_DIR / out_name
        out_path.write_text(output, encoding="utf-8")
        print(f"  ✓ {out_name}")
    except Exception as e:
        errors.append((out_name, str(e)))
        print(f"  ✗ {out_name}: {e}")

# ── Index page ────────────────────────────────────────────────────────────────

LABELS = {
    "password_reset.html":         ("Email", "Password reset request"),
    "registration.html":           ("Email", "Registration confirmation"),
    "add_threepid.html":           ("Email", "Add email address"),
    "notif_mail.html":             ("Email", "Notification digest"),
    "add_threepid_success.html":   ("Web page", "Email verified"),
    "password_reset_success.html": ("Web page", "Password reset confirmed"),
    "registration_token.html":     ("Web page", "Registration token"),
    "registration_token_error.html": ("Web page", "Registration token (error state)"),
    "add_threepid_failure.html":   ("Web page", "Email verification failed"),
    "password_reset_failure.html": ("Web page", "Password reset failed"),
    "registration_failure.html":   ("Web page", "Registration failed"),
    "invalid_token.html":          ("Web page", "Invalid token"),
    "already_in_use.html":         ("Web page", "Email already in use"),
}

items_html = ""
for out_name, out_path in rendered_html:
    kind, label = LABELS.get(out_name, ("", out_name))
    kind_color = "#ed1d26" if kind == "Email" else "#220D46"
    items_html += f"""
    <a href="{out_name}" class="item">
        <span class="kind" style="color:{kind_color}">{kind}</span>
        <span class="label">{label}</span>
        <span class="filename">{out_name}</span>
    </a>"""

error_html = ""
if errors:
    error_html = "<div class='errors'><strong>Errors:</strong><ul>"
    for name, msg in errors:
        error_html += f"<li><code>{name}</code>: {msg}</li>"
    error_html += "</ul></div>"

index = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Template Preview — The Local</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #F9F5F0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #220D46; padding: 2rem; }}
  h1 {{ font-size: 1.25rem; font-weight: 700; margin-bottom: 0.5rem; }}
  p {{ font-size: 14px; color: #8a8299; margin-bottom: 2rem; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 0.75rem; }}
  .item {{ display: block; background: white; border: 1.5px solid #e0dbd3; border-radius: 4px; padding: 1rem 1.25rem; text-decoration: none; color: inherit; transition: border-color 0.15s; }}
  .item:hover {{ border-color: #220D46; }}
  .kind {{ display: block; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.4rem; }}
  .label {{ display: block; font-size: 15px; font-weight: 600; margin-bottom: 0.3rem; }}
  .filename {{ display: block; font-size: 12px; color: #8a8299; font-family: monospace; }}
  .errors {{ background: #fff0f0; border: 1.5px solid #ed1d26; border-radius: 4px; padding: 1rem; margin-top: 1.5rem; font-size: 14px; }}
  .errors ul {{ margin: 0.5rem 0 0 1.25rem; }}
  .ts {{ font-size: 12px; color: #8a8299; margin-top: 2rem; }}
</style>
</head>
<body>
<h1>Template Preview — The Local</h1>
<p>Rendered {len(rendered_html)} templates · {datetime.now().strftime("%H:%M:%S")} · Click any to open</p>
<div class="grid">{items_html}
</div>
{error_html}
<p class="ts">Re-render: <code>python3 preview.py</code></p>
</body>
</html>"""

index_path = RENDERED_DIR / "index.html"
index_path.write_text(index, encoding="utf-8")

print(f"\nIndex: rendered/index.html")
if errors:
    print(f"Errors: {len(errors)}")

subprocess.run(["open", str(index_path)])
