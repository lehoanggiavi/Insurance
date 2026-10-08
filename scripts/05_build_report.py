"""Sinh 2 trang native PBIR cho InsuranceOps. stdlib only. Chay offline, Desktop phai da dong."""
import json, os, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RPT = ROOT / "pbi" / "InsuranceOps.Report" / "definition"
PAGES = RPT / "pages"

# Palette lay tu theme EVIDENTIA (reports/phase5/theme-evidentia.json -> BaseThemes/Evidentia.json)
# de theme va goc trong report khong xung dot. Doi mau o day = doi ca theme.
BG = "#FFFFFF"; PANEL = "#FFFFFF"; INK = "#0B1F35"; NAVY = "#0B1F35"; S1 = "#2251FF"
RED = "#9E2B25"; MUTE = "#3C4A5A"; HAIR = "#C7D0D9"; TEAL = S1
FONT = "Segoe UI"; HEADFONT = "Georgia"
W, H = 1280, 720
SIDEBAR = 144; RAILW = 168
CX0, CX1 = 180, 1272

SCHEMA_PAGE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
SCHEMA_VIS = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json"
SCHEMA_PAGES = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json"

Z = [0]


def lit(v):
    if isinstance(v, bool):
        return {"Literal": {"Value": "true" if v else "false"}}
    if isinstance(v, int):
        return {"Literal": {"Value": f"{v}L"}}
    if isinstance(v, float):
        return {"Literal": {"Value": repr(v)}}
    return {"Literal": {"Value": "'" + str(v).replace("'", "''") + "'"}}


def color(hx):
    return {"solid": {"color": lit(hx)}}


def obj(**props):
    return [{"properties": props}]


def txt(size, c=INK, bold=False):
    """slicer header dung textSize."""
    p = {"textSize": lit(size), "fontColor": color(c), "fontFamily": lit(FONT)}
    if bold:
        p["bold"] = lit(True)
    return p


def vtxt(size, c=INK, bold=False):
    """VCO title dung fontSize (khong phai textSize)."""
    p = {"fontSize": lit(size), "fontColor": color(c), "fontFamily": lit(FONT)}
    if bold:
        p["bold"] = lit(True)
    return p


def rail():
    return {"background": obj(show=True, color=color(RAIL), transparency=lit(0)),
            "border": obj(show=False),
            "padding": obj(top=lit(6), bottom=lit(6), left=lit(8), right=lit(8)),
            "title": obj(show=False)}


def panel(title=None):
    vb = {"background": obj(show=True, color=color(PANEL), transparency=lit(0)),
          "border": obj(show=True, color=color(HAIR), radius=lit(6)),
          "padding": obj(top=lit(8), bottom=lit(8), left=lit(10), right=lit(10))}
    if title:
        vb["title"] = obj(show=True, text=lit(title), alignment=lit("left"), **vtxt(11, NAVY, True))
    else:
        vb["title"] = obj(show=False)
    return vb


def prop(name):
    """PBIR Property la ten hien thi THAT, bo dau nhay TMDL."""
    return name.strip("'")


def col(entity, p):
    return {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop(p)}}


def msr(prop):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": "Measure"}}, "Property": prop}}


def proj(f, ref, native=None):
    return {"field": f, "queryRef": ref, "nativeQueryRef": native or ref.split(".")[-1]}


def qstate(spec):
    """spec: role -> (field, ref, native) hoac list cua cac tuple do."""
    out = {}
    for role, v in spec.items():
        items = v if isinstance(v, list) else [v]
        out[role] = {"projections": [proj(*t) for t in items]}
    return out


def write(path, obj_):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj_, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def visual(vt, x, y, w, h, query, objects=None, vco=None, qfilters=None):
    Z[0] += 1
    vid = f"v{Z[0]:04x}insur0{p_vt[0]}{Z[0]:04x}"
    body = {"visualType": vt, "query": {"queryState": query}}
    if qfilters:
        body["query"]["queryState"].update({})
        body["filters"] = qfilters
    if objects:
        body["objects"] = objects
    body["visualContainerObjects"] = vco if vco is not None else panel()
    out = {"$schema": SCHEMA_VIS, "name": vid,
           "position": {"x": x, "y": y, "width": w, "height": h, "z": Z[0], "tabOrder": Z[0]},
           "visual": body}
    write(PAGES / _page[0] / "visuals" / vid / "visual.json", out)
    return vid


