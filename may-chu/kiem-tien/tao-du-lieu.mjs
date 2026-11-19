// Dựng web/du-lieu.json cho kiemtien.copee.vn (nhật ký công khai của agent).
// Nguồn: sổ cái (python3 kiem-soat/vi.py bao-cao, chỉ đọc) + kinh-doanh/nhat-ky-cong-khai/YYYY-MM-DD.md + cach-kiem-tien.md.
// Mọi chữ đi qua bộ lọc riêng tư (locRiengTu) trước khi ghi. Không thư viện ngoài.
// Chạy: node may-chu/kiem-tien/tao-du-lieu.mjs          (ghi web/du-lieu.json + lưu số hôm nay vào so-theo-ngay.json)
//       node may-chu/kiem-tien/tao-du-lieu.mjs --thu    (chỉ in ra, không ghi gì)
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const DAY = path.dirname(fileURLToPath(import.meta.url));
const GOC_DU_AN = path.resolve(DAY, '..', '..');
const THU_MUC_NHAT_KY = path.join(GOC_DU_AN, 'kinh-doanh', 'nhat-ky-cong-khai');
const TEP_RA = path.join(DAY, 'web', 'du-lieu.json');
const TEP_SO = path.join(DAY, 'so-theo-ngay.json');

export const VON = 2000000;
export const NGAY_DAU = '2026-10-17';
export const HAN = '2026-10-25T23:59:00+07:00';

