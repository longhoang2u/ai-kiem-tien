#!/usr/bin/env python3
"""Đếm việc THẬT trong BANG-VIEC.md — mỗi lượt agent chạy trước khi chọn việc (23/10/2026).

In: số việc CHỜ/ĐANG LÀM/XONG, việc CHỜ quá hạn (tạo > 3 ngày), dòng sai luật (gạch ngang/"đã xong" trong CHỜ).
Thoát mã 1 nếu CHỜ < 5, có dòng sai luật, hoặc việc thiếu câu dễ hiểu cho người xem — lượt đó phải sửa bảng/sinh việc trước khi làm việc khác.
"""
import re, sys, datetime, pathlib

TEP = pathlib.Path(__file__).with_name('BANG-VIEC.md')


def doc_bang(noi_dung, ten_muc):
    m = re.search(r'^## ' + re.escape(ten_muc) + r'[^\n]*\n(.*?)(?=^## |\Z)', noi_dung, re.S | re.M)
    if not m:
        return []
    dong = [l for l in m.group(1).splitlines() if l.startswith('|') and not re.match(r'^\|\s*-', l)]
    return [[o.strip() for o in l.strip('|').split('|')] for l in dong[1:]]  # bỏ dòng tiêu đề


def ngay_tao(o):
    m = re.search(r'(\d{1,2}):(\d{2})\s+(\d{1,2})/(\d{1,2})', o)
    if not m:
        return None
    h, p, d, t = map(int, m.groups())
    return datetime.datetime(datetime.date.today().year, t, d, h, p)


def main():
    s = TEP.read_text(encoding='utf-8')
    cho, dang, xong = doc_bang(s, 'CHỜ'), doc_bang(s, 'ĐANG LÀM'), doc_bang(s, 'XONG')
    sai = [r for r in cho if '~~' in ' '.join(r) or re.search(r'đã xong|ĐÃ CÓ SẴN|xong ở lượt', ' '.join(r), re.I)]
    bay_gio = datetime.datetime.now()
    tre = [r for r in cho if len(r) > 4 and (t := ngay_tao(r[4])) and (bay_gio - t).days > 3]
    # Câu dễ hiểu cho người xem trang kiemtien (27/10): phải có " » " và phần trước » không chứa chữ kỹ thuật.
    ky_thuat = re.compile(r'\.(md|py|sh|json|mjs|html)\b|`|#\d|phiên chính|PHIÊN CHÍNH|\w+_\w+')
    def thieu_de_hieu(o):
        if ' » ' not in o:
            return 'thiếu "Câu dễ hiểu » "'
        c = o.split(' » ', 1)[0]
        if ky_thuat.search(c):
            return 'câu dễ hiểu có chữ kỹ thuật: ' + ky_thuat.search(c).group(0)
        if len(c.split()) > 20:
            return f'câu dễ hiểu dài {len(c.split())} chữ (tối đa 15–20)'
    kho_doc = [(r[0], l, r[1]) for r in cho + dang + xong[:5] if len(r) > 1 and (l := thieu_de_hieu(r[1]))]
    print(f'CHỜ thật: {len(cho)} · ĐANG LÀM: {len(dang)} · XONG: {len(xong)}')
    for r in sai:
        print('  SAI LUẬT (việc xong/bỏ còn nằm trong CHỜ):', r[0], r[1][:70])
    for r in tre:
        print('  QUÁ 3 NGÀY (làm ngay hoặc BỎ):', r[0], r[1][:70])
    for so, ly_do, o in kho_doc:
        print(f'  KHÓ ĐỌC ({ly_do}): {so} {o[:70]}')
    if len(cho) < 5:
        print(f'  THIẾU {5 - len(cho)} việc CHỜ → sinh thêm việc có nguồn (phễu tiền, lỗi, đối thủ, nội dung nổi) trước khi làm việc khác.')
    sys.exit(1 if (len(cho) < 5 or sai or kho_doc) else 0)


if __name__ == '__main__':
    main()
