"""Kiểm thử bộ kiểm soát. Chạy: python3 -m unittest kiem-soat/test_vi.py (từ thư mục dự án) hoặc python3 kiem-soat/test_vi.py"""
import importlib
import os
import sqlite3
import sys
import tempfile
import threading
import unittest

THU_MUC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, THU_MUC)


class CoSo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["VI_DB"] = os.path.join(self.tmp, "so-cai.db")
        os.environ["VI_FILE_DUNG"] = os.path.join(self.tmp, "DUNG")
        import vi
        self.vi = importlib.reload(vi)
        self.cs = self.vi.nap_chinh_sach()
        self.cn = self.vi.ket_noi()
        self.vi.main(["nap-von", "--so-tien", "2000000", "--bang-chung", "test"])

    def xin(self, so_tien, hang_muc="cong-cu", ma=None, ncc="cloudflare.com", loai="mua-dich-vu"):
        ma = ma or "m%d-%s" % (so_tien, os.urandom(3).hex())
        return self.vi.xin_chi(self.cn, self.cs, ma, hang_muc, loai, so_tien, "test", ncc)[0], ma

    def chi(self, so_tien, hang_muc="cong-cu"):
        kq, ma = self.xin(so_tien, hang_muc)
        self.assertEqual(kq, "DUYET")
        self.assertEqual(self.vi.ghi_chi(self.cn, self.cs, ma, so_tien, "GD-" + ma, "hoa don")[0], "DA_GHI")


class TestHanMuc(CoSo):
    def test_trong_han_muc_duoc_duyet(self):
        self.assertEqual(self.xin(30000)[0], "DUYET")

    def test_tren_muc_tu_dong_can_chu_duyet(self):
        self.assertEqual(self.xin(80000)[0], "CHO_CHU_DUYET")

    def test_vuot_moi_lan_tu_choi(self):
        self.assertEqual(self.xin(self.cs["han_muc_moi_lan"] + 1)[0], "TU_CHOI")

    def test_vuot_hang_muc_tu_choi(self):
        for _ in range(4):
            self.chi(50000)          # cong-cu 200.000 dùng hết
        self.assertEqual(self.xin(1000)[0], "TU_CHOI")

    def test_vuot_ngay_tu_choi(self):
        for hm in ("cong-cu", "cong-cu", "ha-tang", "ha-tang"):
            self.chi(50000, hm)      # 200.000 = hạn ngày
        self.assertEqual(self.xin(1000, "ai-api", ncc="anthropic.com")[0], "TU_CHOI")

    def test_quang_cao_bi_chan(self):
        self.assertEqual(self.xin(1000, "quang-cao")[0], "TU_CHOI")

    def test_nha_cung_cap_la_bi_chan(self):
        self.assertEqual(self.xin(1000, ncc="la.example")[0], "TU_CHOI")

    def test_hang_muc_la_bi_chan(self):
        self.assertEqual(self.xin(1000, "du-phong")[0], "TU_CHOI")

    def test_chuyen_tien_luon_can_chu_duyet(self):
        self.assertEqual(self.xin(1000, loai="chuyen-tien")[0], "CHO_CHU_DUYET")

    def test_trung_ma_tu_choi(self):
        self.assertEqual(self.xin(1000, ma="X1")[0], "DUYET")
        self.assertEqual(self.xin(1000, ma="X1")[0], "TU_CHOI")


