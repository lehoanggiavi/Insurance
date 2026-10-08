# 01 — Data Understanding (Insurance Complaints)

Phase 1, ngày 2026-10-05. Worker: OpenCode. Supervisor: Codex.
Revision: sau gói sửa EDA v2 (trailing-missing, literal NULL, cohort 0 ngày, sort+ambiguous history) và notebook 13 mục. Số liệu dưới đây lấy từ `profile_phase1.json` SHA-256 `b4f64ddb…`; mục 3 và 4 của bản trước đã được sửa theo các đính chính ở §5.1.
Nguồn: `data/insurance_complain.xlsx` — SHA-256 `3ace06421c1a8d146b0bfa6b9f08a2ae367bf32ead212182cb84b3d5af159032`, đọc read-only, không thay đổi trong lúc chạy.
Đề bài: `data/Đề bài.docx` — SHA-256 `bcbc2d395d0e597ab5e767a47d48399594f4aa8d24dd311f0dccfc54ed27597c`, đã đọc ở Phase 0, không sửa.

Tái lập:

```text
python scripts\01_profile_insurance.py --xlsx data\insurance_complain.xlsx --outdir reports\profile --baseline-xlsx-sha256 3ace06...
python logs\phase1\investigate_phase1.py
python logs\phase1\crosscheck_phase1.py
python scripts\01_profile_insurance.py ...  # revision sua chay lai, exit 0
python Log\phase1\check_phase1_fixes.py   # 56 assert logic/aggregate, exit 0
```

Bằng chứng đầy đủ: `logs/phase1/RUNS.md`. Số liệu dưới đây lấy từ `reports/profile/profile_phase1.json`, `investigation_phase1.json`, `crosscheck_phase1.json`.

**Đối chiếu độc lập: 24/24 mục khớp** (`crosscheck_phase1.json.comparison` có 24 entry; văn bản revision trước ghi 23 là sai — xem HISTORY L04). Toàn bộ số đếm quan trọng được đọc lại bằng cách parse thẳng `xl/worksheets/*.xml` (không qua openpyxl). Không assert nào fail; 13 assert nội bộ PASS.

> Cảnh báo đã được chứng minh bằng số liệu: `max_row`/`max_column` của mọi sheet trả `None`, và các sheet dimension có tới 1.000 `<row>` XML chỉ mang thuộc tích hiển thị. Nếu đếm bằng dimension sẽ ra sai từ 2 lần trở lên (ví dụ Priorities: 999 dòng thật ra chỉ 2 bản ghi).

---

## 1. Quy mô và grain

| Sheet | Vai trò | Grain | Số bản ghi thật | Khoá duy nhất | Trùng khoá |
|---|---|---|---:|---|---:|
| `Complains Data` | fact sự kiện | 1 dòng = 1 complaint | 13.846 | `ID` (13.846 distinct) | 0 |
| `Status History Data` | fact sự kiện | 1 dòng = 1 sự kiện trạng thái | 11.558 | `ID` (11.558 distinct) | 0 |
| `Customers` | dimension | 1 dòng = 1 khách hàng | 12.305 | `CustomerID` | 0 |
| `Brokers` | dimension | 1 dòng = 1 môi giới | 707 | `BrokerID` | 0 |
| `Products` | dimension | 1 dòng = 1 sản phẩm | 77 | `ProductID` | 0 |
| `Regions` | dimension | 1 dòng = 1 vùng địa lý | 994 | `id` | 0 |
| `State Regions` | dimension | 1 dòng = 1 bang | 48 | `State Code` | 0 |
| `Categories` | dimension | 1 dòng = 1 loại khiếu nại | 56 | `ID` | 0 |
| `Types` | dimension | 1 dòng = 1 hình thức khiếu nại | 10 | `ID` | 0 |
| `Sources` | dimension | 1 dòng = 1 kênh tiếp nhận | 9 | `ID` | 0 |
| `Statuses` | dimension | 1 dòng = 1 trạng thái | 7 | `ID` | 0 |
| `Priorities` | dimension | 1 dòng = 1 mức ưu tiên | 2 | `ID` | 0 |

Tổng 39.619 bản ghi. Grain dự kiến trong PLAN đã được kiểm chứng: một complaint = một dòng fact complaints; một sự kiện trạng thái = một dòng history. Không có khoá trùng ở bất kỳ bảng nào.

**Cảnh báo quan trọng về history:** chỉ **4.351 complaint (31,42%)** có history; **9.495 complaint không có dòng history nào**. History không phải bản ghi đầy đủ của mọi complaint, nên không thể dùng nó làm nguồn duy nhất cho câu hỏi 4 và 8. Phân bố theo trạng thái: trong 13.796 complaint `CLOSED`, 4.301 có history và 9.495 không có; còn 50 complaint đang mở (`NEW`, `IN PROGRESS`, `ASSIGNED TO`, `OUTSTANDING`) thì có history đủ 50/50. Có thể hệ thống chỉ ghi history từ một mốc thời gian nào đó (StatusDate chỉ trong 2018-09-04 → 2020-05-15, trong khi complaint từ 2011).

## 2. Data dictionary

### 2.1 `Complains Data` (13.846 dòng) — fact

