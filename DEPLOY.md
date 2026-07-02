# 올리브영 프로모션 대시보드 — 외부 공개 배포 런북

이 폴더(`deploy_oliveyoung/`)만 GitHub에 올려서 **Streamlit Community Cloud**로 배포합니다.
`streamlit_app.py` 한 페이지(올리브영 프로모션)만 포함됩니다.

> ⚠️ **이 대시보드는 비플레인 실적(구글 시트 raw_total) 데이터를 보여줍니다.**
> **비공개(Private) 앱 + 나만 접근**으로 배포합니다 (아래 5단계).
> → 접근 허용 이메일: **hyk.im@madup.com (본인만)**. 나중에 팀원 추가는 이메일만 더 넣으면 됨.

---

## 왜 서비스계정이 필요한가
내 PC에서는 `~/.claude/google-oauth-token.json`(OAuth 사용자 토큰)으로 시트를 읽지만,
이 토큰은 (1) 서버에서 작동 안 하고 (2) 공개 저장소에 올리면 안 됩니다.
그래서 클라우드에서는 **구글 서비스계정**을 만들어 Streamlit Secrets에 넣습니다.
`gsheet_source.py`는 Secrets가 있으면 서비스계정을, 없으면 로컬 토큰을 자동으로 씁니다.

---

## 1) 구글 서비스계정 만들기
1. https://console.cloud.google.com → 프로젝트 선택(또는 새로 생성)
2. **API 및 서비스 → 라이브러리** → "Google Sheets API" 검색 → **사용 설정**
3. **API 및 서비스 → 사용자 인증 정보 → 사용자 인증 정보 만들기 → 서비스 계정**
   - 이름 아무거나(예: `beplain-dashboard`) → 만들기 → 역할 없이 완료
4. 만든 서비스계정 클릭 → **키 → 키 추가 → 새 키 만들기 → JSON** → 다운로드
   - 이 JSON 파일 안의 `client_email` 값을 복사해둡니다 (예: `beplain-dashboard@xxx.iam.gserviceaccount.com`)

## 2) 구글 시트를 서비스계정에 공유
- 대상 시트(raw_total 있는 스프레드시트) 열기 → **공유** → 위에서 복사한 `client_email` 붙여넣기 → **뷰어** 권한 → 공유
- (서비스계정이 시트를 못 읽으면 대시보드가 빈 화면이 됩니다.)

## 3) GitHub 저장소에 이 폴더 올리기
> 이 PC엔 `gh` CLI가 없으므로, GitHub에서 빈 저장소를 먼저 만든 뒤 아래 명령으로 푸시합니다.
> GitHub 웹에서 New repository → 이름 예: `beplain-oy-dashboard` → **Private** 선택 → 생성.

```bash
cd "C:/Users/MADUP/Desktop/0701_교육/dashboard/deploy_oliveyoung"
git init
git add .
git status   # ← *.json, secrets.toml 이 목록에 없는지 반드시 확인!
git commit -m "올리브영 프로모션 대시보드 배포용"
git branch -M main
git remote add origin https://github.com/<your-id>/beplain-oy-dashboard.git
git push -u origin main
```
- `git status`에 **인증 관련 파일(*.json, secrets.toml)이 절대 보이면 안 됩니다** (.gitignore로 막혀 있음). 보이면 push 중단하고 알려주세요.

## 4) Streamlit Community Cloud 연결
1. https://share.streamlit.io → GitHub 로그인
2. **New app** → 저장소 `beplain-oy-dashboard`, 브랜치 `main`, Main file `streamlit_app.py` 선택
3. **Advanced settings → Secrets** 에 서비스계정 JSON을 아래 형식으로 붙여넣기
   (이 폴더의 `.streamlit/secrets.toml.example` 형식 참고 — JSON의 각 필드를 옮기면 됨):
   ```toml
   [gcp_service_account]
   type = "service_account"
   project_id = "..."
   private_key_id = "..."
   private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
   client_email = "...@...iam.gserviceaccount.com"
   client_id = "..."
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "..."
   universe_domain = "googleapis.com"
   ```
4. **Deploy** → 1~2분 후 `https://<app-이름>.streamlit.app` URL 발급

## 5) 접근 제한 — 나만 보기 (필수)
- 배포 후 앱 화면 우측 하단 **⋮ → Settings → Sharing**
- **"Who can view this app"** 에서 공개(public)를 끄고 **특정 이메일만 허용**으로 설정
- 허용 이메일에 **`hyk.im@madup.com`** 추가 → 저장
- 이러면 링크가 있어도 **본인(구글 로그인)만** 볼 수 있습니다. 팀 공유가 필요해지면 여기에 이메일만 추가하면 됨.
- (참고: 비공개 앱은 무료 Community Cloud에서 지원됩니다. 뷰어 수 제한이 있으니 나만/소수면 충분.)

---

## 데이터 갱신
- 시트(raw_total)에 새 데이터가 쌓이면 → 대시보드에서 우측 상단 **🔄 새로고침** 또는 재접속(5분 캐시)
- 코드/차트를 바꾸려면 이 폴더에서 수정 후 `git add . && git commit && git push` → 클라우드가 자동 재배포

## 로컬에서 테스트
```bash
uv run --with streamlit --with pandas --with plotly --with google-auth --with google-auth-httplib2 --with google-api-python-client streamlit run streamlit_app.py
```
(로컬에선 Secrets 없이 `~/.claude` OAuth 토큰으로 자동 폴백)
