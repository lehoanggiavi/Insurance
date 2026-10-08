# InsuranceOps — phân tích khiếu nại bảo hiểm

[Xem trang dự án](https://lehoanggiavi.github.io/Insurance/) · [Báo cáo PDF](reports/project_report/InsuranceOps_Project_Report.pdf) · [Power BI PBIP](pbi/InsuranceOps.pbip)

Phân tích 13.846 hồ sơ khiếu nại bằng Python và Power BI, nối các chỉ số xử lý, đánh giá khách hàng và độ phủ lịch sử với đề xuất vận hành.

## Phát hiện và đề xuất

- Thời gian xử lý trung bình 12,85 ngày, trung vị 7 ngày: cần xem kỹ nhóm hồ sơ kéo dài; chênh lệch này chưa chứng minh nguyên nhân.
- 89,33% hài lòng trên 7.687 hồ sơ có đánh giá; độ phủ đánh giá chỉ 55,52%. Theo dõi đồng thời tỷ lệ và độ phủ, không suy rộng sang toàn bộ hồ sơ.
- 31,42% hồ sơ có ít nhất một sự kiện lịch sử trạng thái. Ưu tiên cải thiện ghi nhận trước khi đo thời gian ở từng trạng thái.
- Đề xuất rà nhóm ưu tiên và nguồn CRO, thử một thay đổi nhỏ, đối chiếu trung bình/trung vị trên cùng phạm vi trước–sau. Chưa đo hiệu quả cải thiện đã đạt được.

## Sản phẩm

- `index.html`: trang dự án trên GitHub Pages.
- `reports/project_report/`: PDF 13 trang và nguồn LaTeX.
- `reports/phase5/supervisor/after_reopen/`: ảnh hai trang Power BI.
- `pbi/`: report PBIR, semantic model TMDL và file PBIP.
- `scripts/`, `notebooks/`: mã xử lý, phân tích và kiểm tra.
- `docs/`: định nghĩa chỉ số, cách đọc dashboard và giới hạn.

## Mở dashboard

Mở `pbi/InsuranceOps.pbip` bằng Power BI Desktop. Để Refresh cần bộ CSV trong `data/curated` của workspace gốc: vào **Transform data → Edit parameters → Data Folder**, chọn đường dẫn tới bộ CSV đó.

Dữ liệu nguồn có họ tên và ngày sinh. Repo công khai giữ mã phân tích và kết quả tổng hợp; workbook, CSV theo từng hồ sơ, log điều phối và bản sao lưu được giữ cục bộ. Không cần chạy lại script tạo report để mở bản lưu; chạy lại có thể ghi đè bố cục đã sửa trực tiếp.

Dashboard đã được duyệt và kiểm trên revision lịch sử; việc đổi thư mục và xuất bản website không là kiểm runtime Power BI mới. Website hiển thị ảnh dashboard và báo cáo, chưa phải Power BI Service tương tác. Các tham chiếu tới `Log/` trong tài liệu là bằng chứng nội bộ được giữ ở workspace gốc.