| Cột | Kiểu | Null | Distinct | Khoảng giá trị | Nhận xét |
|---|---|---:|---:|---|---|
| `ID` | số (float) | 0 | 13.846 | 7 → 14.575 | Khoá, liên tục lỗ hổng |
| `ComplainDate` | datetime | 0 | 2.156 | 2011-07-08 → 2020-05-14 | Mốc thời gian sự kiện |
| `CompletionDate` | datetime + **50 ô chữ `"NULL"`** | 0 | 2.099 | 2011-07-22 → 2020-05-14 | **Kiểu trộn — xem mục 3.1** |
| `CustomerID` | số | 0 | 8.261 | 18 → 2.581.366 | FK → `Customers` |
| `BrokerID` | số | 0 | 707 | 2 → 12.769 | FK → `Brokers` |
| `ProductID` | số | 0 | 77 | 1 → 78 | FK → `Products` |
| `ComplainPriorityID` | số | 0 | 2 | 1 → 2 | FK → `Priorities` |
| `ComplainTypeID` | số | 0 | 10 | 1 → **99** | FK → `Types` — có ID 99 vượt xa |
| `ComplainSourceID` | số | 0 | 9 | 1 → 9 | FK → `Sources` |
| `ComplainCategoryID` | số | 0 | 54 | 1 → **999** | FK → `Categories` — có ID 999 vượt xa |
| `ComplainStatusID` | số | 0 | 5 | 1 → 9 | FK → `Statuses` |
| `AdministratorID` | số + **172 ô chữ `"NULL"`** | 0 | 9 | 13 → 98 | **Kiểu trộn; không có dimension Administrator** |
| `ClientSatisfaction` | chuỗi | 0 | 3 | `SAT` / `NSA` / `N/A` | Không có ô rỗng; `N/A` là giá trị chữ |
| `ExpectedReimbursement` | số | 0 | 14 | 0 → 15.000,74 | 13.833 giá trị bằng 0; không có currency |

### 2.2 `Status History Data` (11.558 dòng) — fact

| Cột | Kiểu | Null | Distinct | Khoảng giá trị | Nhận xét |
|---|---|---:|---:|---|---|
| `ID` | số | 0 | 11.558 | — | Khoá sự kiện |
| `ComplaintID` | số | 0 | 4.351 | — | FK → `Complains Data.ID` |
| `ComplaintStatusID` | số | 0 | 6 | — | FK → `Statuses.ID` |
| `StatusDate` | datetime | 0 | 423 | 2018-09-04 → 2020-05-15 | Khoảng hẹp hơn nhiều so với `ComplainDate` |

### 2.3 Dimension

**`Customers` (12.305)** — `CustomerID` (khoá), `LastName` (383 distinct, không null), `FirstName` (250 distinct, **183 null**), `BirthDate` (8.863 distinct, **184 null**, 1934 → 2019), `Gender` (**184 null**, 2 giá trị), `ParticipantType` (2 giá trị), `RegionID` (FK, 0 null, 0 orphan), `MaritalStatus` (3 giá trị).

**`Brokers` (707)** — `BrokerID`, `BrokerCode`, `BrokerFullName`, `DistributionNetwork` (3: Direct 369, Brokers 241, Bancassurance 97), `DistributionChannel` (9), `CommissionScheme` (10). Không null ở mọi cột.

**`Products` (77)** — `ProductID`, `ProductCategory` (9: Capital Accumulation 29, Business 15, Health 15, Motor 5, Life 5, Property 3, Mortgaged 3, Family Protection 1, Other 1), `ProductSubCategory` (13), `Product`.

**`Regions` (994)** — `id`, `name` (923 distinct → **tên vùng trùng lặp**), `county`, `state_code` (48), `state` (48), `type` (12), `latitude`, `longitude` (toàn bộ âm vì nước Mỹ — không phải lỗi), `area_code` (220), `population` (50.138 → 8.550.405), `households` (1 giá trị 0), `median_income` (2 giá trị 0), `land_area`, `water_area` (53 giá trị 0), `time_zone` (10).
⚠️ Sheet này có **11 cột header rỗng** ở vị trí 15–25 nhưng **dữ liệu chỉ nằm ở 15 cột đầu (index 0–14), không cột nào trong 11 cột đó có giá trị**. Đây là kết quả audit: cột thừa hoàn toàn trống, loại bỏ được, không mất thông tin.

**`State Regions` (48)** — `State Code`, `State`, `Region` (4 vùng: dùng cho câu hỏi địa lý). Tương tự có **23 cột header rỗng**, tất cả đều trống hoàn toàn.

**`Categories` (56)** — `ID` (**1 → 66 và 999**), `Description` (dài tối đa 79 ký tự, ví dụ `CONTRACT NOTICE (USE OR FAITH)`), `Active` (49 giá trị 1, **7 giá trị 0**).

**`Types` (10)** — `ID` (**1 → 9 và 99**), `Description`.

**`Sources` (9)** — `ID` 1–9, `Description` (Bank Branch, Tele, ...).

**`Statuses` (7)** — `ID` → `Description`: `1=OUTSTANDING`, `2=NEW`, `3=IN PROGRESS`, `4=ASSIGNED TO`, `5=RESOLVED`, `6=PENDING`, `9=CLOSED`. Thiếu 7, 8 — ID không liên tục.

**`Priorities` (2)** — `1=Urgent`, `2=Non Urgent`.

## 3. Đánh giá chất lượng dữ liệu

