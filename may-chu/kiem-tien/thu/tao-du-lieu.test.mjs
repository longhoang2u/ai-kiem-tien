// node --test may-chu/kiem-tien/thu/
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { soTien, vnd, docBaoCao, docNhatKy, docCachKiemTien, locChu, locRiengTu, dungDuLieu } from '../tao-du-lieu.mjs';

const DAY = path.dirname(fileURLToPath(import.meta.url));
const BAO_CAO = `Trạng thái: ACTIVE
Tiền đã đối soát: 2.000.000đ (dự phòng khoá 500.000đ, đã cam kết 0đ)
Khả dụng: 1.500.000đ = 100% vốn vận hành
Doanh thu thực thu: 0đ · Chi thực tế: 0đ · Lãi tiền mặt: 0đ
Chi phí AI quy đổi (không trừ tiền mặt): 771.725đ · Lãi sau AI: -771.725đ
Sống còn (bảo thủ, doanh thu = 0): chưa đốt tiền`;

test('soTien / vnd', () => {
  assert.equal(soTien('771.725đ'), 771725);
  assert.equal(soTien('-49.000đ'), -49000);
  assert.equal(soTien('0đ'), 0);
  assert.equal(soTien('không có'), null);
  assert.equal(vnd(2000000), '2.000.000đ');
  assert.equal(vnd(0), '0đ');
  assert.equal(vnd(-771725), '-771.725đ');
});

test('docBaoCao đọc đúng bản in của vi.py', () => {
  assert.deepEqual(docBaoCao(BAO_CAO), { trang_thai: 'ACTIVE', tien_that: 0, chi_tien_mat: 0, chi_phi_ai: 771725 });
  const co = BAO_CAO.replace('Doanh thu thực thu: 0đ', 'Doanh thu thực thu: 99.000đ').replace('Chi thực tế: 0đ', 'Chi thực tế: 120.000đ');
  const r = docBaoCao(co);
  assert.equal(r.tien_that, 99000);
  assert.equal(r.chi_tien_mat, 120000);
});

test('docBaoCao thiếu dòng thì báo lỗi, không đoán', () => {
  assert.throws(() => docBaoCao('Trạng thái: ACTIVE'), /thiếu dòng/);
});

test('docNhatKy: tiêu đề, gạch đầu dòng, đang làm, số, sự kiện', () => {
  const n = docNhatKy(`# Ngày thử
- Việc một
* Việc hai

> đang làm: Đang đo lượt bấm…, Đang khám kênh TikTok…
> số: Tiền thật = 99.000đ
> số: Lượt bấm = 17
> sự kiện: dong-dau-tien
dòng lạ bị bỏ qua`, '2026-10-22');
  assert.equal(n.tieu_de, 'Ngày thử');
  assert.deepEqual(n.viec, ['Việc một', 'Việc hai']);
  assert.deepEqual(n.dang_lam, ['Đang đo lượt bấm…', 'Đang khám kênh TikTok…']);
  assert.deepEqual(n.so, { 'Tiền thật': '99.000đ', 'Lượt bấm': '17' });
  assert.equal(n.tien_that, 99000);
  assert.equal(n.su_kien, 'dong-dau-tien');
});

test('docNhatKy thiếu tiêu đề thì lỗi', () => {
  assert.throws(() => docNhatKy('- chỉ có gạch', '2026-10-22'), /tiêu đề/);
});

test('docCachKiemTien', () => {
  const ds = docCachKiemTien('# đầu\n- **Chấm điểm web** | Đang chạy · 0 đơn | Miễn phí, bản đủ 99.000đ.\n- thiếu trạng thái\n');
  assert.deepEqual(ds, [{ ten: 'Chấm điểm web', trang_thai: 'Đang chạy · 0 đơn', mo_ta: 'Miễn phí, bản đủ 99.000đ.' }]);
});

test('dungDuLieu: mới nhất trước, số của ngày lấy từ ảnh chụp sổ', () => {
  const nhatKy = [docNhatKy('# A\n- x', '2026-10-17'), docNhatKy('# B\n- y', '2026-10-18')];
  const d = dungDuLieu({ soCai: { tien_that: 0, chi_tien_mat: 0, chi_phi_ai: 5 }, nhatKy, cachKiemTien: [],
    soTheoNgay: { '2026-10-18': { tien_that: 49000, chi_tien_mat: 0, chi_phi_ai: 5 } }, bayGio: new Date('2026-10-18T10:00:00Z') });
  assert.deepEqual(d.ngay.map((n) => n.ngay), ['2026-10-18', '2026-10-17']);
  assert.equal(d.ngay[0].tien_that, 49000);
  assert.equal(d.ngay[0].so['Tiền thật'], '49.000đ');
  assert.equal(d.ngay[1].tien_that, undefined);
  assert.equal(d.von, 2000000);
});

// ---------- Bộ lọc riêng tư ----------
const an = (s) => locChu(s).chu;

test('lọc khoá API / token', () => {
  for (const k of ['sk-ant-api03-AbCdEfGhIjKlMnOpQrStUv', 'sk-proj-abcdefghijklmnop1234', 'apify_api_AbCdEf123456XyZ', 'AIzaSyA1234567890abcdefghijklmnopq',
    'ghp_abcdefghijklmnopqrstuvwxyz0123', '1234567890:AAH_abcdefghijklmnopqrstuvwxyz12345', 'Bearer abcdefghijklmnop.qrstu',
    'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6', 'Xk9TzQ2LmP7wRb4NcV8yHs3JdF6gKa1Ue5'])
    assert.ok(!an('khoá là ' + k + ' nhé').includes(k), k);
});

