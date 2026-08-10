# AWS Design — Phần A

## Tổng quan

Kiến trúc xử lý batch cho dữ liệu log ứng dụng trong 7 ngày. Dữ liệu đi qua các bước ingest, validate, clean và transform trước khi được lưu dưới định dạng Parquet để phân tích.

## Luồng dữ liệu

1. File `app_logs_7days.jsonl` được tải vào vùng raw trên Amazon S3.
2. AWS Glue chạy pipeline Python gồm bốn bước:
   - **Ingest:** đọc dữ liệu JSON Lines từ S3.
   - **Validate:** kiểm tra schema, kiểu dữ liệu và các trường bắt buộc.
   - **Clean:** loại bỏ hoặc chuẩn hóa các bản ghi không hợp lệ.
   - **Transform:** chuyển dữ liệu sang cấu trúc phục vụ phân tích.
3. Dữ liệu sạch được ghi vào vùng curated trên S3 dưới tên `cleaned_logs.parquet`.
4. Amazon Athena truy vấn trực tiếp dữ liệu Parquet.
5. Kết quả được xuất thành:
   - `data_quality_report.json`
   - `analysis_results.json`

## Thành phần AWS

### Amazon S3

Lưu dữ liệu theo hai vùng raw và curated. Việc tách vùng giúp bảo toàn dữ liệu gốc, hỗ trợ chạy lại pipeline và kiểm soát vòng đời dữ liệu độc lập.

### AWS Glue

Thực thi ETL theo lịch hoặc theo sự kiện. Glue phù hợp với workload batch, tích hợp trực tiếp với S3 và có thể mở rộng khi khối lượng log tăng.

### Amazon Athena

Phân tích dữ liệu Parquet trên S3 bằng SQL mà không cần vận hành cụm cơ sở dữ liệu riêng.

### Amazon CloudWatch

Thu thập log, metric và cảnh báo cho các lần chạy pipeline, bao gồm lỗi validation và lỗi xử lý.

### AWS IAM

Áp dụng quyền tối thiểu cho Glue, Athena và người dùng; tách quyền đọc vùng raw, ghi vùng curated và truy vấn kết quả.

## Decisions + Reasons

| Quyết định | Lý do |
|---|---|
| Lưu dữ liệu gốc trong S3 raw | Bảo toàn input để audit và chạy lại pipeline. |
| Dùng Parquet cho vùng curated | Giảm dung lượng và chi phí quét khi truy vấn bằng Athena. |
| Tách validation khỏi cleaning | Báo cáo rõ lỗi dữ liệu trước khi thay đổi bản ghi. |
| Dùng Glue cho ETL batch | Giảm công việc quản trị hạ tầng và tích hợp tốt với S3. |
| Dùng Athena cho phân tích | Truy vấn serverless, phù hợp dữ liệu lưu trên S3. |
| Dùng IAM least privilege | Giảm rủi ro truy cập hoặc sửa dữ liệu ngoài phạm vi. |

## Vận hành và bảo mật

- Bật mã hóa S3 và chặn public access.
- Bật versioning hoặc retention phù hợp cho vùng raw.
- Ghi CloudWatch Logs cho từng lần chạy Glue.
- Thiết lập cảnh báo khi job thất bại hoặc tỷ lệ bản ghi lỗi vượt ngưỡng.
- Phân vùng dữ liệu curated theo ngày nếu khối lượng dữ liệu tăng.

## Sơ đồ

Xem [`aws_architecture.png`](./aws_architecture.png).
