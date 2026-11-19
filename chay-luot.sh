#!/bin/bash
# Một lượt chạy của agent (launchd vn.aiauto.luot, hoặc chạy tay: ./chay-luot.sh).
# Dừng khẩn cấp: touch DUNG (trong thư mục này)
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin
cd "$(dirname "$0")" || exit 1
HAN=6600   # 110 phút: lượt làm nối tiếp từng việc tới sát giờ lượt sau (24/10); khoá chống chồng lượt
NK=nhat-ky/luot-$(date +%F).log
mkdir -p nhat-ky

[[ -e DUNG ]] && { echo "$(date '+%F %T') có tệp DUNG — không chạy." >> "$NK"; exit 0; }
TT=$(python3 kiem-soat/vi.py trang-thai | python3 -c 'import json,sys;print(json.load(sys.stdin)["trang_thai"])')
[[ "$TT" == KILL_SWITCH || "$TT" == PAUSED_BY_OWNER ]] && { echo "$(date '+%F %T') $TT — không chạy." >> "$NK"; exit 0; }

KHOA=/tmp/aiauto-luot.khoa
mkdir "$KHOA" 2>/dev/null || { echo "$(date '+%F %T') lượt trước chưa xong, bỏ lượt này." >> "$NK"; exit 0; }
trap 'rmdir "$KHOA"' EXIT

# Nhập giao dịch ngân hàng mới vào sổ cái trước khi agent nhìn số dư (nếu đã nối).
[[ -x kiem-soat/nhap-giao-dich.sh ]] && kiem-soat/nhap-giao-dich.sh >> "$NK" 2>&1

echo "===== $(date '+%F %T') trạng thái $TT =====" >> "$NK"
CLAUDE=$(command -v claude)   # Claude Code CLI; không có thì tìm trong extension VS Code
[[ -x "$CLAUDE" ]] || CLAUDE=$(ls -d "$HOME"/.vscode/extensions/anthropic.claude-code-* 2>/dev/null | sort -V | tail -1)/resources/native-binary/claude
[[ -x "$CLAUDE" ]] || { echo "Không thấy Claude CLI — bỏ lượt." >> "$NK"; exit 1; }

BAT_DAU=$(date +%s)
SID=""
LOI_NHAC="Bắt đầu một lượt làm việc theo CLAUDE.md. Trạng thái tài chính: $TT. Bây giờ là $(date '+%F %H:%M').
Kết thúc bằng 3–5 dòng tóm tắt tiếng Việt: đã làm gì, bằng chứng, việc lượt sau."
# Lượt hay dừng sau 1 phút → chạy tiếp cùng phiên tới khi hết giờ (tối đa 15 vòng).
for VONG in $(seq 1 15); do
  OUT=$(mktemp)
  TIEP=(); [[ -n "$SID" ]] && TIEP=(--resume "$SID")
  "$CLAUDE" -p "$LOI_NHAC" "${TIEP[@]}" \
    --model sonnet --max-turns 150 --output-format json \
    --allowedTools "Read" "Write" "Edit" "Glob" "Grep" "WebSearch" "WebFetch" "Bash" \
    --disallowedTools "Edit(chinh-sach.json)" "Write(chinh-sach.json)" \
      "Edit(kiem-soat/**)" "Write(kiem-soat/**)" "Edit(du-lieu/**)" "Write(du-lieu/**)" \
      "Edit(chay-luot.sh)" "Write(chay-luot.sh)" "Edit(CLAUDE.md)" "Write(CLAUDE.md)" \
      "Edit(kinh-doanh/trien-khai.sh)" "Write(kinh-doanh/trien-khai.sh)" \
      "Bash(chflags:*)" "Bash(sudo:*)" "Bash(sqlite3:*)" "Bash(ssh:*)" "Bash(scp:*)" "Bash(rsync:*)" \
      "Bash(osascript:*)" "Bash(open:*)" "Bash(launchctl:*)" "Bash(crontab:*)" "Bash(git push:*)" \
      "Bash(python3 kiem-soat/vi.py ghi-thu:*)" "Bash(python3 kiem-soat/vi.py nap-von:*)" "Bash(python3 kiem-soat/vi.py duyet:*)" \
      "Bash(python3 kiem-soat/vi.py tiep-tuc:*)" "Bash(python3 kiem-soat/vi.py tam-dung:*)" \
    > "$OUT" 2>&1 &
  CPID=$!
  CON_LAI=$(( HAN - ($(date +%s) - BAT_DAU) )); (( CON_LAI < 60 )) && CON_LAI=60
  ( sleep "$CON_LAI"; kill -TERM "$CPID" 2>/dev/null; sleep 20; kill -KILL "$CPID" 2>/dev/null;
    pkill -KILL -P "$CPID" 2>/dev/null ) &
  WPID=$!
  wait "$CPID" 2>/dev/null
  kill "$WPID" 2>/dev/null

  # Ghi chi phí AI quy đổi + tóm tắt vào nhật ký; dòng cuối SID= để vòng sau nối tiếp.
  SID=$(python3 - "$OUT" "$VONG" 2>>"$NK" <<'PY2' | tee -a "$NK" | tail -1 | sed -n 's/^SID=//p'
import json, subprocess, sys
raw = open(sys.argv[1], encoding="utf-8", errors="replace").read()
try:
    j = json.loads(raw[raw.index("{"):])
except Exception:
    print("Không đọc được kết quả lượt:\n" + raw[-2000:]); print("SID="); sys.exit()
usd = j.get("total_cost_usd") or 0
subprocess.run(["python3", "kiem-soat/vi.py", "ghi-ai", "--usd", str(usd), "--luot", j.get("session_id", "")], stdout=subprocess.DEVNULL)
print("vòng %s: %s lượt-gọi, %.2f USD, lỗi=%s" % (sys.argv[2], j.get("num_turns"), usd, j.get("is_error")))
print(j.get("result", "")[-3000:])
print("SID=" + (j.get("session_id") or ""))
PY2
)
  grep -q "mixes \* with" "$OUT" && echo "CẢNH BÁO: quy tắc quyền sai cú pháp" >> "$NK"
  rm -f "$OUT"
  DA_CHAY=$(( $(date +%s) - BAT_DAU ))
  (( DA_CHAY >= 6300 )) && break   # gần tới lượt sau thì dừng
  [[ -z "$SID" || -e DUNG ]] && break
  python3 kinh-doanh/kiem-bang-viec.py >/dev/null 2>&1 || true
  LOI_NHAC="Việc vừa làm đã chuyển sang XONG (giờ xong + bằng chứng) trong kinh-doanh/BANG-VIEC.md chưa? Chưa thì làm ngay. Rồi lấy NGAY việc tiếp theo trong CHỜ (làm xong đánh dấu xong, vào tiếp việc kế): chuyển sang ĐANG LÀM + giờ bắt đầu, làm xong hẳn ĐÚNG 1 việc, chuyển sang XONG rồi thêm 1 dòng nhật ký công khai. CHỜ dưới 5 thì sinh thêm việc có nguồn. Việc cần chủ (đăng nhập, bấm nút) → ghi vào \"Cần chủ\" trong KE-HOACH.md rồi lấy việc khác. Kết thúc bằng 2–3 dòng tóm tắt việc vừa xong."
done
echo "===== hết $(date '+%F %T') =====" >> "$NK"
