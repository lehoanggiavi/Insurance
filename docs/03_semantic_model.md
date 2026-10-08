# Phase 3 — Semantic model InsuranceOps

> **Đọc dễ hiểu trước:** Bước này gắn đúng hồ sơ với khách, loại, nguồn và ngày. Nhờ vậy bạn chọn một nhóm trên dashboard thì chỉ các hồ sơ thuộc nhóm đó được đếm. Khi viết tài liệu này, report còn rỗng; đó là trạng thái lịch sử của Phase 3. Sản phẩm cuối hiện đã có hai trang dashboard được duyệt. Phần bên dưới giữ cách nối bảng và cấu hình đường dẫn để tra khi cần. [Báo cáo cuối](06_project_report.md) và [giải thích DA](07_da_explained.md).

**Marker:** `INSURANCE_PHASE3_MODEL_20261006` → `INSURANCE_PHASE3_FINISH_20261006`
Worker: OpenCode · Supervisor: Codex
**Nguồn:** 12 CSV trong `data/curated/` (đã nghiệm thu Gate 2) · manifest `f281cd57…`
**Dự án:** `pbi/InsuranceOps.pbip` — **15 bảng core + 15 liên kết core**, thêm **2 bảng ngày ẩn + 1 liên kết DOB do Desktop tự sinh** (báo riêng, không tính vào core).

> Đây là **bước liên kết dữ liệu**, chưa phải viết chỉ số DAX kinh doanh và chưa phải dashboard. Report chỉ là container tối thiểu (1 trang rỗng tên *Model only*) để Desktop mở được model.
>
> **Cập nhật Phase 4:** bảng `Measure` đã bổ sung 22 chỉ số DAX — xem `docs/04_measures.md`. **Dashboard là Phase 5**, chưa được giao và chưa dựng.

## 1. Cấu trúc và grain

| Bảng | Grain (1 dòng = ?) | Nguồn CSV | Số dòng |
|---|---|---|---:|
| `Fact_Complaint` | 1 `ComplaintID` | `complaints_curated.csv` | 13.846 |
| `Fact_StatusHistory` | 1 `EventID` | `status_history_curated.csv` | 11.558 |
| `Dim_Customer` | 1 `CustomerID` | `customers_curated.csv` | 12.305 |
| `Dim_Broker` | 1 `BrokerID` | `brokers_curated.csv` | 707 |
| `Dim_Product` | 1 `ProductID` | `products_curated.csv` | 77 |
| `Dim_Region` | 1 `id` | `regions_curated.csv` | 994 |
| `Dim_StateRegion` | 1 `State Code` (khóa **chuỗi**) | `state_regions_curated.csv` | 48 |
| `Dim_Priority` | 1 `ID` | `priorities_curated.csv` | 2 |
| `Dim_Category` | 1 `ID` | `categories_curated.csv` | 56 |
| `Dim_Source` | 1 `ID` | `sources_curated.csv` | 9 |
| `Dim_Type` | 1 `ID` | `types_curated.csv` | 10 |
| `Dim_ComplaintStatus` | 1 `ID` | `statuses_curated.csv` | 7 |
| `Dim_EventStatus` | 1 `ID` | `statuses_curated.csv` | 7 |
| `Dim_Date_Complaint` | 1 ngày | sinh từ ngày thực có | 3.234 |
| `Dim_Date_Event` | 1 ngày | sinh từ ngày thực có | 620 |

Tổng **15 bảng core**. `Dim_ComplaintStatus` và `Dim_EventStatus` **cùng đọc** `statuses_curated.csv` nhưng là **hai bảng riêng** — xem §3.

## 2. Sơ đồ quan hệ

