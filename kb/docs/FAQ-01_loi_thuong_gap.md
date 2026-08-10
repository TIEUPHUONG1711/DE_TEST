# FAQ-01 — Các lỗi thường gặp và cách xử lý

**Công ty Tài chính Sao Đỏ — Phòng CNTT** · Cập nhật: 07/2026

## 1. `ERR ConnTimeout db-primary`

- **Ý nghĩa:** dịch vụ không kết nối được database chính trong thời gian chờ (thường 30 giây).
- **Nguyên nhân hay gặp:** database quá tải giờ cao điểm; hết connection pool; sự cố mạng nội bộ.
- **Xử lý:** kiểm tra tải database trên dashboard → nếu quá tải, KHÔNG restart dịch vụ (làm bão kết nối nặng thêm); liên hệ DBA trực. Nếu chỉ 1 dịch vụ bị → kiểm tra connection pool của dịch vụ đó.

## 2. `ERR AuthTokenExpired`

- **Ý nghĩa:** phiên đăng nhập của người dùng hết hạn. Đây là lỗi **bình thường** ở mức thấp; chỉ bất thường khi tăng đột biến (nghi lệch giờ hệ thống).

## 3. `ERR HTTP 502 upstream=payment-api`

- **Ý nghĩa:** web-portal gọi payment-api không được. Hầu như luôn là **hệ quả** của sự cố ở payment-api — xử lý gốc ở payment-api trước, không xử lý ở web-portal.

## 4. `ERR NullPointer in ReportBuilder`

- **Ý nghĩa:** job báo cáo cuối ngày gặp dữ liệu đầu vào thiếu. Xem RUN-01 để chạy lại job sau khi bổ sung dữ liệu.

## 5. `ERR SMTPConnRefused`

- **Ý nghĩa:** không kết nối được mail gateway. Kiểm tra mail-gw trước; email chưa gửi nằm lại queue và tự gửi lại khi kết nối phục hồi.
