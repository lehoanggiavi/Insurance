# Phase 4 — Chỉ số DAX (bảng `Measure`)

> **Đọc dễ hiểu trước:** Bước này tạo 22 công thức để đếm hồ sơ và tính thời gian, đánh giá, mức ưu tiên. Mỗi công thức phải nói rõ đang tính cho nhóm nào và chia cho số nào. Power BI được đối chiếu với phép tính riêng từ dữ liệu đã chuẩn hóa. Kết quả cuối còn được thử lọc và kiểm lại sau đóng/mở dashboard. Phần bên dưới giữ công thức và chi tiết kiểm tra của Phase 4. [Báo cáo cuối](06_project_report.md) và [giải thích DA](07_da_explained.md).

**Marker:** `INSURANCE_PHASE4_DAX_20261006` · Worker: OpenCode · Supervisor: Codex
**Model:** `pbi/InsuranceOps.pbip` → bảng `Measure` (22 chỉ số, 6 folder, **không có relationship**)
**TMDL chuẩn:** `pbi/InsuranceOps.SemanticModel/definition/tables/Measure.tmdl` — SHA-256 `e2a9282f1bb4b090417ea74b382f364a6cdbe9c7c464dfd5f78351519ff89a1a`
**Hiển thị:** bảng `Measure` **hiển thị** (`isHidden=false`) để chọn được trên Desktop; cột khởi tạo `_marker` **ẩn** (`isHidden=true`).

> Expression dưới đây lấy từ `Measure.tmdl` **sau khi Desktop lưu**, đối chiếu với `ExportTMDL` từ model runtime sau khi mở lại. Bằng chứng chạy: `Log/phase4/RUNS.md`.

## 1. Quy ước chung

- **Ngày tiêu chuẩn = ngày tiếp nhận** (`Fact_Complaint[ComplainDate__iso]` → `Dim_Date_Complaint[Date]`), trừ `Completed by Completion Date`.
- **Số đếm → 0 khi cohort rộng** (`COALESCE(..., 0)`). **Trung bình / trung vị / tỷ lệ → BLANK** khi không có mẫu hợp lệ (`DIVIDE` và `AVERAGE`/`MEDIAN` tự trả BLANK; **không** bọc COALESCE cho các chỉ số này).
- **BLANK ≠ 0.** QA kiểm riêng: cohort rộng phải ra 0 cho đếm và BLANK cho tỷ lệ.
- `KEEPFILTERS` cho các nhóm con nên **không ghi đè** bộ lọc của người dùng.
- Tỷ lệ giữ **toàn bộ filter context**; nếu người dùng chỉ chọn SAT thì `SAT Rate` = 100% **của cohort đang lọc**, không phải của toàn bộ.
- Mẫu số của mọi tỷ lệ ghi rõ trong cột *Mẫu số*. **Không cộng hay trung bình các tỷ lệ**; khi tính theo nhóm, tổng luôn tính lại theo mẫu số tổng.

## 2. Registry 22 chỉ số

### Complaints

| Chỉ số | Định nghĩa / filter | Đơn vị | Grain | Mẫu số | Rỗng | Format | Phụ thuộc | Expression |
|---|---|---|---|---|---|---|---|---|
| Total Complaints | DISTINCT ComplaintID trong Fact_Complaint, không đếm history | khiếu nại | Fact_Complaint | — | 0 | `#,0` | — | `COALESCE(DISTINCTCOUNT(Fact_Complaint[ComplaintID]), 0)` |
| Completed Complaints | Total có `CompletionDate__iso` khác rỗng | khiếu nại | Fact_Complaint | Total | 0 | `#,0` | Total | `COALESCE(CALCULATE([Total Complaints], FILTER(Fact_Complaint, NOT ISBLANK(Fact_Complaint[CompletionDate__iso]))), 0)` |
| Uncompleted Complaints | Total − Completed; **không** gọi là backlog lịch sử | khiếu nại | Fact_Complaint | — | 0 | `#,0` | Total, Completed | `[Total Complaints] − [Completed Complaints]` |
| Urgent Complaints | Total với `KEEPFILTERS(Dim_Priority[ID] = 1)`; 1 = Urgent đã kiểm ở lookup | khiếu nại | Fact_Complaint | — | 0 | `#,0` | Total | `COALESCE(CALCULATE([Total Complaints], KEEPFILTERS(Dim_Priority[ID] = 1)), 0)` |
| Urgent Rate | Urgent / Total cùng context | tỷ lệ | Fact_Complaint | **Total** | BLANK | `0.00%` | Urgent, Total | `DIVIDE([Urgent Complaints], [Total Complaints])` |

