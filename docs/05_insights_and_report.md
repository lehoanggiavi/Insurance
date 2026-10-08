# Bàn giao InsuranceOps — đọc và dùng dashboard

**Đã nghiệm thu:** bạn xác nhận “ổn rồi” sau khi supervisor hoàn thành dashboard và kiểm tra cuối. Hai trang đã lưu trong [InsuranceOps.pbip](../pbi/InsuranceOps.pbip). File thử trước đó và các trạng thái chờ duyệt cũ trong log là lịch sử.

## Đã làm được gì?

Dự án giống một tủ hồ sơ đã được sắp xếp và gắn nhãn. Trang **Executive Summary — Tổng quan** cho biết lượng khiếu nại, thời gian xử lý và đánh giá của khách. Trang **Operation Drill-down — Xem sâu vận hành** giúp xem theo nguồn, loại và mức ưu tiên. Các ô chọn giống việc lấy một nhóm hồ sơ ra khỏi tủ để đếm riêng. Dashboard có 13.846 hồ sơ khi bỏ mọi chọn; đó là số hồ sơ, không phải số người.

## Mở và sử dụng

1. Mở file PBIP bằng Power BI Desktop; nếu chuyển máy, xem đường dẫn dữ liệu trong [hướng dẫn model](03_semantic_model.md).
2. Bắt đầu ở Tổng quan. Khi đọc tỷ lệ hài lòng **89,33%**, đọc kèm **55,52% hồ sơ có đánh giá**.
3. Chọn năm 2019 và APPLICATION REQUEST: có **32 hồ sơ**. Bỏ chọn để trở về toàn bộ.
4. Sang Vận hành, bỏ các chọn trước rồi chọn Urgent và Email: có **62 hồ sơ**, thời gian trung bình **14,23 ngày**, trung vị **8,5 ngày**.
5. Dùng nút chuyển trang; trong chế độ chỉnh sửa Desktop có thể cần giữ Ctrl khi bấm nút. Bỏ chọn trước khi so nhóm khác.

**CA** có 2.593 hồ sơ và 2.279 khách trong nguồn. Số hồ sơ trên 1.000 khách có thể lớn hơn 1.000 vì một khách có nhiều hồ sơ. Trung bình **12,85 ngày** và trung vị **7 ngày** trả lời hai câu khác nhau: thời gian tính bình quân và mốc giữa của các hồ sơ đã hoàn tất. Các giá trị này được tính lại khi bạn lọc, nên hãy xem điều kiện chọn trước khi so số.

## Đã kiểm được gì?

Đã chọn/xóa bộ lọc thật, chuyển trang và đối chiếu các nhóm 32, 62 và CA với dữ liệu nguồn. Đã đóng rồi mở lại để kiểm giao diện và số còn đúng. Cả 22 công thức cùng cách hiển thị được đối chiếu; 22 file cần bảo vệ không đổi. Công thức từ đầu năm cũng được thử với dữ liệu các tháng trước, không chỉ nhóm có một tháng. [QA cuối](../Log/phase5/supervisor/qa_final.json) và [ảnh hai trang](../reports/phase5/supervisor/after_reopen/) giữ bằng chứng.

## Chưa thể kết luận gì?

50 hồ sơ thiếu ngày hoàn tất chưa tự chứng minh tồn đọng tại một ngày cụ thể. Chỉ 31,42% hồ sơ có ít nhất một sự kiện lịch sử nên chưa tính đáng tin thời gian ở từng trạng thái. Giá trị yêu cầu chưa có đơn vị tiền được xác nhận. Nhóm ưu tiên xử lý lâu hơn trong mẫu chưa nói được nguyên nhân. Một phần kiểm cấu trúc bị bỏ qua do không tải được mẫu kiểm cho phiên bản hiển thị; hình ảnh, số, lọc và lưu/mở lại được kiểm riêng. Chưa xuất bản lên cloud hoặc đo hiệu quả cải thiện vận hành.

## Đọc tiếp ở đâu?

- [Báo cáo dự án PDF](../reports/project_report/InsuranceOps_Project_Report.pdf) và [source TEX](../reports/project_report/InsuranceOps_Project_Report.tex): 10 câu hỏi, phát hiện, đề xuất và cách đo tiếp; [Markdown](06_project_report.md) là nội dung nguồn/tra cứu.
- [Giải thích DA bằng ví dụ](07_da_explained.md): hiểu mẫu số, trung vị, nhóm đang xét và các cách làm.
- Tài liệu 01–04 giữ phần kỹ thuật; log lịch sử được giữ để tra khi cần.

Script sinh report cũ chưa đồng bộ hoàn toàn với phần giao diện sửa trực tiếp cuối dự án; không chạy lại chỉ để mở dashboard. Phần bàn giao giúp bạn đọc sản phẩm hiện có, không yêu cầu dựng lại pipeline. [DAFlowAuto](<C:/Users/LE HOANG GIA VI/.agents/skills/daflowauto/SKILL.md>) đã được người dùng duyệt và cài global cho Codex và Claude Code ngày 08/10/2026.