```mermaid
erDiagram
    Fact_Complaint      }o--|| Dim_Customer        : CustomerID
    Fact_Complaint      }o--|| Dim_Broker          : BrokerID
    Fact_Complaint      }o--|| Dim_Product         : ProductID
    Fact_Complaint      }o--|| Dim_Priority        : ComplainPriorityID
    Fact_Complaint      }o--|| Dim_Category        : ComplainCategoryID
    Fact_Complaint      }o--|| Dim_Source          : ComplainSourceID
    Fact_Complaint      }o--|| Dim_Type            : ComplainTypeID
    Fact_Complaint      }o--|| Dim_ComplaintStatus : ComplainStatusID
    Fact_Complaint      }o--|| Dim_Date_Complaint  : ComplainDate__iso (active)
    Fact_Complaint      }o--o| Dim_Date_Complaint  : CompletionDate__iso (inactive)
    Fact_StatusHistory  }o--|| Fact_Complaint      : ComplaintID
    Fact_StatusHistory  }o--|| Dim_EventStatus     : ComplaintStatusID
    Fact_StatusHistory  }o--|| Dim_Date_Event      : StatusDate__iso
    Dim_Customer        }o--|| Dim_Region          : RegionID
    Dim_Region          }o--|| Dim_StateRegion     : state_code
    Dim_Customer        }o--o| LocalDateTable      : BirthDate__iso (native, DOB)
```

`Fact_StatusHistory` → `Fact_Complaint` là quan hệ **nhiều–một** (một complaint có nhiều event). `}o--o|` trong sơ đồ là ký hiệu cardinality/optionality của Mermaid, **không** diễn tả active/inactive — trạng thái thật nằm ở metadata (ngày hoàn thành **inactive**; DOB native **active**), xem §4.

**Quy tắc đã áp dụng:** toàn bộ 15 liên kết core là **Many→One, OneDirection, lọc một chiều từ phía khóa duy nhất**. Không có quan hệ many-to-many, không có `both`, không có vòng lặp.

## 3. Vì sao tách 2 bảng trạng thái

Có hai vai trò khác nhau với *trạng thái*:

- **Trạng thái của complaint** (`Fact_Complaint[ComplainStatusID]`) → `Dim_ComplaintStatus`.
- **Trạng thái của event** (`Fact_StatusHistory[ComplaintStatusID]`) → `Dim_EventStatus`.

Nếu dùng chung một bảng trạng thái, sẽ có **hai đường lọc active cùng đi tới `Fact_StatusHistory`** (qua `Dim_EventStatus`) và qua `Fact_Complaint` → trùng vai trò. Tách riêng giữ đúng "một đường lọc cho mỗi vai trò". Bằng chứng: lọc `Dim_EventStatus[ID] = 9` cho **13.846 complaint** (không lọc complaint) nhưng chỉ **4.314 event** — tức đường lọc nằm đúng bảng event; ngược lại `Dim_ComplaintStatus[ID] = 9` lọc cả hai (13.796 complaint / 11.443 event) vì nó nằm trên đường complaint.

## 4. Ngày và chính sách null

| Bảng ngày | Phạm vi | Quan hệ | Trạng thái |
|---|---|---|---|
| `Dim_Date_Complaint` | 08/07/2011 – 14/05/2020 (3.234 ngày) | `Fact_Complaint[ComplainDate__iso]` | **active** |
| `Dim_Date_Complaint` | như trên | `Fact_Complaint[CompletionDate__iso]` | **inactive** |
| `Dim_Date_Event` | 04/09/2018 – 15/05/2020 (620 ngày) | `Fact_StatusHistory[StatusDate__iso]` | **active** (bảng riêng theo vai trò event) |

**Đính chính (theo review Phase 3):** ký hiệu Mermaid `}o--o|` ở trên chỉ thể hiện cardinality/optionality, **không** tự diễn tả trạng thái active/inactive. Chuẩn là **metadata thật**: quan hệ ngày hoàn thành **inactive**; quan hệ DOB của Desktop **active**. Nhãn trong sơ đồ và metadata là nguồn chuẩn, không phải ký hiệu.

