"""Dàn lại layout 2 trang + nav panel theo anh mau (rail pill + bo loc).
GHI DE truc tiep JSON hien co => GIU NGUYEN chinh sua tay cua nguoi dung (areaChart, bo tieu de phu...).
Khong goi generator 05 de khong xoa noi dung da sua.
"""
import json, os, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "pbi" / "InsuranceOps.Report" / "definition" / "pages"
SCHEMA_VIS = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json"

RAIL_W = 168
CX, CW = 180, 1092
RAIL_BG = "#2E2019"
PILL_SEL = "#D2622A"
PILL_BG = "#3B2B22"
ORANGE = "#D2622A"
LIGHT = "#F4EDE7"
SUBTLE = "#C0AA9B"
WHITE = "#FFFFFF"

Z = [0]


def lit(v):
    if isinstance(v, bool):
        return {"Literal": {"Value": "true" if v else "false"}}
    if isinstance(v, int):
        return {"Literal": {"Value": f"{v}L"}}
    return {"Literal": {"Value": "'" + str(v).replace("'", "''") + "'"}}


def color(h):
    return {"solid": {"color": lit(h)}}


def obj(**p):
    return [{"properties": p}]


def rd(p):
    return json.loads(p.read_text(encoding="utf-8"))


def wr(p, j):
    p.parent.mkdir(parents=True, exist_ok=True)
    t = p.with_suffix(p.suffix + ".tmp")
    t.write_text(json.dumps(j, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(t, p)


def new_visual(vt, x, y, w, h, vco, objects=None):
    Z[0] += 1
    vid = f"n{Z[0]:03d}rail" + ("000" if vt == "cardVisual" else vt[:3].lower())
    return vid, {
        "$schema": SCHEMA_VIS,
        "name": vid,
        "position": {"x": x, "y": y, "width": w, "height": h, "z": Z[0], "tabOrder": Z[0]},
        "visual": {"visualType": vt, "objects": objects or {}, "visualContainerObjects": vco},
    }


def panel(bg, border=None, radius=None, pad=6):
    v = {"background": obj(show=True, color=color(bg), transparency=lit(0)),
         "padding": obj(top=lit(pad), bottom=lit(pad), left=lit(pad), right=lit(pad)),
         "title": obj(show=False)}
    if border:
        v["border"] = obj(show=True, color=color(border), radius=lit(radius or 8))
    else:
        v["border"] = obj(show=False)
    return v


def textbox(page, x, y, w, h, runs, size, c, bold=True, align="left"):
    if isinstance(runs, str):
        runs = [runs]
    vid, v = new_visual("textbox", x, y, w, h,
                         {"background": obj(show=False), "border": obj(show=False), "title": obj(show=False),
                          "padding": obj(top=lit(0), bottom=lit(0), left=lit(0), right=lit(0))})
    v["visual"]["objects"] = {"general": [{"properties": {"paragraphs": [
        {"textRuns": [{"value": t, "textStyle": {"fontSize": f"{sz}pt", "fontFamily": "Segoe UI", "color": cc,
                                                  "fontWeight": "bold" if bb else "normal"}}],
         "horizontalTextAlignment": align} for t, sz, cc, bb in runs]}}]}
    wr(PAGES / page / "visuals" / vid / "visual.json", v)


def solid(page, x, y, w, h, bg):
    """Khoi mau: cardVisual rong - visualContainerObjects.background co duoc to mau nen."""
    vid, v = new_visual("cardVisual", x, y, w, h, panel(bg, pad=0))
    wr(PAGES / page / "visuals" / vid / "visual.json", v)
    return vid


PAGES_SPEC = {
    "execsum01": {
        "title": "Insurance Complaints - Executive Summary",
        "subtitle": "Kieu nai theo ngay tiep nhan  ·  Nam / Vung / Muc do uu tien loc o thanh ben trai  ·  KHONG phai muc tieu da chot",
        "filters": [("Dim_Date_Complaint", "Year", "Year", "Nam tiep nhan"),
                    ("Dim_StateRegion", "'State Code__source'", "State Code__source", "Vung / State"),
                    ("Dim_Priority", "Description", "Description", "Muc do uu tien")],
        "footnote": ["Ghi chu: chi so khong danh gia - du lieu quan sat, khong phai muc tieu da chot. Chi 7.687/13.846 co danh gia SAT/NSA (55,52%).",
                     "50 khieu nai chua co CompletionDate va 21 dong IN PROGRESS/OUTSTANDING: KHONG phai backlog theo thoi diem. 'Khach trong file nguon' KHONG phai nguoi duoc bao hiem."],
    },
    "operdrill01": {
        "title": "Insurance Complaints - Operation Drill-down",
        "subtitle": "Chi tiet xu ly va phan bo  ·  Cac bo loc o thanh ben trai chi ap dung cho trang nay",
        "filters": [("Dim_Date_Complaint", "Year", "Year", "Nam tiep nhan"),
                    ("Dim_Category", "Description", "Description", "Nhom khieu nai"),
                    ("Dim_Source", "Description", "Description", "Nguon")],
        "footnote": ["'Co du lieu lich su' = ty le khieu nai co it nhat mot su kien trong Fact_StatusHistory (4.351/13.846 = 31,42%); KHONG cho phep tinh thoi gian o trang thai.",
                     "Nhom tuoi 'negative' (491 dong) va 'missing' (193 dong) duoc giu nguyen; nguyen nhan chua chot nen khong gan nhan. Matrix khong suy nguyen nhan."],
    },
}

PILLS = [("Executive Summary", True), ("Operation Drill-down", False)]

for page, cfg in PAGES_SPEC.items():
    d = PAGES / page / "visuals"
    # 1) don visual do nguoi dung sua: chi chinh position, giu nguyen noi dung
    keep = []
    for f in sorted(d.glob("*/visual.json")):
        j = rd(f)
        vt = j.get("visual", {}).get("visualType")
        p = j["position"]
        if vt == "cardVisual" and p["x"] >= CX:
            p["y"], p["h"] = 58, 96                      # hang KPI
            p["x"] = CX + keep.count("card") * 212
            p["width"] = 204
            keep.append("card")
        elif vt in ("barChart", "areaChart", "lineChart", "pivotTable"):
            keep.append("chart")
            idx = [k for k in keep if k == "chart"].index("chart")
            col, row = (0 if idx % 2 == 0 else 1), (0 if idx < 2 else 1)
            p["x"], p["y"] = CX + col * 552, 166 + row * 260
            p["width"], p["height"] = 540, 248
        elif vt == "textbox":
            # textbox tieu de chinh: giu, dua len; con lai (chu thich) an di
            if p["x"] >= CX:
                p["x"], p["y"], p["width"], p["height"] = CX, 2, CW, 48
            else:
                try:
                    f.unlink()
                    f.parent.rmdir()
                except OSError:
                    pass
                continue
        elif vt == "slicer":
            p["x"], p["width"] = 12, RAIL_W - 24
        wr(f, j)

    # 2) rail: nen toi + 2 pill + nhan + 3 slicer
    solid(page, 0, 0, RAIL_W, 720, RAIL_BG)
    solid(page, 14, 74, RAIL_W - 28, 30, PILL_SEL)        # pill trang hien tai
    solid(page, 14, 110, RAIL_W - 28, 30, PILL_BG)        # pill trang kia
    textbox(page, 22, 79, RAIL_W - 44, 20, [(PILLS[0][0], 9, WHITE, True)], 9, WHITE)
    textbox(page, 22, 115, RAIL_W - 44, 20, [(PILLS[1][0], 9, SUBTLE, False)], 9, SUBTLE)
    textbox(page, 16, 20, RAIL_W - 32, 20, [("INSURANCE", 10, LIGHT, True)], 10, LIGHT)
    textbox(page, 16, 38, RAIL_W - 32, 20, [("COMPLAINTS", 10, LIGHT, True)], 10, LIGHT)
    textbox(page, 14, 152, RAIL_W - 28, 18, [("BO LOC", 9, ORANGE, True)], 9, ORANGE)

    # gan lai slicer theo thu tu khai bao: Year / State|Category / Priority|Source
    sl = sorted([rd(f) for f in d.glob("*/visual.json")
                 if rd(f).get("visual", {}).get("visualType") == "slicer"],
                key=lambda j: j["position"]["y"])
    ys = [168, 300, 432]
    hs = [124, 124, 100]
    for j, y, h in zip(sl, ys, hs):
        j["position"]["y"], j["position"]["height"] = y, h
        j["position"]["x"], j["position"]["width"] = 12, RAIL_W - 24
        vco = j["visual"].setdefault("visualContainerObjects", {})
        vco["background"] = obj(show=True, color=color(WHITE), transparency=lit(0))
        vco["border"] = obj(show=True, color=color("#D9CCC3"), radius=lit(6))
        objs = j["visual"].setdefault("objects", {})
        objs["header"] = obj(show=True, text=lit(cfg["filters"][min(len(ys), 3) - 1][3]),
                             textSize=lit(9), fontFamily=lit("Segoe UI"),
                             fontColor=color("#5B4A40"), bold=lit(True),
                             background=color(WHITE))
        objs["items"] = obj(textSize=lit(9), fontColor=color("#2A2320"))
        wr(d / j["name"] / "visual.json", j)

    # 3) tieu de + phu de + chu thich
    textbox(page, CX, 2, CW, 48, [(cfg["title"], 20, "#183153", True)], 20, "#183153")
    textbox(page, CX, 50, CW, 30, [(cfg["subtitle"], 10, "#5B6472", False)], 10, "#5B6472")
    textbox(page, CX, 690, CW, 28, [(t, 9, "#5B6472", False) for t in cfg["footnote"]], 9, "#5B6472")

print("relayout done:", ", ".join(PAGES_SPEC))