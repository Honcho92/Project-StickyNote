"""
Licensing for StickyNotes.

Model
-----
- Free tier: up to FREE_NOTE_LIMIT notes and the two basic pin types.
- Pro: unlimited notes + the Pro pin plugins (and future Pro features).
- 14-day Pro trial on first run, then it reverts to free limits (notes are kept).
- Pro is unlocked with a license key. Two kinds are accepted:
    1. Gumroad-issued keys (the store) -- verified once, online, at activation.
    2. Our own offline, Ed25519-signed keys (minted with make_license.py) --
       verified locally with the embedded public key, no server needed. These
       are the backup / manual-issue path.

State lives in %APPDATA%\\StickyNotes\\license.json.
"""

import base64
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    _HAVE_CRYPTO = True
except Exception:
    _HAVE_CRYPTO = False

# ---------------------------------------------------------------------------
# The PUBLIC half of the licensing key pair. The matching PRIVATE key mints
# license keys and must be kept secret (see make_license.py). Safe to ship.
PUBLIC_KEY_HEX = "0683417b9e0432d9c79d2de93e3deb3978bb67640978f85e09949b976982ac76"

KEY_PREFIX = "SN1-"
FREE_NOTE_LIMIT = 5
TRIAL_DAYS = 14

# Store (Gumroad) settings
BUY_URL = "https://zachfollett.gumroad.com/l/zzcfwu"
GUMROAD_PRODUCT_ID = "Kk2X-9yBImV_lx_f3XtUjg=="
GUMROAD_VERIFY_URL = "https://api.gumroad.com/v2/licenses/verify"


def _data_dir():
    base = (os.environ.get("APPDATA")
            or os.environ.get("XDG_DATA_HOME")
            or os.path.expanduser("~"))
    d = Path(base) / "StickyNotes"
    d.mkdir(parents=True, exist_ok=True)
    return d


LICENSE_FILE = _data_dir() / "license.json"


def _now():
    return int(time.time())


def _b64d(s):
    s = s.strip()
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s.encode())


def _b64e(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


# ---- offline (our own) signed keys ----------------------------------------
def verify_key(key):
    """Return the payload dict if OUR key's signature is valid, else None.

    Does NOT check expiry -- callers decide what to do with an expired payload.
    Payload shape: {"email": str, "tier": "pro", "iat": int, "exp": int|None}
    """
    if not _HAVE_CRYPTO or not key:
        return None
    try:
        k = key.strip()
        if k.startswith(KEY_PREFIX):
            k = k[len(KEY_PREFIX):]
        payload_b64, sig_b64 = k.split(".", 1)
        msg = _b64d(payload_b64)
        sig = _b64d(sig_b64)
        pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(PUBLIC_KEY_HEX))
        pub.verify(sig, msg)          # raises InvalidSignature if tampered
        return json.loads(msg)
    except (InvalidSignature, ValueError, KeyError, Exception):
        return None


# ---- Gumroad store keys ----------------------------------------------------
def gumroad_verify(key):
    """Verify a Gumroad license key online. Returns {'email':..} on success,
    None on failure (invalid key, refunded, or no network). Called once at
    activation; we do NOT increment the use count so reinstalling won't lock
    anyone out."""
    if not GUMROAD_PRODUCT_ID or not key:
        return None
    data = urllib.parse.urlencode({
        "product_id": GUMROAD_PRODUCT_ID,
        "license_key": key.strip(),
        "increment_uses_count": "false",
    }).encode()
    try:
        req = urllib.request.Request(GUMROAD_VERIFY_URL, data=data)
        with urllib.request.urlopen(req, timeout=12) as resp:
            res = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            res = json.loads(e.read().decode())
        except Exception:
            return None
    except Exception:
        return None
    if not res.get("success"):
        return None
    purchase = res.get("purchase", {}) or {}
    if purchase.get("refunded") or purchase.get("chargebacked") or purchase.get("disputed"):
        return None
    return {"email": purchase.get("email", "")}


# ---- persistent state ------------------------------------------------------
def _load_state():
    try:
        with open(LICENSE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(state):
    try:
        tmp = LICENSE_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        tmp.replace(LICENSE_FILE)
    except Exception:
        pass


def _ensure_first_run(state):
    if "first_run" not in state:
        state["first_run"] = _now()
        _save_state(state)
    return state


def activate(key):
    """Validate and store a license key. Returns (ok: bool, message: str)."""
    key = (key or "").strip()
    if not key:
        return False, "Please paste your license key."

    # 1) Our own offline signed keys (start with SN1-, verified locally)
    payload = verify_key(key)
    if payload is not None:
        exp = payload.get("exp")
        if exp and _now() > exp:
            return False, "That license key has expired."
        state = _load_state()
        state.update({"key": key, "source": "offline", "email": payload.get("email", "")})
        _save_state(state)
        who = payload.get("email", "")
        return True, "Pro unlocked. Thank you!" + (f"\nLicensed to {who}." if who else "")

    # 2) Gumroad-issued keys (verified online, once)
    g = gumroad_verify(key)
    if g is not None:
        state = _load_state()
        state.update({"key": key, "source": "gumroad", "email": g.get("email", "")})
        _save_state(state)
        who = g.get("email", "")
        return True, "Pro unlocked. Thank you!" + (f"\nLicensed to {who}." if who else "")

    return False, ("Couldn't verify that key. Make sure you copied it exactly and "
                   "that you're connected to the internet, then try again.")


def status():
    """Current entitlement.

    Returns a dict:
      pro: bool
      reason: "licensed" | "trial" | "free"
      email: str
      trial_days_left: int   (only meaningful while reason == 'trial')
    """
    state = _ensure_first_run(_load_state())

    key = state.get("key")
    if key:
        if state.get("source") == "gumroad":
            # Verified online at activation; trust it afterwards (offline-friendly).
            return {"pro": True, "reason": "licensed",
                    "email": state.get("email", ""), "trial_days_left": 0}
        # Our offline signed key: re-check the signature every time (cheap, local).
        payload = verify_key(key)
        if payload is not None:
            exp = payload.get("exp")
            if not exp or _now() <= exp:
                return {"pro": True, "reason": "licensed",
                        "email": payload.get("email", ""), "trial_days_left": 0}

    elapsed_days = (_now() - int(state.get("first_run", _now()))) / 86400.0
    days_left = int(TRIAL_DAYS - elapsed_days + 0.9999)
    if elapsed_days < TRIAL_DAYS:
        return {"pro": True, "reason": "trial", "email": "",
                "trial_days_left": max(0, days_left)}

    return {"pro": False, "reason": "free", "email": "", "trial_days_left": 0}


def is_pro():
    return status()["pro"]


def note_limit():
    """Max notes allowed right now, or None for unlimited (Pro)."""
    return None if is_pro() else FREE_NOTE_LIMIT
