# 08. Git / GitHub 협업

## 1. 이번 단계의 목적

로컬 결과를 Private Repository에서 검토·추적한다. 이 작업에서 실제 GitHub 업로드/PR 생성은 하지 않았다.

## 2. 필요한 사전조건

GitHub 계정과 Private Repository 생성 권한. 비밀번호/API Key를 소스에 넣지 않는다.

## 3. 실행환경

Ubuntu 22.04 LTS, /usr/bin/python3 3.10, ROS 2 Humble. 예시 작업경로는 ~/Desktop/INHA-ALATUS_SW/ALATUS_ROS2_v0.4다. 압축을 다른 곳에 풀었다면 cd 경로만 실제 경로로 바꾼다.

## 4. 실제 실행 명령어

```bash
sudo apt update
sudo apt install -y git
cd ~/Desktop/INHA-ALATUS_SW/ALATUS_ROS2_v0.4
git config --global user.name "YOUR_NAME"
git config --global user.email "YOUR_VERIFIED_EMAIL"
git init -b main
git status --short
git add .
git diff --cached --stat
git commit -m "Add ALATUS v0.4 source foundation and verification"
```

GitHub 웹에서 New repository → Private → 빈 Repository를 만든다. 로컬 README가 있으므로 웹에서 README 초기화는 하지 않는다. GitHub URL의 OWNER/REPOSITORY를 실제 값으로 바꾼다:

```bash
git remote add origin git@github.com:OWNER/REPOSITORY.git
git push -u origin main
```

SSH Key를 GitHub 계정에 등록하거나 HTTPS + 공식 credential manager로 인증한다. Token을 URL/명령/README에 기록하지 않는다. 다른 개발자:

```bash
git clone git@github.com:OWNER/REPOSITORY.git
cd REPOSITORY
code .
git switch -c feature/kalman-evaluation
# 파일 수정 후
bash tools/test_v04.sh
git add src tests docs
git diff --cached
git commit -m "Improve tracker dropout evaluation"
git push -u origin feature/kalman-evaluation
```

GitHub에서 Compare & pull request → 변경/시험/NOT TESTED 항목 작성 → 리뷰 → CI 결과 확인 → Merge한다. 로컬 갱신과 Release:

```bash
git switch main
git pull --ff-only
git log --oneline --decorate -10
git tag -a v0.4.0-source -m "Source foundation; ROS/SITL acceptance pending"
git push origin v0.4.0-source
```

실제 검증 뒤 Tag/Release 이름을 근거에 맞게 바꾼다. 이 ZIP만으로 flight-ready나 SITL-validated tag를 붙이지 않는다.

## 5. 전체 코드 또는 수정파일

.github/workflows/humble.yml은 Jammy/Humble 컨테이너에서 dependency install, colcon build/test, Python/ROS smoke를 실행한다. 실제 GitHub Actions 실행은 NOT TESTED다. .gitignore/.gitattributes/CONTRIBUTING/PR template 포함.

## 6. 예상 출력

git log에 Commit이 보이고 Private 원격에 source가 올라간다. Actions가 돌면 실제 성공/실패 로그를 확인한다. 제공한 workflow 파일 존재 자체가 CI PASS는 아니다.

## 7. 성공 판정

branch/PR/review/CI/merge 이력이 남고 메시지·프레임·권한 변경을 리뷰한다. 특정 3인 Task 분배는 제공하지 않는다.

## 8. 대표적인 오류

Permission denied(publickey), remote already exists, non-fast-forward, Git에 영상/가중치가 들어감.

## 9. 오류 해결 방법

GitHub 인증키/원격 주소/권한을 확인한다. git remote -v와 git status를 본다. 충돌은 git pull --rebase 또는 팀 merge 정책에 따라 해결하며 무조건 force push하지 않는다. 대용량 파일은 별도 버전저장소/객체저장소와 SHA manifest를 기본으로 사용한다. Git LFS를 선택할 때만 용량/쿼터/접근권한을 정하고 .gitattributes LFS 규칙을 추가한다. 이미 commit한 Secret은 단순 삭제 외에 폐기/재발급이 필요하다.

## 10. 다음 단계와 연결

CI 결과와 사용자 PC/온보드 시험 증거를 VALIDATION.md에 실제로 갱신한다.