Toàn bộ số dưới đây là **quan sát từ dữ liệu**, chưa phải kết luận nguyên nhân. Không có ngoại lệ nào bị tự sửa.

### 3.1 Vấn đề MỨC CAO: chữ `"NULL"` được lưu thành giá trị thật

| Cột | Số ô chữ `"NULL"` | Hệ quả nếu không xử lý |
|---|---:|---|
| `Complains Data.CompletionDate` | **50** | 50 complaint đang mở bị coi là **đã hoàn tất**, thời gian xử lý tính ra 0 ngày thay vì chưa có |
| `Complains Data.AdministratorID` | **172** | 172 complaint gán sai người xử lý |
| `Customers.BirthDate` | *(ô trống thật, 184)* | khác hợp lệ |

Cả 50 ô `CompletionDate` chữ đều đúng bằng 50 complaint có trạng thái `NEW` (13), `IN PROGRESS` (13), `ASSIGNED TO` (16), `OUTSTANDING` (8) — tức đúng nhóm chưa xử lý xong. Chúng **không parse được** thành ngày (độ dài 4, không đúng định dạng). Không được âm thầm coi là 0 hay là 1/1/1900.

### 3.2 Vấn đề MỨC CAO: tuổi tính được không đáng tin ở một phần dòng

Tính tuổi tại ngày khiếu nại trên 13.162 complaint có dữ liệu:

| Cohort (tính tại ngày khiếu nại) | Số complaint | Nhận xét |
|---|---:|---|
| **≥ 18 tuổi** | **10.438** | Nhóm phân tích nhân khẩu học hợp lệ. **Thống kê trung vị 37 / p95 = 58 / max 85 thuộc cohort profile tuổi ≥ 0 (n = 13.162), không phải số đã tính riêng cho nhóm ≥ 18** |
| 1–17 tuổi | 2.518 | **Nhóm có thật trong dữ liệu, không tự động coi là lỗi** — cần xác nhận (khách vị thành niên đại diện?) |
| Tuổi 0 | 206 | Cần xác nhận lỗi nhập liệu hay nghiệp vụ |
| **Tuổi âm** (ngày khiếu nại **trước** ngày sinh) | **491** | **Dữ liệu không nhất quán, không dùng được** |
| Thiếu/sai BirthDate | 193 | Tách riêng, không điền |
| **Tổng ≥ 1 tuổi** | **12.956** | 10.438 + 2.518. **Không** phải nhóm ≥ 18 |
| Tổng kiểm | 10.438 + 2.518 + 206 + 491 + 193 = 13.846 | Khớp tổng complaint |

Năm sinh cao nhất trong dữ liệu là 2019, tức có khách sinh năm 2019 lại có complaint năm 2011. **Chỉ nhóm tuổi âm mới là dữ liệu không nhất quán** và phải tách riêng. Nhóm 1–17 tuổi (2.518 ca) và 0 tuổi (206 ca) là **nhóm có thật trong dữ liệu, chưa tự động là lỗi** — cần người dùng xác nhận trước khi suy ra nhóm nhân khẩu học.

### 3.3 Vấn đề MỨC TRUNG BÌNH: ID vượt khỏi phạm vi dimension

| Hiện tượng | Chi tiết |
|---|---|
| `Categories.ID` không liên tục | 56 dòng nhưng ID chạy 1–66 **và 999**; thiếu 11 số trong khoảng (22, 24, 26, 28, 30, 39, 41, 43, 48, 49, 51) |
| `Types.ID` | 10 dòng, ID 1–9 và **99**, thiếu 10 |
| `Statuses.ID` | 7 dòng, ID 1–6 và 9, thiếu 7, 8 |
| Complaint dùng ID ngoài dải 1–N | `ComplainCategoryID` có giá trị tới 999; `ComplainTypeID` có giá trị 99 |

Tin tốt: **FK integrity hoàn hảo — 0 orphan ở cả 8 đường join**, kể cả ID 999 và 99. Tức là các ID "lạ" đều tồn tại thật trong dimension, chỉ là không tuần tự. Không được suy ra ID = số thứ tự dòng.

### 3.4 Vấn đề MỨC TRUNG BÌNH: độ phủ đánh giá satisfaction chỉ 55,52%

| Giá trị | Số complaint | Tỷ lệ trên 13.846 |
|---|---:|---:|
| `SAT` | 6.867 | 49,62% |
| `NSA` | 820 | 5,92% |
| `N/A` | 6.159 | 44,48% |
| Rỗng | 0 | 0% |

**Chỉ 7.687 complaint (55,52%) có đánh giá.** Trong nhóm có đánh giá: SAT = 89,33%, NSA = 10,67%. Con số 89,33% **không được trình bày như tỷ lệ của toàn bộ complaint**; phải luôn kèm coverage 55,52%.

Phân bố theo trạng thái (đã đối chiếu):

| Trạng thái | SAT | NSA | N/A | Tổng |
|---|---:|---:|---:|---:|
| `CLOSED` | **6.856** | 820 | 6.120 | 13.796 |
| `NEW` | **11** | 0 | 2 | 13 |
| `IN PROGRESS` | 0 | 0 | 13 | 13 |
| `ASSIGNED TO` | 0 | 0 | 16 | 16 |
| `OUTSTANDING` | 0 | 0 | 8 | 8 |
| **Tổng** | **6.867** | 820 | 6.159 | 13.846 |

