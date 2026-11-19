#!/usr/bin/env python3
"""Nhập tiền khách đã trả (đơn chamdiem đã xác nhận bằng giao dịch ngân hàng) vào sổ cái.
Chạy ở đầu mỗi lượt (chay-luot.sh) và có thể chạy tay. Trùng mã giao dịch thì sổ cái tự bỏ qua."""
import json, os, subprocess, sys, urllib.request
GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Máy chủ bán hàng trả danh sách đơn đã trả tiền. Bản công khai không kèm máy chủ: tự đặt hai biến này.
khoa = os.environ["NGUON_DON_KHOA"]
req = urllib.request.Request(os.environ["NGUON_DON_URL"],
                             headers={"Authorization": "Bearer " + khoa})
don = json.load(urllib.request.urlopen(req, timeout=30))["don"]
moi = 0
for d in don:
    if d.get("trang_thai") not in ("da-tra", "dang-cham", "xong"):
        continue
    # Đơn thử của phiên dựng khung (nguồn bắt đầu bằng "thu" / "kiem-thu") KHÔNG phải doanh thu.
    if str(d.get("nguon") or "").startswith(("thu", "kiem-thu")):
        continue
    for g in d.get("giao_dich", []):
        if not g.get("so_tien") or g["so_tien"] <= 0:
            continue
        tay = str(g["id"]).startswith("chu-")
        kq = subprocess.run([sys.executable, os.path.join(GOC, "kiem-soat", "vi.py"), "ghi-thu",
                             "--so-tien", str(int(g["so_tien"])), "--ma-giao-dich", "VCB-" + str(g["id"]),
                             "--nguon", "chu" if tay else "ngan-hang",
                             "--bang-chung", ("anh Long bấm 'Đã nhận tiền' sau khi thấy Vietcombank báo: " if tay else "webhook ngân hàng: ") + g.get("noi_dung", ""),
                             "--ghi-chu", "đơn chamdiem " + d["ma"]], capture_output=True, text=True).stdout.strip()
        if kq.startswith("đã ghi"):
            moi += 1
print("nhập giao dịch: %d đơn trên máy chủ, %d khoản mới vào sổ" % (len(don), moi))