test('lọc IP nhưng không đụng số tiền', () => {
  assert.equal(an('máy chủ 103.75.183.20 chạy'), 'máy chủ [đã ẩn] chạy');
  assert.equal(an('vốn 2.000.000đ, AI 771.725đ'), 'vốn 2.000.000đ, AI 771.725đ');
  assert.equal(an('phiên bản 1.2.3'), 'phiên bản 1.2.3');
});

test('lọc email, đường dẫn tệp, mã đơn, số tài khoản/điện thoại, địa chỉ nhà', () => {
  assert.equal(an('gửi khach@gmail.com'), 'gửi [đã ẩn]');
  assert.equal(an('xem /Users/ttcenter/AI/khoa.env hoặc /opt/chamdiem/moi-truong.env'), 'xem [đã ẩn] hoặc [đã ẩn]');
  assert.equal(an('tệp ~/hl-ops/a.txt'), 'tệp [đã ẩn]');
  assert.ok(!an('đơn ABC9349008 và abc123').match(/\d{3}/));
  assert.ok(!an('đơn SMAIL5TRHMU huỷ').includes('SMAIL5TRHMU'));
  assert.equal(an('STK 0123456789012 Vietcombank'), 'STK [đã ẩn] Vietcombank');
  assert.equal(an('gọi 0905 123 456'), 'gọi [đã ẩn]');
  assert.ok(!/102A|Cong Hoan/i.test(an('102A Nguyen Cong Hoan, An Khe Ward')));
});

test('tên miền: giữ công cụ của mình, ẩn web lạ (có thể là web khách)', () => {
  assert.equal(an('khamkenh.copee.vn và chamdiem.khothemewordpress.com, apify.com/hoanglongteam, hoanglongteam.com/bio'),
    'khamkenh.copee.vn và chamdiem.khothemewordpress.com, apify.com/hoanglongteam, hoanglongteam.com/bio');
  assert.equal(an('chấm thử shopcuakhach.vn'), 'chấm thử [một trang web]');
  assert.equal(an('evil-copee.vn'), '[một trang web]');
});

test('không ẩn nhầm chữ thường ngày', () => {
  const s = 'Hôm nay 14:02 có 17 lượt bấm, 0,2% của 71,2K; hạn 25/10/2026 23:59; ngày 2026-10-21; thue-hosting-web-ban-hang-khoi-mat-tien-oan';
  assert.equal(an(s), s);
});

test('locRiengTu đi sâu mọi chuỗi và báo chỗ đã ẩn', () => {
  const { du_lieu, an: ds } = locRiengTu({ a: ['ok', 'mail x@y.com'], b: { c: 'IP 10.0.0.1' }, n: 5 });
  assert.deepEqual(du_lieu, { a: ['ok', 'mail [đã ẩn]'], b: { c: 'IP [đã ẩn]' }, n: 5 });
  assert.deepEqual(ds.map((x) => x.cho), ['$.a[1]', '$.b.c']);
});

test('nhật ký công khai thật đi qua bộ lọc mà không phải ẩn gì', () => {
  const thu = path.resolve(DAY, '..', '..', '..', 'kinh-doanh', 'nhat-ky-cong-khai');
  for (const f of fs.readdirSync(thu).filter((f) => /^\d{4}-\d{2}-\d{2}\.md$/.test(f))) {
    const n = docNhatKy(fs.readFileSync(path.join(thu, f), 'utf8'), f.slice(0, 10));
    assert.ok(n.viec.length >= 3 && n.viec.length <= 120, f + ': cần 3–120 gạch đầu dòng (từ 24/10 mỗi lượt làm nối tiếp nhiều việc)');
    assert.deepEqual(locRiengTu(n).an, [], f);
  }
  const web = JSON.parse(fs.readFileSync(path.resolve(DAY, '..', 'web', 'du-lieu.json'), 'utf8'));
  assert.deepEqual(locRiengTu(web).an, [], 'du-lieu.json đã ghi phải sạch');
  assert.ok(!/khoá học|khoa-hoc/i.test(JSON.stringify(web).replace(/gỡ quảng cáo khoá học/g, '')), 'không quảng cáo khoá học');
});

// Anh Long 29/10: dòng nhật ký phải mở bằng giờ ("12:48: …"); lượt 12:45 ngày 29/10 lỡ ghi "29/10: …" cho 13 dòng.
test('nhật ký công khai: dòng mở bằng giờ, không mở bằng ngày', () => {
  const thuMuc = path.join(DAY, '../../../kinh-doanh/nhat-ky-cong-khai');
  const sai = [];
  for (const tep of fs.readdirSync(thuMuc).filter((t) => /^\d{4}-\d{2}-\d{2}\.md$/.test(t))) {
    for (const dong of fs.readFileSync(path.join(thuMuc, tep), 'utf8').split('\n')) {
      if (/^[-*]\s+\d{1,2}\/\d{1,2}\s*:/.test(dong)) sai.push(`${tep}: ${dong.slice(0, 50)}`);
    }
  }
  assert.deepEqual(sai, [], 'ghi giờ HH:MM (lấy bằng date) thay cho ngày');
});
