#!/usr/bin/env python3
"""Archive the ebusd HTTP cache without issuing eBUS reads or writes.

Python 3.10+, standard library only. See docs/logging.md for scope and limits.
"""
import argparse
import csv
import hashlib
import json
import math
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit
from urllib.request import urlopen

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY, started_utc TEXT NOT NULL, metadata_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots (
  id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, received_utc TEXT NOT NULL,
  received_epoch REAL NOT NULL, monotonic_s REAL NOT NULL,
  global_json TEXT, error TEXT
);
CREATE TABLE IF NOT EXISTS samples (
  id INTEGER PRIMARY KEY, snapshot_id INTEGER NOT NULL, circuit TEXT NOT NULL,
  message TEXT NOT NULL, source_epoch REAL, age_s REAL,
  quality TEXT NOT NULL, payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS samples_message ON samples(circuit, message, source_epoch);
"""


def utc(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat()


def cache_url(base, circuit):
    parsed = urlsplit(base)
    if (parsed.scheme not in {"http", "https"} or not parsed.netloc
            or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
            or parsed.username is not None or parsed.password is not None):
        raise ValueError("--url must be an HTTP(S) origin, e.g. http://localhost:8080")
    if not circuit or any(c in circuit for c in "/?#"):
        raise ValueError("invalid circuit")
    # No required, maxage, poll, define or write: this only reads existing cache.
    return (base.rstrip("/") + "/data/" + quote(circuit, safe="")
            + "?exact=true&full=true&raw=true&numeric=true&verbose=true")


def timestamp_quality(lastup, now, stale_after):
    if lastup is None or lastup == 0:
        return None, None, "never_received"
    if isinstance(lastup, bool) or not isinstance(lastup, (int, float)):
        return None, None, "invalid_timestamp"
    if not math.isfinite(lastup) or lastup < 0:
        return None, None, "invalid_timestamp"
    age = now - lastup
    if age < -2:
        return lastup, age, "clock_skew"
    return lastup, age, "stale" if age > stale_after else "fresh"


def store_snapshot(db, run_id, payload, circuit, now, mono, stale_after, error=None):
    """Store the complete message objects; missing fields never become zero."""
    global_state = payload.get("global", {}) if isinstance(payload, dict) else {}
    section = payload.get(circuit, {}) if isinstance(payload, dict) else {}
    if not isinstance(section, dict):
        raise ValueError("invalid circuit object")
    messages = section.get("messages", {})
    if not isinstance(global_state, dict) or not isinstance(messages, dict):
        raise ValueError("invalid ebusd response structure")
    if not messages and error is None:
        error = "circuit_missing_or_empty"
    with db:
        snapshot_id = db.execute(
            "INSERT INTO snapshots(run_id,received_utc,received_epoch,monotonic_s,global_json,error) "
            "VALUES(?,?,?,?,?,?)",
            (run_id, utc(now), now, mono, json.dumps(global_state), error),
        ).lastrowid
        for name, message in messages.items():
            if not isinstance(message, dict):
                raise ValueError("invalid message object")
            if message.get("write") is True:
                continue
            source, age, quality = timestamp_quality(message.get("lastup"), now, stale_after)
            if global_state.get("signal") is False:
                quality = "no_bus_signal"
            db.execute(
                "INSERT INTO samples(snapshot_id,circuit,message,source_epoch,age_s,quality,payload_json) "
                "VALUES(?,?,?,?,?,?,?)",
                (snapshot_id, circuit, name, source, age, quality,
                 json.dumps(message, ensure_ascii=False, sort_keys=True)),
            )


def collect(args):
    if any(not math.isfinite(v) or v <= 0 for v in (args.interval, args.timeout, args.stale_after)):
        raise ValueError("interval, timeout and stale-after must be positive")
    url = cache_url(args.url, args.circuit)
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(db_path)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.executescript(SCHEMA)
    run_id = str(uuid.uuid4())
    meta = {
        "schema_version": 1, "circuit": args.circuit,
        "controller_identity": args.controller, "config_revision": args.config_revision,
        "interval_s": args.interval, "stale_after_s": args.stale_after,
        "config_sha256": {
            str(Path(f).name): hashlib.sha256(Path(f).read_bytes()).hexdigest()
            for f in args.config_file
        },
        "collector": "HTTP cache only; no live validation implied",
    }
    with db:
        db.execute("INSERT INTO runs VALUES(?,?,?)", (run_id, utc(time.time()), json.dumps(meta)))
    try:
        while True:
            started = time.monotonic()
            try:
                with urlopen(url, timeout=args.timeout) as response:
                    # Fail visibly on unbounded or malformed responses.
                    raw = response.read(8 * 1024 * 1024 + 1)
                if len(raw) > 8 * 1024 * 1024:
                    raise ValueError("HTTP response exceeds 8 MiB")
                payload = json.loads(raw)
                if not isinstance(payload, dict):
                    raise ValueError("expected ebusd JSON object")
                store_snapshot(db, run_id, payload, args.circuit, time.time(),
                               time.monotonic(), args.stale_after)
            except (OSError, ValueError) as exc:
                store_snapshot(db, run_id, {}, args.circuit, time.time(),
                               time.monotonic(), args.stale_after, type(exc).__name__ + ": " + str(exc))
                print("capture error:", exc, file=sys.stderr)
            if args.once:
                break
            time.sleep(max(0, args.interval - (time.monotonic() - started)))
    except KeyboardInterrupt:
        pass
    finally:
        db.close()


def report(args):
    # Read-only open: a typo must not silently create an empty database.
    db = sqlite3.connect(Path(args.db).resolve().as_uri() + "?mode=ro", uri=True)
    writer = csv.writer(sys.stdout)
    writer.writerow(["circuit", "message", "cached_observations", "distinct_source_timestamps",
                     "fresh", "stale", "other_quality", "max_observed_age_s"])
    for row in db.execute("""
      SELECT circuit, message, COUNT(*), COUNT(DISTINCT source_epoch),
      SUM(quality='fresh'), SUM(quality='stale'), SUM(quality NOT IN ('fresh','stale')),
      ROUND(MAX(age_s),1) FROM samples GROUP BY circuit,message ORDER BY circuit,message
    """):
        writer.writerow(row)
    errors = db.execute("SELECT COUNT(*) FROM snapshots WHERE error IS NOT NULL").fetchone()[0]
    print(f"Snapshots with errors: {errors}. Cached observations are NOT new bus samples.", file=sys.stderr)
    db.close()


def export(args):
    db = sqlite3.connect(Path(args.db).resolve().as_uri() + "?mode=ro", uri=True)
    writer = csv.writer(sys.stdout)
    writer.writerow(["run_id", "received_utc", "circuit", "message", "source_epoch",
                     "age_s", "quality", "payload_json"])
    writer.writerows(db.execute("""
      SELECT n.run_id,n.received_utc,s.circuit,s.message,s.source_epoch,s.age_s,s.quality,s.payload_json
      FROM samples s JOIN snapshots n ON n.id=s.snapshot_id ORDER BY n.id,s.id
    """))
    db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    capture = sub.add_parser("collect")
    capture.add_argument("--url", default="http://localhost:8080")
    capture.add_argument("--circuit", default="24849")
    capture.add_argument("--db", required=True)
    capture.add_argument("--interval", type=float, default=5)
    capture.add_argument("--timeout", type=float, default=5)
    capture.add_argument("--stale-after", type=float, default=90)
    capture.add_argument("--controller", default="unverified")
    capture.add_argument("--config-revision", default="unknown")
    capture.add_argument("--config-file", action="append", default=[])
    capture.add_argument("--once", action="store_true")
    capture.set_defaults(func=collect)
    for command, function in [("report", report), ("export", export)]:
        cmd = sub.add_parser(command)
        cmd.add_argument("--db", required=True)
        cmd.set_defaults(func=function)
    args = parser.parse_args()
    try:
        args.func(args)
    except (ValueError, OSError, sqlite3.Error) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
