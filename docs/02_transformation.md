# Phase 2 — Transformation (curated bảo toàn dữ liệu)

**Marker:** `INSURANCE_PHASE2_CURATED_20261006` · Worker: OpenCode · Supervisor: Codex
**Nguồn (read-only):** `data/insurance_complain.xlsx` · SHA-256 `3ace06421c1a8d146b0bfa6b9f08a2ae367bf32ead182cb84b3d5af159032` (khớp baseline Phase 1, không đổi)
**Script:** `scripts/02_build_curated.py` (tái chạy được, idempotent) · **Check độc lập:** `Log/phase2/check_phase2_curated.py` (không import script build)
**Output:** `data/curated/` (14 artifact + `manifest.json`)

> Cutoff `2020-05-14` chỉ là **ngày tham chiếu do chọn**, không phải snapshot đã xác nhận từ nguồn. Tài liệu này **không** đóng các quyết định nghiệp vụ còn mở của Phase 1.

## 1. Bốn quy tắc đã hiện thực

| Mã | Quy tắc | Cách hiện thực | Bằng chứng |
|---|---|---|---|
| **R1** | Giữ toàn bộ records; chỉ gắn cột, không loại | 12/12 sheet `source_rows == curated_rows`, `delta = 0` | `manifest.json:row_count_delta`; check `rowcount_*` |
| **R2** | Chuẩn hóa ID/ngày hợp lệ, **giữ giá trị gốc + lineage**, không đoán giá trị | Khóa chính về `int`; giữ `<key>__source`, `<key>__int`; ngày về ISO + cột `__source_kind`; 15.708 dòng lineage | `data/curated/_lineage.csv`; check `complaint_ids_multiset_equal`, `lineage_*` |
| **R3** | Giữ 0 ngày; giữ SAT/NSA/N/A riêng; **không thêm currency** | `processing_days_zero = 1.899` giữ nguyên; 3 nhóm satisfaction tách riêng; không cột currency; `ExpectedReimbursement` nguyên vẹn | check `zero_day_complaints`, `satisfaction_*`, `no_currency_column_added`, `reimbursement_untouched` |
| **R4** | Giữ mọi history event + cờ cutoff/ambiguity; **không chọn tie-break** | 11.558/11.558 event; `event_after_cutoff_flag`, `complaint_latest_ambiguous_flag`; **không** cột `latest_status`/`tie_break`/`is_current` | check `history_*`, `latest_ambiguous_1037`, `no_tiebreak_column_added` |

## 2. Bảng curated và số dòng

| Sheet | Source | Curated | Delta | File |
|---|---:|---:|---:|---|
| Brokers | 707 | 707 | 0 | `brokers_curated.csv` |
| Products | 77 | 77 | 0 | `products_curated.csv` |
| Regions | 994 | 994 | 0 | `regions_curated.csv` |
| State Regions | 48 | 48 | 0 | `state_regions_curated.csv` |
| Priorities | 2 | 2 | 0 | `priorities_curated.csv` |
| Statuses | 7 | 7 | 0 | `statuses_curated.csv` |
| Categories | 56 | 56 | 0 | `categories_curated.csv` |
| Sources | 9 | 9 | 0 | `sources_curated.csv` |
| Types | 10 | 10 | 0 | `types_curated.csv` |
| Customers | 12.305 | 12.305 | 0 | `customers_curated.csv` |
| Complains Data | 13.846 | 13.846 | 0 | `complaints_curated.csv` |
| Status History Data | 11.558 | 11.558 | 0 | `status_history_curated.csv` |

Không có bản ghi nào bị nhân bản: `distinct_complaint_ids = 13.846`, `distinct_event_ids = 11.558`.

## 3. Quy tắc chuẩn hóa và lineage

| Nhóm | Quy tắc | Cột giữ giá trị gốc |
|---|---|---|
| Khóa dimension (Brokers/Products/Regions/Priorities/Statuses/Categories/Sources/Types) | `int` khi giá trị là số nguyên; nếu là chuỗi số thì chuyển và ghi lineage | `<key>__source` + `<key>__int` |
| `State Regions.State Code` | chuỗi giữ nguyên (mã bang, không phải số) | `State Code__source` |
| `Complains Data.ID` | `int` | `ComplaintID__source`, `ComplaintID__int` |
| `Complains Data.CustomerID` | `int` | `CustomerID__source` (bảng Customers) |
| Ngày complaint/completion/status | ISO `YYYY-MM-DD` | `CompletionDate__source_kind` ∈ {`date`,`literal_NULL`}; `ComplainDate__iso` |
| Ngày sinh | `BirthDate__iso` + `BirthYear`, cờ nguồn | `BirthDate__source_is_datetime` |
| Reimbursement | **không** chuẩn hóa, không currency | `ExpectedReimbursement` nguyên vẹn |