class TestDuPhongVaSinhTon(CoSo):
    def test_khong_tieu_duoc_du_phong(self):
        # Rút hết vốn vận hành bằng bút toán điều chỉnh (giả lập đã chi), còn đúng quỹ dự phòng.
        self.cn.execute("INSERT INTO but_toan(thoi_gian,loai,so_tien,nguon,ma_giao_dich,bang_chung) "
                        "VALUES(datetime('now'),'dieu-chinh',-1500000,'chu','DC1','test')")
        self.assertEqual(self.vi.trang_thai_song(self.cn, self.cs), "HALTED")
        self.assertEqual(self.xin(1000)[0], "TU_CHOI")

    def test_cac_nguong(self):
        def con_lai(ty_le):
            self.cn.execute("INSERT INTO but_toan(thoi_gian,loai,so_tien,nguon,ma_giao_dich,bang_chung) "
                            "VALUES(datetime('now'),'dieu-chinh',?,'chu',?,'test')",
                            (-int(1500000 * (1 - ty_le)), os.urandom(4).hex()))
            return self.vi.trang_thai_song(self.cn, self.cs)
        self.assertEqual(self.vi.trang_thai_song(self.cn, self.cs), "ACTIVE")
        self.assertEqual(con_lai(0.6), "THRIFT_MODE")      # còn 60%
        self.cn.execute("INSERT INTO but_toan(thoi_gian,loai,so_tien,nguon,ma_giao_dich,bang_chung) "
                        "VALUES(datetime('now'),'dieu-chinh',-300000,'chu','DC3','t')")   # còn 40% - ε
        self.cn.execute("INSERT INTO but_toan(thoi_gian,loai,so_tien,nguon,ma_giao_dich,bang_chung) "
                        "VALUES(datetime('now'),'dieu-chinh',-1,'chu','DC4','t')")
        self.assertEqual(self.vi.trang_thai_song(self.cn, self.cs), "SURVIVAL_MODE")
        self.assertEqual(self.xin(1000, "cong-cu")[0], "TU_CHOI")   # sinh tồn: chỉ hạ tầng
        self.assertEqual(self.xin(1000, "ha-tang")[0], "DUYET")
        self.cn.execute("INSERT INTO but_toan(thoi_gian,loai,so_tien,nguon,ma_giao_dich,bang_chung) "
                        "VALUES(datetime('now'),'dieu-chinh',-300000,'chu','DC5','t')")   # còn ~20% - ε
        self.assertEqual(self.vi.trang_thai_song(self.cn, self.cs), "HALTED")

    def test_kill_switch(self):
        open(os.environ["VI_FILE_DUNG"], "w").close()
        self.assertEqual(self.vi.trang_thai_song(self.cn, self.cs), "KILL_SWITCH")
        self.assertEqual(self.xin(1000)[0], "TU_CHOI")

    def test_tam_dung_cua_chu(self):
        self.vi.main(["tam-dung"])
        self.assertEqual(self.xin(1000)[0], "TU_CHOI")
        self.vi.main(["tiep-tuc"])
        self.assertEqual(self.xin(1000)[0], "DUYET")


class TestSoCai(CoSo):
    def test_khong_sua_khong_xoa(self):
        with self.assertRaises(sqlite3.DatabaseError):
            self.cn.execute("UPDATE but_toan SET so_tien=999999999")
        with self.assertRaises(sqlite3.DatabaseError):
            self.cn.execute("DELETE FROM but_toan")

    def test_ghi_chi_thieu_bang_chung(self):
        kq, ma = self.xin(10000)
        self.assertEqual(self.vi.ghi_chi(self.cn, self.cs, ma, 10000, "", "")[0], "TU_CHOI")

    def test_ghi_chi_khong_duyet(self):
        self.assertEqual(self.vi.ghi_chi(self.cn, self.cs, "khong-co", 10000, "GD", "hd")[0], "TU_CHOI")

    def test_chi_lo_thi_tam_dung(self):
        kq, ma = self.xin(10000)
        self.assertEqual(self.vi.ghi_chi(self.cn, self.cs, ma, 20000, "GD9", "hd")[0], "BAT_THUONG")
        self.assertEqual(self.vi.trang_thai_song(self.cn, self.cs), "PAUSED_BY_OWNER")

    def test_thu_trung_ma_khong_ghi_hai_lan(self):
        self.assertEqual(self.vi.ghi_thu(self.cn, 99000, "VCB123", "webhook")[0], "DA_GHI")
        self.assertEqual(self.vi.ghi_thu(self.cn, 99000, "VCB123", "webhook")[0], "TRUNG")
        self.assertEqual(self.vi.tinh(self.cn, self.cs)["thu"], 99000)

    def test_thu_khong_bang_chung(self):
        self.assertEqual(self.vi.ghi_thu(self.cn, 99000, "", "")[0], "TU_CHOI")

    def test_ai_khong_tru_tien_mat(self):
        self.vi.main(["ghi-ai", "--usd", "1.5"])
        so = self.vi.tinh(self.cn, self.cs)
        self.assertEqual(so["so_du"], 2000000)
        self.assertEqual(so["ai_vnd"], int(1.5 * self.cs["ty_gia_usd"]))

    def test_con_sau_khi_mo_lai(self):
        self.chi(10000)
        self.cn.close()
        cn2 = self.vi.ket_noi()
        self.assertEqual(self.vi.tinh(cn2, self.cs)["so_du"], 1990000)

    def test_chi_song_song_khong_vuot_hang_muc(self):
        # 10 luồng cùng xin 40.000 ở hạng mục cong-cu (hạn 200.000): tối đa 5 được duyệt.
        kq = []

        def chay(i):
            cn = self.vi.ket_noi()
            kq.append(self.vi.xin_chi(cn, self.cs, "ss%d" % i, "cong-cu", "mua-dich-vu", 40000, "t", "cloudflare.com")[0])
        ts = [threading.Thread(target=chay, args=(i,)) for i in range(10)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertLessEqual(kq.count("DUYET"), 5)
        self.assertEqual(kq.count("DUYET") + kq.count("TU_CHOI"), 10)


if __name__ == "__main__":
    unittest.main(verbosity=1)
