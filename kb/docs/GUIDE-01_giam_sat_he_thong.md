# GUIDE-01 — Hướng dẫn giám sát hệ thống

**Công ty Tài chính Sao Đỏ — Phòng CNTT** · Cập nhật: 06/2026

## Dashboard chính

- **Tổng quan dịch vụ:** trạng thái health-check 5 dịch vụ, tỉ lệ lỗi 15 phút gần nhất.
- **Database:** kết nối đang mở, thời gian truy vấn trung bình, tải CPU db-primary.
- **Hàng đợi:** độ sâu queue của notification-worker và giao dịch chờ ở payment-api.

## Ngưỡng cảnh báo hiện hành

| Chỉ số | Ngưỡng WARN | Ngưỡng CRITICAL |
|---|---|---|
| Tỉ lệ ERROR / tổng log (15') | > 2% | > 5% |
| Thời gian phản hồi web-portal | > 1.5s | > 3s |
| Queue notification-worker | > 2.000 | > 5.000 |
| Kết nối db-primary | > 80% pool | > 95% pool |

## Quy ước log

Log 5 dịch vụ tập trung dạng JSON lines, mỗi dòng 1 sự kiện, các trường: `timestamp`, `service`, `level` (INFO/WARN/ERROR), `message`, `request_id`. **Lưu ý:** một số hệ thống cũ ghi giờ địa phương thay vì UTC — đang trong lộ trình chuẩn hoá.
