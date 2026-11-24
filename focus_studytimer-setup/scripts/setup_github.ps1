# Focus — GitHub 라벨 · 마일스톤 · 이슈 · 일일 계획 일괄 생성
# 사용 (레포 폴더 어디서든):  .\scripts\setup_github.ps1
#      다른 레포에 쓰려면:     .\scripts\setup_github.ps1 -Repo owner/name
# 두 번 실행해도 이미 있는 라벨/마일스톤/이슈는 건너뜀
param([string]$Repo = 'pyr27/focus_studytimer')

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$utf8 = New-Object System.Text.UTF8Encoding($false)
Write-Host "== target repo: $Repo"

# ---------------------------------------------------------------- labels
$labels = @(
    @('edge',          '1D76DB', 'Edge (PC · YOLOv5 · 얼굴 식별)'),
    @('server',        '0E8A16', 'Server (Django REST · Pythonanywhere)'),
    @('android',       'FBCA04', 'Client (Android · Kotlin/Compose)'),
    @('validation',    'D93F0B', '측정 정확도 검증 실험'),
    @('docs',          '5319E7', '문서 · 배포 · 보고서'),
    @('security',      'B60205', '보안 · 권한'),
    @('nonfunctional', 'F9D0C4', '캐시 · 오프라인 · 성능'),
    @('optional',      'BFD4F2', '시간 남으면 진행'),
    @('bug',           'D73A4A', '버그')
)
foreach ($l in $labels) {
    gh label create $l[0] --repo $Repo --color $l[1] --description $l[2] --force | Out-Null
    Write-Host "label  $($l[0])"
}

# ---------------------------------------------------------------- milestones (KST 23:59 = UTC 14:59)
$M1 = 'M1 최소 기능 (MVP)'
$M2 = 'M2 완성도 · 확장'
$milestones = @(
    @($M1, '2026-12-01T14:59:59Z', '핵심 = 정확한 순공시간 측정. 얼굴 식별 재석 + 휴대폰 딴짓 감지, 정답 비교 검증 도구, 세션 저장 API, 앱 홈, PA 배포까지 Edge→서버→앱 한 흐름 완성'),
    @($M2, '2026-12-07T14:59:59Z', '검증 결과 기반 튜닝·예외 보완(고개 숙임), 오프라인 큐, 집계·달력·기록, 최종 실험·데모·보고서. 제출 12/8')
)
$existing = gh api "repos/$Repo/milestones?state=all&per_page=100" | ConvertFrom-Json
foreach ($m in $milestones) {
    if ($existing | Where-Object { $_.title -eq $m[0] }) { Write-Host "ms     $($m[0]) (exists)"; continue }
    gh api "repos/$Repo/milestones" -f title=$m[0] -f due_on=$m[1] -f description=$m[2] | Out-Null
    Write-Host "ms     $($m[0])"
}