p_vt = {}


def register(vt):
    p_vt[0] = vt[0:2]
    p_vt[vt] = vt


for _v in ("cardVisual", "slicer", "lineChart", "barChart", "pivotTable", "textbox", "shape"):
    register(_v)
p_vt[0] = "00"


def textbox(page_dir, x, y, w, h, runs, size=10, c=INK, bold=False, align="left", font=None, fill=None):
    """runs: chuoi hoac list; moi phan tu la chuoi hoac (text, size, color, bold)."""
    Z[0] += 1
    vid = f"v{Z[0]:04x}insur0tb{Z[0]:04x}"
    if isinstance(runs, str):
        runs = [runs]
    paras = []
    for r in runs:
        if isinstance(r, tuple):
            t, sz, cc, bb = r
        else:
            t, sz, cc, bb = r, size, c, bold
        paras.append({"textRuns": [{"value": t,
                                    "textStyle": {"fontSize": f"{sz}pt", "fontFamily": font or FONT, "color": cc,
                                                  "fontWeight": "bold" if bb else "normal"}}],
                      "horizontalTextAlignment": align})
    out = {"$schema": SCHEMA_VIS, "name": vid,
           "position": {"x": x, "y": y, "width": w, "height": h, "z": Z[0], "tabOrder": Z[0]},
           "visual": {"visualType": "textbox",
                      "objects": {"general": [{"properties": {"paragraphs": paras}}]},
                      "visualContainerObjects": {"background": obj(show=True, color=color(fill), transparency=lit(0)) if fill else obj(show=False),
                                                 "border": obj(show=False),
                                                 "title": obj(show=False),
                                                 "padding": obj(top=lit(2), bottom=lit(2), left=lit(0), right=lit(0))}}}
    write(PAGES / page_dir / "visuals" / vid / "visual.json", out)
    return vid


def cardfmt(size, c, prec, pct, lbl=None):
    """labelDisplayUnits/position la ENUM -> phai truyen Literal so (0L), khong phai chuoi."""
    return {"value": obj(show=True, fontSize=lit(size), fontFamily=lit(FONT), bold=lit(True),
                         fontColor=color(c), customFormatString=lit("0.0%" if pct else "#,0.##"),
                         labelDisplayUnits=lit(0), labelPrecision=lit(prec),
                         horizontalAlignment=lit("left"), textWrap=lit(True)),
            "label": obj(show=True, text=lit(lbl) if lbl else lit(""), fontSize=lit(9), fontFamily=lit(FONT), fontColor=color(MUTE),
                         horizontalAlignment=lit("left"))}


def axisfmt(**extra):
    """categoryAxis/valueAxis phai la ARRAY cua {properties:{...}}."""
    p = {"fontFamily": lit(FONT), "fontSize": lit(9), "labelColor": color(MUTE)}
    p.update(extra)
    return [{"properties": p}]


def put(page_dir, vt, x, y, w, h, roles, vo, vco):
    Z[0] += 1
    vid = f"v{Z[0]:04x}insur0{abs(hash(vt + str(Z[0]))) % 9973:04x}"
    qs = {}
    for k, v in roles.items():
        items = v if isinstance(v, list) else [v]
        qs[k] = {"projections": [proj(*t) for t in items]}
    write(PAGES / page_dir / "visuals" / vid / "visual.json",
          {"$schema": SCHEMA_VIS, "name": vid,
           "position": {"x": x, "y": y, "width": w, "height": h, "z": Z[0], "tabOrder": Z[0]},
           "visual": {"visualType": vt, "query": {"queryState": qs}, "objects": vo,
                      "visualContainerObjects": vco}})


def slicer(page_dir, ent, p, lbl, y, hh):
    nm = prop(p)
    put(page_dir, "slicer", 12, y, SIDEBAR, hh,
        {"Values": [(col(ent, p), f"{ent}.{nm}", nm)]},
        {"data": obj(mode=lit("Between")),
         "header": obj(show=True, text=lit(lbl), textSize=lit(9), fontColor=color(NAVY), fontFamily=lit(FONT)),
         "items": obj(textSize=lit(9), fontColor=color(INK), fontFamily=lit(FONT))},
        panel())


