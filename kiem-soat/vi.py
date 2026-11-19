#!/usr/bin/env python3
"""Bộ kiểm soát tài chính (Survival Controller) của agent AI AUTO KIẾM TIỀN.

Sổ cái chỉ-ghi-thêm trên SQLite. Agent chỉ được gọi các lệnh: trang-thai, xin-chi, ghi-chi, huy, bao-cao.
Các lệnh nap-von, ghi-thu, ghi-ai, duyet, tu-choi, dung, tiep-tuc chỉ do anh Long hoặc script nền gọi
(launcher không cấp quyền các lệnh này cho agent).

Tiền tính bằng VND, số nguyên.
"""
import argparse
import json
import os
import sqlite3
import sys
import time
import uuid
from datetime import datetime

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get("VI_DB", os.path.join(GOC, "du-lieu", "so-cai.db"))
CHINH_SACH = os.environ.get("VI_CHINH_SACH", os.path.join(GOC, "chinh-sach.json"))
FILE_DUNG = os.environ.get("VI_FILE_DUNG", os.path.join(GOC, "DUNG"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS but_toan (
  id INTEGER PRIMARY KEY,
  thoi_gian TEXT NOT NULL,
  loai TEXT NOT NULL CHECK (loai IN ('von','thu','chi','dieu-chinh')),
  so_tien INTEGER NOT NULL,            -- dương = tiền vào, âm = tiền ra
  hang_muc TEXT,
  ma_hanh_dong TEXT,
  nguon TEXT NOT NULL,                 -- ngan-hang | chu | agent
  ma_giao_dich TEXT UNIQUE,            -- mã ngân hàng/nhà cung cấp, chống ghi trùng
  bang_chung TEXT NOT NULL,
  tham_chieu INTEGER REFERENCES but_toan(id),
  ghi_chu TEXT
);
CREATE TABLE IF NOT EXISTS yeu_cau_chi (
  ma TEXT PRIMARY KEY,
  thoi_gian TEXT NOT NULL,
  hang_muc TEXT NOT NULL,
  loai TEXT NOT NULL,
  so_tien_toi_da INTEGER NOT NULL,
  muc_dich TEXT NOT NULL,
  nha_cung_cap TEXT NOT NULL,
  trang_thai TEXT NOT NULL,            -- da-duyet | cho-chu-duyet | tu-choi | da-chi | da-huy
  ly_do TEXT,
  het_han TEXT
);
CREATE TABLE IF NOT EXISTS chi_phi_ai (
  id INTEGER PRIMARY KEY,
  thoi_gian TEXT NOT NULL,
  usd REAL NOT NULL,
  vnd INTEGER NOT NULL,
  luot TEXT
);
CREATE TABLE IF NOT EXISTS nhat_ky (
  id INTEGER PRIMARY KEY,
  thoi_gian TEXT NOT NULL,
  tac_nhan TEXT NOT NULL,
  hanh_dong TEXT NOT NULL,
  ket_qua TEXT NOT NULL,
  chi_tiet TEXT
);
CREATE TABLE IF NOT EXISTS he_thong (khoa TEXT PRIMARY KEY, gia_tri TEXT);
CREATE TRIGGER IF NOT EXISTS khong_sua_but_toan BEFORE UPDATE ON but_toan
  BEGIN SELECT RAISE(ABORT, 'but_toan chi duoc ghi them'); END;
CREATE TRIGGER IF NOT EXISTS khong_xoa_but_toan BEFORE DELETE ON but_toan
  BEGIN SELECT RAISE(ABORT, 'but_toan chi duoc ghi them'); END;
"""


def bay_gio():
    return datetime.now().isoformat(timespec="seconds")


def nap_chinh_sach():
    with open(CHINH_SACH, encoding="utf-8") as f:
        return json.load(f)


def ket_noi():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    cn = sqlite3.connect(DB, timeout=30, isolation_level=None)
    cn.row_factory = sqlite3.Row
    cn.executescript(SCHEMA)
    return cn


def ghi_nhat_ky(cn, tac_nhan, hanh_dong, ket_qua, chi_tiet=None):
    cn.execute("INSERT INTO nhat_ky(thoi_gian,tac_nhan,hanh_dong,ket_qua,chi_tiet) VALUES(?,?,?,?,?)",
               (bay_gio(), tac_nhan, hanh_dong, ket_qua,
                json.dumps(chi_tiet, ensure_ascii=False) if chi_tiet is not None else None))


# ---------- Tính toán ----------

def tinh(cn, cs):
    so_du = cn.execute("SELECT COALESCE(SUM(so_tien),0) FROM but_toan").fetchone()[0]
    thu = cn.execute("SELECT COALESCE(SUM(so_tien),0) FROM but_toan WHERE loai='thu'").fetchone()[0]
    chi = -cn.execute("SELECT COALESCE(SUM(so_tien),0) FROM but_toan WHERE loai='chi'").fetchone()[0]
    cam_ket = cn.execute("SELECT COALESCE(SUM(so_tien_toi_da),0) FROM yeu_cau_chi WHERE trang_thai='da-duyet'").fetchone()[0]
    ai_vnd = cn.execute("SELECT COALESCE(SUM(vnd),0) FROM chi_phi_ai").fetchone()[0]
    du_phong = cs["quy_du_phong"]
    von_van_hanh_goc = cs["von_khoi_tao"] - du_phong
    kha_dung = so_du - du_phong - cam_ket
    ty_le = kha_dung / von_van_hanh_goc if von_van_hanh_goc > 0 else 0
    # Đốt tiền bảo thủ: chi trung bình/ngày trong 14 ngày gần nhất, doanh thu coi như 0.
    chi_14 = -cn.execute("SELECT COALESCE(SUM(so_tien),0) FROM but_toan WHERE loai='chi' "
                         "AND thoi_gian >= datetime('now','localtime','-14 days')").fetchone()[0]
    dot_ngay = chi_14 / 14.0
    runway = (kha_dung / dot_ngay) if dot_ngay > 0 else None
    return dict(so_du=so_du, thu=thu, chi=chi, cam_ket=cam_ket, du_phong=du_phong,
                kha_dung=kha_dung, ty_le=ty_le, ai_vnd=ai_vnd, loi_nhuan=thu - chi,
                loi_nhuan_sau_ai=thu - chi - ai_vnd, dot_ngay=dot_ngay, runway=runway)


def trang_thai_song(cn, cs, so=None):
    if os.path.exists(FILE_DUNG):
        return "KILL_SWITCH"
    r = cn.execute("SELECT gia_tri FROM he_thong WHERE khoa='tam_dung'").fetchone()
    if r and r[0] == "1":
        return "PAUSED_BY_OWNER"
    if cn.execute("SELECT 1 FROM but_toan LIMIT 1").fetchone() is None:
        return "HALTED"  # chưa nạp vốn
    so = so or tinh(cn, cs)
    if so["so_du"] < so["du_phong"]:
        return "HALTED"  # bất thường: tiền thấp hơn cả quỹ dự phòng
    n = cs["nguong"]
    if so["ty_le"] < n["dung"]:
        return "HALTED"
    if so["ty_le"] < n["sinh_ton"]:
        return "SURVIVAL_MODE"
    if so["ty_le"] < n["tiet_kiem"]:
        return "THRIFT_MODE"
    return "ACTIVE"


def da_dung(cn, dieu_kien, tham_so):
    """Tiền đã cam kết + đã chi thực tế theo điều kiện thời gian/hạng mục."""
    cam = cn.execute("SELECT COALESCE(SUM(so_tien_toi_da),0) FROM yeu_cau_chi WHERE trang_thai='da-duyet' AND "
                     + dieu_kien, tham_so).fetchone()[0]
    chi = -cn.execute("SELECT COALESCE(SUM(b.so_tien),0) FROM but_toan b JOIN yeu_cau_chi y ON y.ma=b.ma_hanh_dong "
                      "WHERE b.loai='chi' AND " + dieu_kien.replace("thoi_gian", "y.thoi_gian").replace("hang_muc", "y.hang_muc"),
                      tham_so).fetchone()[0]
    return cam + chi


# ---------- Lệnh ----------

def xin_chi(cn, cs, ma, hang_muc, loai, so_tien, muc_dich, nha_cung_cap, tac_nhan="agent"):
    """Trả về (ket_qua, ly_do). ket_qua: DUYET | CHO_CHU_DUYET | TU_CHOI."""
    cn.execute("BEGIN IMMEDIATE")
    try:
        kq, ly_do = _kiem_tra(cn, cs, ma, hang_muc, loai, so_tien, nha_cung_cap)
        if kq != "TRUNG":
            tt = {"DUYET": "da-duyet", "CHO_CHU_DUYET": "cho-chu-duyet", "TU_CHOI": "tu-choi"}[kq]
            het_han = datetime.fromtimestamp(time.time() + 72 * 3600).isoformat(timespec="seconds")
            cn.execute("INSERT INTO yeu_cau_chi VALUES(?,?,?,?,?,?,?,?,?,?)",
                       (ma, bay_gio(), hang_muc, loai, so_tien, muc_dich, nha_cung_cap, tt, ly_do, het_han))
        ghi_nhat_ky(cn, tac_nhan, "xin-chi", kq, dict(ma=ma, hang_muc=hang_muc, so_tien=so_tien, ly_do=ly_do))
        cn.execute("COMMIT")
    except Exception:
        cn.execute("ROLLBACK")
        raise
    return ("TU_CHOI", ly_do) if kq == "TRUNG" else (kq, ly_do)


def _kiem_tra(cn, cs, ma, hang_muc, loai, so_tien, nha_cung_cap):
    if cn.execute("SELECT 1 FROM yeu_cau_chi WHERE ma=?", (ma,)).fetchone():
        return "TRUNG", "mã hành động đã dùng (chống gửi lại)"
    if not isinstance(so_tien, int) or so_tien <= 0:
        return "TU_CHOI", "số tiền phải là số nguyên dương"
    so = tinh(cn, cs)
    tt = trang_thai_song(cn, cs, so)
    if tt in ("KILL_SWITCH", "PAUSED_BY_OWNER", "HALTED"):
        return "TU_CHOI", "hệ thống đang " + tt
    hm = cs["han_muc_hang_muc"]
    if hang_muc not in hm:
        return "TU_CHOI", "hạng mục không có trong chính sách: " + hang_muc
    if hang_muc == "du-phong":
        return "TU_CHOI", "agent không được dùng quỹ dự phòng"
    if tt == "SURVIVAL_MODE" and hang_muc != "ha-tang":
        return "TU_CHOI", "SURVIVAL_MODE: chỉ được chi duy trì hạ tầng"
    if nha_cung_cap not in cs["nha_cung_cap_cho_phep"]:
        return "TU_CHOI", "nhà cung cấp ngoài danh sách cho phép: " + nha_cung_cap
    han_hm = hm[hang_muc]
    if tt == "THRIFT_MODE" and hang_muc == "thu-nghiem":
        han_hm = han_hm // 2
    if so_tien > cs["han_muc_moi_lan"]:
        return "TU_CHOI", "vượt hạn mức mỗi lần %d" % cs["han_muc_moi_lan"]
    if da_dung(cn, "hang_muc=?", (hang_muc,)) + so_tien > han_hm:
        return "TU_CHOI", "vượt hạn mức hạng mục %s (%d)" % (hang_muc, han_hm)
    if da_dung(cn, "date(thoi_gian)=date('now','localtime')", ()) + so_tien > cs["han_muc_ngay"]:
        return "TU_CHOI", "vượt hạn mức ngày %d" % cs["han_muc_ngay"]
    if da_dung(cn, "strftime('%Y-%m',thoi_gian)=strftime('%Y-%m','now','localtime')", ()) + so_tien > cs["han_muc_thang"]:
        return "TU_CHOI", "vượt hạn mức tháng %d" % cs["han_muc_thang"]
    if so_tien > so["kha_dung"]:
        return "TU_CHOI", "không đủ tiền khả dụng (%d)" % so["kha_dung"]
    if (hang_muc in cs["luon_can_chu_duyet"] or loai in cs["loai_luon_can_chu_duyet"]
            or so_tien > cs["tu_dong_duyet_toi_da"]):
        return "CHO_CHU_DUYET", "cần anh Long duyệt"
    return "DUYET", "trong hạn mức"


def ghi_chi(cn, cs, ma, thuc_te, ma_giao_dich, bang_chung, tac_nhan="agent"):
    cn.execute("BEGIN IMMEDIATE")
    try:
        y = cn.execute("SELECT * FROM yeu_cau_chi WHERE ma=?", (ma,)).fetchone()
        if y is None or y["trang_thai"] != "da-duyet":
            kq = ("TU_CHOI", "không có yêu cầu chi đã duyệt mã " + ma)
        elif not bang_chung or not ma_giao_dich:
            kq = ("TU_CHOI", "thiếu bằng chứng hoặc mã giao dịch")
        elif thuc_te <= 0:
            kq = ("TU_CHOI", "số tiền thực tế phải dương")
        else:
            cn.execute("INSERT INTO but_toan(thoi_gian,loai,so_tien,hang_muc,ma_hanh_dong,nguon,ma_giao_dich,bang_chung) "
                       "VALUES(?,?,?,?,?,?,?,?)",
                       (bay_gio(), "chi", -thuc_te, y["hang_muc"], ma, tac_nhan, ma_giao_dich, bang_chung))
            cn.execute("UPDATE yeu_cau_chi SET trang_thai='da-chi' WHERE ma=?", (ma,))
            if thuc_te > y["so_tien_toi_da"]:
                # Chi lố so với hạn được duyệt: bất thường → tạm dừng hệ thống chờ anh Long xem.
                cn.execute("INSERT OR REPLACE INTO he_thong VALUES('tam_dung','1')")
                kq = ("BAT_THUONG", "chi thực tế %d vượt mức duyệt %d — đã tạm dừng hệ thống" % (thuc_te, y["so_tien_toi_da"]))
            else:
                kq = ("DA_GHI", "đã ghi chi %d" % thuc_te)
        ghi_nhat_ky(cn, tac_nhan, "ghi-chi", kq[0], dict(ma=ma, thuc_te=thuc_te, ly_do=kq[1]))
        cn.execute("COMMIT")
    except Exception:
        cn.execute("ROLLBACK")
        raise
    return kq


def ghi_thu(cn, so_tien, ma_giao_dich, bang_chung, nguon="ngan-hang", ghi_chu=None):
    """Chỉ ghi tiền đã về thật (nguồn ngân hàng đã xác minh). Trùng mã giao dịch thì bỏ qua."""
    if so_tien <= 0 or not ma_giao_dich or not bang_chung:
        return ("TU_CHOI", "thiếu số tiền/mã giao dịch/bằng chứng")
    try:
        cn.execute("INSERT INTO but_toan(thoi_gian,loai,so_tien,nguon,ma_giao_dich,bang_chung,ghi_chu) VALUES(?,?,?,?,?,?,?)",
                   (bay_gio(), "thu", so_tien, nguon, ma_giao_dich, bang_chung, ghi_chu))
    except sqlite3.IntegrityError:
        return ("TRUNG", "giao dịch đã ghi rồi")
    ghi_nhat_ky(cn, nguon, "ghi-thu", "DA_GHI", dict(so_tien=so_tien, ma_giao_dich=ma_giao_dich))
    return ("DA_GHI", "đã ghi thu %d" % so_tien)


def bao_cao(cn, cs):
    so = tinh(cn, cs)
    tt = trang_thai_song(cn, cs, so)
    cho = cn.execute("SELECT ma,hang_muc,so_tien_toi_da,muc_dich FROM yeu_cau_chi WHERE trang_thai='cho-chu-duyet'").fetchall()
    tu_choi = cn.execute("SELECT ma,ly_do FROM yeu_cau_chi WHERE trang_thai='tu-choi' "
                         "AND thoi_gian >= datetime('now','localtime','-1 day')").fetchall()
    d = lambda n: "{:,}".format(int(n)).replace(",", ".") + "đ"
    dong = [
        "Trạng thái: " + tt,
        "Tiền đã đối soát: %s (dự phòng khoá %s, đã cam kết %s)" % (d(so["so_du"]), d(so["du_phong"]), d(so["cam_ket"])),
        "Khả dụng: %s = %.0f%% vốn vận hành" % (d(so["kha_dung"]), so["ty_le"] * 100),
        "Doanh thu thực thu: %s · Chi thực tế: %s · Lãi tiền mặt: %s" % (d(so["thu"]), d(so["chi"]), d(so["loi_nhuan"])),
        "Chi phí AI quy đổi (không trừ tiền mặt): %s · Lãi sau AI: %s" % (d(so["ai_vnd"]), d(so["loi_nhuan_sau_ai"])),
        "Sống còn (bảo thủ, doanh thu = 0): " + ("chưa đốt tiền" if so["runway"] is None else "%.0f ngày" % so["runway"]),
    ]
    if cho:
        dong.append("Chờ anh Long duyệt: " + "; ".join("%s %s %s (%s)" % (r[0], r[1], d(r[2]), r[3]) for r in cho))
    if tu_choi:
        dong.append("Bị từ chối 24h qua: " + "; ".join("%s: %s" % (r[0], r[1]) for r in tu_choi))
    return "\n".join(dong)


def main(argv=None):
    p = argparse.ArgumentParser(prog="vi.py")
    sub = p.add_subparsers(dest="lenh", required=True)
    sub.add_parser("trang-thai")
    sub.add_parser("bao-cao")
    a = sub.add_parser("xin-chi")
    a.add_argument("--hang-muc", required=True)
    a.add_argument("--loai", default="mua-dich-vu")
    a.add_argument("--so-tien", type=int, required=True)
    a.add_argument("--muc-dich", required=True)
    a.add_argument("--nha-cung-cap", required=True)
    a.add_argument("--ma", default=None)
    a = sub.add_parser("ghi-chi")
    a.add_argument("--ma", required=True)
    a.add_argument("--thuc-te", type=int, required=True)
    a.add_argument("--ma-giao-dich", required=True)
    a.add_argument("--bang-chung", required=True)
    a = sub.add_parser("huy")
    a.add_argument("--ma", required=True)
    # --- Chỉ dành cho chủ / script nền ---
    a = sub.add_parser("nap-von")
    a.add_argument("--so-tien", type=int, required=True)
    a.add_argument("--bang-chung", required=True)
    a = sub.add_parser("ghi-thu")
    a.add_argument("--so-tien", type=int, required=True)
    a.add_argument("--ma-giao-dich", required=True)
    a.add_argument("--bang-chung", required=True)
    a.add_argument("--ghi-chu")
    # ngan-hang = đồng bộ ngân hàng tự động; chu = anh Long xác nhận tay sau khi thấy báo biến động số dư.
    a.add_argument("--nguon", choices=["ngan-hang", "chu"], default="ngan-hang")
    a = sub.add_parser("ghi-ai")
    a.add_argument("--usd", type=float, required=True)
    a.add_argument("--luot", default="")
    for ten in ("duyet", "tu-choi"):
        a = sub.add_parser(ten)
        a.add_argument("--ma", required=True)
    sub.add_parser("tam-dung")
    sub.add_parser("tiep-tuc")
    k = p.parse_args(argv)

    cs = nap_chinh_sach()
    cn = ket_noi()
    L = k.lenh
    if L == "trang-thai":
        so = tinh(cn, cs)
        print(json.dumps(dict(trang_thai=trang_thai_song(cn, cs, so), **so), ensure_ascii=False))
    elif L == "bao-cao":
        print(bao_cao(cn, cs))
    elif L == "xin-chi":
        ma = k.ma or "c-" + uuid.uuid4().hex[:8]
        kq, ly_do = xin_chi(cn, cs, ma, k.hang_muc, k.loai, k.so_tien, k.muc_dich, k.nha_cung_cap)
        print(json.dumps(dict(ma=ma, ket_qua=kq, ly_do=ly_do), ensure_ascii=False))
        return 0 if kq == "DUYET" else 2
    elif L == "ghi-chi":
        kq = ghi_chi(cn, cs, k.ma, k.thuc_te, k.ma_giao_dich, k.bang_chung)
        print(json.dumps(dict(ket_qua=kq[0], ly_do=kq[1]), ensure_ascii=False))
        return 0 if kq[0] == "DA_GHI" else 2
    elif L == "huy":
        n = cn.execute("UPDATE yeu_cau_chi SET trang_thai='da-huy' WHERE ma=? AND trang_thai IN ('da-duyet','cho-chu-duyet')",
                       (k.ma,)).rowcount
        ghi_nhat_ky(cn, "agent", "huy", "OK" if n else "KHONG_CO", dict(ma=k.ma))
        print("đã huỷ" if n else "không có yêu cầu để huỷ")
    elif L == "nap-von":
        if cn.execute("SELECT 1 FROM but_toan WHERE loai='von'").fetchone():
            print("đã nạp vốn rồi — nạp thêm phải là quyết định của anh Long, dùng ghi-thu nguồn chu")
            return 2
        cn.execute("INSERT INTO but_toan(thoi_gian,loai,so_tien,nguon,ma_giao_dich,bang_chung) VALUES(?,?,?,?,?,?)",
                   (bay_gio(), "von", k.so_tien, "chu", "VON-" + bay_gio(), k.bang_chung))
        ghi_nhat_ky(cn, "chu", "nap-von", "DA_GHI", dict(so_tien=k.so_tien))
        print("đã nạp vốn")
    elif L == "ghi-thu":
        print(ghi_thu(cn, k.so_tien, k.ma_giao_dich, k.bang_chung, nguon=k.nguon, ghi_chu=k.ghi_chu)[1])
    elif L == "ghi-ai":
        vnd = int(round(k.usd * cs["ty_gia_usd"]))
        cn.execute("INSERT INTO chi_phi_ai(thoi_gian,usd,vnd,luot) VALUES(?,?,?,?)", (bay_gio(), k.usd, vnd, k.luot))
        print("đã ghi AI %s USD = %d đ" % (k.usd, vnd))
    elif L in ("duyet", "tu-choi"):
        moi = "da-duyet" if L == "duyet" else "tu-choi"
        n = cn.execute("UPDATE yeu_cau_chi SET trang_thai=?, ly_do='anh Long quyết' WHERE ma=? AND trang_thai='cho-chu-duyet'",
                       (moi, k.ma)).rowcount
        ghi_nhat_ky(cn, "chu", L, "OK" if n else "KHONG_CO", dict(ma=k.ma))
        print("xong" if n else "không có yêu cầu chờ duyệt mã này")
    elif L == "tam-dung":
        cn.execute("INSERT OR REPLACE INTO he_thong VALUES('tam_dung','1')")
        ghi_nhat_ky(cn, "chu", "tam-dung", "OK")
        print("đã tạm dừng")
    elif L == "tiep-tuc":
        cn.execute("INSERT OR REPLACE INTO he_thong VALUES('tam_dung','0')")
        ghi_nhat_ky(cn, "chu", "tiep-tuc", "OK")
        print("đã cho chạy tiếp")
    return 0


if __name__ == "__main__":
    sys.exit(main())
