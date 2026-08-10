# SOP-02 — Quy trình escalation sự cố

**Công ty Tài chính Sao Đỏ — Phòng CNTT** · Ban hành: 04/2026

## Phân mức sự cố

| Mức | Định nghĩa | Ví dụ | Thời hạn phản ứng |
|---|---|---|---|
| **P1** | Dịch vụ thanh toán hoặc đăng nhập ngưng toàn bộ | payment-api down, khách không giao dịch được | 15 phút, mọi khung giờ |
| **P2** | Một dịch vụ suy giảm rõ, có ảnh hưởng khách hàng | lỗi tăng đột biến ở 1 dịch vụ, chậm bất thường | 1 giờ trong giờ hành chính |
| **P3** | Bất thường không ảnh hưởng trực tiếp khách hàng | job báo cáo lỗi, queue email dồn | Ngày làm việc kế tiếp |

## Luồng escalation

1. **Mức 1 — Vận hành trực ca:** nhận cảnh báo, chẩn đoán theo FAQ-01, xử lý theo SOP-01.
2. **Mức 2 — Kỹ sư hệ thống:** khi mức 1 không xử được sau 2 lần thử, hoặc sự cố P2 trở lên.
3. **Mức 3 — Trưởng phòng Vận hành + nhà cung cấp:** sự cố P1, hoặc P2 quá 4 giờ chưa khắc phục.

Mọi sự cố P1/P2 phải có báo cáo post-mortem trong 3 ngày làm việc.
