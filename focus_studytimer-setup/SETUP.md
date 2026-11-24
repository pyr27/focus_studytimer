# 레포 초기 세팅 순서 (한 번만)

## 0. 준비 (데스크탑)
```powershell
winget install GitHub.cli        # gh 설치 (이미 있으면 생략)
gh auth login                    # GitHub.com → HTTPS → 브라우저 로그인
gh auth refresh -s project       # Projects 보드까지 만들려면 (선택)
```

## 1. GitHub에서 빈 레포 생성
- (완료) github.com/pyr27/focus_studytimer

## 2. 로컬에 clone → zip 내용 풀기
```powershell
cd C:\4-2\mwp
git clone https://github.com/pyr27/focus_studytimer.git
cd focus_studytimer
```
이 zip의 내용(README.md, SETUP.md, .github/, docs/, edge/, server/, android/, scripts/, .gitignore)을 **이 폴더 안에** 그대로 풀기.
`dir` 했을 때 `.github`, `docs`, `scripts` 가 보이면 맞게 푼 것.

## 3. 첫 커밋 · push
```powershell
git add -A
git commit -m "S0: 레포 뼈대, CI, 문서 템플릿"
git push -u origin main
```
→ Actions 탭에서 CI가 돌아감. 아직 코드가 없어서 server/edge job은 실패해도 정상 (D5 이관 후 통과시키면 됨).
실패가 거슬리면 D5 끝날 때까지 `.github/workflows/ci.yml`의 `on:` 아래에 `workflow_dispatch:`만 남겨두고 push 트리거를 잠시 빼도 됨.

## 4. 라벨 · 마일스톤 · 이슈 · 보드 생성
```powershell
.\scripts\setup_github.ps1
```
- 라벨 9개, 마일스톤 M1(~12/1)·M2(~12/7), 이슈 23개(제목 앞 [날짜]), 고정 이슈 "📅 일일 계획"이 생김
- 두 번 실행해도 이미 있는 건 건너뜀

## 5. 02 코드 이관 (D5)
```powershell
# midterm2 레포에서 폴더 복사 (venv, runs, faces, db.sqlite3, media/images/2026/11 제외)
robocopy C:\4-2\mwp\mobile_webservice_midterm2\YOLOv5         edge    /E /XD venv runs faces __pycache__ .git
robocopy C:\4-2\mwp\mobile_webservice_midterm2\PhotoBlogServer server  /E /XD venv htmlcov __pycache__ .claude /XF db.sqlite3 .coverage
robocopy C:\4-2\mwp\mobile_webservice_midterm2\PhotoViewer     android /E /XD build .gradle .idea .kotlin
git add -A; git commit -m "D5: 공통평가 02 코드 이관"; git push
```
이후 Actions가 초록불이면 D6 완료.

## 일상 작업 흐름
1. 보드에서 이슈 하나 집기 → 브랜치 `git switch -c feat/E2-distraction`
2. 작업 → 커밋 메시지에 `closes #<이슈번호>`
3. push → PR 생성 (템플릿 체크리스트) → CI 통과 → merge
4. 완료 캡처를 `docs/captures/E2_*.png` 로 저장 (보고서용)
