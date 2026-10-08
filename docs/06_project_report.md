# Báo cáo dự án InsuranceOps

> **Sản phẩm bàn giao:** [báo cáo PDF 13 trang](../reports/project_report/InsuranceOps_Project_Report.pdf) và [source LaTeX](../reports/project_report/InsuranceOps_Project_Report.tex). Markdown này giữ nội dung nguồn/tra cứu; format dùng lại, quy tắc nghiệp vụ phải xác minh riêng theo từng ngành.

## Dự án giúp gì?

Dữ liệu giống một tủ hồ sơ: có hồ sơ khiếu nại, danh sách khách và các lần đổi trạng thái. Dự án sắp xếp chúng để trả lời: có bao nhiêu khiếu nại, xử lý mất bao lâu, khách đánh giá ra sao và nhóm nào cần xem kỹ. Sản phẩm là hai trang Power BI đã được bạn duyệt. Các phát hiện dưới đây là kết quả phân tích dữ liệu, chưa phải thành tích cải thiện vận hành sau triển khai. Nguồn không cho biết ngày chụp toàn hệ thống nên không tự coi ngày cuối trong file là ngày chốt nghiệp vụ.

## Đã làm những bước nào?

| Bước | Làm gì, nói đơn giản | Sản phẩm và cách kiểm |
|---|---|---|
| Hiểu nguồn | Đếm hồ sơ, đọc ý nghĩa cột, tìm phần thiếu | Notebook có kết quả; đối chiếu Excel và đề bài |
| Làm sạch | Chuẩn hóa kiểu và cách ghi; giữ dấu vết nguồn | Dữ liệu chuẩn hóa; kiểm số dòng trước–sau |
| Nối dữ liệu | Gắn đúng khách, loại, nguồn và ngày cho hồ sơ | Model có 16 quan hệ; kiểm khóa và cách lọc |
| Tính chỉ số | Viết 22 công thức với cách đếm rõ ràng | Đối chiếu kết quả Power BI với dữ liệu chuẩn hóa |
| Phân tích | So sánh nhóm, luôn xem số hồ sơ và phần thiếu | Trả lời 10 câu đề bài; ghi rõ hai câu chưa đủ dữ liệu |
| Vẽ và bàn giao | Làm hai trang, thử lọc và mở lại | 34 thành phần hiển thị; ảnh, kiểm tra tương tác và nghiệm thu |

Đây là dự án Excel → Python/CSV → Power BI. Không có kết quả triển khai kho dữ liệu SQL, mô hình học máy hay xuất bản lên cloud trong phạm vi này. Dữ liệu khách có trong nguồn được giữ riêng với hồ sơ khiếu nại để tránh đếm sai. Không đưa tên, ngày sinh hay mẫu từng người vào báo cáo.

## Những con số cần hiểu trước

| Chỉ số | Kết quả | Đọc đúng như thế nào |
|---|---|---|
| Hồ sơ khiếu nại | 13.846 | Số hồ sơ, không phải số khách |
| Khách trong nguồn | 12.305 | Trong đó 8.261 khách có khiếu nại |
| Có ngày hoàn tất | 13.796 | 50 hồ sơ thiếu ngày; chưa thể gọi là tồn đọng tại một ngày cụ thể |
| Thời gian trung bình | 12,85 ngày | Tính trên hồ sơ có ngày hoàn tất; ca lâu kéo số này lên |
| Thời gian trung vị | 7 ngày | Mốc giữa khi xếp thời gian từ ngắn đến dài |
| Hài lòng | 89,33% | 6.867/7.687 hồ sơ có đánh giá; không chia cho toàn bộ 13.846 |
| Có đánh giá | 55,52% | 7.687/13.846; còn 6.159 hồ sơ chưa có đánh giá |
| Ưu tiên | 552, tương đương 3,99% | Một nhóm nhỏ hơn nhiều so với nhóm còn lại |
| Có lịch sử trạng thái | 4.351, tương đương 31,42% | Có ít nhất một lần ghi nhận; chưa có nghĩa lịch sử đầy đủ |

Nguồn có 11.558 sự kiện trạng thái. Một hồ sơ có thể có nhiều sự kiện nên số này không phải số hồ sơ. Ngày 14/05/2020 là ngày tham chiếu đã chọn cho phân tích, không phải ngày xuất dữ liệu được nguồn xác nhận. Lịch sử còn có sự kiện ngày 15/05/2020; khi hỏi tình trạng trước đó phải loại các sự kiện xảy ra sau mốc đang xét.

