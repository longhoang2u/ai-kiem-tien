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

- `CLAUDE.md`: bản mẫu "hiến pháp" cho agent của bạn. Bản gốc từng chạy thật nằm ở `da-khai-tu/CLAUDE-ban-goc.md`.
- `chay-luot.sh`: một lượt chạy theo lịch launchd. Lượt dài tối đa 110 phút, nối tiếp cùng phiên, tự ghi chi phí AI vào sổ. Muốn dừng khẩn cấp thì tạo tệp `DUNG`.
- `chinh-sach.json`: hạn mức chi theo hạng mục, theo ngày và theo tháng, cùng ngưỡng tiết kiệm, sinh tồn và dừng.
- `kiem-soat/vi.py`: sổ cái chỉ-ghi-thêm trên SQLite. Agent chỉ được xin chi và ghi chi. Thu tiền chỉ ghi từ giao dịch ngân hàng, agent không tự ghi.
- `kiem-soat/nhap-giao-dich.py`: kéo đơn đã trả tiền từ máy chủ bán hàng vào sổ. Đặt hai biến `NGUON_DON_URL` và `NGUON_DON_KHOA`.
- `kinh-doanh/kiem-bang-viec.py`: ép agent giữ bảng việc thật, không ngồi chơi.
- `kinh-doanh/nhat-ky-cong-khai/`: nhật ký agent tự viết mỗi ngày.
- `may-chu/kiem-tien/`: trang nhật ký công khai. Bộ dựng dữ liệu có lọc riêng tư (giấu khoá, IP, email, số tài khoản).
- `kinh-doanh/`: chỗ làm việc của agent. Kế hoạch, bảng việc, cơ hội và nhật ký đều để trống, agent tự điền.
- `da-khai-tu/`: lịch launchd và hiến pháp gốc.

Các sản phẩm agent từng bán không nằm trong kho này.

## Chạy trong 5 phút

Cần: máy Mac hoặc Linux, Python 3, [Claude Code](https://claude.com/claude-code) đã đăng nhập (gói Claude hoặc khoá API).

**1. Tải về, kiểm thử**

```bash
git clone https://github.com/longhoang2u/ai-kiem-tien.git
cd ai-kiem-tien
python3 kiem-soat/test_vi.py
```

**2. Viết luật cho agent.** Mở `CLAUDE.md`, sửa các chỗ trong [ngoặc vuông]: tên bạn, số vốn, và quan trọng nhất là mục "Tài sản bạn được dùng" (bạn đang có sản phẩm gì, kênh nào, bao nhiêu người xem). Agent không có tài sản sẵn thì rất khó ra tiền.

**3. Đặt hạn mức.** Sửa `chinh-sach.json`: vốn, hạn mức chi mỗi ngày và mỗi tháng, mức tự duyệt. Rồi nạp vốn vào sổ:

```bash
python3 kiem-soat/vi.py nap-von --so-tien 2000000 --bang-chung "vốn ban đầu"
python3 kiem-soat/vi.py bao-cao
```

**4. Chạy một lượt bằng tay.** Lượt đầu agent sẽ tự viết kế hoạch và sinh việc vào `kinh-doanh/BANG-VIEC.md`.

```bash
bash chay-luot.sh
tail -50 nhat-ky/luot-$(date +%F).log
```

Một lượt chạy tối đa 110 phút và tốn tiền AI thật. Xem chi phí bằng `vi.py bao-cao`. Muốn dừng thì `touch DUNG`.

**5. Cho chạy theo lịch (macOS).** Sửa `TEN_BAN` và đường dẫn trong `da-khai-tu/vn.aiauto.luot.plist`, rồi:

```bash
cp da-khai-tu/vn.aiauto.luot.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/vn.aiauto.luot.plist
```

Trên Linux thì dùng cron: `0 */2 * * * bash /đường/dẫn/ai-kiem-tien/chay-luot.sh`.

**Tuỳ chọn:**
- Ghi tiền khách trả từ máy chủ bán hàng: đặt `NGUON_DON_URL`, `NGUON_DON_KHOA`, rồi chạy `bash kiem-soat/nhap-giao-dich.sh`. Máy chủ phải trả JSON dạng `{"don":[{"ma","trang_thai","giao_dich":[{"id","so_tien","noi_dung"}]}]}`.
- Trang nhật ký công khai: `node may-chu/kiem-tien/tao-du-lieu.mjs` dựng `web/du-lieu.json`, rồi đưa thư mục `web/` lên hosting tĩnh bất kỳ.

## Bài học

- Chi phí AI của agent tự chạy dễ vượt doanh thu rất xa. Hãy đo chi phí AI ngay từ lượt đầu tiên.
- Rào tiền phải nằm ngoài tầm tay agent: tệp khoá, lệnh bị cấm, thu tiền chỉ ghi từ ngân hàng.
- Agent làm được việc. Nhưng tìm khách thật mà không spam là khâu khó nhất.

Người làm: Hoàng Long, hoanglongteam.com/bio

Giấy phép MIT.
