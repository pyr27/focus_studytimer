"""V2 정답(ground truth) 기록기 — 측정 정확도 검증용.

Edge(detect.py, LOG_FRAMES=1)와 같은 PC 에서 동시에 실행하고, 실제 상태가 바뀔 때마다 키를 누른다.
  s = 공부(study)   p = 폰 사용(phone)   a = 자리 비움(away)   q / Esc = 종료
  (한글 입력 상태의 ㄴ/ㅔ/ㅁ/ㅂ 도 인식. 대소문자 무관)

출력: logs/gt_YYYYMMDD_HHMM.csv  —  `ts,label`
  ts    : time.time() (초, 소수 3자리) — frame_logger.py 와 같은 시계
  label : study / phone / away   (Edge state 와 대응: PRESENT / DISTRACTED / IDLE)
라벨이 바뀌면 즉시 1행, 같은 라벨이 이어지면 --interval 초(기본 1)마다 1행, 종료 시 마지막 1행을 쓴다
→ 첫 키 입력부터 종료까지 Edge 로그와 같은 시간 범위를 덮는다.

사용: cd edge && python gt_logger.py [--interval 1] [--log-dir logs]
"""
import argparse
import csv
import os
import time

from frame_logger import new_log_path

LABELS = ('study', 'phone', 'away')
KEYMAP = {'s': 'study', 'p': 'phone', 'a': 'away', 'q': 'quit',
          'ㄴ': 'study', 'ㅔ': 'phone', 'ㅁ': 'away', 'ㅂ': 'quit'}  # 두벌식 같은 자리
KO = {'study': '공부', 'phone': '폰 사용', 'away': '자리 비움', None: '라벨 없음'}
BG = {'study': (60, 150, 60), 'phone': (0, 130, 240), 'away': (60, 60, 200), None: (70, 70, 70)}  # BGR

FONT_CANDIDATES = [r'C:\Windows\Fonts\malgun.ttf', '/System/Library/Fonts/AppleSDGothicNeo.ttc',
                   '/usr/share/fonts/truetype/nanum/NanumGothic.ttf']


def parse_key(key):
    """cv2.waitKey 값 → 'study' / 'phone' / 'away' / 'quit' / None."""
    if key is None or key < 0:
        return None
    if key == 27:  # Esc
        return 'quit'
    for code in (key, key & 0xFFFF, key & 0xFF):
        try:
            label = KEYMAP.get(chr(code).lower())
        except (ValueError, OverflowError):
            continue
        if label:
            return label
    return None


class GtWriter:
    """라벨 변경 시 즉시, 같은 라벨은 interval 초마다 `ts,label` 기록."""

    def __init__(self, path, interval=1.0):
        self.path, self.interval = path, interval
        self.label, self.label_since, self.last_write, self.rows = None, None, None, 0
        self._f = open(path, 'w', newline='', encoding='utf-8', buffering=1)  # 줄 단위 flush
        self._w = csv.writer(self._f, lineterminator='\n')
        self._w.writerow(('ts', 'label'))

    def _write(self, now):
        self._w.writerow((f'{now:.3f}', self.label))
        self.last_write, self.rows = now, self.rows + 1

    def set_label(self, label, now):
        if label in LABELS and label != self.label:
            self.label, self.label_since = label, now
            self._write(now)

    def tick(self, now):
        if self.label and now - self.last_write >= self.interval:
            self._write(now)

    def close(self, now):
        if self._f.closed:
            return
        if self.label:
            self._write(now)
        self._f.close()


def load_font(size):
    try:
        from PIL import ImageFont
        for path in FONT_CANDIDATES:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
    except ImportError:
        pass
    return None


def fmt(sec):
    sec = int(sec)
    return f'{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}'


def render(gw, now, started, fonts):
    """현재 라벨을 화면 가득 크게 표시 (라벨별 배경색)."""
    import cv2
    import numpy as np

    canvas = np.full((360, 640, 3), BG[gw.label], np.uint8)
    big = KO[gw.label] if fonts else (gw.label or 'NO LABEL').upper()
    lines = [(big, 0)]
    if gw.label:
        lines.append((f'경과 {fmt(now - gw.label_since)}' if fonts else f'for {fmt(now - gw.label_since)}', 1))
    else:
        lines.append(('s / p / a 를 눌러 시작' if fonts else 'press s / p / a to start', 1))
    lines += [(f's=study  p=phone  a=away  q=quit    total {fmt(now - started)}  rows {gw.rows}', 2),
              (f'{time.strftime("%H:%M:%S")}  ->  {gw.path}', 2)]
    ys, sizes = (40, 170, 270, 310), (2.6, 1.1, 0.6, 0.5)
    if fonts:
        from PIL import Image, ImageDraw
        img = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
        d = ImageDraw.Draw(img)
        for i, (text, f) in enumerate(lines):
            d.text((24, ys[i]), text, font=fonts[f], fill=(255, 255, 255))
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    for i, (text, f) in enumerate(lines):
        y = ys[i] + (80 if i == 0 else 20)
        cv2.putText(canvas, text, (24, y), cv2.FONT_HERSHEY_SIMPLEX, sizes[i], (255, 255, 255), 2 if i < 2 else 1)
    return canvas


def main():
    ap = argparse.ArgumentParser(description='정답(실제 상태) 기록기: s=공부 p=폰 a=자리 비움 q=종료')
    ap.add_argument('--interval', type=float, default=1.0, help='같은 라벨 반복 기록 간격(초)')
    ap.add_argument('--log-dir', default=None, help='저장 폴더 (기본 LOG_DIR 환경변수 또는 logs)')
    args = ap.parse_args()

    import cv2

    gw = GtWriter(new_log_path('gt', args.log_dir), args.interval)
    big, mid, small = load_font(110), load_font(44), load_font(20)
    fonts = (big, mid, small) if big else None
    win = 'GT Logger (s/p/a/q)'
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    started = time.time()
    print(f'[GT] {gw.path}  — s=공부 p=폰 a=자리 비움 q=종료')
    try:
        while True:
            now = time.time()
            gw.tick(now)
            cv2.imshow(win, render(gw, now, started, fonts))
            label = parse_key(cv2.waitKey(50))
            if label == 'quit':
                break
            if label:
                gw.set_label(label, time.time())
                print(f'[GT] {time.strftime("%H:%M:%S")} {label}')
            if cv2.getWindowProperty(win, cv2.WND_PROP_VISIBLE) < 1:  # 창 X 버튼
                break
    except KeyboardInterrupt:
        pass
    finally:
        gw.close(time.time())
        cv2.destroyAllWindows()
        print(f'[GT] {gw.rows} rows ({fmt(time.time() - started)}) -> {gw.path}')


if __name__ == '__main__':
    main()