### Processing

| Chỉ số | Định nghĩa | Đơn vị | Grain | Mẫu số | Rỗng | Format | Phụ thuộc | Expression |
|---|---|---|---|---|---|---|---|---|
| Average Processing Days | Trung bình `processing_days` = **CompletionDate − ComplainDate** của khiếu nại đã hoàn thành; giữ 0 ngày, bỏ null. **KHÔNG phải time-in-status** | ngày | Fact_Complaint | các dòng có processing_days | BLANK | `#,0.00` | — | `AVERAGE(Fact_Complaint[processing_days])` |
| Median Processing Days | Trung vị cùng cohort | ngày | Fact_Complaint | các dòng có processing_days | BLANK | `#,0.00` | — | `MEDIAN(Fact_Complaint[processing_days])` |
| Completed by Completion Date | Completed **theo ngày hoàn tất thay cho ngày tiếp nhận**: `REMOVEFILTERS` bỏ đường ngày tiếp nhận rồi `USERELATIONSHIP` mở quan hệ inactive ngày hoàn tất | khiếu nại | Fact_Complaint | — | 0 | `#,0` | Completed | `COALESCE(CALCULATE([Completed Complaints], REMOVEFILTERS(Fact_Complaint[ComplainDate__iso]), USERELATIONSHIP(Fact_Complaint[CompletionDate__iso], Dim_Date_Complaint[Date])), 0)` |

### Satisfaction

| Chỉ số | Định nghĩa | Đơn vị | Mẫu số | Rỗng | Format | Phụ thuộc | Expression |
|---|---|---|---|---|---|---|---|
| SAT Complaints | Total với `KEEPFILTERS(ClientSatisfaction = "SAT")` | khiếu nại | — | 0 | `#,0` | Total | `COALESCE(CALCULATE([Total Complaints], KEEPFILTERS(Fact_Complaint[ClientSatisfaction] = "SAT")), 0)` |
| NSA Complaints | Total với `"NSA"` | khiếu nại | — | 0 | `#,0` | Total | `COALESCE(CALCULATE([Total Complaints], KEEPFILTERS(Fact_Complaint[ClientSatisfaction] = "NSA")), 0)` |
| Evaluated Complaints | SAT + NSA (đánh giá thực) | khiếu nại | — | 0 | `#,0` | SAT, NSA | `[SAT Complaints] + [NSA Complaints]` |
| Not Evaluated Complaints | Total − Evaluated; gồm N/A, null, giá trị khác | khiếu nại | — | 0 | `#,0` | Total, Evaluated | `[Total Complaints] − [Evaluated Complaints]` |
| SAT Rate | SAT / **Evaluated** (không dùng Total) | tỷ lệ | Evaluated | BLANK | `0.00%` | SAT, Evaluated | `DIVIDE([SAT Complaints], [Evaluated Complaints])` |
| NSA Rate | NSA / Evaluated | tỷ lệ | Evaluated | BLANK | `0.00%` | NSA, Evaluated | `DIVIDE([NSA Complaints], [Evaluated Complaints])` |
| Evaluation Coverage | Evaluated / Total | tỷ lệ | Total | BLANK | `0.00%` | Evaluated, Total | `DIVIDE([Evaluated Complaints], [Total Complaints])` |

### Customers

| Chỉ số | Định nghĩa | Đơn vị | Grain | Mẫu số | Rỗng | Format | Phụ thuộc | Expression |
|---|---|---|---|---|---|---|---|---|
| Customers with Complaints | DISTINCT `CustomerID` trong Fact_Complaint; **không** đếm từ history | khách | Fact_Complaint | — | 0 | `#,0` | — | `COALESCE(DISTINCTCOUNT(Fact_Complaint[CustomerID]), 0)` |
| Source Customers | COUNTROWS(Dim_Customer). **Chịu** bộ lọc địa lý/nhân khẩu ở dimension; **không** bị lọc ngược bởi ngày/sản phẩm/ưu tiên | khách | Dim_Customer | — | 0 | `#,0` | — | `COALESCE(COUNTROWS(Dim_Customer), 0)` |
| Complaints per 1000 Source Customers | Total / Source Customers × 1000. Mẫu số là **khách trong bảng nguồn, KHÔNG phải dân số được bảo hiểm** | ca/1000 khách | — | Source Customers | BLANK | `#,0.00` | Total, Source | `DIVIDE([Total Complaints], [Source Customers]) * 1000` |

