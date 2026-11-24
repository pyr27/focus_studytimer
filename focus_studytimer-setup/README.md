# Focus — 카메라가 재는 순공타이머

경희대 모바일/웹서비스 프로젝트 기말 (2026-2) · 박예림 (2022105689)

YOLOv5 + 온디바이스 얼굴 식별로 **등록 사용자가 실제로 앉아 있는 시간**만 측정하고,
휴대폰 사용(딴짓)·자리 비움을 자동 차감해 순공부시간을 기록·집계·랭킹하는 서비스.

| 디렉터리 | 역할 | 기반 |
|---|---|---|
| `edge/` | PC + 웹캠. YOLOv5 검출 → 얼굴 식별 → 상태머신(재석/비움/딴짓) → REST 전송, 오프라인 큐 | 공통평가 02 `YOLOv5/` |
| `server/` | Django REST (Pythonanywhere). 세션·이벤트·기록·목표·뱃지·친구 모델, 집계·랭킹 API(캐시), 웹 대시보드 | 공통평가 02 `PhotoBlogServer/` |
| `android/` | Kotlin/Compose 앱. 로그인, 홈(오늘 순공·집중도), 달력 히트맵·뱃지, 친구 랭킹, 공부 기록(ML Kit 태깅) | 공통평가 02 `PhotoViewer/` |
| `docs/` | PRD, 아키텍처, API 명세, 스프린트 계획, 계획서/보고서 | — |

## 일정 (제출 12/8)
| 마일스톤 | 기간 | 목표 |
|---|---|---|
| M1 최소 기능 | 11/24 – 12/1 | 재석·딴짓 측정 + 정답 비교 검증 도구 + 세션 API + 앱 홈 + PA 배포 |
| M2 완성도 | 12/2 – 12/7 | 튜닝·예외 보완, 오프라인 큐, 집계·달력·기록, 최종 실험·보고서 |

핵심: **측정한 순공시간이 실제(직접 기록한 정답)와 얼마나 맞는가**를 수치로 검증 (`edge/` 프레임 로그 · `gt_logger.py` · `evaluate.py`)

이슈 번호 체계: `E#` Edge · `S#` Server · `C#` Client · `V#` 검증 · `D#` Docs (→ `docs/sprints.md`)

## 빠른 시작
```bash
# server
cd server && python -m venv venv && . venv/bin/activate && pip install -r requirements.txt
python manage.py migrate && python manage.py createsuperuser && python manage.py runserver 0.0.0.0:8000
# edge
cd edge && python -m venv venv && . venv/bin/activate && pip install -r requirements.txt
python enroll_face.py --name <계정> && python detect.py --source 0
```
