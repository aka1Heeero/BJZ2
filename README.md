# 📦 발주관리표 - Streamlit 웹앱

아이패드 최적화 발주관리 대시보드입니다.

---

## 📁 프로젝트 구조

```
발주관리표/
├── app.py                        # 메인 Streamlit 앱
├── requirements.txt              # 패키지 목록
├── .streamlit/
│   └── secrets.toml.example      # 시크릿 설정 예시
└── README.md
```

---

## 🗂️ Google Sheets 컬럼 구조

### 기본정보 컬럼 (A~W열)
| 컬럼명 | 설명 |
|--------|------|
| 발주주체 | 발주팀/MD 등 |
| 발주구분 | 재발주/신규 등 |
| 품번 | 상품 코드 |
| 품번2 | 보조 상품 코드 |
| 품명 | 상품명 |
| 대분류 | 상품 대분류 |
| 중분류 | 상품 중분류 |
| 소분류 | 상품 소분류 |
| 담당 | 담당자명 |
| 관계사팀 | 관계사 팀명 |
| 중포 | 중포 수량 |
| 카톤 | 카톤 수량 |
| 등급 | 상품 등급 |
| 상태 | 신상품/정상/단종대기 |
| 업체명 | 공급업체명 |
| 산지 | 원산지 |
| 구입가 | 구입가격 |
| 판매가 | 판매가격 |
| 정상재고 | 정상 재고량 |
| 일출고량 | 일평균 출고량 |
| 미입고 | 미입고 수량 |
| 입고예정 | 입고 예정일 |
| 사진주소 | 상품 이미지 URL |
| S/N단가_통화 | 통화 구분 |
| S/N단가_금액 | 단가 금액 |
| S/N단가_재고일 | 재고일수 |

### 월별 데이터 컬럼 (X열 이후)
각 항목별로 **24/11 ~ 26/04** 월 데이터를 다음 형식으로 입력:

```
발주_24/11, 발주_24/12, 발주_25/01, ... , 발주_26/04
입고_24/11, 입고_24/12, ...
출고_24/11, ...
POS판매_24/11, ...
물류재고_24/11, ...
매장재고_24/11, ...
보유매장_24/11, ...
미입고_24/11, ...
```

> ⚠️ **중요**: 시트의 1행(헤더)에 정확히 위 형식으로 컬럼명을 입력해야 합니다.

---

## 🔐 Google Sheets 보안 연결 (Service Account)

### 1단계: Google Cloud 프로젝트 설정
1. [Google Cloud Console](https://console.cloud.google.com) 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. **APIs & Services > Library** 에서 아래 API 활성화:
   - Google Sheets API
   - Google Drive API

### 2단계: 서비스 계정 생성
1. **IAM & Admin > Service Accounts** 클릭
2. **Create Service Account** 클릭
3. 이름 입력 후 생성 (역할: Editor 또는 Viewer)
4. 생성된 서비스 계정 클릭 > **Keys** 탭 > **Add Key > Create new key**
5. **JSON** 선택 후 다운로드

### 3단계: Google Sheets 공유 설정
1. Google Sheets 열기
2. 우측 상단 **공유** 버튼 클릭
3. 서비스 계정 이메일 (예: `xxx@project.iam.gserviceaccount.com`) 추가
4. 권한: **뷰어** 설정 후 완료

### 4단계: secrets.toml 설정
다운로드한 JSON 파일 내용을 `.streamlit/secrets.toml` 에 입력:

```toml
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "key-id"
private_key = "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n"
client_email = "your-sa@your-project.iam.gserviceaccount.com"
client_id = "123456789"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-sa..."
```

---

## 🚀 로컬 실행

```bash
# 1. 패키지 설치
pip install -r requirements.txt

# 2. secrets 설정
mkdir -p .streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# secrets.toml 편집기로 열어서 실제 값 입력

# 3. 앱 실행
streamlit run app.py
```

---

## ☁️ Streamlit Cloud 배포

1. GitHub에 이 프로젝트 push
2. [share.streamlit.io](https://share.streamlit.io) 접속 > New app
3. Repository / Branch / Main file 선택
4. **Advanced settings > Secrets** 에 `secrets.toml` 내용 붙여넣기
5. **Deploy** 클릭

---

## 📱 아이패드 최적화

- 가로 스크롤 지원 (월별 데이터 테이블)
- 터치 친화적 UI (버튼, 드롭다운 크기 최적화)
- 반응형 레이아웃 (1024px 이하 자동 조정)
- `-webkit-overflow-scrolling: touch` 적용으로 부드러운 스크롤

---

## ⚙️ 주요 기능

| 기능 | 설명 |
|------|------|
| 담당자별 조회 | 담당자 선택 시 해당 상품만 필터링 |
| 분류별 조회 | 대분류 → 중분류 → 소분류 연동 필터 |
| 월 범위 선택 | 조회할 월 범위 선택 가능 (24/11~26/04) |
| 상품 이미지 | 사진주소 컬럼의 URL로 이미지 표시 |
| 월별 데이터 표 | 발주/입고/출고/POS판매/물류재고/매장재고/보유매장/미입고 |
| 캐시 | 5분 단위 데이터 캐시 (성능 최적화) |
