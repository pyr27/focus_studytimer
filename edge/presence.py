"""온디바이스 재석 측정 상태머신 (E1).

상태
- IDLE        : 세션 없음 (등록 사용자 미인식)
- PRESENT     : 등록 사용자 재석 → 순공시간 누적
- DISTRACTED  : 재석 중 딴짓 (휴대폰 사용, E2). 딴짓 시간은 순공에서 빠진다

세션 = 등록 사용자 확인(CONFIRM_FRAMES 연속 인식)으로 시작 ~ ABSENT_SEC 이상 미인식으로 종료.
  present_sec    : 세션 시작 ~ 마지막 인식 시각 (ABSENT_SEC 미만의 짧은 미인식은 재석으로 본다)
  distracted_sec : 딴짓 구간 합
  focus_sec      : present_sec - distracted_sec  (= 순공시간)

얼굴 식별은 YOLO person 영역에서 Haar 로 얼굴을 찾고 enroll_face.py 로 학습한 LBPH 모델로 판정한다.
전부 PC 에서 처리하고 서버로는 결과(세션 시작/종료 게시글)만 보낸다.

환경변수: ABSENT_SEC(30) · CONFIRM_FRAMES(3) · FACE_THRESHOLD(60)
"""
import os
import pathlib
import time
from datetime import datetime

import cv2
import numpy as np
import requests

# 얼굴 검출용 Haar cascade: 레포에 동봉한 파일 우선, 없으면 OpenCV 내장 경로
CASCADE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'haarcascade_frontalface_default.xml')
if not os.path.exists(CASCADE):
    CASCADE = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'

# 한글 오버레이용 폰트 (Windows 맑은 고딕 / macOS / Linux 순으로 탐색, 없으면 영문 표기)
FONT_CANDIDATES = [r'C:\Windows\Fonts\malgun.ttf', '/System/Library/Fonts/AppleSDGothicNeo.ttc',
                   '/usr/share/fonts/truetype/nanum/NanumGothic.ttf']

IDLE, PRESENT, DISTRACTED = 'IDLE', 'PRESENT', 'DISTRACTED'

# 색 (BGR)
GREEN, ORANGE, GRAY = (0, 200, 0), (0, 140, 255), (160, 160, 160)

# 한글 폰트가 없을 때 오버레이 영문 치환 (긴 표현 먼저)
EN = [('딴짓 중', 'DISTRACTED'), ('딴짓', 'distracted'), ('재석', 'PRESENT'), ('대기', 'IDLE'),
      ('순공', 'focus'), ('집중도', 'ratio'), ('미인식', 'unseen'), ('확인 중', 'confirming'),
      ('폰 감지', 'phone'), ('미등록 인원', 'unknown'), ('지난 세션', 'last')]


def env_float(name, default):
    return float(os.environ.get(name, default))


def create_lbph():
    """OpenCV 4.x / 5.x 양쪽 API 지원."""
    face = cv2.face
    if hasattr(face, 'LBPHFaceRecognizer_create'):
        return face.LBPHFaceRecognizer_create()
    return face.LBPHFaceRecognizer.create()


def fmt(sec):
    sec = int(sec)
    return f'{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}'


class FocusTracker:
    """프레임별 검출 결과(bool)만으로 상태와 시간을 계산한다. cv2 를 쓰지 않아 단위 테스트 가능.

    step() 은 그 프레임에 일어난 이벤트 목록을 돌려준다:
      ('session_start', {'at'}) / ('session_end', summary)
    """

    def __init__(self, absent_sec=30.0, confirm_frames=3):
        self.absent_sec = absent_sec
        self.confirm_frames = confirm_frames
        self.state = IDLE
        self.since = None          # 현재 상태가 시작된 시각
        self.streak = 0            # 등록 사용자 연속 인식 프레임 수
        self.last_seen = None      # 등록 사용자 확인(seen) 마지막 시각
        self.sessions = []         # 종료된 세션 요약 목록
        self._new_session(None)

    def _new_session(self, now):
        self.started_at = now
        self.distracted = []       # 닫힌 딴짓 구간 [(start, end), ...]
        self.d_start = None        # 진행 중인 딴짓 구간 시작

    # ------------------------------------------------------------------
    def step(self, now, owner_raw, phone_raw=False):
        if self.since is None:
            self.since = now
        events = []
        self.streak = self.streak + 1 if owner_raw else 0
        seen = self.streak >= self.confirm_frames  # 연속 N프레임 인식돼야 '보임' (오인식 1프레임 방지)
        if seen:
            self.last_seen = now

        if self.state == IDLE:
            if seen:
                self._new_session(now)
                self.state, self.since = PRESENT, now
                events.append(('session_start', {'at': now}))
            return events

        if now - self.last_seen > self.absent_sec:  # ABSENT_SEC 이상 미인식 → 세션 종료
            events.append(('session_end', self._end_session(self.last_seen)))
        return events

    def _end_session(self, end):
        if self.d_start is not None:
            self.distracted.append((self.d_start, end))
            self.d_start = None
        summary = self._summary(end)
        self.sessions.append(summary)
        self.state, self.since = IDLE, end
        return summary

    def _summary(self, end):
        start = self.started_at
        present = max(0.0, end - start)
        distracted = sum(max(0.0, min(e, end) - max(s, start)) for s, e in self.distracted)
        if self.d_start is not None:
            distracted += max(0.0, end - max(self.d_start, start))
        distracted = min(distracted, present)
        return {'started_at': start, 'ended_at': end, 'present_sec': present,
                'distracted_sec': distracted, 'focus_sec': present - distracted}

    def totals(self, now):
        """진행 중인 세션의 현재 누적값 (IDLE 이면 None)."""
        if self.state == IDLE:
            return None
        return self._summary(now)


