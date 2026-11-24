# Focus — 아키텍처

```
┌──────────────── EDGE (PC, Python) ────────────────┐   HTTPS/Token   ┌────────── SERVICE (Pythonanywhere) ──────────┐
│ webcam → YOLOv5 (person, cell phone, book, laptop)│ ─────────────▶ │ Django REST Framework                          │
│        → LBPH 얼굴 식별 (등록 사용자 / unknown)    │  POST events   │  TokenAuth · IsOwner · throttling              │
│        → 상태머신 IDLE/PRESENT/DISTRACTED/PAUSED  │  POST sessions │  models: StudySession FocusEvent StudyNote     │
│        → SQLite 오프라인 큐 → 재전송              │  POST posts    │          Goal Badge Friendship Post            │
│   (영상·얼굴 데이터는 PC 밖으로 나가지 않음)       │                │  services: 집계(일/주/월, cache 60s) · 뱃지 엔진│
└───────────────────────────────────────────────────┘                │  web: 블로그 · 달력 · 랭킹 대시보드           │
                                                                     └──────────────┬───────────────────────────────┘
                                                                                    │ HTTPS/REST (+FCM, 선택)
                                                                     ┌──────────────▼───────────────────────────────┐
                                                                     │ ANDROID (Kotlin · Compose · OkHttp)           │
                                                                     │  로그인(Token) · 홈 · 달력 · 랭킹 · 기록(ML Kit)│
                                                                     └──────────────────────────────────────────────┘
```

## 모듈 경계
| 계층 | 모듈 | 책임 | 02에서 가져옴 |
|---|---|---|---|
| edge | `detect.py` | YOLO 루프, 모듈 호출 | ✔ (수정 5+3곳) |
| edge | `presence.py` | 얼굴 식별 + 재석/비움 상태 | ✔ |
| edge | `distraction.py` | cell phone 기반 딴짓 판정 (신규) | |
| edge | `queue.py` | SQLite 큐, 재전송 (신규) | |
| edge | `changedetection.py` | 미등록 인원 침입 게시 | ✔ |
| server | `blog/` | Post 블로그, 인증 (기존) | ✔ |
| server | `study/` | Session/Event/Note/Goal/Badge/Friendship, 집계·랭킹 API (신규 앱) | |
| android | `MainActivity.kt` → 패키지 분리 | `auth/ home/ calendar/ ranking/ note/` (신규) | ML Kit 부분 ✔ |

## 데이터 모델 (server/study)
```
StudySession(user, started_at, ended_at, present_sec, distracted_sec, focus_sec, source='edge', client_uuid unique)
FocusEvent(user, session?, type[present_start|present_end|distracted_start|distracted_end|pause|resume], at, snapshot?)
StudyNote(user, date unique_together, content, image?, tags[])
Goal(user, period[day|week|month], target_sec, active)
Badge(user, code, earned_at, meta)        # daily_goal, streak_3, streak_7, week_goal, first_10h ...
Friendship(from_user, to_user, status[pending|accepted], created_at)
```
`client_uuid` 로 오프라인 큐 재전송 시 중복 생성 방지 (멱등 POST).

## 비기능
- 보안: 모든 쓰기 API Token 필수, 소유자 외 404, 이미지 업로드 크기/형식 검증
- 성능: 집계·랭킹 LocMemCache 60s, 세션 생성 시 캐시 무효화, 랭킹 30req/min 스로틀
- 오프라인: Edge 큐 (서버 불통 시 저장 → 지수 백오프 재전송)
- 프라이버시: 영상 미전송, 썸네일만(320×240), OFF 모드
