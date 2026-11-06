#!/usr/bin/env python3

import os
import sys
import csv
import json
import math
import time
import ast
import re
import io
import html
import random
import hashlib
import heapq
import argparse
import tokenize
import sqlite3
import tempfile
import statistics

from collections import Counter
from datetime import datetime


VERSION = "6.1"
SAMPLE_SIZE = 10000
TOP_LIMIT = 20
FREQUENCY_LIMIT = 1000

MISSING = {
    "", "na", "n/a", "null", "none",
    "nan", "missing", "?"
}


def banner():
    print(r"""
     ██████╗ ██████╗ ██╗ ██████╗ ███╗   ██╗
    ██╔═══██╗██╔══██╗██║██╔═══██╗████╗  ██║
    ██║   ██║██████╔╝██║██║   ██║██╔██╗ ██║
    ██║   ██║██╔══██╗██║██║   ██║██║╚██╗██║
    ╚██████╔╝██║  ██║██║╚██████╔╝██║ ╚████║
     ╚═════╝ ╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝

       OPEN RESEARCH &
    INTELLIGENT OBSERVATION
           NETWORK

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━
          BY SKNADEEM
             FOUNDER
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)


def cell_text(value):
    if value is None:
        return ""

    if isinstance(value, (dict, list)):
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True
        )

    if isinstance(value, bool):
        return str(value)

    return str(value).strip()


def classify(value):
    value = cell_text(value)

    if value.lower() in MISSING:
        return "MISSING"

    if value.lower() in ("true", "false"):
        return "BOOLEAN"

    try:
        number = float(value)
        if math.isfinite(number):
            return "NUMERIC"
    except (ValueError, OverflowError):
        pass

    if re.fullmatch(
        r"[^@\s]+@[^@\s]+\.[^@\s]+", value
    ):
        return "EMAIL"

    if value.lower().startswith(("http://", "https://")):
        return "URL"

    return "TEXT"


def fingerprint(row):
    raw = json.dumps(
        row,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":")
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class TopValues:
    """Bounded-memory frequent-value tracker using a min-heap."""

    def __init__(self, limit=FREQUENCY_LIMIT):
        self.limit = limit
        self.counts = {}
        self.errors = {}
        self.heap = []
        self.versions = {}
        self.sequence = 0

    def compact(self):
        self.heap = []
        self.versions = {}

        for key, count in self.counts.items():
            self.sequence += 1
            self.versions[key] = self.sequence
            self.heap.append((count, self.sequence, key))

        heapq.heapify(self.heap)

    def add(self, value):
        if self.limit <= 0:
            return

        if value in self.counts:
            self.counts[value] += 1
        elif len(self.counts) < self.limit:
            self.counts[value] = 1
            self.errors[value] = 0
        else:
            while self.heap:
                count, version, old_value = heapq.heappop(self.heap)
                if self.versions.get(old_value) == version:
                    break
            else:
                self.compact()
                return self.add(value)

            del self.counts[old_value]
            del self.errors[old_value]
            del self.versions[old_value]

            self.counts[value] = count + 1
            self.errors[value] = count

        self.sequence += 1
        self.versions[value] = self.sequence

        heapq.heappush(
            self.heap,
            (self.counts[value], self.sequence, value)
        )

        if len(self.heap) > self.limit * 4:
            self.compact()

    def most_common(self, limit=TOP_LIMIT):
        return sorted(
            self.counts.items(),
            key=lambda item: item[1],
            reverse=True
        )[:limit]


def new_column():
    return {
        "count": 0,
        "missing": 0,
        "types": Counter(),
        "first_value": None,
        "constant": True,
        "numeric_count": 0,
        "mean": 0.0,
        "M2": 0.0,
        "minimum": float("inf"),
        "maximum": float("-inf"),
        "sample": [],
        "frequencies": TopValues(),
        "digest": hashlib.sha256()
    }


def update_column(col, value, rng):
    value = cell_text(value)
    col["count"] += 1

    kind = classify(value)
    col["types"][kind] += 1

    col["digest"].update(value.encode("utf-8") + b"\0")

    if kind == "MISSING":
        col["missing"] += 1
        return

    if col["first_value"] is None:
        col["first_value"] = value
    elif value != col["first_value"]:
        col["constant"] = False

    col["frequencies"].add(value)

    if kind != "NUMERIC":
        return

    x = float(value)

    col["numeric_count"] += 1
    n = col["numeric_count"]

    delta = x - col["mean"]
    col["mean"] += delta / n
    col["M2"] += delta * (x - col["mean"])

    col["minimum"] = min(col["minimum"], x)
    col["maximum"] = max(col["maximum"], x)

    sample = col["sample"]

    if len(sample) < SAMPLE_SIZE:
        sample.append(x)
    else:
        j = rng.randint(0, n - 1)
        if j < SAMPLE_SIZE:
            sample[j] = x


def analyze_outliers(col):
    data = sorted(col["sample"])
    n = len(data)

    if n < 4:
        return {
            "method": "IQR",
            "sample_size": n,
            "outliers_in_sample": None,
            "status": "INSUFFICIENT_DATA"
        }

    lower_half = data[:n // 2]
    upper_half = data[(n + 1) // 2:]

    q1 = statistics.median(lower_half)
    q3 = statistics.median(upper_half)

    iqr = q3 - q1
    low = q1 - 1.5 * iqr
    high = q3 + 1.5 * iqr

    outliers = [
        x for x in data if x < low or x > high
    ]

    return {
        "method": "IQR",
        "sample_size": n,
        "q1": q1,
        "q3": q3,
        "lower_bound": low,
        "upper_bound": high,
        "outliers_in_sample": len(outliers),
        "examples": outliers[:10],
        "status": "SAMPLE_BASED"
    }


def read_json_records(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        if isinstance(data.get("data"), list):
            records = data["data"]
        elif isinstance(data.get("records"), list):
            records = data["records"]
        else:
            records = [data]
    else:
        raise ValueError(
            "JSON must contain an object or array."
        )

    for record in records:
        yield record if isinstance(record, dict) else None


def read_jsonl_records(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            if not line.strip():
                continue

            try:
                record = json.loads(line)
                yield record if isinstance(record, dict) else None
            except (ValueError, TypeError):
                yield None


def build_action_guide(warnings, columns, malformed, duplicates):
    actions = []

    priority_map = {
        "Missing values": "HIGH",
        "Mixed data types": "HIGH",
        "Malformed records": "HIGH",
        "Duplicate rows": "MEDIUM",
        "Duplicate column": "MEDIUM",
        "Constant column": "LOW",
        "Zero variance": "LOW"
    }

    for warning in warnings:
        priority = "LOW"

        for key, level in priority_map.items():
            if warning.startswith(key):
                priority = level
                break

        if warning.startswith("Missing values:"):
            name = warning.split(":", 1)[1].strip()
            action = (
                f"Inspect missing entries in '{name}'. "
                "Decide whether to fill, retain or remove them."
            )

        elif warning.startswith("Mixed data types:"):
            name = warning.split(":", 1)[1].strip()
            action = (
                f"Review values in '{name}' and standardize "
                "their data types where appropriate."
            )

        elif warning.startswith("Constant column:"):
            name = warning.split(":", 1)[1].strip()
            action = (
                f"Check whether '{name}' provides useful "
                "information. It may be redundant."
            )

        elif warning.startswith("Zero variance:"):
            name = warning.split(":", 1)[1].strip()
            action = (
                f"All observed numeric values in '{name}' "
                "are identical. Check its usefulness."
            )

        elif warning.startswith("Duplicate column:"):
            action = (
                "Compare the matching columns. Confirm whether "
                "one is redundant before removing anything."
            )

        else:
            action = (
                "Inspect the affected records and verify "
                "whether the data is valid."
            )

        actions.append({
            "priority": priority,
            "issue": warning,
            "recommended_action": action
        })

    if duplicates:
        actions.append({
            "priority": "MEDIUM",
            "issue": f"Duplicate rows detected: {duplicates}",
            "recommended_action": (
                "Review duplicate records. Do not delete them "
                "unless they are genuinely redundant."
            )
        })

    if malformed:
        actions.append({
            "priority": "HIGH",
            "issue": f"Malformed records: {malformed}",
            "recommended_action": (
                "Inspect records excluded from the analysis "
                "and correct their structure."
            )
        })

    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    actions.sort(key=lambda item: order[item["priority"]])

    return actions


def atomic_json_write(path, data):
    temp_path = path + ".tmp"

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(
                data, f, indent=2, ensure_ascii=False,
                allow_nan=False
            )

        os.replace(temp_path, path)

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def create_html_report(report, path):
    rows = []

    for name, col in report["column_analysis"].items():
        numeric = col.get("numeric", {})

        rows.append(
            "<tr>"
            f"<td>{html.escape(name)}</td>"
            f"<td>{col['records']}</td>"
            f"<td>{col['missing']}</td>"
            f"<td>{html.escape(str(col['types']))}</td>"
            f"<td>{html.escape(str(numeric.get('mean', '—')))}</td>"
            f"<td>{html.escape(str(numeric.get('min', '—')))}</td>"
            f"<td>{html.escape(str(numeric.get('max', '—')))}</td>"
            "</tr>"
        )

    warning_items = "".join(
        f"<li>{html.escape(w)}</li>"
        for w in report["warnings"]
    )

    action_items = ""

    for action in report["smart_action_guide"]:
        action_items += (
            "<div class='action'>"
            f"<b>{html.escape(action['priority'])}</b>"
            f"<p>{html.escape(action['issue'])}</p>"
            f"<p>{html.escape(action['recommended_action'])}</p>"
            "</div>"
        )

    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ORION 6.1 Report</title>
<style>
body{{font-family:Arial,sans-serif;margin:20px;background:#f3f5f8;color:#202938}}
main{{max-width:1100px;margin:auto;background:white;padding:24px;border-radius:12px}}
h1{{margin-bottom:4px}}
.muted{{color:#687386}}
.cards{{display:flex;flex-wrap:wrap;gap:12px;margin:22px 0}}
.card{{background:#edf2f8;padding:14px;border-radius:8px;min-width:110px}}
table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}
th{{background:#edf2f8}}
li{{margin:8px 0}}
.action{{padding:12px;margin:10px 0;background:#edf2f8;border-radius:8px}}
</style>
</head>
<body>
<main>
<h1>ORION 6.1</h1>
<div class="muted">Open Research &amp; Intelligent Observation Network</div>
<p>Dataset: {html.escape(report['file'])}</p>
<div class="cards">
<div class="card">Rows<br><b>{report['rows']}</b></div>
<div class="card">Columns<br><b>{report['columns']}</b></div>
<div class="card">Duplicates<br><b>{report['duplicate_rows']}</b></div>
<div class="card">Missing<br><b>{report['missing_cells']}</b></div>
<div class="card">Malformed<br><b>{report['malformed_records']}</b></div>
</div>
<h2>Column analysis</h2>
<table>
<tr><th>Column</th><th>Records</th><th>Missing</th>
<th>Types</th><th>Mean</th><th>Min</th><th>Max</th></tr>
{''.join(rows)}
</table>
<h2>Warnings</h2>
<ul>{warning_items or '<li>No configured warnings.</li>'}</ul>
<h2>Smart Action Guide</h2>
{action_items or '<p>No configured issues detected.</p>'}
<p class="muted">Generated by ORION 6.1 | Offline analysis</p>
</main>
</body>
</html>"""

    temp_path = path + ".tmp"

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(document)

        os.replace(temp_path, path)

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def analyze_dataset(path):
    if not os.path.isfile(path):
        print("[ERROR] File not found:", path)
        return

    extension = os.path.splitext(path)[1].lower()

    supported = {
        ".csv", ".tsv", ".json", ".jsonl", ".ndjson"
    }

    if extension not in supported:
        print("[ERROR] Supported: CSV, TSV, JSON, JSONL, NDJSON")
        return

    start = time.perf_counter()
    size = os.path.getsize(path)
    rng = random.Random(42)

    columns = {}
    total_rows = 0
    duplicates = 0
    malformed = 0
    empty_rows = 0

    temp_db = None
    db = None

    try:
        fd, temp_db = tempfile.mkstemp(
            prefix="orion_", suffix=".sqlite3"
        )
        os.close(fd)

        db = sqlite3.connect(temp_db)
        db.execute("PRAGMA journal_mode=OFF")
        db.execute("PRAGMA synchronous=OFF")
        db.execute("PRAGMA temp_store=MEMORY")
        db.execute("PRAGMA cache_size=-32768")
        db.execute("PRAGMA locking_mode=EXCLUSIVE")
        db.execute(
            "CREATE TABLE seen_rows (fingerprint TEXT PRIMARY KEY)"
        )

        def process_record(record):
            nonlocal total_rows, duplicates, malformed, empty_rows

            if not isinstance(record, dict):
                malformed += 1
                return

            if not record:
                empty_rows += 1
                return

            normalized = {}

            for key, value in record.items():
                name = str(key).strip()

                if not name or name in normalized:
                    malformed += 1
                    return

                normalized[name] = cell_text(value)

            if not any(
                classify(value) != "MISSING"
                for value in normalized.values()
            ):
                empty_rows += 1
                return

            previous_rows = total_rows

            # Support JSON records with changing field sets.
            for name in normalized:
                if name not in columns:
                    col = new_column()
                    col["count"] = previous_rows
                    col["missing"] = previous_rows
                    col["types"]["MISSING"] = previous_rows
                    if previous_rows:
                        col["digest"].update(b"\0" * previous_rows)
                    columns[name] = col

            # Missing fields are treated as missing values.
            complete_record = {
                name: normalized.get(name, "")
                for name in columns
            }

            total_rows += 1

            fp = fingerprint(complete_record)

            cursor = db.execute(
                "INSERT OR IGNORE INTO seen_rows VALUES (?)",
                (fp,)
            )

            if cursor.rowcount == 0:
                duplicates += 1

            for name, value in complete_record.items():
                update_column(columns[name], value, rng)

        if extension == ".json":
            for record in read_json_records(path):
                process_record(record)

        elif extension in (".jsonl", ".ndjson"):
            for record in read_jsonl_records(path):
                process_record(record)

        else:
            with open(
                path, "r", encoding="utf-8-sig", newline=""
            ) as f:

                sample = f.read(8192)
                f.seek(0)

                if extension == ".tsv":
                    delimiter = "\t"
                else:
                    try:
                        delimiter = csv.Sniffer().sniff(
                            sample, delimiters=",;\t|"
                        ).delimiter
                    except csv.Error:
                        delimiter = ","

                reader = csv.reader(f, delimiter=delimiter)
                headers = next(reader, None)

                if not headers:
                    print("[ERROR] Empty file or missing header.")
                    return

                headers = [h.strip() for h in headers]

                if any(not h for h in headers):
                    print("[ERROR] Empty column name in header.")
                    return

                if len(set(headers)) != len(headers):
                    print("[ERROR] Duplicate column names.")
                    return

                columns = {
                    name: new_column() for name in headers
                }

                for row in reader:
                    if not row or all(not cell.strip() for cell in row):
                        empty_rows += 1
                        continue

                    if len(row) != len(headers):
                        malformed += 1
                        continue

                    process_record(dict(zip(headers, row)))

        db.commit()

    except (
        OSError, UnicodeError, csv.Error,
        ValueError, sqlite3.Error, json.JSONDecodeError
    ) as e:
        print("[ERROR]", e)
        return

    finally:
        if db is not None:
            db.close()

        if temp_db and os.path.exists(temp_db):
            os.remove(temp_db)

    warnings = []
    column_reports = {}
    hashes = {}

    for name, col in columns.items():
        report = {
            "records": col["count"],
            "missing": col["missing"],
            "types": dict(col["types"]),
            "constant_column": (
                col["constant"]
                and (col["count"] - col["missing"]) >= 2
            ),
            "top_values": col["frequencies"].most_common(),
            "top_values_note": (
                "Approximate frequent-value tracking; "
                "not guaranteed exact."
            )
        }

        if col["missing"]:
            warnings.append(f"Missing values: {name}")

        if (
            col["constant"]
            and (col["count"] - col["missing"]) >= 2
        ):
            warnings.append(f"Constant column: {name}")

        nonmissing = {
            key: value for key, value in col["types"].items()
            if key != "MISSING"
        }

        if len(nonmissing) > 1:
            warnings.append(f"Mixed data types: {name}")

        if col["numeric_count"]:
            n = col["numeric_count"]
            variance = max(col["M2"] / n, 0.0)

            report["numeric"] = {
                "count": n,
                "mean": col["mean"],
                "min": col["minimum"],
                "max": col["maximum"],
                "variance": variance,
                "standard_deviation": math.sqrt(variance),
                "variance_type": "POPULATION"
            }

            report["outliers"] = analyze_outliers(col)

            if (
                variance == 0
                and col["numeric_count"] >= 2
                and set(nonmissing) == {"NUMERIC"}
            ):
                warnings.append(f"Zero variance: {name}")

        digest = col["digest"].hexdigest()

        if digest in hashes:
            warnings.append(
                f"Duplicate column: {name} matches {hashes[digest]}"
            )
        else:
            hashes[digest] = name

        column_reports[name] = report

    if duplicates:
        warnings.append(f"Duplicate rows: {duplicates}")

    if malformed:
        warnings.append(f"Malformed records: {malformed}")

    actions = build_action_guide(
        warnings, column_reports, malformed, duplicates
    )

    elapsed = time.perf_counter() - start

    report = {
        "engine": "ORION",
        "version": VERSION,
        "file": os.path.basename(path),
        "file_size_bytes": size,
        "rows": total_rows,
        "columns": len(columns),
        "duplicate_rows": duplicates,
        "missing_cells": sum(
            col["missing"] for col in columns.values()
        ),
        "malformed_records": malformed,
        "empty_rows": empty_rows,
        "processing_seconds": round(elapsed, 4),
        "rows_per_second": (
            round(total_rows / elapsed, 2) if elapsed else None
        ),
        "column_analysis": column_reports,
        "warnings": warnings,
        "smart_action_guide": actions,
        "notes": [
            "Outlier counts are based on a reservoir sample.",
            "Statistical outliers are not automatically errors.",
            "Malformed records are excluded from analysis.",
            "Duplicate rows are not automatically invalid.",
            "Numeric variance is population variance.",
            "Top values use bounded approximate tracking.",
            "JSON input is loaded into memory before analysis."
        ],
        "timestamp": datetime.now().isoformat()
    }

    base = os.path.splitext(os.path.basename(path))[0]
    json_path = f"orion_{base}_report.json"
    html_path = f"orion_{base}_report.html"

    try:
        atomic_json_write(json_path, report)
        create_html_report(report, html_path)

    except (OSError, ValueError) as e:
        print("[ERROR] Could not create reports:", e)
        return

    print("\n" + "=" * 48)
    print("             ORION 6.1 REPORT")
    print("=" * 48)
    print("File:", path)
    print("Rows:", total_rows)
    print("Columns:", len(columns))
    print("Duplicates:", duplicates)
    print("Missing cells:", report["missing_cells"])
    print("Malformed records:", malformed)
    print("Empty rows:", empty_rows)

    print("\n[PERFORMANCE]")
    print("Time:", report["processing_seconds"], "seconds")
    print("Rows/sec:", report["rows_per_second"])

    print("\n[DATA QUALITY]")
    if warnings:
        for item in warnings:
            print("[WARNING]", item)
    else:
        print("[+] No configured warnings found.")

    print("\n[ORION SMART ACTION GUIDE]")

    if actions:
        for action in actions:
            print(
                f"[{action['priority']}] {action['issue']}"
            )
            print("  ->", action["recommended_action"])
    else:
        print("[+] No configured issues detected.")

    print("\n[+] JSON report:", json_path)
    print("[+] HTML report:", html_path)
    print("[+] Analysis completed.")


def analyze_python(path):
    print("\n[ORION 6.1 CODESCAN]")
    print("File:", path)

    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            source = f.read()

        tree = ast.parse(source, filename=path)

    except SyntaxError as e:
        print("[ERROR] Syntax error at line:", e.lineno)
        print(e.msg)
        return

    except (OSError, UnicodeError) as e:
        print("[ERROR]", e)
        return

    findings = set()
    pickle_modules = set()
    pickle_functions = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pickle":
                    pickle_modules.add(
                        alias.asname or "pickle"
                    )

        elif (
            isinstance(node, ast.ImportFrom)
            and node.module == "pickle"
        ):
            for alias in node.names:
                if alias.name in ("load", "loads"):
                    pickle_functions.add(
                        alias.asname or alias.name
                    )

    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                findings.add(
                    (node.lineno, "Bare except clause")
                )

        if isinstance(node, ast.Call):
            name = ""

            if isinstance(node.func, ast.Name):
                name = node.func.id

            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr

            if name in ("eval", "exec"):
                findings.add(
                    (node.lineno, f"Review {name}() usage")
                )

            if name == "system":
                findings.add(
                    (node.lineno, "Review OS command execution")
                )

            if name in ("Popen", "run", "call", "check_output"):
                findings.add(
                    (node.lineno, "Review subprocess execution")
                )

            if (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in pickle_modules
                and node.func.attr in ("load", "loads")
            ):
                findings.add(
                    (node.lineno, "Review pickle deserialization")
                )

            if (
                isinstance(node.func, ast.Name)
                and node.func.id in pickle_functions
            ):
                findings.add(
                    (node.lineno, "Review pickle deserialization")
                )

    try:
        tokens = tokenize.generate_tokens(
            io.StringIO(source).readline
        )

        for token in tokens:
            if token.type == tokenize.COMMENT:
                if "TODO" in token.string or "FIXME" in token.string:
                    findings.add(
                        (token.start[0], "TODO/FIXME comment")
                    )

    except (tokenize.TokenError, IndentationError):
        pass

    findings = sorted(findings)

    print("Syntax: VALID")
    print("Lines:", len(source.splitlines()))
    print("Findings:", len(findings))

    for line, message in findings:
        print(f"[REVIEW] Line {line}: {message}")

    if not findings:
        print("[+] No configured checks triggered.")

    print(
        "\nNote: CodeScan is basic static analysis, "
        "not a complete security audit."
    )


def menu():
    while True:
        print("""
╔══════════════════════════════════╗
║          ORION 6.1 MENU          ║
╠══════════════════════════════════╣
║  1. Analyse a dataset            ║
║  2. Scan Python code             ║
║  3. Exit                         ║
╚══════════════════════════════════╝
""")

        try:
            choice = input("Select option: ").strip()

            if choice == "1":
                path = input("Dataset file path: ").strip()
                analyze_dataset(path)

            elif choice == "2":
                path = input("Python file path: ").strip()
                analyze_python(path)

            elif choice == "3":
                print("ORION closed.")
                break

            else:
                print("[ERROR] Choose 1, 2 or 3.")

        except (KeyboardInterrupt, EOFError):
            print("\nORION closed.")
            break


def main():
    parser = argparse.ArgumentParser(
        description=(
            "ORION 6.1 - Open Research & "
            "Intelligent Observation Network"
        )
    )

    parser.add_argument(
        "file",
        nargs="?",
        help="Dataset or Python file"
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"ORION {VERSION}"
    )

    args = parser.parse_args()
    banner()

    if not args.file:
        menu()
        return

    extension = os.path.splitext(args.file)[1].lower()

    if extension == ".py":
        analyze_python(args.file)
    else:
        analyze_dataset(args.file)


if __name__ == "__main__":
    main()
