# RUN-01 — Runbook job báo cáo cuối ngày (batch-report)

**Công ty Tài chính Sao Đỏ — Phòng CNTT** · Cập nhật: 05/2026

## Lịch chạy

- Job `batch-report` chạy **23:00 hằng ngày**, tổng hợp giao dịch trong ngày thành báo cáo gửi Ban điều hành lúc 07:00 sáng hôm sau.
- Job phụ thuộc dữ liệu từ `payment-api` (bảng giao dịch) và `auth-service` (bảng phiên đăng nhập).

## Khi job lỗi (`ERR NullPointer in ReportBuilder`)

1. Kiểm tra dữ liệu đầu vào ngày đó có thiếu không (thường do sự cố payment-api trong ngày làm hụt giao dịch).
2. Nếu thiếu dữ liệu: chờ dữ liệu được bổ sung/đồng bộ lại, **không** chạy lại job ngay.
3. Chạy lại job bằng lệnh rerun theo ngày: job tự xoá kết quả cũ của ngày đó trước khi tính lại (an toàn chạy lại nhiều lần).
4. Xác nhận báo cáo sinh đủ số dòng so với ngày thường (800–1.200 dòng) trước khi gửi.

## Lưu ý mùa cao điểm

Cuối tháng số giao dịch tăng ~40% — thời gian chạy job dài hơn bình thường, không coi là bất thường nếu xong trước 01:00.