def put_month(page_dir, x, y, w, h):
    """lineChart YearMonth co sortDefinition tang dan theo chinh YearMonth."""
    Z[0] += 1
    vid = f"v{Z[0]:04x}insur0{Z[0]:04x}"
    ym = col("Dim_Date_Complaint", "YearMonth")
    write(PAGES / page_dir / "visuals" / vid / "visual.json",
          {"$schema": SCHEMA_VIS, "name": vid,
           "position": {"x": x, "y": y, "width": w, "height": h, "z": Z[0], "tabOrder": Z[0]},
           "visual": {"visualType": "lineChart",
                      "query": {"queryState": {
                          "Category": {"projections": [{"field": ym, "queryRef": "Dim_Date_Complaint.YearMonth",
                                                        "nativeQueryRef": "YearMonth"}]},
                          "Y": {"projections": [proj(msr("Total Complaints"), "Measure.Total Complaints", "Total Complaints")]}}},
                      "objects": {"categoryAxis": axisfmt(concatenateLabels=lit(False)),
                                  "valueAxis": axisfmt(), "labels": obj(show=lit(False)),
                                  "legend": obj(show=lit(False))},
                      "visualContainerObjects": panel("Kieu nai theo thoi gian - YearMonth x Total Complaints (theo thu tu thoi gian)")}})


# ---------------------------------------------------------------- trang 1
_page = ["execsum01"]
shutil.rmtree(PAGES / "7154a9c72e424ea0b6a7", ignore_errors=True)   # bo placeholder "Model only"
shutil.rmtree(PAGES / "execsum01", ignore_errors=True)
P = "execsum01"

textbox(P, 180, 2, 1092, 48, "Insurance Complaints - Executive Summary", 20, NAVY, True, font=HEADFONT)
textbox(P, 180, 48, 1092, 34,
        "Kieu nai theo ngay tiep nhan  ·  Nam / Vung / Muc do uu tien loc o thanh ben trai  ·  Nguon: file curated trong ban giao  ·  KHONG phai muc tieu da chot",
        10, MUTE)
# rail toi ben trai: tieu de report + bo loc (khong phai nav - PLAN cam tab menu)
textbox(P, 14, 12, SIDEBAR, 52, "B O C L O C", 9, MUTE, True)

slicer(P, "Dim_Date_Complaint", "Year", "Nam tiep nhan", 78, 92)
slicer(P, "Dim_StateRegion", "'State Code__source'", "Vung / State", 182, 200)
slicer(P, "Dim_Priority", "Description", "Muc do uu tien", 396, 84)

for i, (m, lbl) in enumerate([("Total Complaints", "Tong so khieu nai"), ("Average Processing Days", "TB ngay xu ly"),
                              ("Median Processing Days", "Trung vi ngay xu ly"), ("SAT Rate", "Ty le SAT"),
                              ("Evaluation Coverage", "Do phu evaluation")]):
    pct = m in ("SAT Rate", "Evaluation Coverage")
    put(P, "cardVisual", CX0 + i * 215, 88, 207, 96,
        {"Data": [(msr(m), f"Measure.{m}", m)]},
        cardfmt(20, TEAL if i == 0 else NAVY, 1 if pct else 0, pct, lbl), panel())

put_month(P, CX0, 192, 524, 218)

put(P, "barChart", CX0 + 548, 192, 524, 218,
    {"Category": (col("Dim_Category", "Description"), "Dim_Category.Description", "Description"),
     "Y": (msr("NSA Rate"), "Measure.NSA Rate", "NSA Rate"),
     "Tooltips": [(msr("NSA Complaints"), "Measure.NSA Complaints", "NSA Complaints"),
                  (msr("Evaluated Complaints"), "Measure.Evaluated Complaints", "Evaluated Complaints")]},
    {"categoryAxis": axisfmt(), "valueAxis": axisfmt(labelPrecision=lit(1)),
     "dataPoint": obj(defaultColor=color(RED), fill={"solid": {"color": lit(RED)}}),
     "labels": obj(show=lit(True), fontSize=lit(9), fontFamily=lit(FONT), color=color(INK))},
    panel("Ty le khong han ho theo nhom - n va do phu danh gia o tooltip"))