## Đề bài đã trả lời đến đâu?

| Câu hỏi | Kết quả dễ hiểu | Điều cần giữ khi diễn giải |
|---|---|---|
| 1. Theo loại và mức ưu tiên | Nhóm ưu tiên trung bình 15,61 ngày, trung vị 10; nhóm còn lại 12,73 và 6 | Hai nhóm khác nhau về loại hồ sơ; chưa biết nguyên nhân |
| 2. Nhóm ít hài lòng | DISCLAIMER OF DISMISSAL có 112/155 đánh giá không hài lòng; POOR INFORMATION có 212/486 | Đây là hai nhóm đáng rà, không phải hai nhóm đứng đầu mọi bảng xếp hạng |
| 3. Mạng phân phối | Direct 7.218 hồ sơ, Brokers 4.700, Bancassurance 1.928; thời gian trung bình khoảng 12,36–12,93 ngày | Chênh lệch chưa chứng minh mạng nào làm tốt hơn |
| 4. Tồn đọng | Có 50 hồ sơ thiếu ngày hoàn tất; 21 mang trạng thái IN PROGRESS/OUTSTANDING | Chưa dựng được tồn đọng lịch sử đáng tin tại một mốc ngày |
| 5. Vùng | CA có 2.593 khiếu nại và 2.279 khách trong nguồn | 1.137,78 khiếu nại/1.000 khách có thể lớn hơn 1.000; một khách có nhiều hồ sơ |
| 6. Giá trị yêu cầu | Trung vị bằng 0; không có dòng trên một triệu theo giá trị ghi trong nguồn | Chưa biết đơn vị tiền và chưa biết số đã chi; không tự gắn ký hiệu tiền |
| 7. Nguồn tiếp nhận | Call Center trung bình 8,81 ngày với 296 hồ sơ; CRO 16,12 với 911 | Không gọi đây là nguyên nhân; nhóm 7 hồ sơ quá nhỏ để kết luận chắc |
| 8. Thời gian ở từng trạng thái | Chưa đủ dữ liệu để trả lời đáng tin | Tuổi của hồ sơ khác thời gian nằm trong một trạng thái |
| 9. Sản phẩm | Capital Accumulation có 5.169 hồ sơ, Business 2.715, Health 2.701 | Nhiều khiếu nại chưa có nghĩa rủi ro cao nếu chưa biết số khách được bảo hiểm |
| 10. Đặc điểm khách | Có 491 hồ sơ tính ra tuổi âm và 193 thiếu tuổi | Cần xác nhận quy tắc ngày sinh; không đoán nguyên nhân hoặc tự sửa |

Tên nhóm tiếng Anh được giữ theo nguồn để tra đúng hồ sơ; ý nghĩa nghiệp vụ chi tiết cần chủ dữ liệu xác nhận. Nhóm PERFORMANCE / USE OF SITE có 100% không hài lòng nhưng chỉ có một đánh giá trong ba hồ sơ, nên không chọn nó chỉ vì tỷ lệ lớn. Hai nhóm gợi ý ở câu 2 có tỷ lệ không hài lòng lần lượt 72,26% và 43,62%; tỷ lệ có đánh giá cũng khác nhau. Dữ liệu hiện mô tả điều xảy ra trong mẫu, chưa chứng minh nguyên nhân hoặc đại diện toàn bộ khách được bảo hiểm.

## Nên hành động thế nào?

| Việc đề xuất | Vì sao | Cách biết có tiến bộ | Phần chưa được chốt |
|---|---|---|---|
| Rà nội dung trao đổi ở hai nhóm câu 2 | Nhiều đánh giá không hài lòng; thời gian trung bình 23,82 và 22,53 ngày | Ghi lý do phải làm lại; theo dõi thời gian và đánh giá, kèm số hồ sơ | Chủ việc, số hồ sơ cần rà và mục tiêu cải thiện |
| Xem kỹ hàng đợi ưu tiên và CRO | Nhóm ưu tiên trong mẫu xử lý lâu hơn nhóm còn lại | So sánh cùng loại, nguồn và kỳ; theo dõi trung vị cùng số hồ sơ | Nguyên nhân chậm; chưa có bằng chứng tách hàng đợi sẽ giúp |
| Chốt quy tắc ngày sinh và ghi lịch sử | Tuổi bất thường; 9.495 hồ sơ không có lịch sử trạng thái | Theo dõi tỷ lệ dữ liệu hợp lệ và mức đầy đủ lịch sử | Quy tắc nghiệp vụ, trách nhiệm cập nhật và mốc đo |

