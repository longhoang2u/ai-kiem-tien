# Bảng việc (agent tự cập nhật MỖI lượt)

LUẬT:
- CHỜ chỉ chứa việc CHƯA làm. Bắt đầu → chuyển sang ĐANG LÀM (giờ bắt đầu). Xong → chuyển sang XONG (giờ xong + bằng chứng). Bỏ → sang XONG, ghi lý do.
- Cấm gạch ngang (~~) hay ghi "đã xong" mà để lại trong CHỜ.
- Mỗi lượt chạy `python3 kinh-doanh/kiem-bang-viec.py`: CHỜ dưới 5 việc thì sinh thêm việc có nguồn; việc CHỜ quá 3 ngày phải làm hoặc bỏ.
- Giờ ghi dạng `HH:MM DD/MM`.
- Ô Việc viết `Câu dễ hiểu » chi tiết kỹ thuật`. Câu dễ hiểu ≤ 15 chữ, không tên tệp, không mã.

## CHỜ
| # | Việc (thí nghiệm) | Khâu | Kỳ vọng (số nào tăng) | Tạo lúc | Hạn đo | Nguồn sinh việc |
|---|---|---|---|---|---|---|

## ĐANG LÀM
| # | Việc | Bắt đầu | Ghi chú |
|---|---|---|---|

## XONG (mới nhất ở trên)
| # | Việc | Xong lúc | Bằng chứng | Kết quả |
|---|---|---|---|---|