- Phạm vi lấy từ **ngày hợp lệ thực có**, không cắt theo ngày tham chiếu. `Dim_Date_Event` chứa tới **15/05/2020** nên giữ được event sau ngày tham chiếu 14/05/2020.
- **Không** biến ngày thiếu thành ngày 0/epoch: cột ngày import kiểu `date`, rỗng ở CSV → **null**. `CompletionDate__iso` có **50** null, đúng bằng 50 complaint `CompletionDate` là chuỗi `"NULL"` ở nguồn.
- Ngày **hoàn thành** dùng chung bảng ngày complaint nhưng quan hệ **inactive** → lọc ngày hoàn thành không cạnh tranh vai trò với lọc ngày complaint. Chỉ số `Completed by Completion Date` (Phase 4) dùng `REMOVEFILTERS` + `USERELATIONSHIP` để mở đúng đường này.
- `BirthDate__iso` chỉ là **thuộc tính khách**, không phải trục thời gian của phân tích. Quan hệ DOB của Desktop là **active** nhưng chỉ là helper native. `age_at_complaint` lấy **nguyên từ curated** (tính tại ngày complaint của chính record), không tính lại trong model.
- Không thêm time intelligence, không có cột `latest_status`.

**Đính chính về `processing_days`:** `processing_days` = **`CompletionDate` − `ComplainDate`**, thuộc `Fact_Complaint` (theo `scripts/02_build_curated.py`). `Fact_StatusHistory` **không có** cột này. Đây **không phải** khoảng giữa hai sự kiện trạng thái liên tiếp như các đoạn cũ mô tả. Chưa có phép tính time-in-status.

## 5. Cờ và giá trị đặc biệt được giữ nguyên

Model **không lọc bỏ** gì. Các giá trị khó đã được kiểm đọc lại trên runtime:

| Kiểm | Giá trị | Ý nghĩa |
|---|---:|---|
| `ProcessingZero` | 1.899 | complaint 0 ngày — **giữ** |
| `CompletionBlank` | 50 | `CompletionDate` literal `"NULL"` → **null**, không ép ngày |
| `AdminBlank` | 172 | `AdministratorID` literal `"NULL"` → null |
| `BirthBlank` | 184 | khách thiếu ngày sinh |
| `AfterCutoff` | 1 | event sau ngày tham chiếu — **giữ** |
| `AmbiguousEvents` | 2.772 | event thuộc complaint có timestamp trùng |
| SAT / NSA / N/A | 6.867 / 820 / 6.159 | 3 nhóm tách riêng |
| Nhóm tuổi | ge18 10.438 · 1–17 2.518 · thiếu 193 · âm 491 · 0 tuổi 206 | tổng 13.846 |

`age_negative` và `age_1_17` là **quan sát**, không phải kết luận bản ghi không hợp lệ. Không có currency, không có cột `time-in-status`, không có mẫu số insured base.

## 6. Bằng chứng đã kiểm

Lệnh: `python -X utf8 scripts/04_check_semantic_model.py verify` → **actual exit 0, 113/113 PASS** (76 so sánh trường DAX + 15 liên kết + 22 hash nguồn được bảo vệ).

| Nhóm | Kết quả |
|---|---|
| 13 bảng: số dòng + khóa duy nhất | `Rows == Unique` ở cả 13 |
| Null/cờ/cohort (14 trường) | khớp 100% |
| FK integrity (12 trường) | tất cả **0** — gồm FK11 vùng |
| 2 bảng ngày | 3.234 và 620 ngày, min/max đúng |
| 8 bộ lọc | complaint 7.445 · vùng CA 2.593/2.140 · product 201/181 · category 2.451/4.575 · trạng thái complaint 13.796/11.443 · ngày complaint 87/175 · ngày event 13.846/1 · trạng thái event 13.846/4.314 |
| 15 liên kết core | đúng endpoints, Many→One, OneDirection, đúng cờ active |
| 22 hash nguồn/curated/Phase 1–2 | **giữ nguyên** |
| Lưu + đóng/mở lại | 12/12 trường khớp, liên kết vùng còn nguyên |

Bằng chứng thô: `Log/phase3/live_queries.json`, `relationships.json`, `reconciliation.json`, `persistence_queries.json`, `bridge_status_before_save.json`, `bridge_status_after_save.json`.

## 7. Cách mở lại

