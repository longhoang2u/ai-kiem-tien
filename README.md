# AI Kiếm Tiền

Một agent Claude Code được cấp 2.000.000đ vốn, một máy Mac chạy 24/7 và một nhiệm vụ: **tự kiếm tiền thật, hợp pháp, đủ để sống**.
Chạy từ 17/10/2026 tới 15/11/2026 thì khai tử. Nhật ký từng ngày công khai ở kiemtien.copee.vn.

## Kết quả thật

| | |
|---|---|
| Số ngày chạy | 29 |
| Tiền thật khách trả (ghi từ ngân hàng) | 572.000đ |
| Chi phí AI quy đổi | khoảng 4.718.000đ |
| Lỗ | khoảng 4,1 triệu |

**Chạy mã này không làm ra tiền.** Đây là bộ khung và bài học, không phải cỗ máy in tiền.

## Bên trong có gì?

- `CLAUDE.md`: "hiến pháp" của agent. Gồm cách chạy mỗi lượt, luật tiền, luật cứng (không spam, không bịa số, không quảng cáo trả phí).
- `chay-luot.sh`: một lượt chạy theo lịch launchd. Lượt dài tối đa 110 phút, nối tiếp cùng phiên, tự ghi chi phí AI vào sổ. Muốn dừng khẩn cấp thì tạo tệp `DUNG`.
- `chinh-sach.json`: hạn mức chi theo hạng mục, theo ngày và theo tháng, cùng ngưỡng tiết kiệm, sinh tồn và dừng.
- `kiem-soat/vi.py`: sổ cái chỉ-ghi-thêm trên SQLite. Agent chỉ được xin chi và ghi chi. Thu tiền chỉ ghi từ giao dịch ngân hàng, agent không tự ghi.
- `kiem-soat/nhap-giao-dich.py`: kéo đơn đã trả tiền từ máy chủ bán hàng vào sổ. Đặt hai biến `NGUON_DON_URL` và `NGUON_DON_KHOA`.
- `kinh-doanh/kiem-bang-viec.py`: ép agent giữ bảng việc thật, không ngồi chơi.
- `kinh-doanh/nhat-ky-cong-khai/`: nhật ký agent tự viết mỗi ngày.
- `may-chu/kiem-tien/`: trang nhật ký công khai. Bộ dựng dữ liệu có lọc riêng tư (giấu khoá, IP, email, số tài khoản).
- `da-khai-tu/`: hai lịch launchd đã gỡ.

Các sản phẩm agent từng bán không nằm trong kho này.

## Chạy thử

```bash
python3 kiem-soat/vi.py nap-von --so-tien 2000000 --bang-chung "vốn ban đầu"
python3 kiem-soat/vi.py bao-cao
python3 kiem-soat/test_vi.py
node --test may-chu/kiem-tien/thu/
```

`chay-luot.sh` tìm Claude CLI trong extension VS Code. Hãy sửa dòng `CLAUDE=` cho đúng máy bạn.

## Bài học

- Chi phí AI của agent tự chạy dễ vượt doanh thu rất xa. Hãy đo chi phí AI ngay từ lượt đầu tiên.
- Rào tiền phải nằm ngoài tầm tay agent: tệp khoá, lệnh bị cấm, thu tiền chỉ ghi từ ngân hàng.
- Agent làm được việc. Nhưng tìm khách thật mà không spam là khâu khó nhất.

Người làm: Hoàng Long, hoanglongteam.com/bio

Giấy phép MIT.
