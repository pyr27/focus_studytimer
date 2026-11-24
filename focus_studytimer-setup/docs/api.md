# Focus — API 명세 (초안)

Base: `https://pyr.pythonanywhere.com` · 인증: `Authorization: Token <token>` (쓰기 전부 필수)

| Method | Path | 설명 | 권한 |
|---|---|---|---|
| POST | `/api-token-auth/` | username/password → token | - |
| GET/POST | `/api_root/Post/` | 이벤트 이미지 블로그 (기존) | 읽기 공개 / 쓰기 Token |
| POST | `/api/sessions/` | 세션 생성 `{client_uuid, started_at, ended_at, present_sec, distracted_sec}` (멱등) | owner |
| GET | `/api/sessions/?date=YYYY-MM-DD` | 내 세션 목록 | owner |
| POST | `/api/events/` | 상태 전이 이벤트 `{type, at, snapshot?}` | owner |
| GET | `/api/stats/daily/?date=` | 하루 집계 `{present_sec, distracted_sec, focus_sec, sessions, focus_rate}` | owner |
| GET | `/api/stats/weekly/?week=` | 요일별 집계 + 시간대 히스토그램 | owner |
| GET | `/api/stats/monthly/?month=` | 날짜별 focus_sec (달력 히트맵용) + 뱃지 | owner |
| GET/PUT | `/api/goals/` | 일/주/월 목표 | owner |
| GET | `/api/badges/` | 획득 뱃지, 현재 스트릭 | owner |
| GET/POST/PUT | `/api/notes/?date=` | 날짜별 공부 기록 (content, image, tags) | owner |
| GET/POST | `/api/friends/` | 친구 목록 / 요청 `{username}` | owner |
| POST | `/api/friends/{id}/accept/` | 수락 | 대상자 |
| GET | `/api/ranking/?period=day\|week&scope=friends\|all` | 순공시간 랭킹 + `studying_now` 플래그 (cache 60s, 30/min) | 로그인 |
| GET | `/api/me/` | 프로필, 현재 상태(PRESENT/...) | owner |

## 응답 예시 — `/api/stats/daily/`
```json
{"date":"2026-12-05","present_sec":14520,"distracted_sec":720,"focus_sec":13800,"sessions":4,"focus_rate":0.95,"goal_sec":14400,"goal_met":false}
```

## 오류 규약
- 401 토큰 없음/무효 · 403 권한 없음 · 404 타인 리소스(존재 숨김) · 429 스로틀 · 400 검증 실패(`{"field":["msg"]}`)