**Đính chính quan trọng:** nhóm chưa đóng **không phải toàn bộ là `N/A`** — 11 ca `NEW` đã có điểm SAT. Quy trình chấm **không chỉ xảy ra sau khi đóng**; tỷ lệ đánh giá thay đổi theo thời điểm xử lý nên phân tích SAT theo phân khúc phải kèm coverage của nhóm đó.

### 3.5 Vấn đề MỨC CAO: history không đủ dùng cho phân tích hành trình

| Kiểm tra | Kết quả |
|---|---|
| Coverage toàn population | 4.351/13.846 = **31,42%** |
| Coverage nhóm `CLOSED` | 4.301/13.796 = **31,18%** |
| Coverage nhóm chưa đóng 50 ca | **50/50 = 100%** |
| Thiếu history | **9.495** ca |
| Khoảng `StatusDate` | 2018-09-04 → 2020-05-15, trong khi `ComplainDate` từ 2011 |
| Complaint có nhiều hơn một trạng thái | 4.323 |
| Complaint chỉ có một trạng thái duy nhất | 28 |
| Sự kiện trùng `StatusDate` | **1.552 complaint** có timestamp trùng |
| Trong đó **cùng timestamp nhưng khác trạng thái** | **1.552** — tức gần như toàn bộ |
| Thứ tự sự kiện không theo thời gian trong sheet | 4 complaint |
| `StatusDate` trước `ComplainDate` | **152 sự kiện** |
| Trạng thái cuối tại cutoff **xác định** | **3.314** |
| Trạng thái cuối **mơ hồ (tie)** — nhiều trạng thái cùng timestamp max | **1.037** — **tỷ lệ 23,83% trên mẫu số riêng là 4.351 ca có history**, không phải 13.846 |
| Tổng đối chiếu | 3.314 + 1.037 = 4.351 = đúng số complaint có history ≤ cutoff |
| Cặp liên tiếp cùng timestamp (gap = 0) bị loại khỏi dwell | **1.832** — tất cả đều khác trạng thái |
| **Inter-event gap dương quan sát được** (gap > 0) | **n = 5.375**, trung vị 3 ngày, p90 = 14, max 142 |

Hệ quả: **không thể dựng hành trình tuyến tính cho toàn bộ tập dữ liệu**, và không được tự chọn ID hay thứ tự lưu làm tie-break. Đính chính quan trọng: 1.037 là **ambiguity do timestamp trùng**, không phải mâu thuẫn trạng thái.

Hai đại lượng được báo cáo đều là **observed**, không phải dwell theo trạng thái: **inter-event gap** (khoảng dương giữa hai event liên tiếp sau sort, loại cặp cùng timestamp) và **observed span** (khoảng event đầu → event cuối). **Không có censoring nào được tính.**

**Giới hạn quan trọng:** coverage 100% ở nhóm 50 ca chưa đóng **không chứng minh lịch sử đầy đủ** — nó chỉ nói các ca đó có event ≤ cutoff. 4.351 ca có history vẫn có 1.037 ca latest ambiguous. Xem notebook Q9 và Q13.

### 3.6 Thời gian xử lý

| Chỉ số | Giá trị |
|---|---|
| Complaint có `CompletionDate` thật | 13.796 (`CLOSED`) |
| Complaint có `"NULL"` | 50 (đang mở) |
| Ngày âm (CompletionDate trước ComplainDate) | **0** |
| Hoàn tất trong 0 ngày | **1.899** — toàn bộ ở trạng thái `CLOSED` |
| Có ngày > 0 | 11.897 |
| **Baseline** (mọi cặp ngày hợp lệ, delta ≥ 0, **gồm 0 ngày**) | n = 13.796 |
| Baseline: trung vị / p25 / p75 / p90 / p99 / max | **7,0** / 1 / 18 / 35 / 75 / 222 ngày |
| Baseline: trung bình | 12,85 ngày |
| **Positive-only** (delta > 0, nhãn riêng để so sánh) | n = 11.897; trung vị 8,0; trung bình 14,90; p90 38 |
| Complaint trạng thái mở có **ngày hoàn tất thật** | **0** |
| Complaint trạng thái mở mang chữ `"NULL"` | 50 (gồm 21 `OUTSTANDING`/`IN PROGRESS`) |
| Median baseline vs positive-only | **7,0** vs **8,0** — khác nhau chính vì 0 ngày được giữ |

1.899 complaint "0 ngày" là câu hỏi nghiệp vụ thật, không phải lỗi: có thể xử lý trong ngày, có thể CompletionDate bị ghi bằng ngày nhận. **Baseline giữ 0 ngày**; positive-only tách riêng có nhãn để so sánh. **Chưa có quy tắc nào được duyệt để loại 0 ngày** — cần người dùng chốt ở Gate 1, và giữ cả hai cohort cho tới lúc đó.
Đính chính so với revision trước: câu "21 complaint đang mở nhưng đã có ngày hoàn tất" là **sai** — 21 là số `OUTSTANDING`/`IN PROGRESS` mang chữ `"NULL"`, không có complaint mở nào có ngày thật (`open_status_with_real_completion_date = 0`).

### 3.7 `ExpectedReimbursement` — gần như không có thông tin