### History

| Chỉ số | Định nghĩa | Đơn vị | Grain | Mẫu số | Rỗng | Format | Phụ thuộc | Expression |
|---|---|---|---|---|---|---|---|---|
| Status Events | COUNTROWS(Fact_StatusHistory); lọc ngày event chỉ lọc history | sự kiện | Fact_StatusHistory | — | 0 | `#,0` | — | `COALESCE(COUNTROWS(Fact_StatusHistory), 0)` |
| Complaints with History | DISTINCT ComplaintID trong Fact_StatusHistory | khiếu nại | Fact_StatusHistory | — | 0 | `#,0` | — | `COALESCE(DISTINCTCOUNT(Fact_StatusHistory[ComplaintID]), 0)` |
| History Presence Coverage | CwH / Total. Khi lọc ngày event: sự kiện **trong kỳ đó** / cohort complaint. **KHÔNG chứng minh đủ journey** | tỷ lệ | — | Total | BLANK | `0.00%` | CwH, Total | `DIVIDE([Complaints with History], [Total Complaints])` |

### Time

| Chỉ số | Định nghĩa | Đơn vị | Grain | Rỗng | Format | Phụ thuộc | Expression |
|---|---|---|---|---|---|---|---|
| Complaints YTD | Tích lũy theo năm của `Dim_Date_Complaint` (năm tiếp nhận), giữ filter lookup. Chỉ phục vụ so sánh tích lũy; **YoY/MoM chưa giao** | khiếu nại | Fact_Complaint | 0 | `#,0` | Total | `COALESCE(TOTALYTD([Total Complaints], Dim_Date_Complaint[Date]), 0)` |

**Thứ tự tạo:** Base → Derived → Time. Kiểm dependency: không thiếu, không vòng lặp (mọi measure cơ sở không tham chiếu measure khác; các measure dẫn xuất chỉ trỏ về measure đã có trước đó trong cùng hoặc nhóm trước).

## 3. Kết quả trên model (không lọc)

| Chỉ số | Giá trị |
|---|---:|
| Total Complaints | 13.846 |
| Completed / Uncompleted | 13.796 / 50 |
| Urgent Complaints / Rate | 552 / 3,99% |
| Average / Median Processing Days | 12,85 / 7 |
| SAT / NSA / Evaluated / Not Evaluated | 6.867 / 820 / 7.687 / 6.159 |
| SAT Rate / NSA Rate / Coverage | 89,33% / 10,67% / 55,52% |
| Customers with Complaints / Source Customers | 8.261 / 12.305 |
| Complaints per 1000 | 1.125,23 |
| Status Events / Complaints with History / Coverage | 11.558 / 4.351 / 31,42% |
| Complaints YTD (2020 tới 14/05) | 639 |

## 4. Bằng chứng lọc và biên

**19 cohort, 402 so sánh, 402 PASS** (exit 0). Mười cohort đầu đã có ở gói trước và **không chạy lại** (công thức không đổi, số đã được supervisor đối chiếu); chín cohort dưới đây là phần bổ sung của gói R401–R402. Chi tiết các lượt chạy: `RUNS.md` §5.

### 4.1 Cohort gốc (đã có, không chạy lại)

| Cohort | Filter | Kết quả đáng chú ý |
|---|---|---|
| `all` | không lọc | **21 measure** khớp (không phải 22 — `Complaints YTD` kiểm riêng ở 2 case năm) |
| `type_x_priority` | Type 1 × Urgent (0 bản ghi) | đếm = 0, tỷ lệ/TB = **BLANK**, Source Customers 12.305 |
| `type_x_priority_nonurgent` | Type 1 × Non Urgent (1 bản ghi) | SAT Rate = **100%** của cohort lọc; TB/TV = 0 (0 ngày xử lý) |
| `state_CA` | vùng CA | Total 2.593 · Source Customers **2.279** · CwH 812 |
| `complaint_day_2019-03-20` | ngày tiếp nhận | Total 87 · Completed by Completion Date **65** |
| `completion_day_2011-07-08` | ngày 08/07/2011 | Completed **1** (nhận) vs Completed by Completion Date **0** |
| `event_day_2020-05-15` | ngày event | Total **không đổi** 13.846 · Events 1 |
| `na_only_cohort` | Type 99 (chỉ N/A) | SAT Rate = **BLANK** |
| `year_2019_ytd` | 01/01–31/12/2019 | YTD 3.192 |
| `year_2020_partial_ytd` | 01/01–14/05/2020 | YTD **639** (ký chưa đủ năm) |