put(P, "barChart", CX0, 418, 524, 218,
    {"Category": (col("Dim_Product", "ProductCategory"), "Dim_Product.ProductCategory", "ProductCategory"),
     "Y": (msr("Total Complaints"), "Measure.Total Complaints", "Total Complaints")},
    {"categoryAxis": axisfmt(), "valueAxis": axisfmt(),
     "dataPoint": obj(defaultColor=color(NAVY)),
     "labels": obj(show=lit(True), fontSize=lit(9), fontFamily=lit(FONT), color=color(INK))},
    panel("Kieu nai theo nhom san pham - ProductCategory x Total Complaints"))

put(P, "barChart", CX0 + 548, 418, 524, 218,
    {"Category": (col("Dim_StateRegion", "'State Code__source'"), "Dim_StateRegion.State Code__source", "StateCode"),
     "Y": (msr("Complaints per 1000 Source Customers"), "Measure.Complaints per 1000 Source Customers", "per1000"),
     "Tooltips": [(msr("Total Complaints"), "Measure.Total Complaints", "Total Complaints"),
                  (msr("Source Customers"), "Measure.Source Customers", "Source Customers")]},
    {"categoryAxis": axisfmt(), "valueAxis": axisfmt(),
     "dataPoint": obj(defaultColor=color(TEAL)),
     "labels": obj(show=lit(True), fontSize=lit(9), fontFamily=lit(FONT), color=color(INK))},
    panel("Kieu nai tren 1000 khach trong file nguon (khong la nguoi duoc bao hiem)"))

textbox(P, CX0, 644, 1072, 68, [
    "Ghi chu: (1) Chi so khong danh gia - du lieu quan sat, khong phai muc tieu da chot. Chi 7.687/13.846 khieu nai co "
    "danh gia SAT/NSA (55,52%).",
    "(2) 50 khieu nai chua co CompletionDate va 21 dong dang IN PROGRESS/OUTSTANDING. Day KHONG phai backlog theo thoi diem.",
    "(3) 'Khach trong file nguon' la so khach co trong file goc, KHONG phai danh sach nguoi duoc bao hiem.",
], 9, MUTE)

# ---------------------------------------------------------------- trang 2
shutil.rmtree(PAGES / "operdrill01", ignore_errors=True)
P = "operdrill01"

textbox(P, 180, 2, 1092, 48, "Insurance Complaints - Operation Drill-down", 20, NAVY, True, font=HEADFONT)
textbox(P, 180, 48, 1092, 34,
        "Chi tiet xu ly va phan bo  ·  Nam / Nhom khieu nai / Nguon loc o thanh ben trai  ·  Bo loc chi ap dung cho trang nay", 10, MUTE)
# rail toi ben trai: tieu de report + bo loc (khong phai nav - PLAN cam tab menu)
textbox(P, 14, 12, SIDEBAR, 52, "B O C L O C", 9, MUTE, True)

slicer(P, "Dim_Date_Complaint", "Year", "Nam tiep nhan", 78, 92)
slicer(P, "Dim_Category", "Description", "Nhom khieu nai", 182, 200)
slicer(P, "Dim_Source", "Description", "Nguon", 396, 110)

for i, (m, lbl) in enumerate([("Completed Complaints", "Da hoan thanh"), ("Uncompleted Complaints", "Chua hoan thanh"),
                              ("Urgent Complaints", "Uu tien"), ("History Presence Coverage", "Co du lieu lich su")]):
    pct = "Coverage" in m
    put(P, "cardVisual", CX0 + i * 269, 88, 261, 96,
        {"Data": [(msr(m), f"Measure.{m}", m)]},
        cardfmt(20, TEAL if i == 0 else NAVY, 1 if pct else 0, pct, lbl), panel())

put(P, "barChart", CX0, 180, 524, 226,
    {"Category": (col("Dim_Source", "Description"), "Dim_Source.Description", "Description"),
     "Y": [(msr("Average Processing Days"), "Measure.Average Processing Days", "Average Processing Days"),
           (msr("Median Processing Days"), "Measure.Median Processing Days", "Median Processing Days")]},
    {"categoryAxis": axisfmt(), "valueAxis": axisfmt(),
     "dataPoint": obj(defaultColor=color(TEAL)),
     "legend": obj(show=lit(True), fontFamily=lit(FONT), fontSize=lit(9), labelColor=color(INK)),
     "labels": obj(show=lit(False))},
    panel("Thoi gian xu ly theo nguon - TB va trung vi ngay"))