| Chỉ số | Giá trị |
|---|---:|
| Số complaint có giá trị khác 0 | **13** trên 13.846 (0,09%) |
| Giá trị 0 | 13.833 |
| Số âm | 0 |
| Giá trị khác 0: min / trung vị / max | 14,37 / 1.000 / 15.000,74 |
| Tổng 13 giá trị khác 0 | 35.379,26 |
| Currency trong nguồn | **không có** |

Phân bố tổng hợp: 13 ca đều `CLOSED`; 7 `SAT` / 6 `N/A` / 0 `NSA`; theo category tập trung 66 (6 ca) và 50 (3 ca); **3 giá trị lớn nhất chiếm 70,66% tổng** — trung bình không đại diện.

Hệ quả: với 13 quan sát không rời nhau, cột này **đủ để mô tả phạm vi nhưng không đủ cho suy luận tương quan** ở câu hỏi 6. Cần chốt: currency, ý nghĩa "expected" (yêu cầu hay kỳ vọng?), và có cột đã chi trả ở đâu không. Cũng không nên suy ra mối liên hệ giữa tiền và SAT khi 99,91% giá trị bằng 0.

### 3.8 Toàn bộ complaint gần như đã đóng

| Trạng thái | Số complaint | Tỷ lệ |
|---|---:|---:|
| `CLOSED` | 13.796 | 99,64% |
| `ASSIGNED TO` | 16 | 0,12% |
| `NEW` | 13 | 0,09% |
| `IN PROGRESS` | 13 | 0,09% |
| `OUTSTANDING` | 8 | 0,06% |
| `RESOLVED`, `PENDING` | 0 | 0% |

**Cần tách hai đại lượng, chúng cho kết luận khác nhau:**

| Đại lượng (cutoff 14/05/2020) | Giá trị | Ý nghĩa |
|---|---:|---|
| Cohort lấy từ **trạng thái fact** (`OUTSTANDING`+`IN PROGRESS`) | 21 ca | **Chưa xác minh** là state tại cutoff (có 4 ca latest ambiguous) |
| **Complaint age** > 30 ngày | **2 ca** | `cutoff − ComplainDate` — đo tuổi complaint, không phải thời gian ở trạng thái |
| **Days since last observed event** | max 28 ngày; **0 ca > 30** | `cutoff − ngày event cuối ≤ cutoff` — **proxy**, không phải time-in-status |

Hệ quả: **chưa có bằng chứng backlog > 30 ngày trong nguồn này.** Ngày 14/05/2020 là **ngày tham chiếu phân tích do chọn** (max `ComplainDate`/`CompletionDate`), **không phải ngày chụp hệ thống đã xác nhận** — quét toàn văn đề và metadata không tìm thấy quy định snapshot. Có đúng **1** event `StatusDate` ngày 15/05/2020 nằm sau cutoff và bị loại. Không tự chọn tie-break, không tự chốt ngày snapshot; cần người dùng xác nhận trước khi xây KPI.

### 3.9 Mẫu số khách hàng: giới hạn nghiêm trọng

- `Customers` có 12.305 dòng; 8.261 khách có ít nhất một complaint; **4.044 khách (32,86%) không có complaint nào** (tính lại và xác nhận ở notebook Q6/Q10).
- Complaint trên mỗi 1.000 khách = **1.125,23** nếu lấy 12.305 làm mẫu số.
- Tỷ lệ khách không có complaint = **4.044/12.305 = 32,86%**. Con số này **vô nghĩa nếu 12.305 chỉ là những người từng khiếu nại**: khi đó mẫu số và tử số cùng lấy từ một tập khiếu nại, và tỷ lệ sẽ luôn dồn về cao.
- Không có bảng policy, hợp đồng, hay exposed customer nào trong workbook. Vì vậy câu hỏi 5 và 9 (địa lý trên 1.000 khách, hotspot theo sản phẩm) **chưa có mẫu số exposure đúng**. Có thể dùng `population` của Regions làm mẫu số thay thế, nhưng đó là dân số dân cư, không phải khách hàng bảo hiểm — phải nêu rõ giới hạn khi trình bày.
- Đường join địa lý chạy trọn vẹn: `Customers.RegionID` → `Regions.id` → `Regions.state_code` → `State Regions`. 0 orphan, 48/48 bang có mặt, complaint phân bố đủ 48 bang.

### 3.10 Phân bố và kiểm tra khác

| Kiểm tra | Kết quả |
|---|---|
| `AdministratorID` | **8 mã số** (98: 7.522, 16: 3.673, 42: 1.205, 85: 785, 13: 287, 50: 149, 81: 52, 24: 1) + **172 ô chữ `NULL`**. **Không có bảng danh mục** → không gán tên hay đánh giá cá nhân được |
| `Categories.Active` | 49 active, 7 inactive (ID 5, 17, 20, 46, 47, 53, 54). **5 ID thực sự được dùng, gắn 158/13.846 = 1,14% complaint** (46: 79, 54: 58). Cờ là **hiện tại**, không có ngày hiệu lực → không chứng minh dữ liệu lịch sử sai. Cần chốt: có lọc hay không |
| Complaint mỗi khách | trung vị 1; tối đa 8; 1% khách có nhiều nhất tạo ra 2,93% complaint — **không có skew nghiêm trọng** |
| `Regions.name` | 923 distinct trên 994 dòng → 71 tên lặp; dùng `id` làm khoá, không dùng tên |
| Mức ưu tiên | `Non Urgent` 13.294 (96,0%), `Urgent` 552 (4,0%) — nhóm nhỏ, cần cẩn thận khi so sánh tỷ lệ |

