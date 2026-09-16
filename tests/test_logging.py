import csv
import importlib.util
import json
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / (name + ".py"))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


capture = module("ebus_capture")
profile = module("build_logging_profile")


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.executescript(capture.SCHEMA)
        self.payload = {"global": {"signal": True}, "24849": {"messages": {
            "heatpump.status.string": {"lastup": 100, "write": False,
                "fields": {"status": {"value": 28}}, "slave": [10, 53, 129, 0, 0, 255, 0, 0, 0, 28, 0]}
        }}}

    def tearDown(self):
        self.db.close()

    def save(self, now, payload=None):
        capture.store_snapshot(self.db, "test", payload if payload is not None else self.payload,
                               "24849", now, now, 90)

    def test_cache_reread_is_not_new_source_measurement(self):
        self.save(101)
        self.save(220)
        self.assertEqual(self.db.execute("SELECT COUNT(DISTINCT source_epoch) FROM samples").fetchone()[0], 1)
        self.assertEqual(self.db.execute("SELECT quality FROM samples ORDER BY id").fetchall(),
                         [("fresh",), ("stale",)])

    def test_raw_and_numeric_code_survive(self):
        self.save(101)
        stored = json.loads(self.db.execute("SELECT payload_json FROM samples").fetchone()[0])
        self.assertEqual(stored, self.payload["24849"]["messages"]["heatpump.status.string"])

    def test_offline_is_not_zero(self):
        self.payload["global"]["signal"] = False
        self.save(101)
        self.assertEqual(self.db.execute("SELECT quality FROM samples").fetchone()[0], "no_bus_signal")
        self.assertEqual(json.loads(self.db.execute("SELECT payload_json FROM samples").fetchone()[0])
                         ["fields"]["status"]["value"], 28)

    def test_never_received_future_and_invalid_timestamps(self):
        for lastup, expected in [(0,"never_received"), (None,"never_received"),
                                 (200,"clock_skew"), ("100","invalid_timestamp"),
                                 (float("nan"),"invalid_timestamp"), (-1,"invalid_timestamp")]:
            with self.subTest(lastup=lastup):
                self.assertEqual(capture.timestamp_quality(lastup, 100, 90)[2], expected)

    def test_missing_circuit_is_explicit_error(self):
        self.save(100, {"global": {"signal": True}})
        self.assertEqual(self.db.execute("SELECT error FROM snapshots").fetchone()[0], "circuit_missing_or_empty")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM samples").fetchone()[0], 0)

    def test_malformed_frame_rolls_back_snapshot(self):
        self.payload["24849"]["messages"]["broken"] = None
        with self.assertRaises(ValueError):
            self.save(100)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0], 0)

    def test_counter_drop_is_preserved_not_corrected(self):
        msg = self.payload["24849"]["messages"]["heatpump.status.string"]
        msg["fields"] = {"cycles": {"value": 18000}}
        self.save(101)
        msg["lastup"] = 105
        msg["fields"]["cycles"]["value"] = 0
        self.save(106)
        values = [json.loads(r[0])["fields"]["cycles"]["value"]
                  for r in self.db.execute("SELECT payload_json FROM samples ORDER BY id")]
        self.assertEqual(values, [18000, 0])

    def test_read_only_http_query(self):
        query = parse_qs(urlsplit(capture.cache_url("http://localhost:8080", "24849")).query)
        self.assertFalse(set(query) & {"poll", "required", "maxage", "define", "write"})
        self.assertEqual(query["numeric"], ["true"])
        for url in ["file:///tmp/x", "http://localhost/data?poll=1", "http://user:pass@localhost"]:
            with self.assertRaises(ValueError):
                capture.cache_url(url, "24849")

    def test_http_to_database_and_csv_export(self):
        payload = self.payload
        payload["24849"]["messages"]["heatpump.status.string"]["lastup"] = int(time.time())
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode())

            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                db = str(Path(directory) / "capture.sqlite")
                tool = str(ROOT / "tools/ebus_capture.py")
                subprocess.run([sys.executable, tool, "collect", "--once", "--db", db,
                                "--url", f"http://127.0.0.1:{server.server_port}"],
                               check=True, capture_output=True, timeout=10)
                result = subprocess.run([sys.executable, tool, "export", "--db", db],
                                        check=True, capture_output=True, text=True, timeout=10)
                rows = list(csv.DictReader(result.stdout.splitlines()))
                self.assertEqual(rows[0]["quality"], "fresh")
                self.assertEqual(json.loads(rows[0]["payload_json"])["fields"]["status"]["value"], 28)
                result = subprocess.run([sys.executable, tool, "report", "--db", db],
                                        check=True, capture_output=True, text=True, timeout=10)
                self.assertIn("Snapshots with errors: 0", result.stderr)
                self.assertEqual(len(requests), 1)
                self.assertNotIn("maxage", requests[0])
                self.assertNotIn("required", requests[0])
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()


class ProfileTests(unittest.TestCase):
    def setUp(self):
        with (ROOT / "configuration/ochsner/15.24849.HW0102.SW0605.csv").open() as f:
            self.source = list(csv.reader(f))
        self.result = profile.transform(self.source)

    def test_diagnostic_profile_has_no_writes_or_relay_tests(self):
        self.assertFalse(any(r[0].startswith(("w", "*w")) for r in self.result))
        self.assertFalse(any("relay" in r[2] for r in self.result if len(r) > 2))

    def test_existing_registers_and_datatypes_are_unchanged(self):
        original = {r[2]:r for r in self.source if r and r[0].startswith("r")}
        for row in self.result:
            if row[0].startswith("r"):
                self.assertEqual(row[1:], original[row[2]][1:])

    def test_every_priority_point_is_present(self):
        priorities = {r[2]:r[0] for r in self.result if len(r) > 2 and r[0].startswith("r")}
        for names, expected in [(profile.FAST,"r1"), (profile.TEMPERATURES,"r2"), (profile.SLOW,"r9")]:
            for name in names:
                self.assertEqual(priorities[name], expected)


if __name__ == "__main__":
    unittest.main()
