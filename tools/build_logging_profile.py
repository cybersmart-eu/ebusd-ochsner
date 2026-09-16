#!/usr/bin/env python3
"""Build an opt-in, read-only diagnostic CSV from the original controller profile.

Output goes to stdout. Does not edit installed files or communicate with ebusd.
"""
import argparse
import csv
import sys
from pathlib import Path

FAST = {
    "heatpump.status.string", "hotwater.status.string", "heating.status.string",
    "heatmanager.status", "heatpump.cycles",
}
TEMPERATURES = {
    "hotwater.temp.buffer.tb", "hotwater.temp.buffer.tb.setpoint",
    "heatmanager.temp.buffer.tpo", "heatmanager.temp.buffer.tpm",
    "heatpump.temp.twv", "heatpump.temp.twr", "heatpump.flow",
}
SLOW = {
    "heating.temp.outside", "heating.temp.outside.average", "heating.temp.flow",
    "heating.temp.flow.setpoint", "heatpump.temp.tqe", "heatpump.temp.tqa",
    "auxheater.status.string", "heatpump.hours", "auxheater.cycles", "auxheater.hours",
    "heatpump.energy.mwh", "heatpump.energy.kwh", "heatpump.heating.mwh",
    "heatpump.heating.kwh", "heatpump.hotwater.mwh", "heatpump.hotwater.kwh",
    "heatpump.deicing.mwh", "heatpump.deicing.kwh",
}


def transform(rows):
    selected = FAST | TEMPERATURES | SLOW
    found = set()
    result = [["# Diagnostic profile: review docs/logging.md before use"],
              ["# Existing addresses and templates retained; no firmware mapping is inferred"]]
    defaults = 0
    for row in rows:
        if not row:
            continue
        if row[0] == "*r":
            result.append(row.copy())
            defaults += 1
            continue
        if not row[0].startswith("r") or len(row) < 8:
            continue
        name = row[2]
        # Exclude duplicate aliases, writes and relay-test definitions from this profile.
        if name not in selected and row[0] != "r":
            continue
        if "test.relay" in name or "relaytest" in name:
            continue
        if name in found:
            raise ValueError("duplicate message: " + name)
        found.add(name)
        row = row.copy()
        row[0] = "r1" if name in FAST else "r2" if name in TEMPERATURES else "r9" if name in SLOW else "r"
        result.append(row)
    if defaults != 1 or selected - found:
        raise ValueError(f"unexpected source profile; defaults={defaults}, missing={sorted(selected-found)}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1]
                        / "configuration/ochsner/15.24849.HW0102.SW0605.csv")
    args = parser.parse_args()
    with args.source.open(encoding="utf-8-sig", newline="") as f:
        rows = transform(list(csv.reader(f)))
    csv.writer(sys.stdout, lineterminator="\n").writerows(rows)


if __name__ == "__main__":
    main()