## 4. Hợp đồng KPI — điều chỉnh sau khi profile

Bảng KPI dự kiến trong PLAN §3 cần sửa theo số liệu thật. Trạng thái cột cuối là **đề xuất của worker, chờ người dùng chốt ở Gate 1**.

| KPI | Định nghĩa sau khi profile | Điều chỉnh so với PLAN | Cần chốt |
|---|---|---|---|
| Total complaints | `COUNT(DISTINCT ID)` trong `Complains Data` = 13.846 | Không đổi. Đã xác nhận không trùng | — |
| Processing days | `(CompletionDate − ComplainDate)` trong ngày lịch, **chỉ ngày thật** | Loại 50 chữ `"NULL"` khỏi phép tính ngày; **baseline giữ 1.899 ca 0 ngày, n = 13.796**; positive-only n = 11.897 **chỉ để so sánh**, **chưa có quy tắc được duyệt loại 0 ngày** | Có tính 0 ngày vào phân phối không? |
| SAT / NSA rate | `SAT / (SAT + NSA)`, mẫu số **7.687** | Bắt buộc kèm coverage **55,52%**. Không được coi `N/A` là NSA | Đánh giá thiếu là do quy trình hay do chưa đóng? |
| Backlog > 30 ngày | Trạng thái mở **tại cutoff** và vượt 30 ngày | **21 ca lấy từ trạng thái fact, chưa xác minh là cohort tại cutoff**; **2 ca có complaint age > 30 ngày** — **chưa phải KPI time-in-status hay backlog lịch sử** | Có nguồn case đang xử lý riêng? Ngày snapshot? Quy tắc tie? |
| Status dwell (proxy) | **Inter-event gap** và **observed span** — đều **không phải dwell theo trạng thái** | Coverage: toàn **31,42%**, `CLOSED` **31,18%**, chưa đóng **100%**, thiếu **9.495**. Ambiguous **1.037/4.351 = 23,83%** trên mẫu số riêng. **Chưa tính censoring** | Quy tắc tie-break? Có nguồn giờ chi tiết? |
| Complaints / 1.000 khách | Complaint / khách × 1.000 | **1.125,23 nếu dùng 12.305 — chưa xác nhận là insured base** | Có sẵn danh sách khách hàng bảo hiểm không? |
| Expected reimbursement | Số tiền yêu cầu/kỳ vọng | **13 quan sát khác 0**; không có currency | Currency, và cột đã chi trả ở đâu? |
| Age / urgency | Tuổi tại ngày khiếu nại | **≥18: 10.438**; 1–17: 2.518 (**nhóm có thật, không tự thành lỗi**); 0 tuổi: 206; **âm: 491** (dữ liệu không nhất quán); thiếu BirthDate: 193 | 1–17 là lỗi hay người đại diện? Có chấp nhận nhóm nào? |

Không đặt target cho bất kỳ KPI nào. Không có baseline nào được chứng minh.

## 5. Ma trận 13 câu hỏi — dữ liệu đã trả lời tới đâu

Bằng chứng: `notebooks/01_data_understanding.ipynb` (mục `## Q1` … `## Q13`), chạy từ kernel sạch ở run C01–C03 (`Log/phase1/RUNS.md` §17): **0 error output, 12 ảnh inline, cell reconcile 17/17**, `Log/phase1/check_phase1_fixes.py` **56 PASS** exit 0, aggregate exit 0. Đây là bằng chứng cho **run hiện hành**; số đếm của revision trước không dùng lại. Số quan trọng được đối chiếu bằng check và bằng cell reconcile so biến notebook tự tính.

Phân loại: **✔ trả lời được** (mô tả bằng số, không cần quyết định nghiệp vụ) · **~ trả lời một phần** (đếm được nhưng diễn giải phụ thuộc quyết định chưa chốt) · **✋ cần người dùng hoặc nguồn khác**.