put(P, "pivotTable", CX0 + 548, 192, 524, 218,
    {"Rows": (col("Dim_Type", "Description"), "Dim_Type.Description", "Description"),
     "Values": [(msr("Total Complaints"), "Measure.Total Complaints", "Total Complaints"),
                (msr("Completed Complaints"), "Measure.Completed Complaints", "Completed Complaints"),
                (msr("Average Processing Days"), "Measure.Average Processing Days", "Average Processing Days"),
                (msr("Median Processing Days"), "Measure.Median Processing Days", "Median Processing Days")]},
    {"grid": obj(textSize=lit(9)), "columnHeaders": obj(fontSize=lit(9), bold=lit(True), fontColor=color(NAVY)),
     "rowHeaders": obj(fontSize=lit(9), fontColor=color(INK)), "values": obj(fontSize=lit(9)),
     "subTotals": obj(rowSubtotals=lit(True))},
    panel("Kieu nai x muc do uu tien - completed / TB / trung vi"))

put(P, "pivotTable", CX0, 418, 524, 218,
    {"Rows": (col("Dim_Broker", "DistributionNetwork"), "Dim_Broker.DistributionNetwork", "DistributionNetwork"),
     "Values": [(msr("Total Complaints"), "Measure.Total Complaints", "Total Complaints"),
                (msr("Average Processing Days"), "Measure.Average Processing Days", "Average Processing Days"),
                (msr("SAT Rate"), "Measure.SAT Rate", "SAT Rate"),
                (msr("Evaluated Complaints"), "Measure.Evaluated Complaints", "Evaluated Complaints"),
                (msr("Evaluation Coverage"), "Measure.Evaluation Coverage", "Evaluation Coverage")]},
    {"grid": obj(textSize=lit(9)), "columnHeaders": obj(fontSize=lit(9), bold=lit(True), fontColor=color(NAVY)),
     "rowHeaders": obj(fontSize=lit(9), fontColor=color(INK)), "values": obj(fontSize=lit(9)),
     "subTotals": obj(rowSubtotals=lit(True))},
    panel("Phan bo theo mang phan phoi - total / TB / SAT / coverage"))

put(P, "barChart", CX0 + 548, 418, 524, 218,
    {"Category": (col("Fact_Complaint", "age_bucket"), "Fact_Complaint.age_bucket", "age_bucket"),
     "Y": (msr("Urgent Rate"), "Measure.Urgent Rate", "Urgent Rate"),
     "Tooltips": [(msr("Total Complaints"), "Measure.Total Complaints", "Total Complaints"),
                  (msr("Urgent Complaints"), "Measure.Urgent Complaints", "Urgent Complaints")]},
    {"categoryAxis": axisfmt(), "valueAxis": axisfmt(),
     "dataPoint": obj(defaultColor=color(RED), fill={"solid": {"color": lit(RED)}}),
     "labels": obj(show=lit(True), fontSize=lit(9), fontFamily=lit(FONT), color=color(INK))},
    panel("Ty le uu tien theo nhom tuoi - n va so uu tien o tooltip"))

textbox(P, CX0, 644, 1072, 68, [
    "Ghi chu: (1) 'Co du lieu lich su' chi la ty le khieu nai co it nhat mot su kien trong Fact_StatusHistory "
    "(4.351/13.846 = 31,42%), KHONG phai do phu day du va KHONG cho phep tinh thoi gian o trang thai.",
    "(2) Nhom tuoi 'negative' (491 dong) va 'missing' (193 dong) duoc giu nguyen; nguyen nhan chua chot nen khong gan nhan.",
    "(3) Matrix khong suy nguyen nhan: so sanh mang phan phoi phai doc kem case-mix.",
], 9, MUTE)

# ---------------------------------------------------------------- pages.json
for name, disp in (("execsum01", "Executive Summary"), ("operdrill01", "Operation Drill-down")):
    write(PAGES / name / "page.json",
          {"$schema": SCHEMA_PAGE, "name": name, "displayName": disp, "displayOption": "FitToPage",
           "height": H, "width": W,
           "objects": {"background": obj(color=color(BG), transparency=lit(0))}})

write(PAGES / "pages.json",
      {"$schema": SCHEMA_PAGES, "pageOrder": ["execsum01", "operdrill01"], "activePageName": "execsum01"})

print("visuals:", Z[0])
print("pages: execsum01, operdrill01 (placeholder 'Model only' removed)")
print("WROTE", PAGES)