`_lineage.csv` có 15.708 dòng (`table`, `source_row`, `column`, `original_value`, `curated_value`, `rule`). Không dòng nào để trống `original_value` hay `rule`.

**Vì sao phải chuẩn hóa khóa về `int`:** lượt validation đầu phát hiện `complaint_category_fk_resolves` và `history_complaint_fk_resolves` FAIL (13.846 và 11.558 dòng) vì khóa ở một bảng là `5.0` (float, đọc từ XLSX) ở bảng khác là `5` (int). Sai lệch kiểu này làm join Phase 3 rỗng âm thầm dù số dòng vẫn khớp. Đã sửa tập trung một lần; chi tiết ở `Log/phase2/RUNS.md` §4.

## 4. Cờ chất lượng dữ liệu (quan sát, không phải kết luận nguyên nhân)

`data/curated/_flags.csv` — 5.274 dòng, gồm các cờ:

| Cờ | Số dòng | Nghĩa |
|---|---:|---|
| `processing_days_zero` | 1.899 | complaint có 0 ngày xử lý — **giữ lại**, không loại |
| `age_1_17_observed` | 2.518 | tuổi tại ngày complaint nằm trong 1–17 — **quan sát**, không kết luận bản ghi không hợp lệ |
| `age_negative` | 491 | tuổi âm tại ngày complaint — nghĩa là ngày sinh **sau** ngày complaint; **giữ lại**, cần người dùng xác nhận ý nghĩa |
| `age_zero` | 206 | complaint trong năm đầu tiên của khách |
| `age_missing_birthdate_or_complaindate` | 193 | không tính được tuổi (thiếu ngày sinh hoặc ngày complaint không hợp lệ) |
| `birthdate_blank` | 184 | ngày sinh trống ở Customers — 184 dòng này **không** được dùng cho cohort tuổi |
| `administrator_literal_null` | 172 | `AdministratorID` là chuỗi `"NULL"`, không phải null thật |
| `category_inactive` | 158 | complaint thuộc category `Active = 0` — **giữ lại**, chỉ gắn cờ |
| `completion_literal_null` | 50 | `CompletionDate` là chuỗi `"NULL"` — **không** ép thành ngày, không epoch |
| `event_after_cutoff` | 1 | event nằm sau ngày tham chiếu 2020-05-14 |

### 4.1 Tuổi tại ngày complaint (gói sửa R201)

`complaints_curated.csv` có hai cột mới: `age_at_complaint` (số nguyên, rỗng khi không tính được) và `age_bucket`.

| Bucket | Số | Nghĩa |
|---|---:|---|
| `ge18` | 10.438 | từ 18 tuổi trở lên tại ngày complaint |
| `1_17` | 2.518 | **quan sát**; không tự kết luận bản ghi không hợp lệ |
| `negative` | 491 | ngày sinh sau ngày complaint |
| `zero` | 206 | dưới 1 tuổi tại ngày complaint |
| `missing` | 193 | không tính được |
| **Tổng** | **13.846** | bằng tổng complaint → không lọc dòng nào |

Cách tính: `tuổi = năm(ComplainDate) − năm(DOB)`, trừ 1 nếu cặp (tháng, ngày) sinh chưa tới trong năm complaint. Nguồn tuổi là `Customers.BirthDate`, khớp qua `CustomerID`.

**Không** dùng tuổi tại một mốc cutoff chung cho cả bộ dữ liệu — mỗi complaint có ngày riêng. 184 khách thiếu ngày sinh (`birthdate_blank`) không đồng nghĩa 193 complaint thiếu tuổi, vì một khách có thể có nhiều complaint.

**Trạng thái kiểm chứng:** số ở trên đã được reconciliation độc lập xác nhận ở gói R203 — check đọc `age_bucket`/`age_at_complaint` trong curated và đối chiếu **từng `ComplaintID`** với nguồn: 0 complaint thiếu, 0 dòng trùng, 0 lệch bucket, 0 lệch giá trị tuổi; đếm bucket trên curated 491/206/2.518/193/10.438 và khớp `manifest.json`. Xem §8.

`ComplainCategoryID` thuộc nhóm inactive: `{5, 17, 20, 46, 47, 53, 54}` — 158 complaint vẫn nằm trong curated.

## 5. Satisfaction — giữ 3 nhóm riêng

| Nhóm | Số |
|---|---:|
| SAT | 6.867 |
| NSA | 820 |
| N/A | 6.159 |
| **Tổng** | **13.846** |

Không gộp `N/A` vào nhóm đánh giá. Coverage đánh giá = (6.867 + 820) / 13.846 ≈ 55,52%; phần còn lại là `N/A`, không phải dữ liệu thiếu do lỗi.

