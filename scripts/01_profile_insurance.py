#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Phase 1 - read-only profiling cua data/insurance_complain.xlsx.

Khong ghi, khong mo, khong dong nguon. Chi doc bang openpyxl read_only.
Khong ghi ten ca nhan / ngay sinh / raw row sample: chi tong hop va metadata.
Ket qua DQ la ket qua hop le; script chi exit != 0 khi assertion noi bo that bai.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from collections import Counter, defaultdict
from datetime import date, datetime

import openpyxl

PII_SAMPLE_BLOCK = {"FirstName", "LastName", "BirthDate", "BrokerFullName"}
MAX_DISTINCT_TRACK = 20000
MAX_SAMPLES = 20
MAX_ID_SAMPLES = 10

FACT_COMPLAINTS = "Complains Data"
FACT_HISTORY = "Status History Data"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_blank(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def new_col(header):
    return {
        "header": header,
        "header_is_blank": header is None or header.strip() == "",
        "non_null": 0,
        "null": 0,
        "types": Counter(),
        "_distinct": set(),
        "distinct_truncated": False,
        "_samples": [],
        "num_min": None,
        "num_max": None,
        "num_sum": 0.0,
        "num_count": 0,
        "negative": 0,
        "zero": 0,
        "date_min": None,
        "date_max": None,
        "blank_string": 0,
        "literal_null": 0,
    }


def touch(col, v):
    if is_blank(v):
        col["null"] += 1
        if isinstance(v, str):
            col["blank_string"] += 1
        return
    col["non_null"] += 1
    col["types"][type(v).__name__] += 1
    if isinstance(v, str) and v.strip().upper() == "NULL":
        col["literal_null"] += 1
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        fv = float(v)
        col["num_count"] += 1
        col["num_sum"] += fv
        col["num_min"] = fv if col["num_min"] is None else min(col["num_min"], fv)
        col["num_max"] = fv if col["num_max"] is None else max(col["num_max"], fv)
        if fv < 0:
            col["negative"] += 1
        if fv == 0:
            col["zero"] += 1
    elif isinstance(v, (datetime, date)):
        col["date_min"] = v if col["date_min"] is None else min(col["date_min"], v)
        col["date_max"] = v if col["date_max"] is None else max(col["date_max"], v)
    if len(col["_distinct"]) < MAX_DISTINCT_TRACK:
        key = v if not isinstance(v, (datetime, date)) else v.isoformat()
        col["_distinct"].add(key)
        name = col["header"]
        if name not in PII_SAMPLE_BLOCK and len(col["_samples"]) < MAX_SAMPLES:
            col["_samples"].append(str(key)[:60])
    elif len(col["_distinct"]) >= MAX_DISTINCT_TRACK:
        col["distinct_truncated"] = True


def finalize(col):
    out = {
        "header": col["header"],
        "header_is_blank": col["header_is_blank"],
        "non_null": col["non_null"],
        "null": col["null"],
        "blank_string": col["blank_string"],
        "literal_null": col["literal_null"],
        "distinct": len(col["_distinct"]),
        "distinct_truncated": col["distinct_truncated"],
        "types": dict(col["types"]),
    }
    name = col["header"]
    if name not in PII_SAMPLE_BLOCK:
        out["samples"] = col["_samples"]
    else:
        out["samples"] = "withheld_pii"
    if col["num_count"]:
        out["numeric"] = {
            "min": col["num_min"],
            "max": col["num_max"],
            "mean": round(col["num_sum"] / col["num_count"], 6),
            "negative": col["negative"],
            "zero": col["zero"],
        }
    if col["date_min"] is not None:
        out["date"] = {"min": col["date_min"].isoformat(), "max": col["date_max"].isoformat()}
    return out


def profile_sheet(ws):
    it = ws.iter_rows(values_only=True)
    header_row = next(it, None)
    header = [(None if h is None else str(h).strip()) for h in (header_row or [])]
    cols = [new_col(h) for h in header]
    data_rows = 0
    fully_empty_rows = 0
    trailing_blank_rows = 0
    width_max = 0
    extra_cells_beyond_header = 0
    widths = Counter()
    for row in it:
        data_rows += 1
        width = 0
        for i, v in enumerate(row):
            if not is_blank(v):
                width = i + 1
        if width == 0:
            fully_empty_rows += 1
            continue
        widths[width] += 1
        if width > len(cols):
            for _ in range(width - len(cols)):
                cols.append(new_col(None))
                header.append(None)
            extra_cells_beyond_header += width - (len(header) - (width - len(cols)))
        for i in range(min(width, len(cols))):
            touch(cols[i], row[i])
    width_max = len(cols)
    n_records = data_rows - fully_empty_rows
    for i, col in enumerate(cols):
        col["null"] += sum(cnt for w, cnt in widths.items() if w <= i)
    trailing_blank_rows = sum(cnt for w, cnt in widths.items() if w < width_max)
    empty_columns = [i for i, c in enumerate(cols) if c["non_null"] == 0]
    return {
        "sheet": ws.title,
        "max_row_attr": ws.max_row,
        "max_col_attr": ws.max_column,
        "header_columns_detected": width_max,
        "header_blank_count": sum(1 for h in header if h is None),
        "data_rows_iterated": data_rows,
        "records_non_empty": data_rows - fully_empty_rows,
        "fully_empty_rows": fully_empty_rows,
        "rows_shorter_than_width": trailing_blank_rows,
        "columns": [finalize(c) for c in cols],
        "empty_column_indexes": empty_columns,
    }


def read_rows(ws):
    it = ws.iter_rows(values_only=True)
    header = [(None if h is None else str(h).strip()) for h in (next(it, None) or [])]
    idx = {h: i for i, h in enumerate(header) if h}
    return header, idx, it


def key_profile(header, idx, it, key_cols):
    """Dem ban ghi theo khoa, orphan FK va null, khong ghi raw row."""
    pos = [idx[c] for c in key_cols if c in idx]
    seen = Counter()
    null_key = 0
    for row in it:
        if all(is_blank(v) for v in row):
            continue
        if any(pos_i >= len(row) or is_blank(row[pos_i]) for pos_i in pos):
            null_key += 1
            continue
        vals = tuple(row[i] for i in pos)
        seen[vals] += 1
    dups = {str(k): c for k, c in seen.items() if c > 1}
    return {
        "key_columns": key_cols,
        "distinct_keys": len(seen),
        "rows_with_null_key": null_key,
        "duplicate_key_groups": len(dups),
        "duplicate_extra_rows": sum(c - 1 for c in dups.values()),
        "duplicate_key_samples": list(dups.keys())[:MAX_ID_SAMPLES],
    }


def col_values(ws, name):
    header, idx, it = read_rows(ws)
    i = idx[name]
    return [row[i] for row in it if not all(is_blank(v) for v in row)]


def build_key_set(ws, key_col):
    header, idx, it = read_rows(ws)
    if key_col not in idx:
        return None
    i = idx[key_col]
    s, nulls = set(), 0
    for row in it:
        if all(is_blank(v) for v in row):
            continue
        v = row[i]
        if is_blank(v):
            nulls += 1
        else:
            s.add(v)
    return {"set": s, "nulls": nulls, "key": key_col, "sheet": ws.title}


def pct(sorted_vals, q):
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return round(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo), 6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--baseline-xlsx-sha256", default=None)
    ap.add_argument("--timeout-note", default="")
    args = ap.parse_args()

    started = datetime.now()
    report = {
        "phase": "Phase 1 - Data Understanding (profiling)",
        "startedLocal": started.isoformat(timespec="seconds"),
        "environment": {
            "python": sys.version.split()[0],
            "openpyxl": openpyxl.__version__,
            "platform": platform.platform(),
        },
        "source": {
            "path": os.path.relpath(args.xlsx).replace("\\", "/"),
            "bytes": os.path.getsize(args.xlsx),
            "sha256_before": sha256_file(args.xlsx),
            "read_mode": "openpyxl load_workbook(read_only=True, data_only=True)",
        },
        "assertions": [],
    }
    if args.baseline_xlsx_sha256:
        report["source"]["baseline_sha256"] = args.baseline_xlsx_sha256
        report["source"]["matches_baseline"] = (
            report["source"]["sha256_before"].lower() == args.baseline_xlsx_sha256.lower()
        )

    def check(name, ok, detail=""):
        report["assertions"].append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})
        return ok

    wb = openpyxl.load_workbook(args.xlsx, read_only=True, data_only=True)
    report["sheet_names"] = list(wb.sheetnames)

    # --- 1. Profile tung sheet -------------------------------------------------
    profiles = {}
    for ws in wb.worksheets:
        profiles[ws.title] = profile_sheet(ws)
    report["sheet_profiles"] = profiles
    check("sheet_count_12", len(wb.sheetnames) == 12, f"{len(wb.sheetnames)} sheets")
    check("all_sheets_profiled", all(p["data_rows_iterated"] > 0 for p in profiles.values()),
          ", ".join(f"{k}:{v['data_rows_iterated']}" for k, v in profiles.items()))
    # khong duoc dua vao worksheet dimensions
    check("max_row_attr_none_as_documented",
          all(p["max_row_attr"] is None for p in profiles.values()),
          "worksheet dimensions None; counts tuyet duyet dong du lieu")
    for sheet, p in profiles.items():
        bad = [c["header"] for c in p["columns"] if c["non_null"] + c["null"] != p["records_non_empty"]]
        check("columns_reconcile_" + sheet, not bad,
              f"mismatch cols={bad[:5]}" if bad else f"{len(p['columns'])} cols -> {p['records_non_empty']} records")

    # --- 2. Khoa / trung lap cac sheet ---------------------------------------
    key_specs = {
        "Brokers": ["BrokerID"],
        "Products": ["ProductID"],
        "Regions": ["id"],
        "Customers": ["CustomerID"],
        "State Regions": ["State Code"],
        "Priorities": ["ID"],
        "Statuses": ["ID"],
        "Categories": ["ID"],
        "Sources": ["ID"],
        "Types": ["ID"],
        FACT_COMPLAINTS: ["ID"],
        FACT_HISTORY: ["ID"],
    }
    keys = {}
    for sheet, kc in key_specs.items():
        header, idx, it = read_rows(wb[sheet])
        kp = key_profile(header, idx, it, kc)
        kp["records_non_empty"] = profiles[sheet]["records_non_empty"]
        kp["unique_row_grain"] = kp["duplicate_key_groups"] == 0 and kp["rows_with_null_key"] == 0
        keys[sheet] = kp
    report["key_profiles"] = keys

    # --- 3. Lookup dimension --------------------------------------------------
    dims = {}
    for sheet in ["Brokers", "Products", "Regions", "Customers", "State Regions", "Priorities",
                  "Statuses", "Categories", "Sources", "Types"]:
        prof = profiles[sheet]
        dims[sheet] = {
            "records_non_empty": prof["records_non_empty"],
            "columns": [c["header"] for c in prof["columns"] if not c["header_is_blank"]],
            "empty_columns_ignored": len(prof["empty_column_indexes"]),
        }
    status_rows = {}
    ws = wb["Statuses"]
    header, idx, it = read_rows(ws)
    for row in it:
        if all(is_blank(v) for v in row):
            continue
        status_rows[row[idx["ID"]]] = row[idx["Description"]]
    report["status_lookup"] = {str(k): v for k, v in sorted(status_rows.items())}
    priority_rows = {}
    ws = wb["Priorities"]
    header, idx, it = read_rows(ws)
    for row in it:
        if all(is_blank(v) for v in row):
            continue
        priority_rows[row[idx["ID"]]] = row[idx["Description"]]
    report["priority_lookup"] = {str(k): v for k, v in sorted(priority_rows.items())}

    # --- 4. Key sets de kiem FK ---------------------------------------------
    key_sets = {}
    for sheet, kc in [("Customers", "CustomerID"), ("Brokers", "BrokerID"), ("Products", "ProductID"),
                      ("Regions", "id"), ("Priorities", "ID"), ("Statuses", "ID"),
                      ("Categories", "ID"), ("Sources", "ID"), ("Types", "ID")]:
        ks = build_key_set(wb[sheet], kc)
        key_sets[sheet] = ks
        dims[sheet]["null_key_values"] = ks["nulls"]

    # --- 5. Complaints: grain, FK, ngay, satisfaction, reimbursement ---------
    header, idx, it = read_rows(wb[FACT_COMPLAINTS])
    complaints = {}
    dup_rows = 0
    complaints_rows = 0
    fk_orphans = defaultdict(lambda: {"count": 0, "sample_complaint_ids": []})
    sat_counts = Counter()
    status_counts = Counter()
    prio_counts = Counter()
    reimb_values = []
    reimb_null = 0
    reimb_negative = 0
    reimb_zero = 0
    admin_values = Counter()
    for row in it:
        if all(is_blank(v) for v in row):
            continue
        complaints_rows += 1
        cid = row[idx["ID"]]
        if cid in complaints:
            dup_rows += 1
            continue
        complaints[cid] = {
            "complain": row[idx["ComplainDate"]],
            "completion": row[idx["CompletionDate"]],
            "customer": row[idx["CustomerID"]],
            "broker": row[idx["BrokerID"]],
            "product": row[idx["ProductID"]],
            "priority": row[idx["ComplainPriorityID"]],
            "type": row[idx["ComplainTypeID"]],
            "source": row[idx["ComplainSourceID"]],
            "category": row[idx["ComplainCategoryID"]],
            "status": row[idx["ComplainStatusID"]],
            "admin": row[idx["AdministratorID"]],
            "sat": row[idx["ClientSatisfaction"]],
            "reimb": row[idx["ExpectedReimbursement"]],
        }
        for fk, dim in [("customer", "Customers"), ("broker", "Brokers"), ("product", "Products"),
                        ("priority", "Priorities"), ("type", "Types"), ("source", "Sources"),
                        ("category", "Categories"), ("status", "Statuses")]:
            val = complaints[cid][fk]
            if is_blank(val):
                fk_orphans[f"{fk}_null"]["count"] += 1
                if len(fk_orphans[f"{fk}_null"]["sample_complaint_ids"]) < MAX_ID_SAMPLES:
                    fk_orphans[f"{fk}_null"]["sample_complaint_ids"].append(cid)
            elif val not in key_sets[dim]["set"]:
                fk_orphans[fk]["count"] += 1
                if len(fk_orphans[fk]["sample_complaint_ids"]) < MAX_ID_SAMPLES:
                    fk_orphans[fk]["sample_complaint_ids"].append(cid)
        sat = complaints[cid]["sat"]
        sat_counts["<null>" if is_blank(sat) else str(sat).strip()] += 1
        status_counts["<null>" if is_blank(complaints[cid]["status"]) else status_rows.get(complaints[cid]["status"], f"UNKNOWN_ID:{complaints[cid]['status']}")] += 1
        prio_counts["<null>" if is_blank(complaints[cid]["priority"]) else priority_rows.get(complaints[cid]["priority"], f"UNKNOWN_ID:{complaints[cid]['priority']}")] += 1
        r = complaints[cid]["reimb"]
        if is_blank(r):
            reimb_null += 1
        else:
            try:
                fv = float(r)
            except (TypeError, ValueError):
                sat_counts["__reimb_non_numeric__"] += 0
            else:
                reimb_values.append(fv)
                if fv < 0:
                    reimb_negative += 1
                if fv == 0:
                    reimb_zero += 1
        a = complaints[cid]["admin"]
        admin_values["<null>" if is_blank(a) else str(a)] += 1

    reimb_sorted = sorted(reimb_values)
    sat_total = sum(v for k, v in sat_counts.items() if not k.startswith("__"))
    sat_n = sat_counts.get("SAT", 0)
    sat_nsa = sat_counts.get("NSA", 0)
    sat_na = sat_counts.get("N/A", 0)
    check("complaints_unique_grain", dup_rows == 0,
          f"duplicate complaint ID rows={dup_rows}; distinct={len(complaints)}")
    check("complaints_rows_match_profile", complaints_rows == profiles[FACT_COMPLAINTS]["records_non_empty"],
          f"iterated={complaints_rows} vs profile={profiles[FACT_COMPLAINTS]['records_non_empty']}")
    report["complaints"] = {
        "rows_non_empty": complaints_rows,
        "distinct_ids": len(complaints),
        "duplicate_id_rows": dup_rows,
        "distinct_customers": len({c["customer"] for c in complaints.values() if not is_blank(c["customer"])}),
        "distinct_brokers_used": len({c["broker"] for c in complaints.values() if not is_blank(c["broker"])}),
        "distinct_products_used": len({c["product"] for c in complaints.values() if not is_blank(c["product"])}),
        "distinct_administrators": len(admin_values),
        "administrator_note": "khong co dimension Administrator trong workbook",
        "status_distribution": dict(status_counts.most_common()),
        "priority_distribution": dict(prio_counts.most_common()),
        "client_satisfaction_distribution": dict(sat_counts.most_common()),
        "satisfaction_evaluated_rows": sat_n + sat_nsa,
        "satisfaction_rows_NA": sat_na,
        "satisfaction_rows_blank": sat_counts.get("<null>", 0),
        "satisfaction_coverage_pct": round(100.0 * (sat_n + sat_nsa) / complaints_rows, 4) if complaints_rows else None,
    }

    report["complaints_fk_check"] = {
        "paths": {
            "CustomerID->Customers.CustomerID": fk_orphans["customer"]["count"],
            "BrokerID->Brokers.BrokerID": fk_orphans["broker"]["count"],
            "ProductID->Products.ProductID": fk_orphans["product"]["count"],
            "ComplainPriorityID->Priorities.ID": fk_orphans["priority"]["count"],
            "ComplainTypeID->Types.ID": fk_orphans["type"]["count"],
            "ComplainSourceID->Sources.ID": fk_orphans["source"]["count"],
            "ComplainCategoryID->Categories.ID": fk_orphans["category"]["count"],
            "ComplainStatusID->Statuses.ID": fk_orphans["status"]["count"],
        },
        "null_key_rows": {k: v["count"] for k, v in fk_orphans.items() if k.endswith("_null")},
        "orphan_sample_complaint_ids": {k: v["sample_complaint_ids"] for k, v in fk_orphans.items() if not k.endswith("_null")},
    }
    total_fk_orphan = sum(v["count"] for k, v in fk_orphans.items() if not k.endswith("_null"))
    check("complaints_fk_integrity", total_fk_orphan == 0,
          f"orphan FK rows={total_fk_orphan}; ghi nhan la DQ finding, khong tu sua")

    # ngay
    date_issues = {
        "complain_null": 0, "completion_null": 0, "completion_literal_null": 0,
        "negative_days": 0, "zero_days": 0,
        "positive_days": 0, "non_datetime": 0, "completion_before_complain": 0,
    }
    day_values = []
    pos_values = []
    complain_min = complain_max = None
    completion_min = completion_max = None
    for c in complaints.values():
        cd, cpd = c["complain"], c["completion"]
        if is_blank(cd):
            date_issues["complain_null"] += 1
        else:
            if complain_min is None or cd < complain_min:
                complain_min = cd
            if complain_max is None or cd > complain_max:
                complain_max = cd
        if is_blank(cpd):
            date_issues["completion_null"] += 1
        elif isinstance(cpd, str) and cpd.strip().upper() == "NULL":
            date_issues["completion_literal_null"] += 1
        elif not isinstance(cpd, (datetime, date)):
            date_issues["non_datetime"] += 1
        else:
            if completion_min is None or cpd < completion_min:
                completion_min = cpd
            if completion_max is None or cpd > completion_max:
                completion_max = cpd
        if isinstance(cd, (datetime, date)) and isinstance(cpd, (datetime, date)):
            delta = (cpd - cd).days
            if delta < 0:
                date_issues["negative_days"] += 1
                date_issues["completion_before_complain"] += 1
            elif delta == 0:
                date_issues["zero_days"] += 1
                day_values.append(delta)
            else:
                date_issues["positive_days"] += 1
                day_values.append(delta)
                pos_values.append(delta)
    day_sorted = sorted(day_values)
    pos_sorted = sorted(pos_values)
    closed_ids = {k for k, v in status_rows.items() if str(v).strip().upper() in {"RESOLVED", "CLOSED"}}
    open_ids = {k for k, v in status_rows.items() if str(v).strip().upper() in {"OUTSTANDING", "IN PROGRESS"}}

    def _completion_kind(v):
        if is_blank(v):
            return "blank"
        if isinstance(v, str) and v.strip().upper() == "NULL":
            return "literal_NULL"
        if isinstance(v, (datetime, date)):
            return "real_date"
        return "invalid"

    kind_by_status = Counter(
        (status_rows.get(c["status"], f"UNKNOWN_ID:{c['status']}"), _completion_kind(c["completion"]))
        for c in complaints.values())
    open_with_real_completion = sum(
        1 for c in complaints.values()
        if c["status"] in open_ids and _completion_kind(c["completion"]) == "real_date")
    open_with_literal_null = sum(
        1 for c in complaints.values()
        if c["status"] in open_ids and _completion_kind(c["completion"]) == "literal_NULL")
    closed_without_real_completion = sum(
        1 for c in complaints.values()
        if c["status"] in closed_ids and _completion_kind(c["completion"]) != "real_date")
    report["dates"] = {
        "complain_date_min": complain_min.isoformat() if complain_min else None,
        "complain_date_max": complain_max.isoformat() if complain_max else None,
        "completion_date_min": completion_min.isoformat() if completion_min else None,
        "completion_date_max": completion_max.isoformat() if completion_max else None,
        "issues": date_issues,
        "quantile_method": "noi suy tuyen tinh k=(n-1)q, tuong duong numpy linear",
        "completed_cohort_days": {
            "cohort": "moi cap ngay hop le delta>=0, GOM ca 0 ngay",
            "n": len(day_sorted),
            "min": day_sorted[0] if day_sorted else None,
            "p25": pct(day_sorted, 0.25), "median": pct(day_sorted, 0.5),
            "p75": pct(day_sorted, 0.75), "p90": pct(day_sorted, 0.90),
            "p99": pct(day_sorted, 0.99), "max": day_sorted[-1] if day_sorted else None,
            "mean": round(sum(day_sorted) / len(day_sorted), 6) if day_sorted else None,
        },
        "positive_only_days": {
            "cohort": "chi delta>0, nhan rieng de so sanh",
            "n": len(pos_sorted),
            "min": pos_sorted[0] if pos_sorted else None,
            "p25": pct(pos_sorted, 0.25), "median": pct(pos_sorted, 0.5),
            "p75": pct(pos_sorted, 0.75), "p90": pct(pos_sorted, 0.90),
            "p99": pct(pos_sorted, 0.99), "max": pos_sorted[-1] if pos_sorted else None,
            "mean": round(sum(pos_sorted) / len(pos_sorted), 6) if pos_sorted else None,
        },
        "status_vs_completion": {
            "open_status_ids": sorted(str(i) for i in open_ids),
            "closed_status_ids": sorted(str(i) for i in closed_ids),
            "open_status_with_real_completion_date": open_with_real_completion,
            "open_status_with_literal_null": open_with_literal_null,
            "closed_status_without_real_completion": closed_without_real_completion,
            "completion_kind_by_status": {f"{k[0]}|{k[1]}": v for k, v in kind_by_status.most_common()},
        },
        "note": "Ngay am/invalid la ngoai le; khong dien 0. Baseline gom 0 ngay; positive-only tach rieng.",
    }
    check("negative_processing_days", date_issues["negative_days"] == 0,
          f"negative_days={date_issues['negative_days']}; ghi nhan, khong sua nguon")

    # reimbursement
    report["expected_reimbursement"] = {
        "currency_declared_in_source": False,
        "null": reimb_null, "negative": reimb_negative, "zero": reimb_zero,
        "n_numeric": len(reimb_sorted),
        "min": reimb_sorted[0] if reimb_sorted else None,
        "p25": pct(reimb_sorted, 0.25), "median": pct(reimb_sorted, 0.5),
        "p75": pct(reimb_sorted, 0.75), "p95": pct(reimb_sorted, 0.95),
        "p99": pct(reimb_sorted, 0.99),
        "max": reimb_sorted[-1] if reimb_sorted else None,
        "mean": round(sum(reimb_sorted) / len(reimb_sorted), 6) if reimb_sorted else None,
        "note": "La so tien YEU CAU/ky vong, khong phai da chi tra. Currency chua ro.",
    }

    # --- 6. Customers: BirthDate, RegionID, denominator ----------------------
    header, idx, it = read_rows(wb["Customers"])
    birth = {}
    customer_ids = set()
    cust_dup = 0
    cust_region_orphan = 0
    cust_region_null = 0
    birth_null = 0
    birth_nondate = 0
    birth_years = Counter()
    cust_rows = 0
    for row in it:
        if all(is_blank(v) for v in row):
            continue
        cust_rows += 1
        cid = row[idx["CustomerID"]]
        if cid in customer_ids:
            cust_dup += 1
            continue
        customer_ids.add(cid)
        b = row[idx["BirthDate"]]
        r = row[idx["RegionID"]]
        if is_blank(b):
            birth_null += 1
        elif isinstance(b, (datetime, date)):
            birth[cid] = b
            birth_years[b.year] += 1
        else:
            birth_nondate += 1
            birth[cid] = None
        if is_blank(r):
            cust_region_null += 1
        elif r not in key_sets["Regions"]["set"]:
            cust_region_orphan += 1
    report["customers"] = {
        "rows_non_empty": cust_rows,
        "distinct_ids": len(customer_ids),
        "duplicate_id_rows": cust_dup,
        "birthdate_null": birth_null,
        "birthdate_non_datetime": birth_nondate,
        "birthyear_min": min(birth_years) if birth_years else None,
        "birthyear_max": max(birth_years) if birth_years else None,
        "birthyear_distribution": dict(sorted(birth_years.items())),
        "regionid_null": cust_region_null,
        "regionid_orphan": cust_region_orphan,
        "note": "Chi birth year/aggregate; khong ghi ngay sinh hoac ten.",
    }
    check("customers_unique_grain", cust_dup == 0, f"duplicate CustomerID rows={cust_dup}")
    check("customers_region_fk", cust_region_orphan == 0,
          f"Customers.RegionID orphan={cust_region_orphan}")

    # age at complaint
    ages, age_issues = [], {"birth_null_or_invalid": 0, "negative": 0, "under18": 0, "over100": 0}
    band = Counter()
    for c in complaints.values():
        b = birth.get(c["customer"])
        cd = c["complain"]
        if b is None or not isinstance(cd, (datetime, date)):
            age_issues["birth_null_or_invalid"] += 1
            continue
        a = cd.year - b.year - ((cd.month, cd.day) < (b.month, b.day))
        if a < 0:
            age_issues["negative"] += 1
            continue
        if a < 18:
            age_issues["under18"] += 1
        if a > 100:
            age_issues["over100"] += 1
        ages.append(a)
        band["<25" if a < 25 else "25-34" if a < 35 else "35-44" if a < 45 else
             "45-54" if a < 55 else "55-64" if a < 65 else "65+"] += 1
    ages.sort()
    urgent = {k for k, v in priority_rows.items() if str(v).strip().lower() == "urgent"}
    report["age_at_complaint"] = {
        "n": len(ages),
        "min": ages[0] if ages else None,
        "median": pct(ages, 0.5),
        "p95": pct(ages, 0.95),
        "max": ages[-1] if ages else None,
        "issues": age_issues,
        "bands": dict(band.most_common()),
        "urgent_complaints": sum(1 for c in complaints.values() if c["priority"] in urgent),
        "non_urgent_complaints": sum(1 for c in complaints.values() if c["priority"] not in urgent),
        "note": "Tuoi tai ngay complain; khong dung tuoi hien tai.",
    }

    # --- 7. Regions / State Regions -----------------------------------------
    header, idx, it = read_rows(wb["Regions"])
    region_state = {}
    region_rows = 0
    region_null_name = 0
    region_null_state = 0
    for row in it:
        if all(is_blank(v) for v in row):
            continue
        region_rows += 1
        rid = row[idx["id"]]
        region_state[rid] = row[idx["state_code"]]
        if is_blank(row[idx["name"]]):
            region_null_name += 1
        if is_blank(row[idx["state_code"]]):
            region_null_state += 1
    header, idx, it = read_rows(wb["State Regions"])
    state_region = {}
    for row in it:
        if all(is_blank(v) for v in row):
            continue
        state_region[row[idx["State Code"]]] = row[idx["Region"]]
    covered_states = {region_state[c] for c in complaints.values() if c["customer"] in birth and False}
    cust_state = {}
    header, idx, it = read_rows(wb["Customers"])
    for row in it:
        if all(is_blank(v) for v in row):
            continue
        cid, r = row[idx["CustomerID"]], row[idx["RegionID"]]
        cust_state[cid] = region_state.get(r)
    complaint_states = Counter()
    complaint_regions = Counter()
    state_unmapped = Counter()
    for c in complaints.values():
        st = cust_state.get(c["customer"])
        complaint_regions["<null>"] += 1 if st is None else 0
        if st is None:
            state_unmapped["<null_or_unmapped>"] += 1
            continue
        complaint_states[st] += 1
        if st not in state_region:
            state_unmapped[str(st)] += 1
    report["geography"] = {
        "regions_rows": region_rows,
        "regions_distinct_state_codes": len({v for v in region_state.values() if not is_blank(v)}),
        "regions_null_name": region_null_name,
        "regions_null_state_code": region_null_state,
        "state_regions_rows": profiles["State Regions"]["records_non_empty"],
        "state_regions_blank_columns_ignored": profiles["State Regions"]["empty_column_indexes"],
        "complaints_by_state_top10": dict(complaint_states.most_common(10)),
        "distinct_states_in_complaints": len(complaint_states),
        "complaints_with_unmapped_state": sum(state_unmapped.values()),
        "state_unmapped_detail": dict(state_unmapped.most_common(10)),
        "customers_region_coverage_note": "Customers.RegionID -> Regions.id -> Regions.state_code -> State Regions",
    }
    check("complaint_states_mapped", sum(state_unmapped.values()) == 0,
          f"complaints khong map duoc sang state={sum(state_unmapped.values())}")

    # --- 8. Status history: grain, ordering, ties, dwell --------------------
    header, idx, it = read_rows(wb[FACT_HISTORY])
    events = defaultdict(list)
    hist_rows = 0
    hist_dup_rows = 0
    seen_hist = set()
    hist_orphan_complaint = 0
    hist_orphan_status = 0
    hist_null_statusdate = 0
    hist_before_complain = 0
    date_min = date_max = None
    for row in it:
        if all(is_blank(v) for v in row):
            continue
        hist_rows += 1
        rid = row[idx["ID"]]
        sig = (rid, row[idx["ComplaintID"]], row[idx["ComplaintStatusID"]], row[idx["StatusDate"]])
        if sig in seen_hist:
            hist_dup_rows += 1
            continue
        seen_hist.add(sig)
        cid, sid, sd = row[idx["ComplaintID"]], row[idx["ComplaintStatusID"]], row[idx["StatusDate"]]
        if is_blank(cid):
            hist_null_statusdate += 1
            continue
        if cid not in complaints:
            hist_orphan_complaint += 1
            if hist_orphan_complaint <= MAX_ID_SAMPLES:
                pass
        if sid not in key_sets["Statuses"]["set"]:
            hist_orphan_status += 1
        if not isinstance(sd, (datetime, date)):
            hist_null_statusdate += 1
        else:
            date_min = sd if date_min is None else min(date_min, sd)
            date_max = sd if date_max is None else max(date_max, sd)
            c = complaints.get(cid)
            if c and isinstance(c["complain"], (datetime, date)) and sd < c["complain"]:
                hist_before_complain += 1
        events[cid].append((sd, sid, rid))

    order_as_stored = 0
    tie_complaints = 0
    tie_conflicting_status = 0
    identical_event_complaints = 0
    dwell_values = []
    zero_gap_pairs = 0
    zero_gap_diff_status = 0
    zero_gap_same_status = 0
    last_matches_complaint_status = 0
    last_status_disagree = 0
    latest_ambiguous = 0
    no_clean_dates = 0
    multi_status_complaints = 0
    never_leaves_first = 0
    for cid, evs in events.items():
        clean = [e for e in evs if isinstance(e[0], (datetime, date))]
        sev = sorted(clean, key=lambda e: e[0])
        if [e[0] for e in clean] != [e[0] for e in sev]:
            order_as_stored += 1
        if not sev:
            no_clean_dates += 1
            continue
        dates = [e[0] for e in sev]
        dup_dates = len(dates) - len(set(dates))
        if dup_dates > 0:
            tie_complaints += 1
            by_date = defaultdict(set)
            for d, s, _ in sev:
                by_date[d].add(s)
            if any(len(v) > 1 for v in by_date.values()):
                tie_conflicting_status += 1
        sids = {e[1] for e in sev}
        if len(sids) > 1:
            multi_status_complaints += 1
        if len(sids) == 1:
            identical_event_complaints += 1
        for i in range(len(sev) - 1):
            gap = (sev[i + 1][0] - sev[i][0]).days
            if gap > 0:
                dwell_values.append(gap)
            else:
                zero_gap_pairs += 1
                if sev[i + 1][1] != sev[i][1]:
                    zero_gap_diff_status += 1
                else:
                    zero_gap_same_status += 1
        c = complaints.get(cid)
        if c:
            maxdate = sev[-1][0]
            latest_statuses = {s for d, s, _ in sev if d == maxdate}
            if len(latest_statuses) > 1:
                latest_ambiguous += 1
            elif next(iter(latest_statuses)) == c["status"]:
                last_matches_complaint_status += 1
            else:
                last_status_disagree += 1

    dwell_sorted = sorted(dwell_values)
    complaints_with_events = len(events)
    report["status_history"] = {
        "rows_non_empty": hist_rows,
        "distinct_event_ids": len(seen_hist),
        "duplicate_event_rows": hist_dup_rows,
        "distinct_complaints_with_history": complaints_with_events,
        "complaints_without_history": len(complaints) - complaints_with_events,
        "orphan_complaint_id_rows": hist_orphan_complaint,
        "orphan_status_id_rows": hist_orphan_status,
        "non_datetime_or_null_statusdate_rows": hist_null_statusdate,
        "statusdate_min": date_min.isoformat() if date_min else None,
        "statusdate_max": date_max.isoformat() if date_max else None,
        "events_before_complain_date": hist_before_complain,
        "complaints_events_not_in_chronological_order": order_as_stored,
        "complaints_with_duplicate_timestamps": tie_complaints,
        "complaints_with_conflicting_status_same_timestamp": tie_conflicting_status,
        "complaints_single_status_only": identical_event_complaints,
        "complaints_multiple_statuses": multi_status_complaints,
        "complaints_without_clean_dates": no_clean_dates,
        "latest_history_status_equals_complaint_status": last_matches_complaint_status,
        "latest_history_status_differs_unambiguous": last_status_disagree,
        "latest_history_status_ambiguous_tie": latest_ambiguous,
        "zero_gap_pairs_excluded_from_dwell": zero_gap_pairs,
        "zero_gap_diff_status": zero_gap_diff_status,
        "zero_gap_same_status": zero_gap_same_status,
        "consecutive_dwell_days": {
            "cohort": "chi cap ke gap>0 sau khi sort; cap cung timestamp loai ra",
            "n": len(dwell_sorted),
            "min": dwell_sorted[0] if dwell_sorted else None,
            "median": pct(dwell_sorted, 0.5), "p90": pct(dwell_sorted, 0.90),
            "max": dwell_sorted[-1] if dwell_sorted else None,
            "note": "Trang thai cuoi bi censored tai as-of, tach rieng; khong suy tie-break.",
        },
        "history_coverage_pct_of_complaints": round(100.0 * complaints_with_events / len(complaints), 4) if complaints else None,
        "note": "Khong gia dinh hanh trinh tuan tuyen tinh. As-of backlog chua chot (Gate 1).",
    }
    check("history_fk_complaint", hist_orphan_complaint == 0,
          f"history rows tro ComplaintID khong ton tai={hist_orphan_complaint}")
    check("history_unique_event_id", hist_dup_rows == 0, f"duplicate event rows={hist_dup_rows}")

    # --- 9. As-of candidates (de cho Gate 1, khong chot dinh nghia) ---------
    asof = max((c["complain"] for c in complaints.values() if isinstance(c["complain"], (datetime, date))),
               default=None)
    backlog_candidates = 0
    age_gt30_open = 0
    for c in complaints.values():
        if c["status"] in open_ids and isinstance(c["complain"], (datetime, date)) and asof:
            age = (asof - c["complain"]).days
            if age > 30:
                age_gt30_open += 1
            backlog_candidates += 1
    report["asof_observation"] = {
        "max_complain_date_used_as_candidate_asof": asof.isoformat() if asof else None,
        "max_statusdate_in_history": date_max.isoformat() if date_max else None,
        "open_status_complaints": backlog_candidates,
        "open_status_age_gt_30_days_at_asof": age_gt30_open,
        "open_status_with_history": sum(
            1 for cid, c in complaints.items()
            if c["status"] in open_ids and cid in events),
        "status_age_vs_dwell_note": "Tuoi complaint (asof - ComplainDate) khac thoi gian o trang thai (asof - StatusDate cuoi). So tren la snapshot tai ngay complain max, KHONG phai tai dung as-of tu history; Gate 1 phai chot dinh nghia.",
    }

    # --- 10. Baseline KPI observations --------------------------------------
    report["kpi_observations"] = {
        "total_complaints": len(complaints),
        "complaints_with_SAT_or_NSA": sat_n + sat_nsa,
        "complaints_NA": sat_na,
        "complaints_blank_satisfaction": sat_counts.get("<null>", 0),
        "evaluation_coverage_pct": round(100.0 * (sat_n + sat_nsa) / len(complaints), 4) if complaints else None,
        "SAT": sat_n, "NSA": sat_nsa,
        "sat_rate_pct_of_evaluated": round(100.0 * sat_n / (sat_n + sat_nsa), 4) if (sat_n + sat_nsa) else None,
        "nsa_rate_pct_of_evaluated": round(100.0 * sat_nsa / (sat_n + sat_nsa), 4) if (sat_n + sat_nsa) else None,
        "complaints_per_1000_customers_in_source": round(1000.0 * len(complaints) / len(customer_ids), 6) if customer_ids else None,
        "customers_rows_in_source": len(customer_ids),
        "denominator_caveat": "Customers co the chi la nguoi tung khieu nai; chua chung minh la insured base day du.",
        "completed_cohort_median_days": pct(day_sorted, 0.5),
    }

    wb.close()
    report["source"]["sha256_after"] = sha256_file(args.xlsx)
    check("source_unchanged_during_profile", report["source"]["sha256_after"] == report["source"]["sha256_before"],
          "sha256 truoc == sau")
    report["finishedLocal"] = datetime.now().isoformat(timespec="seconds")
    report["summary"] = {
        "assertions_total": len(report["assertions"]),
        "assertions_failed": sum(1 for a in report["assertions"] if a["status"] == "FAIL"),
        "sheets_profiled": len(profiles),
        "records_total": sum(p["records_non_empty"] for p in profiles.values()),
    }

    os.makedirs(args.outdir, exist_ok=True)
    out_json = os.path.join(args.outdir, "profile_phase1.json")
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1, default=str)
    print("WROTE", out_json)
    for a in report["assertions"]:
        print(f"ASSERT {a['status']:4} {a['check']}: {a['detail']}")
    print("SUMMARY", json.dumps(report["summary"], ensure_ascii=False))
    failed = report["summary"]["assertions_failed"]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())