**Việc quan trọng nhất tiếp theo:** chọn một nhóm cần rà và xác nhận cách hiểu nhóm đó với chủ dữ liệu trước khi thay đổi quy trình. Các đề xuất chưa được triển khai và chưa có hiệu quả đo được. Nếu thử thay đổi, cần ghi mức hiện tại, kỳ đo và cách so sánh công bằng trước; không tự đặt mức cải thiện hay tuyên bố tiết kiệm tiền.

## Dashboard đã được kiểm như thế nào?

Hai trang là **Executive Summary — Tổng quan** và **Operation Drill-down — Xem sâu vận hành**. Đã thử chọn CA rồi xóa chọn, chọn năm 2019 cùng APPLICATION REQUEST trên cả hai trang, chọn Urgent cùng Email và chuyển trang bằng nút thật. Nhóm năm 2019 cùng APPLICATION REQUEST có 32 hồ sơ; nhóm Urgent cùng Email có 62. Khi bỏ bộ lọc, số tổng trở về 13.846. Đóng rồi mở lại vẫn giữ đúng giao diện và số liệu.

Đã đối chiếu 22 công thức, định dạng và nhóm công thức sau mở lại; 22 file được bảo vệ vẫn giữ nguyên. Công thức cộng từ đầu năm đã thử với nhóm có dữ liệu tháng trước: 552 hồ sơ riêng tháng 3 mở rộng thành 708 từ đầu năm. Kiểm tra cấu trúc không có lỗi và có một cảnh báo vì chưa tải được mẫu kiểm tra cho một phiên bản thành phần hiển thị; phần đó bị bỏ qua. Vì vậy không gọi đây là kiểm tra cấu trúc đầy đủ, dù hình ảnh, số, thao tác lọc và lưu/mở lại đã được kiểm riêng.

Bằng chứng: [QA cuối](../Log/phase5/supervisor/qa_final.json), [đối chiếu model](../Log/phase5/supervisor/model_verification.json), [phân tích gốc](../Log/phase5/analysis.json), [ảnh Tổng quan](../reports/phase5/supervisor/after_reopen/Executive%20Summary.png), [ảnh Vận hành](../reports/phase5/supervisor/after_reopen/Operation%20Drill-down.png).

## Công nghệ và cách làm đã dùng

| Thành phần | Công dụng trong dự án |
|---|---|
| Excel, Python, CSV, notebook | Đọc nguồn, chuẩn hóa và tính đối chiếu độc lập |
| Power BI, DAX | Hiển thị và tính lại số theo nhóm người xem chọn |
| TMDL, PBIR, PBIP | Lưu model, report và dự án thành file có thể kiểm tra |
| Modeling MCP, Desktop Bridge | Thao tác model và kiểm report trên Desktop; hai khả năng khác nhau |
| PowerShell, kiểm tra hash | Chụp đúng cửa sổ và kiểm file quan trọng không bị thay đổi |
| OpenCode và Codex | Worker triển khai; supervisor review và tiếp quản dashboard theo quyền đã duyệt |

Báo cáo áp dụng skill **end-to-end-data-analytics-portfolio** để nối phát hiện → bằng chứng → đề xuất → giới hạn, và **eli5** để diễn giải. Các nguyên tắc DA như kiểm chất lượng, đếm đúng đối tượng, so sánh đúng nhóm và kể lại kết quả được giải thích trong [hướng dẫn DA](07_da_explained.md). Giữ kế hoạch hiện có thay vì tạo lại cấu trúc kho dữ liệu, học máy hay website chỉ để đủ mẫu của skill.

## Bài học dùng lại và phần chưa thử

[DAFlowAuto](<C:/Users/LE HOANG GIA VI/.agents/skills/daflowauto/SKILL.md>) gom quy trình; [bài học có bằng chứng](<C:/Users/LE HOANG GIA VI/.agents/skills/daflowauto/references/verified-lessons.md>) giữ các lỗi cụ thể. “100%” chỉ có thể hiểu là bao phủ đủ danh mục bài học đã rà trong dự án, không phải đảm bảo mọi dự án mới thành công. Quy tắc mới hai lượt tối đa 15 phút đã được ghi, nhưng chưa chạy một lượt giao việc mới để thử cơ chế tự gọi supervisor đúng mốc. Người dùng đã duyệt đóng gói DAFlowAuto global cho Codex và Claude Code ngày 08/10/2026; việc cài không là một lượt kiểm runtime mới.
