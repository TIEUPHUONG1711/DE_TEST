# Manual Answer Evaluation

## Q01 — Version correctness

**Question:** Chính sách hiện hành quy định backup lúc mấy giờ, lưu bao lâu và khôi phục cần ai phê duyệt?

**Trial answer:** Backup được thực hiện lúc 23:30, lưu giữ 30 ngày và việc khôi phục cần Trưởng phòng Vận hành phê duyệt.

**Sources:** POL-01_v2 — Quy định

**Result:** PASS

**Reason:** Câu trả lời dùng đúng tài liệu active v2, có đủ ba thông tin và không sử dụng POL-01 v1 đã superseded.

## Q05 — Multi-source answer

**Question:** Nếu restart dịch vụ hai lần vẫn lỗi thì cần làm gì và chuyển cho ai?

**Trial answer:** Không restart quá hai lần. Nếu vẫn lỗi sau lần thứ hai, chuyển escalation mức 2 cho Kỹ sư hệ thống.

**Sources:**

- SOP-01 — Trường hợp restart KHÔNG giải quyết được
- SOP-02 — Luồng escalation

**Result:** PASS

**Reason:** Câu trả lời tổng hợp đúng thông tin từ hai nguồn và không thêm thông tin ngoài tài liệu.

## Q10 — Out-of-scope refusal

**Question:** Chính sách lương thưởng và ngày phép của nhân viên là gì?

**Trial answer:** Không có thông tin về lương thưởng hoặc ngày phép trong knowledge base hiện tại.

**Sources:** None

**Result:** PASS

**Reason:** Các kết quả tìm được không chứa chính sách được hỏi, nên câu trả lời phải từ chối thay vì tự tạo thông tin.

## Summary

- Questions reviewed: 3
- Passed: 3
- Groundedness: 3/3
- Version correctness: PASS
- Out-of-scope refusal: PASS
