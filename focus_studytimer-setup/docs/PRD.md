# Focus — PRD (Product Requirements Document)

> 상태: 초안 (S0) · 작성 2026-11-14 · 담당 박예림

## 1. 한 줄 정의
카메라가 등록 사용자의 **재석 여부와 휴대폰 사용**을 직접 판단해 순공부시간을 자동 측정하고, 기록·목표·친구 랭킹으로 공부 습관을 유지시키는 서비스.

## 2. 문제
| 문제 | 근거 | Focus의 답 |
|---|---|---|
| 수동 타이머는 "켜 놓고 자리 비움"을 못 잡아 순공시간이 부풀려짐 | 열품타·Forest 모두 사용자 입력 기반 | 얼굴 식별 재석 측정, 30초 부재 시 자동 종료 |
| 휴대폰 사용이 집중 이탈 1순위인데 감지 불가 | — | YOLO `cell phone` 검출 → 딴짓 구간 차감, 집중도 산출 |
| 상시 카메라는 프라이버시 거부감 | — | 영상·얼굴은 Edge에서만 처리, 서버는 시각·상태만 보관, OFF 모드 |
| 혼자 공부는 지속이 어려움 | 열품타 그룹 랭킹·Study With Me 인기 | 친구 랭킹, "지금 공부 중" 표시, 스트릭 뱃지 |

## 3. 사용자
- 1차: 혼자 장시간 공부하는 대학생·수험생·취준생 (PC + 웹캠 보유)
- 2차: 스터디 그룹 (서로 랭킹 비교)

## 4. 범위
### In (기말 제출)
- Edge: E1 재석 측정(02 완료) · E2 딴짓 감지 · E3 프라이버시 모드 · E4 오프라인 큐 · E5 이벤트 스냅샷
- Server: S1 Session/Event 모델+권한 · S2 집계 API+캐시 · S3 목표·뱃지 · S4 친구·랭킹 · S5 공부 기록 · S6 토큰 보안 · S7 웹 대시보드
- Client: C1 로그인 · C2 홈 · C3 달력 · C4 랭킹 · C5 기록(ML Kit) · C6 주간 리포트 · C7 이미지 목록(공통)
### Out / 선택
- S8 FCM 푸시, 얼굴 블러, iOS, 다중 카메라, 학원 관리자 모드

## 5. 핵심 흐름
1. `enroll_face.py --name <계정>` 으로 얼굴 등록 (1회)
2. `detect.py --source 0` 실행 → 본인 인식 시 세션 시작, 상태 전이마다 `POST /api/events/`
3. 세션 종료 시 `POST /api/sessions/` (started_at, ended_at, focus_sec, distracted_sec)
4. 서버가 일/주/월 집계·목표 달성·뱃지 발급
5. 앱이 홈/달력/랭킹/기록 화면에 표시, 기록 작성 시 ML Kit 태깅

## 6. 상태 정의 (Edge)
| 상태 | 진입 조건 | 이탈 조건 | 서버 이벤트 |
|---|---|---|---|
| IDLE | 시작 / 자리 비움 확정 | 본인 연속 3프레임 인식 | `present_start` |
| PRESENT | — | 30초 미인식 → IDLE / cell phone N초 → DISTRACTED / OFF → PAUSED | `present_end` |
| DISTRACTED | PRESENT 중 cell phone ≥ N초(기본 10) | cell phone 미검출 N초 | `distracted_start` / `distracted_end` |
| PAUSED | 사용자 OFF | 사용자 ON | `pause` / `resume` |

순공시간 = PRESENT 누적 − DISTRACTED 누적. 집중도 = 순공 / PRESENT.

## 7. 지표 (KPI)
- 측정 정확도: 수동 기록 대비 오차 ±5% 이내 (자체 검증 1주)
- 서버 집계 응답: 랭킹 API p95 < 300ms (캐시 적중 시 < 50ms)
- 앱 주요 화면 4개 모두 Pythonanywhere 연동 동작

## 8. 리스크
| 리스크 | 대응 |
|---|---|
| 마스크·조명으로 얼굴 오인식 | 연속 프레임 확정, 임계값 환경변수, 재등록 안내 |
| PA 무료 플랜 CPU 제한 | 집계 캐시, 이미지 썸네일만 업로드 |
| Android 빌드 환경 이슈 | CI assembleDebug로 조기 검출 |
| 일정 (3주) | S1에서 수직 슬라이스 먼저, 소셜 기능은 S3로 격리 |