## 6. History — giữ mọi event, không chọn tie-break

- 11.558 event trên 4.351 complaint có event; 1.552 complaint có timestamp trùng nhau.
- **1.037 complaint** có nhiều event cùng thời điểm ở trạng thái cuối → gắn `complaint_latest_ambiguous_flag = True`, **không** chọn event nào.
- 1 event nằm sau ngày tham chiếu → `event_after_cutoff_flag = True`, **không** cắt bỏ.
- Không có cột trạng thái đã chọn. `Status History Data` có khóa `EventID` duy nhất, nhưng curated vẫn giữ `_source_row` để truy vết về dòng nguồn.

## 7. Cố ý KHÔNG làm trong Phase 2

| Không làm | Lý do |
|---|---|
| Chọn tie-break cho `latest_status` | chưa có quy tắc nghiệp vụ được duyệt; tự chọn sẽ là dữ liệu bịa |
| Lọc age `<18` hoặc category inactive | sẽ vi phạm R1 (mất dòng) |
| Suy `time-in-status`, backlog cohort, dwell theo trạng thái | cần quy tắc dwell + censoring chưa được duyệt |
| Thêm cột currency, quy đổi reimbursement | nguồn không có nghĩa currency; thêm là bịa |
| Tính insured base / tỷ lệ KPI | chưa có mẫu số được chốt |
| Cố chứng minh nguyên nhân dữ liệu | tài liệu này chỉ ghi **quan sát** |

## 8. Kiểm chứng

`Log/phase2/check_phase2_curated.py` đọc lại **nguồn XLSX bằng openpyxl** và **CSV curated** rồi đối chiếu độc lập với script build.

**Gói R203 (2026-10-06): check chạy trọn `exit 0` — 96 PASS / 0 FAIL, `CHECKS_FAILED: none`, stderr rỗng, không traceback.** Đây là lượt chạy đầu tiên đi hết toàn bộ check (lượt trước crash ở dòng 137 sau 21 PASS và chỉ dừng ở §4c).

Đoạn chưa từng chạy trước đó — nay đã chạy và PASS:

| Nhóm | Assertion mới chạy | Kết quả |
|---|---|---|
| Tuổi (R201) | `age_every_source_id_has_curated_row`, `age_no_duplicate_curated_row`, `age_bucket_matches_source_per_id`, `age_value_matches_source_per_id` | 0 / 0 / 0 / 0 lệch |
| Tuổi (đếm trên curated) | `age_negative_491`, `age_zero_206`, `age_1_17_2518`, `age_missing_193`, `age_ge18_10438`, `age_sum_equals_complaints`, `age_bucket_exhaustive`, `manifest_age_buckets_match_curated`, `age_1_17_kept_in_curated` | 491 / 206 / 2.518 / 193 / 10.438, tổng 13.846, khớp manifest |
| Dimension (R202) | 7 × `dim_rowcount_*_curated.csv`, `dim_keys_unique`, `regions_rowcount_csv`, `state_regions_rowcount_csv` | 707 / 77 / 2 / 10 / 9 / 56 / 7; 994; 48; khóa không trùng |
| Lineage (R202) | `lineage_source_row_maps_to_real_source`, `lineage_original_equals_source_cell`, `lineage_curated_value_is_integer`, `lineage_covers_every_normalized_complaint_id`, `lineage_value_matches_complaint_output`, `complaint_source_row_back_maps_to_source` | 0 lệch |
| Flags (R202) | `flags_completion_literal_null_count` + `_same_rows`, `flags_administrator_literal_null_count` + `_same_rows`, `complaint_quality_flags_column_matches_flags_csv`, `flags_no_spurious_completion_literal_null`, `flags_rows_present`, `flag_zero_day_total_matches` | 50 / 172, 0 dòng lệch, 1.899 zero-day |
| History record (R203) | `history_source_id_is_integer`, `history_curated_eventid_int_unique`, `history_event_id_matches_source`, `history_record_pairs_match_source` | 0 lệch |

Điểm đáng lưu ý về cách đối chiếu tuổi: `expected_bucket` tra **theo CustomerID** (nguồn `Customers.BirthDate`), còn tra cứu dòng curated thì theo **ComplaintID**. Nếu lẫn hai khoá này thì số bucket có thể vẫn ra 13.846 nhưng so với sai khách — nên check kiểm cả `age_value_matches_source_per_id` (đối chiếu **giá trị tuổi từng dòng**), không chỉ đếm bucket.