def focus_ratio(t):
    return t['focus_sec'] / t['present_sec'] if t['present_sec'] > 0 else 0.0


class PresenceDetection:
    HOST = os.environ.get('BLOG_HOST', 'http://127.0.0.1:8000')
    username = os.environ.get('BLOG_USER', 'admin')
    password = os.environ.get('BLOG_PASS', 'password')
    ABSENT_SEC = env_float('ABSENT_SEC', 30)               # 이 시간 이상 안 보이면 세션 종료
    THRESHOLD = env_float('FACE_THRESHOLD', 60)            # LBPH 거리: 작을수록 유사. 본인≈40, 타인≈75~ 사이에 선을 긋는다
    CONFIRM_FRAMES = int(os.environ.get('CONFIRM_FRAMES', 3))  # 연속 N프레임 인식돼야 '재석' 확정

    def __init__(self, token=None):
        self.enabled = False
        self.others = 0               # 이번 프레임에서 등록 사용자가 아닌 사람 수 (침입자 판정에 사용)
        self.last = {'ts': time.time(), 'owner_seen': False, 'person_count': 0, 'state': IDLE}
        model = os.path.join('faces', f'{self.username}.yml')
        if not (hasattr(cv2, 'face') and os.path.exists(model)):
            print(f'[Presence] disabled: {model} 없음 (python enroll_face.py --name {self.username})')
            return
        self.recognizer = create_lbph()
        self.recognizer.read(model)
        self.detector = cv2.CascadeClassifier(CASCADE)
        self.token = token or self._login()
        self.font = self._load_font()
        self.tracker = FocusTracker(self.ABSENT_SEC, self.CONFIRM_FRAMES)
        self.enabled = True
        print(f'[Presence] enabled for {self.username} '
              f'(ABSENT_SEC={self.ABSENT_SEC:g}, CONFIRM_FRAMES={self.CONFIRM_FRAMES}, FACE_THRESHOLD={self.THRESHOLD:g})')

    def _login(self):
        res = requests.post(self.HOST + '/api-token-auth/', {'username': self.username, 'password': self.password})
        res.raise_for_status()
        return res.json()['token']

    def _load_font(self):
        try:
            from PIL import ImageFont
            for path in FONT_CANDIDATES:
                if os.path.exists(path):
                    return ImageFont.truetype(path, 28)
        except ImportError:
            pass
        return None

    # ------------------------------------------------------------------
    def is_owner(self, frame, det, names):
        """person 박스마다 얼굴을 찾아 등록 사용자인지 판정. 등록 사용자가 아닌 사람 수는 self.others 에 기록."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        found, others = False, 0
        for *xyxy, conf, cls in det:
            if names[int(cls)] != 'person':
                continue
            x1, y1, x2, y2 = (int(v) for v in xyxy)
            roi = gray[max(0, y1):y2, max(0, x1):x2]
            if roi.size == 0:
                continue
            owner_here = False
            for (fx, fy, fw, fh) in self.detector.detectMultiScale(roi, 1.2, 5, minSize=(60, 60)):
                face = cv2.resize(roi[fy:fy + fh, fx:fx + fw], (200, 200))
                label, dist = self.recognizer.predict(face)
                owner = label == 0 and dist < self.THRESHOLD  # label 1(타인 샘플)에 더 가까우면 거리와 무관하게 타인
                color = (0, 255, 0) if owner else (0, 0, 255)
                cv2.rectangle(frame, (x1 + fx, y1 + fy), (x1 + fx + fw, y1 + fy + fh), color, 2)
                cv2.putText(frame, f'{self.username if owner else "unknown"} {dist:.0f}', (x1 + fx, y1 + fy - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                owner_here = owner_here or owner
            found = found or owner_here
            if not owner_here:
                others += 1  # 얼굴이 안 보이거나 등록 사용자가 아닌 person
        self.others = others
        return found

    def update(self, frame, det, names, save_dir):
        """매 프레임 호출: 상태 갱신 + 오버레이. 세션 시작/종료 시 서버에 게시. 프레임 정보는 self.last 에 남긴다."""
        now = time.time()
        person_count = sum(1 for *_, cls in det if names[int(cls)] == 'person')
        self.last = {'ts': now, 'owner_seen': False, 'person_count': person_count, 'state': IDLE}
        if not self.enabled:
            return
        owner_raw = self.is_owner(frame, det, names)
        for kind, info in self.tracker.step(now, owner_raw):
            self.on_event(kind, info, frame, save_dir)
        self.last.update(owner_seen=owner_raw, state=self.tracker.state)
        self.draw(frame, self.overlay(now))

    def on_event(self, kind, info, frame, save_dir):
        if kind == 'session_start':
            self.post('재석 시작', f'{self.username} 인식됨 - 세션 시작', frame, save_dir)
        elif kind == 'session_end':
            s = info
            text = (f'{self.username} 세션 종료 - 순공 {fmt(s["focus_sec"])} · 딴짓 {fmt(s["distracted_sec"])} · '
                    f'재석 {fmt(s["present_sec"])} · 집중도 {focus_ratio(s):.0%}')
            print(f'[Presence] session: present_sec={s["present_sec"]:.1f} distracted_sec={s["distracted_sec"]:.1f} '
                  f'focus_sec={s["focus_sec"]:.1f}')
            self.post('자리 비움', text, frame, save_dir)

    def overlay(self, now):
        """오버레이 줄 목록 [(text, color)]: 상태 · 순공시간 · 집중도."""
        tr = self.tracker
        t = tr.totals(now)
        if t is None:
            text = f'대기 {fmt(now - tr.since)}'
            if 0 < tr.streak < tr.confirm_frames:
                text += f'  (확인 중 {tr.streak}/{tr.confirm_frames})'
            if tr.sessions:
                text += f'  지난 세션 순공 {fmt(tr.sessions[-1]["focus_sec"])}'
            lines = [(text, GRAY)]
        else:
            head, color = ('딴짓 중', ORANGE) if tr.state == DISTRACTED else ('재석', GREEN)
            text = f'{head} · 순공 {fmt(t["focus_sec"])} · 집중도 {focus_ratio(t):.0%}'
            away_for = now - tr.last_seen
            if away_for > 2:
                text += f'  (미인식 {int(away_for)}s)'
            lines = [(text, color)]
            if tr.state == DISTRACTED or t['distracted_sec'] > 0:
                lines.append((f'딴짓 {fmt(t["distracted_sec"])}', ORANGE))
        if self.others:
            lines[0] = (lines[0][0] + f'  / 미등록 인원 {self.others}', lines[0][1])
        return lines

    def owner_only(self):
        """등록 사용자만 있고 미등록 인원이 없는 프레임이면 True → 침입자 판정에서 person 제외."""
        return self.enabled and self.tracker.state != IDLE and self.others == 0

    def draw(self, frame, lines):
        if self.font is None:  # 한글 폰트 없으면 영문
            for i, (text, color) in enumerate(lines):
                for ko, en in EN:
                    text = text.replace(ko, en)
                cv2.putText(frame, text, (10, 34 + 36 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
            return
        from PIL import Image, ImageDraw
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img)
        for i, (text, color) in enumerate(lines):
            draw.text((10, 8 + 36 * i), text, font=self.font, fill=color[::-1])
        frame[:] = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    def post(self, title, text, frame, save_dir):
        """상태 변화 이벤트를 블로그 게시글로 등록 (changedetection.send 와 동일한 API)."""
        today = datetime.now()
        save_path = pathlib.Path(os.getcwd()) / save_dir / 'presence' / str(today.year) / str(today.month) / str(today.day)
        save_path.mkdir(parents=True, exist_ok=True)
        full_path = save_path / f'{today.hour}-{today.minute}-{today.second}-{today.microsecond}.jpg'
        cv2.imwrite(str(full_path), cv2.resize(frame, (320, 240), interpolation=cv2.INTER_AREA))
        headers = {'Authorization': 'Token ' + self.token, 'Accept': 'application/json'}
        data = {'title': title, 'text': text, 'created_date': today, 'published_date': today}
        with open(full_path, 'rb') as f:
            res = requests.post(self.HOST + '/api_root/Post/', data=data, files={'image': f}, headers=headers)
        print(f'[Presence] {title}: {text} -> {res.status_code}')