### 4.2 Cohort bổ sung R402

| Cohort | Filter | Kết quả đáng chú ý |
|---|---|---|
| `category_59_active` | `Dim_Category.ID=59` | 2.451 khiếu nại · SAT 2.123 · NSA 28 · coverage 87,76% |
| `category_59_ytd_2019-01-04` | Category 59 **+** ngày 01/01–04/01/2019 | YTD **lũy kế từ 01/01** = 2 (không phải chỉ đếm 2 ngày đã chọn); Completed by Completion Date **0** |
| `category_59_completion_2019-01-04` | Category 59 **+** ngày 04/01/2019 | Total 2 (giữ lookup) · Completed by Completion Date **0** |
| `source_1_mean_median` | `Dim_Source.ID=1` | TB **14,32** ngày · TV **8** ngày (khác TB/TV toàn cục) |
| `sat_only_fact_filter` | `TREATAS({"SAT"}, Fact_Complaint[ClientSatisfaction])` — lọc thật trên fact | SAT Rate = **100%** của cohort; NSA = 0 |
| `age_negative_kept` | `age_bucket="negative"` (491 dòng) | **GIỐNG NGuyên 491**, không bị loại |
| `age_missing_kept` | `age_bucket="missing"` (193 dòng) | **GIỐNG NGuyên 193**, không bị loại |
| `event_date_with_lookup` | Category 59 **+** ngày event 15/05/2020 **cùng lúc** | Total giữ 2.451 (lookup còn) · Events **0** (event ngày đó không thuộc category 59) |
| `urgent_with_category` | Urgent **×** Category 59 | 3 khiếu nại · Urgent Rate = 100% của nhóm này |

**Điểm R402 đã sửa và được chứng minh:** trước đây history dùng `if/elif` nên khi lọc ngày event thì **mất** lookup; và `Completed by Completion Date` đọc lại toàn CSV nên **mất** lookup. Nay `event_date_with_lookup` cho thấy lookup còn hiệu lực (Total 2.451) đồng thời ngày event vẫn áp dụng (Events 0); `category_59_completion_2019-01-04` cho thấy lookup còn hiệu lực khi đếm theo ngày hoàn tất (Total 2).

## 5. Giới hạn — chưa chốt

1. **Câu 4 (backlog lịch sử > 30 ngày) và câu 8 (dwell/bottleneck) chưa trả lời.** Cần quy tắc cutoff, xử lý timestamp trùng và censoring. `processing_days` là khoảng giữa hai mốc ngày của một khiếu nại, **không** phải dwell theo trạng thái.
2. **Câu 5 chỉ có `Source Customers`** — khách trong bảng nguồn, **không** phải dân số được bảo hiểm. Không suy rủi ro bảo hiểm.
3. **Câu 6 `ExpectedReimbursement` chưa có currency/đã chi** → **không** có chỉ số tiền nào.
4. **Câu 10 dùng `age_bucket` sẵn có**; người tuổi âm (491) và thiếu ngày sinh (193) **không** bị loại.
5. **`Complaints YTD` chỉ phục vụ so sánh tích lũy.** Chưa có YoY/MoM vì chưa có yêu cầu so sánh kỳ và chính sách kỳ.
6. **Biên ngày không đủ tròn năm:** 08/07/2011–14/05/2020. Không suy tháng không có bản ghi là mất dữ liệu.
7. **`History Presence Coverage` không chứng minh journey đầy đủ** — chỉ là có ≥1 event.
8. **`Source Customers` co theo lọc địa lý** (CA → 2.279). Đây là hành vi đúng hợp đồng nhưng dễ gây nhầm khi đọc tỷ lệ `per 1000` giữa các vùng.

## 6. Cách thêm/sửa chỉ số

```powershell
# ghi trực tiếp qua Modeling MCP vào model đang mở, rồi lưu trong Desktop
python -X utf8 Log\phase4\04_check_measures.py prepare   # dựng expected độc lập
python -X utf8 Log\phase4\04_check_measures.py verify    # actual exit 0 khi khớp
```

**Không** sửa `Measure.tmdl` trên đĩa khi Desktop đang giữ revision khác. Folder hiển thị lấy từ `displayFolder`; không thêm relationship cho bảng `Measure`.

## 7. Bước tiếp theo

Supervisor review → **Gate 4**. Dashboard là **Phase 5**, chưa được giao và chưa dựng. Cần chốt các quyết định §5 trước khi viết biểu đồ.