// ---------- Số tiền ----------
// "771.725đ" → 771725 ; "-49.000đ" → -49000 ; "0đ" → 0
export function soTien(chu) {
  const m = String(chu).match(/(-?)\s*([\d.]+)\s*đ/);
  if (!m) return null;
  return (m[1] ? -1 : 1) * Number(m[2].replace(/\./g, ''));
}
export const vnd = (n) => (n < 0 ? '-' : '') + Math.abs(Math.round(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.') + 'đ';

// ---------- Sổ cái ----------
// Đọc bản in của `vi.py bao-cao`. Thiếu dòng nào thì báo lỗi, không đoán.
export function docBaoCao(chu) {
  const lay = (re, ten) => {
    const m = chu.match(re);
    if (!m) throw new Error('bao-cao thiếu dòng: ' + ten);
    const n = soTien(m[1]);
    if (n === null) throw new Error('bao-cao không đọc được số: ' + ten);
    return n;
  };
  return {
    trang_thai: (chu.match(/Trạng thái:\s*(\S+)/) || [])[1] || null,
    tien_that: lay(/Doanh thu thực thu:\s*([-\d.]+đ)/, 'Doanh thu thực thu'),
    chi_tien_mat: lay(/Chi thực tế:\s*([-\d.]+đ)/, 'Chi thực tế'),
    chi_phi_ai: lay(/Chi phí AI quy đổi[^:]*:\s*([-\d.]+đ)/, 'Chi phí AI quy đổi'),
  };
}

function chayViPy() {
  return execFileSync('python3', [path.join(GOC_DU_AN, 'kiem-soat', 'vi.py'), 'bao-cao'], { cwd: GOC_DU_AN, encoding: 'utf8', timeout: 30000 });
}

// ---------- Nhật ký viết tay ----------
// # tiêu đề
// - gạch đầu dòng
// > đang làm: dòng 1, dòng 2        (chữ chạy trên màn hình laptop)
// > số: Nhãn = giá trị             (số của ngày; "Tiền thật = 0đ" thì cũng thành số tien_that)
// > sự kiện: dong-dau-tien          (bật pháo giấy)
// Agent đôi khi chép nguyên dòng sổ nội bộ "2026-10-25 14:46 · Claude (lượt 148) · #164: … · doanh thu thật theo sổ …" vào nhật ký công khai
// (25/10): bộ lọc tưởng "2026-10-25 14" là số tài khoản nên che thành [đã ẩn]. Đổi về dạng người xem đọc được "14:46: …".
export function dongCongKhai(v) {
  const m = v.match(/^\d{4}-\d{2}-\d{2}\s+(\d{1,2}:\d{2})\s*·\s*(?:Claude|agent)[^·]*·\s*(.+)$/i);
  if (!m) return v;
  let chu = m[2].replace(/^#\d+\s*(bỏ)?\s*:?\s*/i, (x, bo) => (bo ? 'Bỏ việc: ' : ''))
    .replace(/\s*·\s*doanh thu thật theo sổ[^·]*$/i, '').replace(/\s*\(#\d+\)/g, '').replace(/#(\d+)\b/g, 'việc $1').trim();
  return m[1] + ': ' + chu.charAt(0).toUpperCase() + chu.slice(1);
}

export function docNhatKy(chu, ngay) {
  const out = { ngay, tieu_de: '', viec: [], so: {}, dang_lam: [] };
  for (const dong0 of String(chu).replace(/\r/g, '').split('\n')) {
    const dong = dong0.trim();
    if (!dong) continue;
    let m;
    if (!out.tieu_de && (m = dong.match(/^#\s+(.+)/))) out.tieu_de = m[1].trim();
    else if ((m = dong.match(/^[-*]\s+(.+)/))) out.viec.push(dongCongKhai(m[1].trim()));
    else if ((m = dong.match(/^>\s*đang làm\s*:\s*(.+)/i))) out.dang_lam.push(...m[1].split(/\s*[,;|]\s*/).map((s) => s.trim()).filter(Boolean));
    else if ((m = dong.match(/^>\s*số\s*:\s*(.+?)\s*=\s*(.+)/i))) out.so[m[1].trim()] = m[2].trim();
    else if ((m = dong.match(/^>\s*sự kiện\s*:\s*([a-z0-9-]+)/i))) out.su_kien = m[1].toLowerCase();
  }
  if (!out.tieu_de) throw new Error(`nhật ký ${ngay}: thiếu dòng "# tiêu đề"`);
  if (out.so['Tiền thật'] !== undefined) out.tien_that = soTien(out.so['Tiền thật']);
  return out;
}

// - **Tên** | trạng thái | một câu giải thích
export function docCachKiemTien(chu) {
  const ds = [];
  for (const dong of String(chu).split('\n')) {
    const m = dong.trim().match(/^[-*]\s+(.+)/);
    if (!m) continue;
    const [ten, trang_thai, mo_ta] = m[1].split(/\s+\|\s+/).map((s) => s.replace(/\*\*/g, '').trim());
    if (ten && trang_thai) ds.push({ ten, trang_thai, mo_ta: mo_ta || '' });
  }
  return ds;
}

// ---------- Bộ lọc riêng tư ----------
// Tên miền được phép hiện: công cụ công khai của agent / anh Long + mạng xã hội lớn. Tên miền khác = có thể là web khách → ẩn.
export const MIEN_DUOC_PHEP = ['copee.vn', 'khothemewordpress.com', 'hoanglongteam.com', 'apify.com', 'tiktok.com', 'youtube.com', 'facebook.com'];
const CHU_CAM = [/nguy[eễ]n\s+c[oô]ng\s+ho[aà]n/gi, /\b102A\b/g, /an\s+kh[eê]\s+ward/gi]; // địa chỉ nhà anh Long
const LUAT = [
  ['khoá', /\b(?:sk-ant-[\w-]{8,}|sk-[A-Za-z0-9_-]{16,}|apify_api_\w{10,}|AIza[\w-]{20,}|gh[pousr]_\w{20,}|xox[abprs]-[\w-]{10,}|\d{8,10}:[\w-]{30,}|Bearer\s+[\w.~+/-]{16,}=*)/g],
  ['khoá', /\b(?=\w*\d)(?=\w*[A-Za-z])\w{32,}\b/g],                                             // chuỗi dài lẫn chữ + số (không gạch nối, để slug bài viết không bị ẩn)
  ['khoá', /\b[a-f0-9]{24,}\b/gi],
  ['email', /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g],
  ['đường dẫn', /(?:~|\/(?:Users|opt|root|home|etc|var|tmp|private))\/[^\s,;)"'`]*/g],
  ['mã đơn', /\bABC\d+\b/gi],
  ['mã đơn', /\bSMAIL[A-Z0-9]{4,}\b/g],
  ['số tài khoản', /(?<![\d.,])(?!\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2})\d(?:[ -]?\d){8,18}(?![\d.,]*\d)/g],                              // 9–19 chữ số liền (STK, số điện thoại)
];
const IP = /\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b(?![.\d]*đ)/g;
const MIEN = /\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:vn|com|net|org|io|co|info|biz|shop|store|xyz|me|app|dev|site|online|top|asia)\b/gi;

export function locChu(chu) {
  let s = String(chu);
  const an = [];
  const thay = (re, loai) => { s = s.replace(re, () => { an.push(loai); return '[đã ẩn]'; }); };
  for (const re of CHU_CAM) thay(re, 'địa chỉ');
  for (const [loai, re] of LUAT) thay(re, loai);
  s = s.replace(IP, (all, ...o) => (o.slice(0, 4).every((x) => +x <= 255) ? (an.push('IP'), '[đã ẩn]') : all));
  s = s.replace(MIEN, (m) => {
    const d = m.toLowerCase();
    if (MIEN_DUOC_PHEP.some((ok) => d === ok || d.endsWith('.' + ok))) return m;
    an.push('tên miền lạ'); return '[một trang web]';
  });
  return { chu: s, an };
}

// Lọc sâu mọi chuỗi trong object. Trả { du_lieu, an: [{cho, loai}] }.

// Bảng việc (kinh-doanh/BANG-VIEC.md) cho người xem: việc chờ, đang làm, 5 việc xong gần nhất kèm giờ (23/10/2026).
// Chỉ lấy cột tên việc + giờ, không lấy cột "nguồn"/"bằng chứng" (có thể chứa đường dẫn nội bộ). Vẫn qua locRiengTu.
export function docBangViec(noiDung) {
  const muc = (ten) => {
    const m = noiDung.match(new RegExp('^## ' + ten + '[^\\n]*\\n([\\s\\S]*?)(?=^## |$(?![\\s\\S]))', 'm'));
    if (!m) return [];
    const dong = m[1].split('\n').filter((l) => l.startsWith('|') && !/^\|\s*-/.test(l));
    return dong.slice(1).map((l) => l.replace(/^\||\|$/g, '').split('|').map((o) => o.trim()));
  };
  // Cắt ở ranh giới từ + "…", bỏ phần lệnh nội bộ ("TỰ đăng bằng ….sh", `mã`) (23/10: trang hiện "chờ phiê", ",.sh").
  const cat = (t, n) => { t = String(t || '').replace(/\s+/g, ' ').trim(); if (t.length <= n) return t; const c = t.slice(0, n); return c.slice(0, Math.max(c.lastIndexOf(' '), n * 0.6)).replace(/[\s,;:—–-]+$/, '') + '…'; };
  const gon = (t, n = 140) => cat(String(t || '').replace(/,?\s*TỰ (đưa|đăng)[^|]*?\.sh/gi, '').replace(/`[^`]*`/g, '').replace(/\s*\S+\.sh\b/g, ''), n);
  // Người xem chỉ thấy câu dễ hiểu trước " » "; phần sau là ghi chép kỹ thuật của agent (anh Long 27/10: "viết gì mà đọc không hiểu").
  // Dòng chưa có câu dễ hiểu thì ẩn chi tiết, chỉ nói chung chung.
  const de = (t, thay) => { t = String(t || ''); const i = t.indexOf(' » '); return i > 0 ? gon(t.slice(0, i), 120) : thay; };
  const choHoTro = (t) => /CHỜ PHIÊN CHÍNH/.test(String(t || ''));
  return {
    cho: muc('CHỜ').map((r) => ({ viec: de(r[1], 'Việc kỹ thuật nội bộ'), ho_tro: choHoTro(r[1]) || undefined })),
    dang: muc('ĐANG LÀM').map((r) => ({ viec: de(r[1], 'Việc kỹ thuật nội bộ'), tu: r[2] || '' })),
    xong: muc('XONG').slice(0, 5).map((r) => ({ viec: de(r[1], 'Việc kỹ thuật nội bộ'), luc: r[2] || '', ket_qua: de(r[4], '') })),
    dang_chay: process.env.DANG_CHAY === '1',
  };
}

export function locRiengTu(o) {
  const an = [];
  const di = (x, cho) => {
    if (typeof x === 'string') { const r = locChu(x); r.an.forEach((loai) => an.push({ cho, loai })); return r.chu; }
    if (Array.isArray(x)) return x.map((v, i) => di(v, `${cho}[${i}]`));
    if (x && typeof x === 'object') return Object.fromEntries(Object.entries(x).map(([k, v]) => [locChu(k).chu, di(v, `${cho}.${k}`)]));
    return x;
  };
  return { du_lieu: di(o, '$'), an };
}

// ---------- Dựng dữ liệu ----------
export function ngayVN(d = new Date()) { return new Date(d.getTime() + 7 * 3600e3).toISOString().slice(0, 10); }

// Chuyện cười (gợi ý người xem 24/10) không nằm trong nhật ký: tách ra cho bảng tin đọc (anh Long 24/10: tách ủng hộ/gợi ý khỏi nhật ký).
const LA_CHUYEN_CUOI = /^(\d{1,2}:\d{2}:\s*)?Chuyện cười/i;

export function dungDuLieu({ soCai, nhatKy, cachKiemTien, soTheoNgay = {}, bayGio = new Date(), bangViec = null, goiY = null }) {
  const chuyen_cuoi = [];
  nhatKy = nhatKy.map((n) => {
    const viec = (n.viec || []).filter((v) => { if (LA_CHUYEN_CUOI.test(v)) { chuyen_cuoi.push(v.replace(/^\d{1,2}:\d{2}:\s*/, '').replace(/^Chuyện cười[^:]*:\s*/i, '')); return false; } return true; });
    return { ...n, viec };
  });
  const ngay = nhatKy.map((n) => {
    const snap = soTheoNgay[n.ngay];
    const so = { ...n.so };
    let tien_that = n.tien_that;
    if (snap) {
      if (!('Tiền thật' in so)) so['Tiền thật'] = vnd(snap.tien_that);
      if (!('Chi tiền mặt' in so)) so['Chi tiền mặt'] = vnd(snap.chi_tien_mat);
      if (!('Chi phí AI (cộng dồn)' in so)) so['Chi phí AI (cộng dồn)'] = vnd(snap.chi_phi_ai);
      if (tien_that == null) tien_that = snap.tien_that;
    }
    const r = { ngay: n.ngay, tieu_de: n.tieu_de, viec: n.viec, so, dang_lam: n.dang_lam };
    if (tien_that != null) r.tien_that = tien_that;
    if (n.su_kien) r.su_kien = n.su_kien;
    return r;
  }).sort((a, b) => (a.ngay < b.ngay ? 1 : -1));                    // mới nhất trước
  return {
    cap_nhat: bayGio.toISOString(),
    von: VON,
    tien_that: soCai.tien_that,
    chi_tien_mat: soCai.chi_tien_mat,
    chi_phi_ai: soCai.chi_phi_ai,
    ngay_dau: NGAY_DAU,
    han: HAN,
    ngay,
    cach_kiem_tien: cachKiemTien,
    bang_viec: bangViec,
    chuyen_cuoi: chuyen_cuoi.slice(-10),
    goi_y: goiY,
  };
}

function main() {
  const thu = process.argv.includes('--thu');
  const soCai = docBaoCao(chayViPy());
  const tep = fs.readdirSync(THU_MUC_NHAT_KY).filter((f) => /^\d{4}-\d{2}-\d{2}\.md$/.test(f)).sort();
  const nhatKy = tep.map((f) => docNhatKy(fs.readFileSync(path.join(THU_MUC_NHAT_KY, f), 'utf8'), f.slice(0, 10)));
  let cach = [];
  try { cach = docCachKiemTien(fs.readFileSync(path.join(THU_MUC_NHAT_KY, 'cach-kiem-tien.md'), 'utf8')); } catch {}
  let soTheoNgay = {};
  try { soTheoNgay = JSON.parse(fs.readFileSync(TEP_SO, 'utf8')); } catch {}
  const homNay = ngayVN();
  soTheoNgay[homNay] = { tien_that: soCai.tien_that, chi_tien_mat: soCai.chi_tien_mat, chi_phi_ai: soCai.chi_phi_ai };

  let bangViec = null;
  try { bangViec = docBangViec(fs.readFileSync(path.join(GOC_DU_AN, 'kinh-doanh', 'BANG-VIEC.md'), 'utf8')); } catch {}
  let goiY = null;
  try { goiY = JSON.parse(fs.readFileSync(path.join(GOC_DU_AN, 'kinh-doanh', 'goi-y-tra-loi.json'), 'utf8')); delete goiY._ghi_chu; delete goiY.cap_nhat; } catch {}
  const { du_lieu, an } = locRiengTu(dungDuLieu({ soCai, nhatKy, cachKiemTien: cach, soTheoNgay, bangViec, goiY }));
  if (an.length) console.error('BỘ LỌC ĐÃ ẨN', an.length, 'chỗ:', an.map((a) => `${a.cho} (${a.loai})`).join('; '));
  const chu = JSON.stringify(du_lieu, null, 1);
  if (thu) { console.log(chu); return; }
  fs.writeFileSync(TEP_RA + '.tmp', chu); fs.renameSync(TEP_RA + '.tmp', TEP_RA);
  fs.writeFileSync(TEP_SO, JSON.stringify(soTheoNgay, null, 1));
  console.log(`ok · ${du_lieu.ngay.length} ngày · tiền thật ${vnd(du_lieu.tien_that)} · chi phí AI ${vnd(du_lieu.chi_phi_ai)} · ẩn ${an.length} chỗ → ${path.relative(GOC_DU_AN, TEP_RA)}`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) main();
