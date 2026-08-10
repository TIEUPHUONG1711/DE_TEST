# SOP-01 — Quy trình khởi động lại dịch vụ

**Công ty Tài chính Sao Đỏ — Phòng CNTT** · Ban hành: 03/2026 · Người duyệt: Trưởng phòng Vận hành

## Phạm vi

Áp dụng cho 5 dịch vụ nội bộ: `auth-service`, `payment-api`, `web-portal`, `batch-report`, `notification-worker`.

## Quy trình chuẩn (theo thứ tự, KHÔNG bỏ bước)

1. Kiểm tra dashboard giám sát (xem GUIDE-01) — xác nhận dịch vụ thực sự bất thường, không phải cảnh báo giả.
2. Thông báo vào kênh `#ops-alert` trước khi thao tác: tên dịch vụ, lý do, thời gian dự kiến.
3. Với `payment-api`: **bắt buộc** kiểm tra không còn giao dịch đang xử lý (queue = 0) trước khi restart. Restart khi còn giao dịch treo có thể gây lệch số dư.
4. Chạy lệnh restart theo runbook của từng dịch vụ. Chờ health-check xanh (tối đa 5 phút).
5. Xác nhận log không còn lỗi lặp lại trong 10 phút sau restart.
6. Ghi nhận sự cố vào hệ thống ticket: thời gian, nguyên nhân sơ bộ, người thao tác.

## Trường hợp restart KHÔNG giải quyết được

Không restart quá 2 lần liên tiếp. Sau lần thứ 2 vẫn lỗi → chuyển escalation mức 2 (xem SOP-02).