| # | Câu hỏi | Kết luận có bằng chứng | Phân loại | Bằng chứng |
|---|---|---|---|---|
| 1 | 50 ô `CompletionDate` chữ `"NULL"` | 13.796 `CLOSED` đều có ngày thật; 50 complaint chưa đóng đều là chữ `"NULL"`, không ô nào parse được; `open_status_with_real_completion_date = 0`. **Chưa chứng minh `"NULL"` là cờ nghiệp vụ** | ✔ số đếm · ✋ quy tắc | Q1 · `figures/q01_completion_kind.png` |
| 2 | 1.899 ca "0 ngày" giữ hay loại | Baseline (delta ≥ 0, **gồm 0 ngày**): n = 13.796, median **7,0**, mean 12,85. Positive-only: n = 11.897, median **8,0**, mean 14,90. **Chưa có quy tắc được duyệt để loại** | ✔ số đếm · ✋ nghiệp vụ | Q2 · `figures/q02_processing_days.png` |
| 3 | Ngày as-of nào dùng được | Cutoff **14/05/2020** là **ngày tham chiếu phân tích do chọn** (max ComplainDate/CompletionDate), **không phải snapshot xác nhận**. `max StatusDate` = 15/05, **1 event sau cutoff bị loại** | ~ tham số · ✋ ngày snapshot | Q3 · `figures/q03_trend.png` |
| 4 | Backlog > 30 ngày | Cohort **21 lấy từ trạng thái fact, chưa xác minh là state tại cutoff** (4 ambiguous). **Complaint age >30: 2 ca**; **days-since-last-observed-event >30: 0 ca** (max 28) — proxy, không phải time-in-status | ✔ quan sát · ✋ KPI thật | Q4 · `figures/q04_backlog.png` |
| 5 | SAT 89,33% dùng được không | **SAT = 6.856 `CLOSED` + 11 `NEW` = 6.867**; NSA 820; `N/A` 6.159; coverage **55,52%**. **Đính chính: nhóm chưa đóng không toàn `N/A`** — 11 ca `NEW` đã có điểm | ✔ số đếm · ✋ nghĩa `N/A` | Q5 · `figures/q05_satisfaction.png` |
| 6 | 12.305 khách phải insured base? | 8.261 khách có ≥1 complaint; **4.044/12.305 = 32,86%** không có. Tỷ lệ 1.125,23/1.000 chỉ hợp lệ nếu xác nhận được mẫu số | ~ | Q6 · `figures/q06_customer_coverage.png`, Q10 |
| 7 | Reimbursement | **13/13.846 = 0,09%** khác 0 (14,37 → 15.000,74; tổng 35.379,26); đều `CLOSED`; 7 SAT / 6 `N/A` / 0 NSA; **top-3 chiếm 70,66%** → trung bình không đại diện. Không có currency | ~ mô tả được | Q7 |
| 8 | Tuổi dùng được cho nhân khẩu học | **≥18: 10.438**; 1–17: **2.518** (nhóm thật, **không tự coi là lỗi**); 0 tuổi: 206; **âm: 491**; thiếu BirthDate: 193; ≥1 = **12.956** | ~ tách nhóm | Q8 · `figures/q08_age.png`, `figures/q08_age_distribution.png` |
| 9 | History ties và đại lượng nào đáng tin | **Inter-event gap** (n = 5.375, median 3, p90 14, max 142) và **observed span** (3.539 ca ≤ 60 ngày) — **không phải dwell theo trạng thái**, **chưa tính censoring**. **1.037 latest ambiguous** (23,83% trên 4.351 ca có history) | ✔ số quan sát · ✋ tie-break | Q9 · `figures/q09_dwell_span.png` |
| 10 | 4.044 khách không complaint | Xác nhận **4.044/12.305 = 32,86%**; trung bình 1,68 complaint/khách, tối đa 8 | ✔ đếm · ✋ diễn giải | Q10 |
| 11 | `AdministratorID` dùng được không | **8 mã số** (98: 7.522; 16: 3.673; 42: 1.205; 85: 785; còn lại <300) + **172 ô `"NULL"`**; **không có dimension Administrator** | ✔ mức mã · ✋ danh mục | Q11 · `figures/q11_admin.png` |
| 12 | Category inactive có đang dùng | 7 ID inactive (lấy từ lookup), **5 ID** dùng thật, gắn **158/13.846 = 1,14%**; 46: 79 ca, 54: 58 ca. Cờ là **hiện tại**, không có ngày hiệu lực | ✔ đếm · ✋ quyết định lọc | Q12 · `figures/q12_inactive.png` |
| 13 | History thiếu thì journey làm được gì | Coverage trên **toàn population**: toàn **4.351/13.846 = 31,42%**; `CLOSED` **4.301/13.796 = 31,18%**; chưa đóng **50/50 = 100%**; **thiếu 9.495**. Ambiguous **1.037/4.351 = 23,83%** trên mẫu số riêng. **Presence coverage không chứng minh lịch sử đầy đủ** nên **không nhận journey đầy đủ** cho bất kỳ cohort nào | ✔ coverage · ✋ journey | Q13 · `figures/q13_coverage.png` |

### 5.1 Đính chính so với revision V1 (đã kiểm, không phải suy đoán)

| Nội dung V1 | Revision đã kiểm | Nguồn đối chiếu |
|---|---|---|
| "21 complaint mở nhưng đã có `CompletionDate`" | Sai do đếm chuỗi `"NULL"` là có giá trị. Đúng là **0** open có ngày thật; 21 là số `OUTSTANDING`/`IN PROGRESS` mang `"NULL"` | `open_status_with_real_completion_date = 0` · assert `open_real_completion` |
| Cohort gọi là 13.796 nhưng n = 11.897 | Baseline đúng là n = **13.796** (đã gồm 0 ngày), median **7,0**; positive-only n = 11.897, median 8,0 | assert `cohort_n_incl_zero`, `cohort_direct_median` |
| "1.037 trạng thái cuối mâu thuẫn" | Tại cutoff ≤14/05: **3.314 latest xác định + 1.037 ambiguous = 4.351**. Không so trạng thái fact thay historical state | cell reconcile `Q13_ambiguous` |
| Dwell n = 7.203 | N = **5.375** sau khi loại 1.832 cặp gap-0 (cùng timestamp khác trạng thái) | `zero_gap_pairs_excluded_from_dwell` |
| "History thiếu nên backlog không làm được" | Sai. Nhóm mục tiêu (case đang mở) có độ phủ **100%**; chỉ journey toàn bộ 13.846 case mới không đủ | Q13 · `history_coverage_by_status` |
| "Dữ liệu gần như vô dụng cho reimbursement" | Nói quá. Đúng là chỉ 13 quan sát nên không suy luận tương quan, nhưng vẫn mô tả được phạm vi | Q7 |
| "mọi complaint đang mở đều `N/A`" | Sai. Có **11 SAT** ở `NEW`; tổng SAT 6.867 = **6.856 CLOSED + 11 NEW** | Q5 · notebook reconcile |
| "12.956 complaint tuổi ≥ 18" | Sai. 12.956 là cohort **≥ 1 tuổi**; ≥18 thật là **10.438** | Q8 · notebook reconcile |
| "AdministratorID: 9 mã" | Thực tế **8 mã số** + 172 ô chữ `NULL` | Q11 · notebook reconcile |
| "days từ event cuối = thời gian ở trạng thái" | Đổi nhãn thành **days since last observed event** — proxy, không phải time-in-status | Q4 · notebook reconcile |
| `Customers.MaritalStatus` thiếu 184 ô trong profile | Đã sửa ở hàm profile dùng chung; **12 cột × 12 sheet** đều reconcile về `records_non_empty` (12 assert `columns_reconcile_*`) | assert `marital_reconcile`, `marital_short_equals_null` |

