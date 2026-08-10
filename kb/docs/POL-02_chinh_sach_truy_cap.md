# POL-02 — Chính sách truy cập hệ thống

**Công ty Tài chính Sao Đỏ — Phòng CNTT** · Phiên bản 1.1 · Ban hành: 02/2026

## Quy định chung

1. Tài khoản cấp theo nguyên tắc **quyền tối thiểu** — chỉ đúng hệ thống phục vụ công việc.
2. Truy cập database production: chỉ nhóm DBA và kỹ sư hệ thống mức 2 trở lên; mọi truy cập được ghi log.
3. Mật khẩu đổi mỗi 90 ngày; bắt buộc xác thực 2 lớp với truy cập từ ngoài mạng nội bộ.
4. Tài khoản không hoạt động 30 ngày bị khoá tự động.
5. Nhân viên nghỉ việc: khoá toàn bộ tài khoản **trong ngày làm việc cuối cùng**.

## Với đối tác bên ngoài

Đối tác (như đội POC của nhà cung cấp) chỉ được cấp **dữ liệu đã che thông tin định danh khách hàng** (masking) và làm việc trên môi trường tách biệt, không kết nối production.