# ---------------------------------------------------------------- issues  (제목, 라벨, 마일스톤, 본문)
$issues = @(
    # ===== M1 : 11/24(화) ~ 12/1(화) =====
    @('[11/24] D1 레포 초기 세팅 + 공통평가 02 코드 이관', 'docs', $M1, @'
## 할 일
- [ ] 세팅 zip(README, .github, docs, scripts) 커밋 · push
- [ ] mobile_webservice_midterm2 → edge/ server/ android/ 이관 (SETUP.md 5번 robocopy)
- [ ] venv · runs · faces · db.sqlite3 · 테스트 이미지 제외 확인
- [ ] Actions CI 실행 확인 (실패 job 있으면 메모)
## 완료 조건
레포에서 edge/server/android 코드가 보이고 첫 커밋 이력이 남음
'@),
    @('[11/25] E1 재석 측정 상태머신 정리 (IDLE / PRESENT / DISTRACTED)', 'edge', $M1, @'
## 할 일
- [ ] presence.py 상태를 IDLE / PRESENT / DISTRACTED 3단계로 정리
- [ ] 세션 = PRESENT 시작 ~ 30초 부재 종료, 세션별 present_sec / distracted_sec / focus_sec 누적
- [ ] 오버레이: 상태 · 순공시간 · 집중도(focus/present)
- [ ] 파라미터 환경변수화: ABSENT_SEC, CONFIRM_FRAMES, FACE_THRESHOLD
## 완료 조건
웹캠 앞 착석 → 순공시간 증가, 30초 이탈 → 세션 종료 로그
'@),
    @('[11/25] E2 휴대폰 사용(딴짓) 감지', 'edge', $M1, @'
## 할 일
- [ ] PRESENT 중 YOLO cell phone 이 PHONE_SEC(기본 10초) 이상 연속 검출 → DISTRACTED
- [ ] 미검출 PHONE_SEC 지속 → PRESENT 복귀, 딴짓 시간은 순공에서 차감
- [ ] 오버레이 '딴짓 00:00:12' (주황)
## 완료 조건 / 증빙
폰 들기 전·후 화면 캡처, 딴짓 시간이 순공에서 빠지는 로그
'@),
    @('[11/26] V1 Edge 프레임 로그 (CSV)', 'validation,edge', $M1, @'
## 할 일
- [ ] 매 프레임 `ts, owner_seen, phone_seen, person_count, state` 를 logs/edge_YYYYMMDD_HHMM.csv 로 저장
- [ ] LOG_FRAMES=1 환경변수로 on/off
## 완료 조건
5분 실행 후 CSV 행 수 ≈ FPS × 300
'@),
    @('[11/26] V2 정답 기록기 gt_logger.py', 'validation', $M1, @'
## 할 일
- [ ] 키 입력으로 실제 상태 기록: s=공부 · p=폰 사용 · a=자리 비움 · q=종료
- [ ] `ts, label` CSV 저장 (Edge 로그와 같은 시계 사용)
- [ ] 화면에 현재 라벨 크게 표시 (누락 방지)
## 완료 조건
Edge와 동시에 실행해 두 CSV가 같은 시간 범위를 가짐
'@),
    @('[11/27] V3 평가 스크립트 evaluate.py', 'validation', $M1, @'
## 할 일
- [ ] 두 CSV를 1초 단위로 정렬 · 병합
- [ ] 지표: 순공시간 오차(분, %), 1초 상태 일치율, 혼동표(공부/딴짓/비움), 전환 감지 지연(초), 딴짓 구간 정밀도·재현율
- [ ] 비교군: 수동 타이머(켜 놓기) / 얼굴만 / 얼굴+폰
- [ ] 타임라인 그래프(정답 vs 측정) PNG 출력 → docs/results/
## 완료 조건
샘플 CSV로 지표 표 + 그래프 1장 생성
'@),
    @('[11/27] V4 예비 실험 T1 (평범한 공부 20분)', 'validation', $M1, @'
## 할 일
- [ ] Edge + gt_logger 동시 실행, 휴대폰으로 화면 녹화
- [ ] evaluate.py 로 첫 결과 확인, 이상한 점 메모
## 산출물
docs/results/T1_pilot.md (지표 표 + 그래프)
'@),
    @('[11/28] S1 StudySession / FocusEvent 모델 + 권한 + API', 'server,security', $M1, @'
## 할 일
- [ ] study 앱: StudySession(user, started_at, ended_at, present_sec, distracted_sec, focus_sec, client_uuid unique), FocusEvent(user, session, type, at)
- [ ] POST/GET /api/sessions/ , /api/events/ — Token 필수, 본인 것만(타인 404), client_uuid 멱등
- [ ] GET /api/stats/daily/ — 오늘 합계·집중도
- [ ] 테스트: 비인증 401 / 타인 404 / 중복 POST 1건
'@),
    @('[11/28] E3 Edge → 서버 세션 전송', 'edge', $M1, @'
## 할 일
- [ ] 세션 종료 시 POST /api/sessions/ (client_uuid 포함)
- [ ] 상태 전이 시 POST /api/events/ (present_start/end, distracted_start/end)
- [ ] 실패 시 콘솔 경고 (재전송은 M2 E4)
'@),
    @('[11/29] C1 Android 로그인 + 토큰 보관', 'android,security', $M1, @'
## 할 일
- [ ] 로그인 화면 → /api-token-auth/ → 토큰 저장(EncryptedSharedPreferences)
- [ ] OkHttp 인터셉터로 Authorization 헤더 자동 첨부, 로그아웃
- [ ] 기존 author=1 하드코딩 제거
'@),
    @('[11/29] C2 앱 홈: 오늘 순공시간 · 집중도', 'android', $M1, @'
## 할 일
- [ ] /api/stats/daily/ 표시: 순공시간, 집중도 %, 딴짓 시간, 오늘 세션 목록
- [ ] 당겨서 새로고침(또는 30초 폴링)
## 증빙
Edge 측정 → 앱 숫자 반영 화면
'@),
    @('[11/30] V5 검증 실험 T1~T6 1차', 'validation', $M1, @'
| # | 시나리오 | 확인 |
|---|---|---|
| T1 | 평범한 공부 | 기본 오차 |
| T2 | 자리 비움 10초 / 1분 | 30초 기준 |
| T3 | 폰 사용 5초 / 15초 / 60초 | 딴짓 기준·지연 |
| T4 | 폰을 책상에 두기만 | 오탐 |
| T5 | 고개 숙여 필기 | 얼굴 미검출 → 비움 오판 |
| T6 | 마스크·조명·타인 등장 | 식별 안정성 |

- [ ] 시나리오별 10~20분, 대본(언제 무엇을 할지) 미리 작성
- [ ] 결과를 docs/results/round1.md 에 표로 정리
'@),
    @('[12/1] D2 Pythonanywhere 배포 + MVP 통합 점검', 'docs', $M1, @'
## 할 일
- [ ] PA: git pull · migrate · Reload, BLOG_HOST=https://pyr.pythonanywhere.com 로 Edge 실행
- [ ] Edge → PA 서버 → 앱 홈 한 흐름 확인 (캡처)
- [ ] CI 초록불
- [ ] M1 회고: 남은 문제 · M2 우선순위 정리
'@),

    # ===== M2 : 12/2(수) ~ 12/7(월) =====
    @('[12/2] V6 결과 분석 + 파라미터 튜닝', 'validation', $M2, @'
## 할 일
- [ ] ABSENT_SEC · CONFIRM_FRAMES · PHONE_SEC · FACE_THRESHOLD 조합별로 evaluate.py 재계산(로그 재생)
- [ ] 오차 최소 조합 선택, 선택 근거 표 → 보고서 "설계 이유"
'@),
    @('[12/3] E5 고개 숙임(필기) 오판 보완 + 개선 전후 비교', 'edge,validation', $M2, @'
## 할 일
- [ ] YOLO person 박스는 유지되는데 얼굴만 안 보이는 경우 → 재석 유지(최대 N초)
- [ ] 단, 등록 사용자 확인은 마지막 인식 후 일정 시간 내만 인정
- [ ] T5 재실험: 개선 전/후 오차 비교 표 + 타임라인 그래프
'@),
    @('[12/3] E4 오프라인 큐 + 자동 재전송', 'edge,nonfunctional', $M2, @'
## 할 일
- [ ] 전송 실패 시 SQLite 큐 저장, 주기적 재전송(지수 백오프), client_uuid로 중복 방지
## 증빙
서버 끈 채 측정 → 서버 켜면 자동 업로드 로그
'@),
    @('[12/4] S2 일/월 집계 API + 캐시', 'server,nonfunctional', $M2, @'
- [ ] /api/stats/monthly/ (날짜별 focus_sec), 캐시 60s, 세션 생성 시 무효화
- [ ] 테스트: 캐시 HIT/MISS
'@),
    @('[12/4] C3 달력 히트맵', 'android', $M2, @'
- [ ] 월 달력, focus_sec 4단계 색, 날짜 탭 → 그날 세션 목록
'@),
    @('[12/5] S5 공부 기록 API + C5 기록 작성 (ML Kit 태깅)', 'server,android', $M2, @'
- [ ] StudyNote(user, date, content, image, tags) CRUD
- [ ] 앱: 날짜별 메모 작성·수정, 사진 첨부 시 ML Kit 라벨 → tags (02 코드 재사용)
'@),
    @('[12/5] S3 목표 · 뱃지', 'server,optional', $M2, @'
- [ ] 일 목표 시간, 달성 시 뱃지·연속 달성(스트릭) — 시간 남으면
'@),
    @('[12/6] S4 전체 사용자 순공 랭킹', 'server,android,optional', $M2, @'
- [ ] /api/ranking/?period=day|week (캐시) + 앱 리스트 — 시간 남으면
'@),
    @('[12/6] V7 최종 검증 실험 (튜닝 후 수치 확정)', 'validation', $M2, @'
- [ ] 최종 파라미터로 T1~T6 재실행, round1 대비 개선 표
- [ ] 수동 타이머 / 얼굴만 / 얼굴+폰 최종 비교 그래프
'@),
    @('[12/7] D3 데모 영상 + 결과 보고서', 'docs', $M2, @'
- [ ] 데모 영상 2분: 착석 → 폰 사용 → 자리 비움 → 앱 반영 → PA 웹
- [ ] 보고서: 문제 정의 · 설계 이유 · 정확도 결과 · 예외(T5) 개선 전후 · 커밋 이력 · AI 활용 · 한계
- [ ] 12/8 제출 체크리스트
'@)
)

$existingIssues = gh issue list --repo $Repo --state all --limit 300 --json title -q '.[].title'
$tmp = [IO.Path]::GetTempFileName()
foreach ($i in $issues) {
    if ($existingIssues -contains $i[0]) { Write-Host "issue  $($i[0]) (exists)"; continue }
    [IO.File]::WriteAllText($tmp, $i[3], $utf8)
    gh issue create --repo $Repo --title $i[0] --label $i[1] --milestone $i[2] --body-file $tmp | Out-Null
    Write-Host "issue  $($i[0])"
}

# ---------------------------------------------------------------- daily plan tracking issue
$planTitle = '📅 일일 계획 (11/24 ~ 12/8)'
$plan = @'
제출 **12/8(화)** · 핵심 = 정확한 순공시간 측정 (교수님 피드백: 얼굴 식별 + 휴대폰 검출로 잰 시간을 직접 잰 시간과 비교)

### M1 최소 기능 — ~12/1(화)
- [ ] 11/24(화) 레포 세팅 · 02 코드 이관 (D1)
- [ ] 11/25(수) 상태머신 정리 (E1) · 휴대폰 딴짓 감지 (E2)
- [ ] 11/26(목) 프레임 로그 (V1) · 정답 기록기 (V2)
- [ ] 11/27(금) 평가 스크립트 (V3) · 예비 실험 T1 (V4)
- [ ] 11/28(토) 세션/이벤트 모델·권한·API (S1) · Edge→서버 전송 (E3)
- [ ] 11/29(일) 앱 로그인 (C1) · 앱 홈 (C2)
- [ ] 11/30(월) 검증 실험 T1~T6 1차 (V5)
- [ ] 12/1(화) PA 배포 · 통합 점검 · M1 회고 (D2)

### M2 완성도 — ~12/7(월)
- [ ] 12/2(수) 결과 분석 · 파라미터 튜닝 (V6)
- [ ] 12/3(목) 고개 숙임 오판 보완 + 전후 비교 (E5) · 오프라인 큐 (E4)
- [ ] 12/4(금) 일/월 집계 + 캐시 (S2) · 달력 (C3)
- [ ] 12/5(토) 공부 기록 + ML Kit (S5/C5) · (선택) 목표·뱃지 (S3)
- [ ] 12/6(일) 최종 검증 실험 (V7) · (선택) 랭킹 (S4)
- [ ] 12/7(월) 데모 영상 · 보고서 (D3)
- [ ] 12/8(화) 최종 점검 · 제출

> 매일 끝나면 이 이슈에 한 줄 코멘트(한 일 / 막힌 점 / AI 활용) → 보고서 "과정" 항목 자료
'@
if ($existingIssues -notcontains $planTitle) {
    [IO.File]::WriteAllText($tmp, $plan, $utf8)
    $url = gh issue create --repo $Repo --title $planTitle --label docs --body-file $tmp
    try { gh issue pin $url --repo $Repo | Out-Null } catch {}
    Write-Host "issue  $planTitle (pinned)"
}
Remove-Item $tmp -ErrorAction SilentlyContinue
Write-Host "== done: https://github.com/$Repo/issues"
