#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Phase 2 - xay curated bao toan du lieu tu workbook nguon (chi doc).

4 quy tac duoc chap thuan tai Gate 1:
  R1 Giu TOAN BO complaint/customer/history records va category inactive; KHONG loai
     tre em, tuoi 0 hay tuoi am. Chi gan co (flag), khong doan gia tri thay the.
  R2 Giu gia tri goc/lineage cho truong duoc chuan hoa. ID -> int CHI khi gia tri
     nguyen. Ngay hop le -> ISO; chuoi "NULL"/blank phan biet + co, KHONG dien 0/1900
     va KHONG tu gan ngay hoan thanh. Khong suy nghia business tu NULL.
  R3 Processing baseline giu 0 ngay. Satisfaction giu SAT/NSA/N/A rieng; KHONG them
     currency, KHONG cong bo ty le rui ro theo insured base.
  R4 History giu MOI event ke ca event sau 14/05 va timestamp trung; xuat co
     cutoff/latest-ambiguity; KHONG chon tie-break. 14/05 chi la tham so.

Khong ghi PII (ten/ngay sinh) va khong ghi mau hang ca nhan vao log.
Output: data/curated/*.csv + _lineage.csv + _flags.csv + manifest.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import date, datetime, timezone

import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX = os.path.join(ROOT, "data", "insurance_complain.xlsx")
OUT = os.path.join(ROOT, "data", "curated")
BASELINE_SHA = "3ace06421c1a8d146b0bfa6b9f08a2ae367bf32ead212182cb84b3d5af159032"
CUTOFF = date(2020, 5, 14)  # tham so tham chieu; KHONG phai snapshot da xac nhan

STATUS = {1.0: "OUTSTANDING", 2.0: "NEW", 3.0: "IN PROGRESS", 4.0: "ASSIGNED TO",
          5.0: "RESOLVED", 6.0: "PENDING", 9.0: "CLOSED"}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def blank(v):
    return v is None or (isinstance(v, str) and v.strip() == "")


def literal_null(v):
    return isinstance(v, str) and v.strip().upper() == "NULL"


def to_int(v):
    """Chuan hoa sang int CHI khi gia tri la so nguyen. Tra (int|None, co_nguyen)."""
    if isinstance(v, bool):
        return None, False
    if isinstance(v, int):
        return v, True
    if isinstance(v, float) and v.is_integer():
        return int(v), True
    return None, False


def to_iso_date(v):
    """Ngay hop le -> ISO. chuoi NULL/blank/invalid -> None (khong doan)."""
    if isinstance(v, datetime):
        return v.date().isoformat(), True
    if isinstance(v, date):
        return v.isoformat(), True
    return None, False


def read_sheet(wb, name):
    ws = wb[name]
    it = ws.iter_rows(values_only=True)
    header = [(None if h is None else str(h).strip()) for h in next(it)]
    cols = [c for c in header if c]
    out = []
    for row in it:
        if all(blank(v) for v in row):
            continue
        out.append({c: row[i] for i, c in enumerate(header) if c})
    return out


def write_csv(path, rows, cols):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    started = datetime.now(timezone.utc)
    src_sha = sha256_file(XLSX)
    if src_sha != BASELINE_SHA:
        raise SystemExit("NGUON LECH: %s != %s" % (src_sha, BASELINE_SHA))
    os.makedirs(OUT, exist_ok=True)

    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    raw = {name: read_sheet(wb, name) for name in
           ["Brokers", "Products", "Regions", "Customers", "State Regions", "Priorities",
            "Statuses", "Categories", "Sources", "Types", "Complains Data", "Status History Data"]}
    wb.close()

    stats = {}
    lineage = []  # (table, row_index_source, column, original_value, curated_value, rule)
    flags_rows = []
    complaints, customers, history = [], [], []

    # ---------- R2: dimension normalize ID + keep original ----------
    dims = {}
    for sheet, keycol, extra in [("Brokers", "BrokerID", None), ("Products", "ProductID", None),
                                ("Regions", "id", None), ("Priorities", "ID", None),
                                ("Statuses", "ID", None), ("Categories", "ID", "Active"),
                                ("Sources", "ID", None), ("Types", "ID", None),
                                ("State Regions", "State Code", None)]:
        out = []
        for idx, r in enumerate(raw[sheet]):
            new = {}
            for c, v in r.items():
                if c == keycol:
                    iv, ok = to_int(v)
                    new[c + "__int"] = iv if ok else None
                    new[c + "__source"] = v
                    if ok and str(v).strip() != str(iv):
                        lineage.append((sheet, idx, c, v, iv, "R2 string-id -> int"))
                        new[c] = iv
                    else:
                        new[c] = v
                else:
                    new[c] = v
            if extra == "Active" and "Active" in new:
                ai, ok = to_int(new["Active"])
                new["Active__int"] = ai if ok else None
                if new["Active__int"] == 0:
                    new["category_inactive_flag"] = True
            out.append(new)
        dims[sheet] = out
        stats[sheet] = {"source_rows": len(raw[sheet]), "curated_rows": len(out)}

    inactive_ids = {d["ID"] for d in dims["Categories"] if d.get("Active__int") == 0}

    # ---------- R1+R2+R3: customers (PII: BirthDate -> age flags only) ----------
    for idx, r in enumerate(raw["Customers"]):
        cid, ok = to_int(r["CustomerID"])
        b = r["BirthDate"]
        iso, is_date = to_iso_date(b)
        flags = []
        if not ok:
            flags.append("customer_id_not_integer")
        if blank(b):
            flags.append("birthdate_blank")
        elif not is_date:
            flags.append("birthdate_invalid")
        rec = {
            "CustomerID": cid if ok else r["CustomerID"],
            "CustomerID__source": r["CustomerID"],
            "Gender": r.get("Gender"),
            "ParticipantType": r.get("ParticipantType"),
            "RegionID": (to_int(r.get("RegionID"))[0] if to_int(r.get("RegionID"))[1] else r.get("RegionID")),
            "MaritalStatus": r.get("MaritalStatus"),
            "BirthDate__iso": iso,
            "BirthDate__source_is_datetime": is_date,
            "birthdate_null_flag": blank(b),
            "quality_flags": "|".join(flags),
            "_source_row": idx,
        }
        # KHONG giu ten vao curated (PII); chi con Count Nam Sinh de audit tong hop
        rec["BirthYear"] = iso[:4] if iso else None
        customers.append(rec)
        if flags:
            flags_rows.append({"table": "customers", "source_row": idx,
                               "CustomerID": rec["CustomerID"], "flags": "|".join(flags)})
    # ---------- R201: DOB -> ngay sinh de tinh tuoi TAI NGAY COMPLAINT ----------
    dob = {}
    for r in raw["Customers"]:
        k, k_ok = to_int(r["CustomerID"])
        if k_ok:
            dob[k] = to_iso_date(r["BirthDate"])[0]

    stats["Customers"] = {"source_rows": len(raw["Customers"]), "curated_rows": len(customers)}

    # ---------- R1+R2+R3+R4: complaints ----------
    for idx, r in enumerate(raw["Complains Data"]):
        flags = []
        cpd = r["CompletionDate"]
        cp_iso, cp_is_date = to_iso_date(cpd)
        if literal_null(cpd):
            flags.append("completion_literal_null")
        elif blank(cpd):
            flags.append("completion_blank")
        elif not cp_is_date:
            flags.append("completion_invalid")

        cda = r["ComplainDate"]
        cd_iso, cd_is_date = to_iso_date(cda)
        if not cd_is_date:
            flags.append("complain_date_invalid")

        days = None
        if cd_is_date and cp_is_date:
            days = (date.fromisoformat(cp_iso) - date.fromisoformat(cd_iso)).days
            if days < 0:
                flags.append("processing_days_negative")
            elif days == 0:
                flags.append("processing_days_zero")  # R3: GIU, chi gan co

        sat = r["ClientSatisfaction"]
        if blank(sat):
            flags.append("satisfaction_blank")
        elif sat not in ("SAT", "NSA", "N/A"):
            flags.append("satisfaction_unrecognised")

        # R201: tuoi TAI NGAY COMPLAINT (khong dung tuoi o cutoff chung).
        # Nhom 1-17 la QUAN SAT, khong ket luan ban ghi khong hop le.
        cust = to_int(r["CustomerID"])[0]
        b_iso = dob.get(cust)
        age = None
        age_bucket = "missing"
        if b_iso and cd_iso:
            bd = date.fromisoformat(b_iso)
            cdd = date.fromisoformat(cd_iso)
            age = cdd.year - bd.year - ((cdd.month, cdd.day) < (bd.month, bd.day))
            if age < 0:
                age_bucket = "negative"
                flags.append("age_negative")
            elif age == 0:
                age_bucket = "zero"
                flags.append("age_zero")
            elif age < 18:
                age_bucket = "1_17"
                flags.append("age_1_17_observed")
            else:
                age_bucket = "ge18"
        else:
            flags.append("age_missing_birthdate_or_complaindate")

        adm = r["AdministratorID"]
        adm_int, adm_ok = to_int(adm)
        if literal_null(adm):
            flags.append("administrator_literal_null")

        cat = r["ComplainCategoryID"]
        cat_int, cat_ok = to_int(cat)
        cat_inactive = cat_ok and cat_int in inactive_ids
        if cat_inactive:
            flags.append("category_inactive")  # R1: giu ban ghi, chi gan co

        reimb = r["ExpectedReimbursement"]
        cid_int, cid_ok = to_int(r["ID"])
        if not cid_ok:
            flags.append("complaint_id_not_integer")
        else:
            lineage.append(("Complains Data", idx, "ID", r["ID"], cid_int,
                            "R2 string-id -> int"))
        rec = {
            "ComplaintID": cid_int if cid_ok else r["ID"],
            "ComplaintID__source": r["ID"],
            "ComplaintID__int": cid_int,
            "ComplainDate__iso": cd_iso,
            "CompletionDate__iso": cp_iso,
            "CompletionDate__source_kind": ("literal_NULL" if literal_null(cpd)
                                            else "blank" if blank(cpd)
                                            else "date" if cp_is_date else "invalid"),
            "CustomerID": to_int(r["CustomerID"])[0],
            "BrokerID": to_int(r["BrokerID"])[0],
            "ProductID": to_int(r["ProductID"])[0],
            "ComplainPriorityID": to_int(r["ComplainPriorityID"])[0],
            "ComplainTypeID": to_int(r["ComplainTypeID"])[0],
            "ComplainSourceID": to_int(r["ComplainSourceID"])[0],
            "ComplainCategoryID": cat_int,
            "ComplainStatusID": to_int(r["ComplainStatusID"])[0],
            "ComplainStatus": STATUS.get(to_int(r["ComplainStatusID"])[0], "UNKNOWN"),
            "AdministratorID": adm_int if adm_ok else None,
            "ClientSatisfaction": sat,
            "ExpectedReimbursement": reimb,          # KHONG them currency (R3)
            "processing_days": days,
            "age_at_complaint": age,
            "age_bucket": age_bucket,
            "completion_null_flag": (literal_null(cpd) or blank(cpd)),
            "category_inactive_flag": bool(cat_inactive),
            "quality_flags": "|".join(flags),
            "_source_row": idx,
        }
        complaints.append(rec)
        if flags:
            flags_rows.append({"table": "complaints", "source_row": idx,
                               "ComplaintID": rec["ComplaintID"], "flags": "|".join(flags)})
    stats["Complains Data"] = {"source_rows": len(raw["Complains Data"]), "curated_rows": len(complaints)}

    # ---------- R1+R4: status history (giu MOI event) ----------
    per_complaint = defaultdict(list)
    for idx, r in enumerate(raw["Status History Data"]):
        sd = r["StatusDate"]
        sd_iso, sd_ok = to_iso_date(sd)
        flags = []
        if not sd_ok:
            flags.append("status_date_invalid")
        after = sd_ok and date.fromisoformat(sd_iso) > CUTOFF
        if after:
            flags.append("event_after_cutoff")  # R4: giu event, chi gan co
        ev_id = r["ID"]
        rec = {
            "EventID": ev_id,                                  # giu khoa su kien nguon
            "EventID__int": to_int(ev_id)[0],
            "ComplaintID": to_int(r["ComplaintID"])[0],
            "ComplaintStatusID": to_int(r["ComplaintStatusID"])[0],
            "StatusDate__iso": sd_iso,
            "event_after_cutoff_flag": bool(after),
            "quality_flags": "|".join(flags),
            "_source_row": idx,
        }
        history.append(rec)
        if flags:
            flags_rows.append({"table": "status_history", "source_row": idx,
                               "EventID": ev_id, "flags": "|".join(flags)})
        if sd_ok:
            per_complaint[to_int(r["ComplaintID"])[0]].append((date.fromisoformat(sd_iso),
                                                               to_int(r["ComplaintStatusID"])[0]))

    # R4: gan co latest-ambiguous (chi quan sat, KHONG chon tie-break)
    amb = set()
    for cid, evs in per_complaint.items():
        evs.sort()
        mx = evs[-1][0]
        sts = {s for d, s in evs if d == mx}
        if len(sts) > 1:
            amb.add(cid)
    for rec in history:
        if rec["ComplaintID"] in amb:
            rec["complaint_latest_ambiguous_flag"] = True
        else:
            rec["complaint_latest_ambiguous_flag"] = False
    stats["Status History Data"] = {"source_rows": len(raw["Status History Data"]), "curated_rows": len(history)}

    # ---------- ghi curated ----------
    CC = ["ComplaintID", "ComplaintID__source", "ComplaintID__int", "ComplainDate__iso", "CompletionDate__iso",
          "CompletionDate__source_kind", "CustomerID", "BrokerID", "ProductID", "ComplainPriorityID",
          "ComplainTypeID", "ComplainSourceID", "ComplainCategoryID", "ComplainStatusID",
          "ComplainStatus", "AdministratorID", "ClientSatisfaction", "ExpectedReimbursement",
          "processing_days", "age_at_complaint", "age_bucket",
          "completion_null_flag", "category_inactive_flag", "quality_flags",
          "_source_row"]
    CU = ["CustomerID", "CustomerID__source", "Gender", "ParticipantType", "RegionID",
          "MaritalStatus", "BirthDate__iso", "BirthYear", "BirthDate__source_is_datetime",
          "birthdate_null_flag", "quality_flags", "_source_row"]
    HC = ["EventID", "EventID__int", "ComplaintID", "ComplaintStatusID", "StatusDate__iso",
          "event_after_cutoff_flag", "complaint_latest_ambiguous_flag", "quality_flags", "_source_row"]
    write_csv(os.path.join(OUT, "complaints_curated.csv"), complaints, CC)
    write_csv(os.path.join(OUT, "customers_curated.csv"), customers, CU)
    write_csv(os.path.join(OUT, "status_history_curated.csv"), history, HC)

    DKEY = {"Brokers": "BrokerID", "Products": "ProductID", "Regions": "id", "State Regions": "State Code",
            "Priorities": "ID", "Statuses": "ID", "Categories": "ID", "Sources": "ID", "Types": "ID"}
    for sheet, cols in [("Brokers", ["BrokerID", "BrokerID__int", "BrokerCode", "DistributionNetwork",
                                     "DistributionChannel", "CommissionScheme"]),
                        ("Products", ["ProductID", "ProductID__int", "ProductCategory",
                                      "ProductSubCategory", "Product"]),
                        ("Regions", ["id", "id__int", "name", "county", "state_code", "state", "type",
                                     "latitude", "longitude", "area_code", "population",
                                     "households", "median_income", "land_area", "water_area",
                                     "time_zone"]),
                        ("State Regions", ["State Code__int", "State", "Region"]),
                        ("Priorities", ["ID", "ID__int", "Description"]),
                        ("Statuses", ["ID", "ID__int", "Description"]),
                        ("Categories", ["ID", "ID__int", "Description", "Active", "Active__int",
                                        "category_inactive_flag"]),
                        ("Sources", ["ID", "ID__int", "Description"]),
                        ("Types", ["ID", "ID__int", "Description"])]:
        if dims[sheet]:
            avail = [c for c in cols if c in dims[sheet][0]]
            kc = DKEY[sheet]
            if kc + "__source" in dims[sheet][0] and kc + "__source" not in avail:
                avail.insert(avail.index(kc) + 1 if kc in avail else 0, kc + "__source")
        else:
            avail = cols
        write_csv(os.path.join(OUT, sheet.lower().replace(" ", "_") + "_curated.csv"), dims[sheet], avail)

    write_csv(os.path.join(OUT, "_flags.csv"), flags_rows, ["table", "source_row", "flags"])
    write_csv(os.path.join(OUT, "_lineage.csv"),
              [{"table": a, "source_row": b, "column": c, "original_value": d,
                "curated_value": e, "rule": f} for a, b, c, d, e, f in lineage],
              ["table", "source_row", "column", "original_value", "curated_value", "rule"])

    # ---------- manifest (metadata + tong hop; KHONG PII) ----------
    fc = Counter()
    for r in complaints:
        for f in r["quality_flags"].split("|"):
            if f:
                fc[f] += 1
    uc = Counter()
    for r in customers:
        for f in r["quality_flags"].split("|"):
            if f:
                uc[f] += 1
    hc = Counter()
    for r in history:
        for f in r["quality_flags"].split("|"):
            if f:
                hc[f] += 1

    manifest = {
        "phase": "Phase 2 - curated bao toan du lieu",
        "generatedUtc": started.isoformat(),
        "source": {"path": os.path.relpath(XLSX, ROOT).replace("\\", "/"),
                   "sha256": src_sha, "sha256_matches_baseline": True},
        "cutoff_reference": CUTOFF.isoformat(),
        "cutoff_note": "Tham so tham chieu do chon; KHONG phai snapshot da xac nhan nguon.",
        "rules": {"R1": "Giu toan bo records; chi gan co, khong loai",
                  "R2": "Chuan hoa ID/ngay + giu gia tri goc/lineage; khong doan gia tri",
                  "R3": "Giu 0 ngay; giu SAT/NSA/N/A rieng; khong them currency",
                  "R4": "Giu moi history event + co cutoff/ambiguity; khong chon tie-break"},
        "row_counts": stats,
        "row_count_delta": {k: v["curated_rows"] - v["source_rows"] for k, v in stats.items()},
        "complaint_flag_counts": dict(fc.most_common()),
        "customer_flag_counts": dict(uc.most_common()),
        "history_flag_counts": dict(hc.most_common()),
        "satisfaction_curated": dict(Counter(c["ClientSatisfaction"] for c in complaints).most_common()),
        "zero_day_complaints": sum(1 for c in complaints if c["processing_days"] == 0),
        "literal_null_completion": sum(1 for c in complaints if c["CompletionDate__source_kind"] == "literal_NULL"),
        "negative_processing_days": sum(1 for c in complaints if (c["processing_days"] or 0) < 0),
        "category_inactive_complaints": sum(1 for c in complaints if c["category_inactive_flag"]),
        "events_after_cutoff": sum(1 for h in history if h["event_after_cutoff_flag"]),
        "complaints_with_latest_ambiguous": len(amb),
        "age_at_complaint_buckets": dict(Counter(c["age_bucket"] for c in complaints).most_common()),
        "age_note": ("Tuoi tinh tai ComplainDate cua chinh complaint do (khong dung tuoi o cutoff chung). "
                     "Nhom 1_17/negative/zero la QUAN SAT, khong phai ket luan ban ghi khong hop le."),
        "distinct_complaint_ids": len({c["ComplaintID"] for c in complaints}),
        "distinct_event_ids": len({h["EventID"] for h in history}),
        "files": {},
    }
    for fn in sorted(os.listdir(OUT)):
        p = os.path.join(OUT, fn)
        if fn != "manifest.json":
            manifest["files"][fn] = {"bytes": os.path.getsize(p), "sha256": sha256_file(p)}
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)

    # ---------- bang lieu san (log chi metadata/tong hop) ----------
    print("SOURCE_SHA_OK", src_sha == BASELINE_SHA)
    for k, v in stats.items():
        print("ROWS %-20s source=%6d curated=%6d delta=%d" % (k, v["source_rows"], v["curated_rows"],
                                                              v["curated_rows"] - v["source_rows"]))
    print("COMPLAINTS", manifest["distinct_complaint_ids"], "HISTORY", manifest["distinct_event_ids"])
    print("SAT_CURATED", manifest["satisfaction_curated"])
    print("LITERAL_NULL_COMPLETION", manifest["literal_null_completion"],
          "ZERO_DAY", manifest["zero_day_complaints"],
          "NEG_DAYS", manifest["negative_processing_days"])
    print("INACTIVE_COMPLAINTS", manifest["category_inactive_complaints"],
          "EVENTS_AFTER_CUTOFF", manifest["events_after_cutoff"],
          "LATEST_AMBIGUOUS", manifest["complaints_with_latest_ambiguous"])
    print("FLAGS_C", dict(fc.most_common()))
    print("FLAGS_U", dict(uc.most_common()))
    print("FLAGS_H", dict(hc.most_common()))
    print("LINEAGE_ROWS", len(lineage))
    print("FILES", len(manifest["files"]))
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())