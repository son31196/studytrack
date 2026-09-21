"""Edit-access control.

Local use is unchanged: with no STUDYTRACK_PASSWORD set the app is a
single-user tool and every request may write. Setting the variable (as a
public deployment must) flips the app into public mode, where anonymous
visitors get a read-only site and writes require logging in.
"""
import hmac
import os
import time
from flask import jsonify, request, session

PASSWORD_ENV = "STUDYTRACK_PASSWORD"
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# GETs that expose personal data rather than coursework. Public visitors get
# an empty payload instead of the real thing.
PRIVATE_GETS = {"/api/gcal/events"}

# Endpoints the guard must never block, or logging in becomes impossible.
EXEMPT_PATHS = {"/api/session"}

_attempts: dict[str, list[float]] = {}
_MAX_ATTEMPTS, _WINDOW = 8, 300.0


def password() -> str:
    return os.environ.get(PASSWORD_ENV, "").strip()


def is_public() -> bool:
    """True when a password is configured, i.e. this is a shared deployment."""
    return bool(password())


def can_edit() -> bool:
    if not is_public():
        return True
    return bool(session.get("editor"))


def _throttled(ip: str) -> bool:
    now = time.time()
    hits = [t for t in _attempts.get(ip, []) if now - t < _WINDOW]
    _attempts[ip] = hits
    return len(hits) >= _MAX_ATTEMPTS


def _record(ip: str) -> None:
    _attempts.setdefault(ip, []).append(time.time())


def attempt_login(candidate: str) -> tuple[bool, str]:
    """Verify a password guess. Returns (ok, error message)."""
    ip = request.remote_addr or "?"
    if _throttled(ip):
        return False, "too many attempts — wait a few minutes"
    pw = password()
    if not pw:
        return False, "no password configured on this server"
    if not hmac.compare_digest(candidate, pw):
        _record(ip)
        return False, "wrong password"
    _attempts.pop(ip, None)
    return True, ""


def guard():
    """before_request hook: refuse writes and private reads to visitors."""
    if request.path in EXEMPT_PATHS or can_edit():
        return None
    if request.method in WRITE_METHODS:
        return jsonify({"error": "This site is read-only. Log in to make changes."}), 403
    if request.path in PRIVATE_GETS:
        return jsonify({"connected": False, "events": [], "private": True})
    return None