### 5.2 Câu hỏi nghiệp vụ còn lại cần người dùng chốt (xếp theo mức ảnh hưởng)

1. 50 ô `"NULL"`: xác nhận là "chưa hoàn tất"? Có nguồn nào giữ ngày cho case đang mở không? *(Q1 — quyết định cách xử lý ở Phase 2)*
2. Ngày as-of và định nghĩa age-vs-dwell dùng để tính backlog. *(Q3, Q4)*
3. Có bộ dữ liệu case đang xử lý riêng không, để câu 4 của đề có đối tượng đo? *(Q4)*
4. 6.159 `N/A` và **11 SAT ở `NEW`**: vì sao `NEW` được chấm sớm — quy trình lọc phân tích hay quy trình khác? Có cho phép công bố SAT 89,33% kèm coverage 55,52%? *(Q5)*
5. 12.305 khách là insured base hay chỉ người từng khiếu nại? Nếu không có exposure thật, câu 5 và 9 của đề dùng mẫu số nào? *(Q6, Q10)*
6. Currency của `ExpectedReimbursement`, nghĩa của "expected", và cột đã chi trả ở đâu? *(Q7)*
7. **2.518 ca 1–17 tuổi và 206 ca 0 tuổi**: lỗi nhập liệu hay khách vị thành niên đại diện? Và 491 tuổi âm có phải lỗi nhất quán cần loại? *(Q8)*
8. Quy tắc tie-break khi nhiều trạng thái cùng timestamp; có nguồn nào có giờ chi tiết hơn không? *(Q9)*
9. Có danh mục nhân viên cho `AdministratorID` không? *(Q11)*
10. Giữ hay lọc 158 complaint thuộc category inactive? Nghĩa nghiệp vụ của cờ `Active` là gì? *(Q12)*
11. Có nguồn history đầy đủ cho **9.495 ca thiếu history** không? Nếu không, câu 8 của đề chỉ mô tả được 4.351 ca có history. *(Q13)*
12. **Ngày snapshot** để tái dựng trạng thái lịch sử: nguồn không công bố; 14/05 chỉ là ngày tham chiếu do chọn. *(Q3, Q4)*
13. **Quy tắc tie-break** khi nhiều trạng thái cùng timestamp cuối (1.037 ca) và nguồn nào có giờ chi tiết hơn? *(Q9)*


## 6. Kết luận Phase 1

**Dữ liệu đủ dùng cho:** tổng số complaint, phân tích theo Type/Priority/Category/Source/Product/Broker (câu 1, 2, 3, 7, 9, một phần 10), thống kê mức độ hài lòng có kèm coverage, thống kê thời gian xử lý trên cohort đã đóng, phân bố địa lý theo bang.

**Dữ liệu một phần, chưa đủ cho KPI thật:** backlog > 30 ngày (21 ca lấy từ trạng thái fact, chưa xác minh là cohort tại cutoff; 2 ca có complaint age > 30 ngày, chưa phải KPI time-in-status); **presence coverage 50/50 ở nhóm đang mở chỉ xác nhận các ca đó có event ≤ cutoff — thiếu quy tắc tie và chưa tính censoring nên không chứng minh journey hoàn chỉnh, kể cả ở nhóm đang mở**; độ phủ toàn nguồn chỉ 31,42% với 9.495 ca thiếu history; tỷ lệ trên mẫu số khách hàng thật; phân tích reimbursement (chỉ 13 quan sát khác 0, đủ để mô tả phạm vi chứ không đủ suy luận tương quan); phân tích tuổi nếu chưa chốt cách xử lý 2.518 ca 1–17 và 206 ca 0 tuổi.

**Rủi ro lớn nhất phát hiện ở Phase 1:** ba cột (`CompletionDate`, `AdministratorID`, và độ phủ satisfaction) đều có vấn đề chất lượng riêng, và tất cả đều dễ tạo ra kết luận sai nếu không xử lý ở Phase 2. Đặc biệt, bảng điều khiển nếu hiển thị "89,33% hài lòng" mà không kèm "chỉ 55,52% được đánh giá" sẽ gây hiểu sai có hệ thống.

Đã dừng đúng phạm vi Phase 1. Không tạo transform, model, DAX hay dashboard. Chờ supervisor review và Human Gate 1.