Về khóa event: `status_history_curated.csv` giữ `EventID` dạng float-string gốc (`129.0`) kèm `EventID__int` (`129`). Check dùng `EventID__int` và kiểm nó khớp cả giá trị nguyên của `EventID` lẫn `ID` nguồn, **không** dùng `int(float(...))` để cắt phần lẻ rồi nhận PASS. Header sheet `Status History Data` là `ComplaintStatusID`, còn sheet `Complains Data` là `ComplainStatusID` — hai tên khác nhau và check giữ đúng ranh giới đó.

**Ghi chú log:** `r203_check.stdout.txt` 101.677 B, trong đó ~94 KB là `processing_days_equal_sorted` in hai danh sách 13.796 số `processing_days`. Assertion này có sẵn từ trước, nội dung không phải PII, và **không** thuộc các điểm R203 nên không sửa.

| Nhóm kiểm | Nội dung |
|---|---|
| Baseline nguồn | hash XLSX và manifest khớp baseline |
| Số dòng / ID | 12 sheet delta 0; ID unique + multiset (ký băm `n=… sha=…`, không in danh sách) |
| FK | 8 FK không đổi theo từng dòng; resolve trong 7 CSV dimension đọc thật; history↔complaint nối từng `EventID` |
| Số dòng dimension | đọc từ CSV, so với sheet nguồn, khóa không trùng |
| Tuổi (R201) | mọi ComplaintID nguồn có đúng 1 dòng curated; `age_bucket` và `age_at_complaint` khớp từng dòng; đếm bucket trên curated = 491/206/2.518/193/10.438, tổng 13.846 |
| Lineage (R202) | `source_row` trỏ đúng dòng sheet; `original_value` bằng **cell thật**; `curated_value` là số nguyên; phủ mọi ComplaintID đã chuẩn hóa; `_source_row` của complaint trỏ đúng dòng nguồn |
| Flags (R202) | `_flags.csv` thật: đếm + đối chiếu tập `source_row` cho literal NULL (50/172); cột `quality_flags` từng dòng khớp `_flags.csv`; không gắn cờ giả |
| Không thêm KPI giả | không cột currency; `ExpectedReimbursement` nguyên vẹn |
| History | event sau cutoff giữ; ties giữ; `latest_ambiguous` 1.037; không có cột tie-break |
| PII | không tên/ngày sinh trong log; curated không có `FirstName`/`LastName` |

## 9. Điểm cần supervisor/Human Gate 2 cân nhắc

1. **Check đã chạy trọn và xanh** (exit 0, 96 PASS / 0 FAIL), nhưng **độ phủ hợp đồng vẫn hẹp**: check xác nhận transform giữ nguyên dữ liệu và gắn cờ đúng. Nó **không** chứng minh các quyết định nghiệp vụ — dưới đây vẫn còn các điểm cần người dùng chốt.
2. **Customers bỏ `FirstName`/`LastName`** khỏi curated. Đây là **projection đã dùng**, không phải yêu cầu xóa PII khỏi dữ liệu: workbook gốc còn nguyên, không cần tên để tính KPI, và chưa có yêu cầu giữ mọi trường trong curated. Nếu sau này cần tên/BrokerFullName để đối chiếu hoặc hiển thị, đọc trực tiếp từ workbook theo `CustomerID`.
3. **Giá trị chuẩn hóa truy về nguồn bằng mapping source-row**, không cần lineage từng ô: `ComplaintID__source`, `*__source`, `CompletionDate__source_kind` và cột `_source_row` là đủ. Lineage hiện chỉ ghi các chuyển đổi **có thay đổi giá trị** (15.708 dòng); tuổi không sinh lineage vì là **tính toán dẫn xuất**, không phải chuẩn hóa giá trị nguồn.
4. **`regions_curated.csv` giữ tọa độ và `State Code` ở cột `__source`** dạng chuỗi như nguồn; không dùng để tính khoảng cách khi chưa kiểm tra kiểu.
5. **`_flags.csv` là aggregate theo dòng nguồn** (5.274 dòng), chưa phải bảng cờ wide; Phase 3 có thể cần bản wide để join thuận tiện.
6. **Không có cột nào chứa `time-in-status`** và không có bảng fact trạng thái tại một mốc thời gian. Đây vẫn là khoảng trống đã biết từ Phase 1.
7. **Cutoff 2020-05-14 vẫn là ngày tham chiếu do chọn.** 1 event sau cutoff được giữ kèm cờ; 491 complaint có tuổi âm và 206 complaint dưới 1 tuổi cũng chỉ là **quan sát**, cần người dùng xác nhận ý nghĩa nghiệp vụ trước khi dùng cho KPI.

## 10. Reproduce

```powershell
python scripts\02_build_curated.py
python Log\phase2\check_phase2_curated.py
```

Lệnh thứ hai trả `exit 0` khi tất cả assertion PASS, `exit != 0` nếu có bất kỳ FAIL nào. Không hạ assertion, không bỏ qua sheet.