```powershell
& "$env:ProgramFiles\Microsoft Power BI Desktop\bin\PBIDesktop.exe" `
  "E:\Practice_DSEA\DA\OpenSrcDA\Insurance\pbi\InsuranceOps.pbip"
```

Đổi đường dẫn nguồn: sửa **một** giá trị trong `pbi/InsuranceOps.SemanticModel/definition/expressions.tmdl` (`expression 'Data Folder'`), rồi Refresh. Sinh lại toàn bộ TMDL từ CSV: `python scripts\03_build_pbip.py` — **chỉ chạy khi Desktop đang đóng**, không chạy khi Desktop đang giữ revision khác.

## 8. Giới hạn — chưa chốt

1. **Chưa có chỉ số DAX kinh doanh và chưa có dashboard.** Report là container rỗng; viết measure/biểu đồ là Phase 4.
2. **Chưa có bảng trạng thái tại một mốc** và **chưa có `time-in-status`.** `processing_days` = `CompletionDate` − `ComplainDate` trên `Fact_Complaint`; đây **không phải** dwell theo trạng thái và không có xử lý censoring. Không được dùng như KPI backlog.
3. **Không có currency, không có mẫu số insured base** → chưa tính được tỷ lệ nào cần mẫu số nghiệp vụ.
4. **`Dim_Date_Completion` không còn** (đã gộp về `Dim_Date_Complaint` + quan hệ inactive). Đây là lựa chọn để tránh hai đường lọc ngày active.
5. **2 bảng ngày ẩn + 1 liên kết DOB do Desktop tự sinh** (`DateTableTemplate_*`, `LocalDateTable_*`). Đã **giữ nguyên**, không xóa: đó là helper native của công cụ, không tính vào 15 bảng/15 liên kết core.
6. **Ngày tham chiếu 14/05/2020 vẫn là ngày do chọn**, không phải snapshot nguồn. 1 event sau ngày đó được giữ kèm cờ.
7. **491 complaint có tuổi âm** (ngày sinh sau ngày complaint) và **206 dưới 1 tuổi**: chỉ là quan sát, chưa có quyết định nghiệp vụ.
8. `Dim_Region.latitude/longitude` chuyển sang `double` ở đây. Chưa kiểm chứng chất lượng tọa độ → **không** dùng để tính khoảng cách khi chưa kiểm kiểu.
9. **Bộ kiểm FK dùng `TREATAS`; chưa chứng minh tuyệt đối cho dữ liệu tương lai.** Dữ liệu hiện tại **không có** cặp FK nào rỗng (12/12 cặp = 0 blank, supervisor đã đọc), nên cách đếm này khớp. Khi dữ liệu đổi hoặc có khóa rỗng, phải kiểm lại null/FK — không suy rộng tính đúng.
10. **Hai thử nghiệm DAX ban đầu của tôi sai cú pháp** (tên cột đặt trong dấu nháy thừa bên trong `[...]`; cú pháp đúng là `'Dim_StateRegion'[State Code__source]`) và `COUNTROWS` trả BLANK khi bảng rỗng. Vì vậy **không có bằng chứng "lỗi engine RELATED"** như báo cáo Phase 3 đã ghi ở đây trước đây — **đã rút lại kết luận đó**. Liên kết vùng hoạt động bình thường và truyền bộ lọc thật.
11. **Điểm kẹt `powerbi-desktop open` chưa được sửa tận gốc.** Lượt gọi đó không kết thúc (1.656s). Các lượt sau **tránh được** bằng discovery + Connect của MCP và `Start-Process` trực tiếp, nhưng **không** khẳng định đã sửa được lỗi CLI.

## 9. Bước tiếp theo

Supervisor review bằng chứng → **Gate 3**. **Phase 4 = chỉ số DAX** (`docs/04_measures.md`, bảng `Measure`), đã triển khai và kiểm chứng. **Phase 5 = dashboard/biểu đồ**, chưa được giao và **chưa** dựng. Cần chốt trước các quyết định còn mở ở §8 (mẫu số, currency, quy tắc dwell/backlog).