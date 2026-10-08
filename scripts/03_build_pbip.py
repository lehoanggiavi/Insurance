#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sinh PBIP semantic model cho insurance tu data/curated (Phase 3 - M04/M05).

Tao model tu 12 CSV curated: 2 bang fact + 11 lookup theo vai tro + 2 bang ngay.
GHI CHAM: moi file ghi bang open(..., encoding='utf-8') -> KHONG BOM.
Power BI Desktop tu choi file co BOM (PBIProjectShredder.CheckBom) - da gap loi nay.

Khong sua data/curated, khong them measure kinh doanh (Phase 3 chi lam lien ket du lieu).
Chay: python scripts\\03_build_pbip.py
"""
import csv
import json
import os
import sys
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURATED = os.path.join(ROOT, "data", "curated")
PBI = os.path.join(ROOT, "pbi")
MODEL = "InsuranceOps"
BASE = os.path.join(PBI, MODEL + ".SemanticModel")
DEFN = os.path.join(BASE, "definition")
TDIR = os.path.join(DEFN, "tables")
REPORT = os.path.join(PBI, MODEL + ".Report")

DATA_FOLDER = os.path.join(ROOT, "data", "curated")
MODEL_LOGICAL_ID = "3f6a1c48-7b25-4e19-9d83-5c0a2e64b791"
PAGE_ID = "1f2e3d4c-5b6a-4798-8f01-2a3b4c5d6e7f"


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def write_json(path, obj):
    write_text(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def q(name):
    """Ten cot co khoang trang phai boc dau nhay trong TMDL."""
    return "'%s'" % name if " " in name else name


def csv_header(fn):
    with open(os.path.join(CURATED, fn), encoding="utf-8", newline="") as fh:
        return next(csv.reader(fh))


def date_range(fn, col):
    lo = hi = None
    with open(os.path.join(CURATED, fn), encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            v = (row.get(col) or "").strip()
            if len(v) == 10:
                d = date.fromisoformat(v)
                lo = d if lo is None or d < lo else lo
                hi = d if hi is None or d > hi else hi
    return lo, hi


def m_literal(s):
    return '"' + s.replace('"', '""') + '"'


# --------------------------------------------------------------------------
# Mieu ta bang: (ten, csv, key, danh sach cot)
# Cot = (ten, dataType TMDL, kieu M, summarizeBy, isHidden)
# --------------------------------------------------------------------------
TECH = "hidden"          # cot ky thuat: giu trong model, an khoi goc dien hinh
KEEP = "keep"


def SIMPLE_ID(desc):
    return [
        ("ID", "int64", "Int64.Type", "none", False, True),
        ("ID__source", "string", "type text", "none", True, False),
        ("ID__int", "int64", "Int64.Type", "none", True, False),
        (desc, "string", "type text", "none", False, False),
    ]

FACT_COMPLAINT = [
    ("ComplaintID", "int64", "Int64.Type", "none", False, True),
    ("ComplaintID__source", "string", "type text", "none", True, False),
    ("ComplaintID__int", "int64", "Int64.Type", "none", True, False),
    ("ComplainDate__iso", "dateTime", "type date", "none", False, False),
    ("CompletionDate__iso", "dateTime", "type date", "none", False, False),
    ("CompletionDate__source_kind", "string", "type text", "none", False, False),
    ("CustomerID", "int64", "Int64.Type", "none", False, False),
    ("BrokerID", "int64", "Int64.Type", "none", False, False),
    ("ProductID", "int64", "Int64.Type", "none", False, False),
    ("ComplainPriorityID", "int64", "Int64.Type", "none", False, False),
    ("ComplainTypeID", "int64", "Int64.Type", "none", False, False),
    ("ComplainSourceID", "int64", "Int64.Type", "none", False, False),
    ("ComplainCategoryID", "int64", "Int64.Type", "none", False, False),
    ("ComplainStatusID", "int64", "Int64.Type", "none", False, False),
    ("ComplainStatus", "string", "type text", "none", False, False),
    ("AdministratorID", "int64", "Int64.Type", "none", False, False),
    ("ClientSatisfaction", "string", "type text", "none", False, False),
    ("ExpectedReimbursement", "double", "type number", "sum", False, False),
    ("processing_days", "int64", "Int64.Type", "none", False, False),
    ("age_at_complaint", "int64", "Int64.Type", "none", False, False),
    ("age_bucket", "string", "type text", "none", False, False),
    ("completion_null_flag", "boolean", "type logical", "none", False, False),
    ("category_inactive_flag", "boolean", "type logical", "none", False, False),
    ("quality_flags", "string", "type text", "none", False, False),
    ("_source_row", "int64", "Int64.Type", "none", True, False),
]

FACT_HISTORY = [
    ("EventID", "int64", "Int64.Type", "none", False, True),
    ("EventID__int", "int64", "Int64.Type", "none", True, False),
    ("ComplaintID", "int64", "Int64.Type", "none", False, False),
    ("ComplaintStatusID", "int64", "Int64.Type", "none", False, False),
    ("StatusDate__iso", "dateTime", "type date", "none", False, False),
    ("event_after_cutoff_flag", "boolean", "type logical", "none", False, False),
    ("complaint_latest_ambiguous_flag", "boolean", "type logical", "none", False, False),
    ("quality_flags", "string", "type text", "none", False, False),
    ("_source_row", "int64", "Int64.Type", "none", True, False),
]

DIM_CUSTOMER = [
    ("CustomerID", "int64", "Int64.Type", "none", False, True),
    ("CustomerID__source", "string", "type text", "none", True, False),
    ("Gender", "string", "type text", "none", False, False),
    ("ParticipantType", "string", "type text", "none", False, False),
    ("RegionID", "int64", "Int64.Type", "none", False, False),
    ("MaritalStatus", "string", "type text", "none", False, False),
    ("BirthDate__iso", "dateTime", "type date", "none", False, False),
    ("BirthYear", "string", "type text", "none", False, False),
    ("BirthDate__source_is_datetime", "boolean", "type logical", "none", True, False),
    ("birthdate_null_flag", "boolean", "type logical", "none", False, False),
    ("quality_flags", "string", "type text", "none", False, False),
    ("_source_row", "int64", "Int64.Type", "none", True, False),
]

TABLES = [
    ("Fact_Complaint", "complaints_curated.csv", "ComplaintID", FACT_COMPLAINT,
     "Bang fact khiếu nại. Grain = 1 dòng / 1 ComplaintID. Nguyên bản từ complaints_curated.csv."),
    ("Fact_StatusHistory", "status_history_curated.csv", "EventID", FACT_HISTORY,
     "Bang fact lịch sử trạng thái. Grain = 1 dòng / 1 EventID. Giữ MỌI event, "
     "không chọn latest, không tie-break; cờ ambiguity đi kèm từng dòng."),
    ("Dim_Customer", "customers_curated.csv", "CustomerID", DIM_CUSTOMER,
     "Dimension khách hàng. Grain = 1 dòng / 1 CustomerID. "
     "Không có FirstName/LastName (projection; không cần cho tính chỉ số)."),
    ("Dim_Broker", "brokers_curated.csv", "BrokerID", [
        ("BrokerID", "int64", "Int64.Type", "none", False, True),
        ("BrokerID__source", "string", "type text", "none", True, False),
        ("BrokerID__int", "int64", "Int64.Type", "none", True, False),
        ("BrokerCode", "string", "type text", "none", False, False),
        ("DistributionNetwork", "string", "type text", "none", False, False),
        ("DistributionChannel", "string", "type text", "none", False, False),
        ("CommissionScheme", "string", "type text", "none", False, False),
    ], "Dimension môi giới. Grain = 1 dòng / 1 BrokerID."),
    ("Dim_Product", "products_curated.csv", "ProductID", [
        ("ProductID", "int64", "Int64.Type", "none", False, True),
        ("ProductID__source", "string", "type text", "none", True, False),
        ("ProductID__int", "int64", "Int64.Type", "none", True, False),
        ("ProductCategory", "string", "type text", "none", False, False),
        ("ProductSubCategory", "string", "type text", "none", False, False),
        ("Product", "string", "type text", "none", False, False),
    ], "Dimension sản phẩm. Grain = 1 dòng / 1 ProductID."),
    ("Dim_Region", "regions_curated.csv", "id", [
        ("id", "int64", "Int64.Type", "none", False, True),
        ("id__source", "string", "type text", "none", True, False),
        ("id__int", "int64", "Int64.Type", "none", True, False),
        ("name", "string", "type text", "none", False, False),
        ("county", "string", "type text", "none", False, False),
        ("state_code", "string", "type text", "none", False, False),
        ("state", "string", "type text", "none", False, False),
        ("type", "string", "type text", "none", False, False),
        ("latitude", "double", "type number", "none", False, False),
        ("longitude", "double", "type number", "none", False, False),
        ("area_code", "string", "type text", "none", False, False),
        ("population", "int64", "Int64.Type", "sum", False, False),
        ("households", "int64", "Int64.Type", "sum", False, False),
        ("median_income", "double", "type number", "none", False, False),
        ("land_area", "double", "type number", "sum", False, False),
        ("water_area", "double", "type number", "sum", False, False),
        ("time_zone", "string", "type text", "none", False, False),
    ], "Dimension vùng. Grain = 1 dòng / 1 id. Tọa độ chuyển sang double ở đây "
     "(nguồn là chuỗi, cần kiểm kiểu trước khi dùng tính khoảng cách)."),
    ("Dim_StateRegion", "state_regions_curated.csv", "State Code__source", [
        ("State Code__source", "string", "type text", "none", False, True),
        ("State Code__int", "string", "type text", "none", True, False),
        ("State", "string", "type text", "none", False, False),
        ("Region", "string", "type text", "none", False, False),
    ], "Dimension vùng theo bang. Grain = 1 dòng / 1 State Code (khoá CHUỖI, "
     "vì mã bang không phải số)."),
    ("Dim_Priority", "priorities_curated.csv", "ID", SIMPLE_ID("Description"),
     "Dimension độ ưu tiên khiếu nại."),
    ("Dim_Category", "categories_curated.csv", "ID", [
        ("ID", "int64", "Int64.Type", "none", False, True),
        ("ID__source", "string", "type text", "none", True, False),
        ("ID__int", "int64", "Int64.Type", "none", True, False),
        ("Description", "string", "type text", "none", False, False),
        ("Active", "double", "type number", "none", False, False),
        ("Active__int", "int64", "Int64.Type", "none", True, False),
    ], "Dimension nhóm khiếu nại. Active=0 vẫn giữ đủ, chỉ gắn cờ."),
    ("Dim_Source", "sources_curated.csv", "ID", SIMPLE_ID("Description"),
     "Dimension nguồn khiếu nại."),
    ("Dim_Type", "types_curated.csv", "ID", SIMPLE_ID("Description"),
     "Dimension loại khiếu nại."),
]

STATUS_COLS = SIMPLE_ID("Description")
TABLES.append(("Dim_ComplaintStatus", "statuses_curated.csv", "ID", list(STATUS_COLS),
               "Lookup trạng thái theo VAI TRÒ CỦA COMPLAINT (ComplainStatusID ở Fact_Complaint). "
               "Tách riêng với Dim_EventStatus để không có hai đường lọc active tới history."))
TABLES.append(("Dim_EventStatus", "statuses_curated.csv", "ID", list(STATUS_COLS),
               "Lookup trạng thái theo VAI TRÒ CỦA EVENT (ComplaintStatusID ở Fact_StatusHistory). "
               "Cùng nguồn CSV nhưng là bảng riêng, có grain và quan hệ riêng."))

DATE_TABLES = []


def build_date_table(name, lo, hi, role, active, src_desc):
    cols = [
        ("Date", "dateTime", "type date", "none", False, True, "Time"),
        ("Year", "int64", "Int64.Type", "none", False, False, None),
        ("YearMonth", "string", "type text", "none", False, False, None),
        ("Quarter", "string", "type text", "none", False, False, None),
        ("MonthNum", "int64", "Int64.Type", "none", True, False, None),
        ("MonthName", "string", "type text", "none", False, False, None),
        ("DayOfWeek", "string", "type text", "none", False, False, None),
        ("DayOfWeekNum", "int64", "Int64.Type", "none", True, False, None),
    ]
    m = """let
    NgayDau = #date({y0}, {m0}, {d0}),
    NgayCuoi = #date({y1}, {m1}, {d1}),
    DanhSachNgay = List.Dates(NgayDau, Duration.Days(NgayCuoi - NgayDau) + 1, #duration(1, 0, 0, 0)),
    Raw = Table.TransformColumnTypes(Table.FromList(DanhSachNgay, Splitter.SplitByNothing(), {{"Date"}}), {{{{"Date", type date}}}}),
    CoNam = Table.AddColumn(Raw, "Year", each Date.Year([Date]), Int64.Type),
    CoThang = Table.AddColumn(CoNam, "MonthNum", each Date.Month([Date]), Int64.Type),
    CoNamThang = Table.AddColumn(CoThang, "YearMonth", each Date.ToText([Date], "yyyy-MM"), type text),
    CoQuy = Table.AddColumn(CoNamThang, "Quarter", each "Q" & Text.From(Date.QuarterOfYear([Date])), type text),
    CoTenThang = Table.AddColumn(CoQuy, "MonthName", each Date.ToText([Date], "MMM", "en-US"), type text),
    CoThu = Table.AddColumn(CoTenThang, "DayOfWeek", each Date.ToText([Date], "ddd", "en-US"), type text),
    CoSoThu = Table.AddColumn(CoThu, "DayOfWeekNum", each Date.DayOfWeek([Date], Day.Monday) + 1, Int64.Type)
in
    CoSoThu""".format(y0=lo.year, m0=lo.month, d0=lo.day, y1=hi.year, m1=hi.month, d1=hi.day)
    desc = ("Bảng ngày cho VAI TRÒ {role}. Phạm vi {lo:%d/%m/%Y}–{hi:%d/%m/%Y} "
            "lấy từ ngày hợp lệ thực có trong {src}. {state}").format(
        role=role, lo=lo, hi=hi, src=src_desc,
        state=("Đây là bảng ngày ACTIVE của model (quan hệ tới nó isActive)."
               if active else
               "Quan hệ tới bảng này isActive = 0 (inactive) để không tranh vai trò "
               "lọc ngày với bảng ngày complaint."))
    DATE_TABLES.append((name, cols, m, desc, active))


def emit_table(name, cols, doc, m_expr=None, partition_name=None):
    lines = ["/// " + doc.replace("\n", " "), "table " + name]
    if name.startswith("Dim_Date_"):
        lines.append("\tdataCategory: Time")
    for c in cols:
        cn, dtype, _m, summ, hidden, key, cat = (list(c) + [None])[:7]
        lines.append("")
        lines.append("\tcolumn " + q(cn))
        lines.append("\t\tdataType: " + dtype)
        if key:
            lines.append("\t\tisKey")
        if cat:
            lines.append("\t\tdataCategory: " + cat)
        if dtype == "dateTime":
            lines.append("\t\tformatString: Long Date")
        elif dtype == "double":
            lines.append("\t\tformatString: #,0.00")
        elif dtype == "int64":
            lines.append("\t\tformatString: #,0")
        if hidden:
            lines.append("\t\tisHidden")
        lines.append("\t\tsummarizeBy: " + summ)
        lines.append("\t\tsourceColumn: " + q(cn))
        if name.startswith("Dim_Date_") and cn in ("MonthName", "DayOfWeek"):
            lines.append("\t\tsortByColumn: " + ("MonthNum" if cn == "MonthName" else "DayOfWeekNum"))
        if dtype == "dateTime":
            lines.append("")
            lines.append("\t\tannotation UnderlyingDateTimeDataType = Date")
    lines.append("")
    lines.append("\tpartition %s = m" % (partition_name or name))
    lines.append("\t\tmode: import")
    lines.append("\t\tsource =")
    for ln in m_expr.split("\n"):
        lines.append("\t\t\t" + ln if ln.strip() else "")
    return "\n".join(lines) + "\n"


def m_for_csv(fn, cols, key):
    header = csv_header(fn)
    ncol = len(header)
    nullcols = [c[0] for c in cols
                if c[1] in ("dateTime", "int64", "double") and c[0] != key]
    types = ",\n\t        ".join('{%s, %s}' % (m_literal(c[0]), c[2]) for c in cols)
    repl = ", ".join(m_literal(c) for c in nullcols)
    null_step = ""
    if repl:
        null_step = ("\n    RongThanhNull = Table.ReplaceValue(PromotedHeaders, \"\", null, "
                     "Replacer.ReplaceValue, {%s})," % repl).replace("\n    RongThanhNull", "\n    RongThanhNull")
        base = "RongThanhNull"
    else:
        base = "PromotedHeaders"
    return """let
    Source = Csv.Document(File.Contents(#"Data Folder" & "\\{fn}"), [Delimiter = ",", Columns = {ncol}, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),{null}
    Typed = Table.TransformColumnTypes({base}, {{
        {types}
    }}, "en-US"),
    Sorted = Table.Sort(Typed, {{{qkey}, Order.Ascending}})
in
    Sorted""".format(fn=fn, ncol=ncol, null=null_step, base=base, types=types,
                     qkey=m_literal(key))


def main():
    # Fail-fast: moi cot khai bao phai ton tai that trong header CSV. Khong do la
    # 'sau khi refresh se bao loi' - PBI bao 'column was not found' 12 query roi.
    missing = []
    for name, fn, key, cols, _doc in TABLES:
        hdr = set(csv_header(fn))
        for c in cols:
            if c[0] not in hdr:
                missing.append("%s.%s (thiếu trong %s)" % (name, c[0], fn))
    if missing:
        raise SystemExit("COT KHAI BAO KHONG TON TAI TRONG CSV:\n  " + "\n  ".join(missing))

    lo_c, hi_c = date_range("complaints_curated.csv", "ComplainDate__iso")
    lo_e, hi_e = date_range("status_history_curated.csv", "StatusDate__iso")
    lo_x, hi_x = date_range("complaints_curated.csv", "CompletionDate__iso")
    DATE_TABLES.clear()
    build_date_table("Dim_Date_Complaint", min(lo_c, lo_x), max(hi_c, hi_x), "ngày complaint (active) / hoàn thành (inactive)", True,
                     "complaints_curated.csv (ComplainDate__iso và CompletionDate__iso)")
    build_date_table("Dim_Date_Event", lo_e, hi_e, "ngày event của lịch sử trạng thái", True,
                     "status_history_curated.csv (StatusDate__iso)")

    os.makedirs(TDIR, exist_ok=True)
    names = []
    for name, fn, key, cols, doc in TABLES:
        m = m_for_csv(fn, cols, key)
        write_text(os.path.join(TDIR, name + ".tmdl"), emit_table(name, cols, doc, m))
        names.append(name)
    for name, cols, m, doc, _active in DATE_TABLES:
        write_text(os.path.join(TDIR, name + ".tmdl"), emit_table(name, cols, doc, m))
        names.append(name)

    write_text(os.path.join(DEFN, "database.tmdl"),
               "database\n\tcompatibilityLevel: 1700\n")
    write_text(os.path.join(DEFN, "model.tmdl"),
               "model {m}\n\tculture: vi-VN\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
               "\tsourceQueryCulture: vi-VN\n\n{refs}".format(
                   m=MODEL,
                   refs="\n".join("ref table " + n for n in names) + "\n"))
    write_text(os.path.join(DEFN, "expressions.tmdl"),
               '/// Điểm duy nhất để đổi đường dẫn nguồn sau khi clone. Sửa 1 giá trị này rồi Refresh.\n'
               'expression \'Data Folder\' = "{p}" meta [IsParameterQuery=true, Type="Text", '
               'IsParameterQueryRequired=true]\n\n\tannotation PBI_ResultType = Text\n'.format(p=DATA_FOLDER))

    rels = [
        ("Fact_Complaint_to_Dim_Customer", "Fact_Complaint.CustomerID", "Dim_Customer.CustomerID", True),
        ("Fact_Complaint_to_Dim_Broker", "Fact_Complaint.BrokerID", "Dim_Broker.BrokerID", True),
        ("Fact_Complaint_to_Dim_Product", "Fact_Complaint.ProductID", "Dim_Product.ProductID", True),
        ("Fact_Complaint_to_Dim_Priority", "Fact_Complaint.ComplainPriorityID", "Dim_Priority.ID", True),
        ("Fact_Complaint_to_Dim_Category", "Fact_Complaint.ComplainCategoryID", "Dim_Category.ID", True),
        ("Fact_Complaint_to_Dim_Source", "Fact_Complaint.ComplainSourceID", "Dim_Source.ID", True),
        ("Fact_Complaint_to_Dim_Type", "Fact_Complaint.ComplainTypeID", "Dim_Type.ID", True),
        ("Fact_Complaint_to_Dim_ComplaintStatus", "Fact_Complaint.ComplainStatusID", "Dim_ComplaintStatus.ID", True),
        ("Fact_Complaint_to_Dim_Date_Complaint", "Fact_Complaint.ComplainDate__iso", "Dim_Date_Complaint.Date", True),
        ("Fact_Complaint_to_Dim_Date_Completion", "Fact_Complaint.CompletionDate__iso", "Dim_Date_Complaint.Date", False),
        ("Fact_StatusHistory_to_Fact_Complaint", "Fact_StatusHistory.ComplaintID", "Fact_Complaint.ComplaintID", True),
        ("Fact_StatusHistory_to_Dim_EventStatus", "Fact_StatusHistory.ComplaintStatusID", "Dim_EventStatus.ID", True),
        ("Fact_StatusHistory_to_Dim_Date_Event", "Fact_StatusHistory.StatusDate__iso", "Dim_Date_Event.Date", True),
        ("Dim_Customer_to_Dim_Region", "Dim_Customer.RegionID", "Dim_Region.id", True),
        ("Dim_Region_to_Dim_StateRegion", "Dim_Region.state_code", "Dim_StateRegion.'State Code__source'", True),
    ]
    body = []
    for rname, frm, to, active in rels:
        lines = ["relationship " + rname, "\tfromColumn: " + frm, "\ttoColumn: " + to,
                 "\tfromCardinality: many", "\ttoCardinality: one", "\tcrossFilteringBehavior: oneDirection"]
        if not active:
            # TMDL boolean phai la true/false. 'isActive: 0' bi parser boi:
            # Failed to convert the value '0' to the expected type Boolean!
            lines.append("\tisActive: false")
        body.append("\n".join(lines))
    write_text(os.path.join(DEFN, "relationships.tmdl"), "\n\n".join(body) + "\n")

    write_json(os.path.join(BASE, ".platform"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": MODEL},
        "config": {"version": "2.0", "logicalId": MODEL_LOGICAL_ID}})
    write_json(os.path.join(BASE, "definition.pbism"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.2", "settings": {}})

    # Container report da co thi giu nguyen (khong ghi de pages sau Phase 3).
    if os.path.isfile(os.path.join(REPORT, "definition", "report.json")):
        print("Semantic model written:", BASE)
        print("tables:", len(names), "relationships:", len(rels))
        return 0

    # Schema PBIP 1.0 chi cho phep 'report' trong artifacts (semanticModel duoc
    # tham chieu ngoai bang datasetReference cua report). Bo them semanticModel o day
    # se bi PBIProjectSchemaValidator bao 'Property semanticModel has not been defined'.
    write_json(os.path.join(PBI, MODEL + ".pbip"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0",
        "artifacts": [{"report": {"path": MODEL + ".Report"}}],
        "settings": {"enableAutoRecovery": True}})

    write_json(os.path.join(REPORT, ".platform"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": MODEL},
        "config": {"version": "2.0", "logicalId": "6b1d0e2f-8c37-4a50-bf94-d3e5a7c9b123"}})
    write_json(os.path.join(REPORT, "definition.pbir"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "1.0",
        "datasetReference": {"byPath": {"path": "../" + MODEL + ".SemanticModel"},
                             "byConnection": None}})
    write_json(os.path.join(REPORT, "definition", "pages", "pages.json"),
               {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/pagesMetadata/1.0.0/schema.json",
                "pageOrder": [PAGE_ID], "activePageName": PAGE_ID})
    write_json(os.path.join(REPORT, "definition", "pages", PAGE_ID, "page.json"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/page/2.0.0/schema.json",
        "name": PAGE_ID,
        "displayName": "Page1",
        "displayOption": "FitToPage",
        "height": 720.0,
        "width": 1280.0,
        "layout": {"id": 0, "width": 1280.0, "height": 720.0},
        "resourcePackages": [],
        "filterConfig": {"filters": []},
        "visualContainers": []})

    print("PBIP written:", PBI)
    print("tables:", len(TABLES), "csv-backed +", len(DATE_TABLES), "date =", len(names))
    print("relationships:", len(rels))
    print("date ranges: complaint %s..%s | event %s..%s | completion %s..%s"
          % (lo_c, hi_c, lo_e, hi_e, lo_x, hi_x))
    for f in sorted(os.listdir(TDIR)):
        with open(os.path.join(TDIR, f), "rb") as fh:
            b = fh.read(3)
        assert not (b[:3] == b"\xef\xbb\xbf"), "BOM in " + f
    print("BOM check: none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
