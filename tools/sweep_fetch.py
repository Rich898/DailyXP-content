#!/usr/bin/env python3
"""
sweep_fetch.py — the sweep FETCHER (limb #1a of the automated weekly sweep).

Deterministic. No LLM. Pulls each active student's Canvas through THEIR OWN
student API token and dumps the raw record to disk. Summarisation into the
targets outline is a SEPARATE limb (sweep_summarise.py, built next against
real dumps) — this file's only job is a faithful, minimal, auditable pull.

Doctrine enforced in code:
  - SIX CONTENT SURFACES ONLY (data minimisation, and this file is the public
    proof of what we read): courses, front pages, modules(+items), pages,
    announcements, assignments + calendar events. NEVER grades, submissions,
    inbox, or people. Adding a surface is a doctrine change, not a tweak.
  - Per-seat student tokens from env (CANVAS_TOKEN_<CODE>), read-only use.
    Token values are never printed. A dead/expired token degrades LOUDLY
    (seat marked failed) and never silently.
  - SHADOW-SAFE BY CONSTRUCTION: this tool writes only where --out points.
    The workflow points it at private/shadow/sweeps/<date>/ — physically
    outside targets/, which the live pipeline auto-picks. Promotion to
    targets/ is a separate, deliberate step that does not exist yet.
  - Raw is the record: page/announcement bodies kept as-is (truncated at a
    cap, flagged when cut) so the summariser can be re-run and improved
    against the same pull. Per SWEEP.md quirks, front pages are always
    body-fetched (week-by-week schedules live on course HOMEPAGES for some
    subjects) and per-teacher class shells arrive automatically because the
    student token sees every enrollment.

Env:
  CANVAS_BASE_URL      e.g. https://<school>.instructure.com  (no trailing /)
  CANVAS_TOKEN_<CODE>  per-seat student token, e.g. CANVAS_TOKEN_Y8

Usage:
  python3 tools/sweep_fetch.py --out private/shadow/sweeps/2026-08-24 [--seat y8]
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import time

try:
    import requests
except ImportError:
    sys.exit("sweep_fetch: `pip install requests` first")

# ---- tunables (windows chosen to match what a good manual sweep looked at) --
PAGE_BODY_WINDOW_DAYS = 28     # fetch bodies only for pages updated recently
PAGE_BODY_CAP_PER_COURSE = 20  # ...and never more than this many per course
ANNOUNCEMENT_WINDOW_DAYS = 35
ASSIGNMENT_PAST_DAYS = 7       # due dates: a week back...
ASSIGNMENT_FUTURE_DAYS = 75    # ...to most of a term ahead
EVENT_FUTURE_DAYS = 60
BODY_TRUNCATE_CHARS = 20000
DESC_TRUNCATE_CHARS = 4000
SLEEP_BETWEEN_CALLS = 0.35     # polite pacing, per SWEEP.md's batching spirit
TIMEOUT = 30
RETRIES = 3


def now_utc():
    return dt.datetime.now(dt.timezone.utc)


def iso(d):
    return d.strftime("%Y-%m-%d")


def parse_when(s):
    """Canvas ISO8601 -> aware datetime, or None."""
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def truncate(text, cap):
    if text is None:
        return None, False
    if len(text) <= cap:
        return text, False
    return text[:cap], True


class Canvas:
    """Tiny read-only Canvas REST client: auth, pagination, retry, pacing."""

    def __init__(self, base, token):
        self.base = base.rstrip("/")
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {token}"
        self.calls = 0

    def _get(self, url, params=None):
        for attempt in range(1, RETRIES + 1):
            time.sleep(SLEEP_BETWEEN_CALLS)
            self.calls += 1
            r = self.s.get(url, params=params, timeout=TIMEOUT)
            if r.status_code in (429, 500, 502, 503, 504) and attempt < RETRIES:
                wait = float(r.headers.get("Retry-After", 2 * attempt))
                time.sleep(min(wait, 30))
                continue
            return r
        return r

    def paged(self, path, params=None):
        """Yield items across Link-header pagination. Raises on 401 (dead
        token) so the seat fails loudly; other errors raise RuntimeError with
        the path so the caller can log-and-continue per surface."""
        url = self.base + path
        params = dict(params or {})
        params.setdefault("per_page", 100)
        while url:
            r = self._get(url, params=params)
            params = None  # only on first request; Link URLs carry the rest
            if r.status_code == 401:
                raise PermissionError("token rejected (401)")
            if r.status_code == 404:
                return
            if not r.ok:
                raise RuntimeError(f"{path}: HTTP {r.status_code}")
            data = r.json()
            if isinstance(data, dict):
                yield data
                return
            for item in data:
                yield item
            url = None
            for part in r.headers.get("Link", "").split(","):
                m = re.search(r'<([^>]+)>;\s*rel="next"', part)
                if m:
                    url = m.group(1)

    def one(self, path, params=None):
        """Single-object GET; None on 404."""
        r = self._get(self.base + path, params=params)
        if r.status_code == 401:
            raise PermissionError("token rejected (401)")
        if r.status_code == 404:
            return None
        if not r.ok:
            raise RuntimeError(f"{path}: HTTP {r.status_code}")
        return r.json()


def fetch_course(cv, course, log):
    """Pull the six surfaces for one course. Per-surface failures are logged
    and skipped so one broken corner never sinks the seat."""
    cid = course["id"]
    out = {
        "id": cid,
        "name": course.get("name"),
        "course_code": course.get("course_code"),
        "term": (course.get("term") or {}).get("name"),
        "front_page": None,
        "modules": [],
        "pages": [],
        "announcements": [],
        "assignments": [],
        "events": [],
    }
    now = now_utc()

    def surface(name, fn):
        try:
            fn()
        except PermissionError:
            raise
        except Exception as e:  # noqa: BLE001 — log-and-continue is the design
            log.append(f"course {cid} {name}: {e}")

    def _front():
        fp = cv.one(f"/api/v1/courses/{cid}/front_page")
        if fp:
            body, cut = truncate(fp.get("body"), BODY_TRUNCATE_CHARS)
            out["front_page"] = {
                "title": fp.get("title"),
                "updated_at": fp.get("updated_at"),
                "body": body,
                "truncated": cut,
            }

    def _modules():
        for m in cv.paged(f"/api/v1/courses/{cid}/modules",
                          {"include[]": "items"}):
            out["modules"].append({
                "name": m.get("name"),
                "position": m.get("position"),
                "items": [
                    {"title": i.get("title"), "type": i.get("type"),
                     "position": i.get("position")}
                    for i in (m.get("items") or [])
                ],
            })

    def _pages():
        fresh = now - dt.timedelta(days=PAGE_BODY_WINDOW_DAYS)
        listed = list(cv.paged(
            f"/api/v1/courses/{cid}/pages",
            {"sort": "updated_at", "order": "desc"}))
        bodies = 0
        for p in listed:
            entry = {"title": p.get("title"), "url": p.get("url"),
                     "updated_at": p.get("updated_at"), "body": None,
                     "truncated": False}
            upd = parse_when(p.get("updated_at"))
            if upd and upd >= fresh and bodies < PAGE_BODY_CAP_PER_COURSE:
                full = cv.one(f"/api/v1/courses/{cid}/pages/{p.get('url')}")
                if full:
                    entry["body"], entry["truncated"] = truncate(
                        full.get("body"), BODY_TRUNCATE_CHARS)
                    bodies += 1
            out["pages"].append(entry)

    def _announcements():
        fresh = now - dt.timedelta(days=ANNOUNCEMENT_WINDOW_DAYS)
        for a in cv.paged(f"/api/v1/courses/{cid}/discussion_topics",
                          {"only_announcements": "true"}):
            posted = parse_when(a.get("posted_at"))
            if posted and posted < fresh:
                continue
            msg, cut = truncate(a.get("message"), DESC_TRUNCATE_CHARS)
            out["announcements"].append({
                "title": a.get("title"), "posted_at": a.get("posted_at"),
                "message": msg, "truncated": cut,
            })

    def _assignments():
        lo = now - dt.timedelta(days=ASSIGNMENT_PAST_DAYS)
        hi = now + dt.timedelta(days=ASSIGNMENT_FUTURE_DAYS)
        upd_lo = now - dt.timedelta(days=PAGE_BODY_WINDOW_DAYS)
        for a in cv.paged(f"/api/v1/courses/{cid}/assignments",
                          {"order_by": "due_at"}):
            due = parse_when(a.get("due_at"))
            upd = parse_when(a.get("updated_at"))
            keep = (due and lo <= due <= hi) or (upd and upd >= upd_lo)
            if not keep:
                continue
            desc, cut = truncate(a.get("description"), DESC_TRUNCATE_CHARS)
            out["assignments"].append({
                "name": a.get("name"), "due_at": a.get("due_at"),
                "points_possible": a.get("points_possible"),
                "updated_at": a.get("updated_at"),
                "description": desc, "truncated": cut,
            })

    def _events():
        for e in cv.paged("/api/v1/calendar_events", {
                "type": "event",
                "context_codes[]": f"course_{cid}",
                "start_date": iso(now - dt.timedelta(days=3)),
                "end_date": iso(now + dt.timedelta(days=EVENT_FUTURE_DAYS))}):
            desc, cut = truncate(e.get("description"), DESC_TRUNCATE_CHARS)
            out["events"].append({
                "title": e.get("title"), "start_at": e.get("start_at"),
                "description": desc, "truncated": cut,
            })

    surface("front_page", _front)
    surface("modules", _modules)
    surface("pages", _pages)
    surface("announcements", _announcements)
    surface("assignments", _assignments)
    surface("events", _events)
    return out


def sweep_seat(base, code, token, out_dir):
    cv = Canvas(base, token)
    seat = {
        "seat": code,
        "fetched_at_utc": now_utc().isoformat(timespec="seconds"),
        "windows": {
            "page_body_days": PAGE_BODY_WINDOW_DAYS,
            "announcement_days": ANNOUNCEMENT_WINDOW_DAYS,
            "assignment_days": [ASSIGNMENT_PAST_DAYS, ASSIGNMENT_FUTURE_DAYS],
            "event_days": EVENT_FUTURE_DAYS,
        },
        "courses": [],
        "errors": [],
    }
    courses = [c for c in cv.paged("/api/v1/courses", {
                   "enrollment_state": "active", "include[]": "term"})
               if not c.get("access_restricted_by_date")]
    for c in courses:
        seat["courses"].append(fetch_course(cv, c, seat["errors"]))

    stats = {
        "courses": len(seat["courses"]),
        "page_bodies": sum(1 for c in seat["courses"] for p in c["pages"]
                           if p["body"]),
        "announcements": sum(len(c["announcements"]) for c in seat["courses"]),
        "assignments": sum(len(c["assignments"]) for c in seat["courses"]),
        "events": sum(len(c["events"]) for c in seat["courses"]),
        "api_calls": cv.calls,
        "errors": len(seat["errors"]),
    }
    seat["stats"] = stats
    path = os.path.join(out_dir, f"{code}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(seat, f, ensure_ascii=False, indent=1)
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roster", default="roster.json")
    ap.add_argument("--out", required=True,
                    help="output dir, e.g. private/shadow/sweeps/<date>")
    ap.add_argument("--seat", help="single seat code (default: all eligible)")
    args = ap.parse_args()

    base = os.environ.get("CANVAS_BASE_URL", "").strip()
    if not base:
        sys.exit("sweep_fetch: CANVAS_BASE_URL is not set")
    os.makedirs(args.out, exist_ok=True)

    roster = json.load(open(args.roster, encoding="utf-8"))
    manifest = {"date": iso(now_utc()), "seats": {}, "skipped": {}}
    attempted = failed = 0

    for s in roster.get("students", []):
        code = s.get("code")
        if args.seat and code != args.seat:
            continue
        if not s.get("active"):
            manifest["skipped"][code] = "inactive"
            continue
        if s.get("targets_alias"):
            manifest["skipped"][code] = f"aliases {s['targets_alias']}"
            continue
        token = os.environ.get(f"CANVAS_TOKEN_{code.upper()}", "").strip()
        if not token:
            manifest["skipped"][code] = "no CANVAS_TOKEN_* secret"
            print(f"{code}: SKIPPED — no token configured")
            continue
        attempted += 1
        try:
            st = sweep_seat(base, code, token, args.out)
            manifest["seats"][code] = st
            print(f"{code}: {st['courses']} courses · "
                  f"{st['page_bodies']} page bodies · "
                  f"{st['announcements']} announcements · "
                  f"{st['assignments']} assignments · "
                  f"{st['events']} events · {st['errors']} errors "
                  f"({st['api_calls']} API calls)")
        except PermissionError:
            failed += 1
            manifest["seats"][code] = {"failed": "token rejected (401)"}
            print(f"{code}: FAILED — token rejected (expired or revoked); "
                  f"re-mint and update CANVAS_TOKEN_{code.upper()}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            manifest["seats"][code] = {"failed": str(e)}
            print(f"{code}: FAILED — {e}")

    with open(os.path.join(args.out, "manifest.json"), "w",
              encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)

    if attempted and failed == attempted:
        sys.exit(2)  # every attempted seat failed -> the run itself failed


if __name__ == "__main__":
    main()
