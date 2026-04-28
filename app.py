import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ─── 페이지 설정 ───────────────────────────────────────────────
st.set_page_config(
    page_title="BJ-KLP",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');

  html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
    font-size: 12px;
  }
  .stApp { background: #f5f5f5; }

  /* 헤더 */
  .page-header {
    display: flex; align-items: center; gap: 8px;
    padding: 8px 16px; margin-bottom: 10px;
  }
  .page-header .dot { color: #e53e3e; font-size: 18px; }
  .page-header h1 { font-size: 1.1rem; font-weight: 700; margin: 0; color: #1a1a1a; }

  /* 필터 영역 */
  .filter-box {
    background: white; border: 1px solid #ccc; padding: 10px 14px;
    margin-bottom: 10px; font-size: 12px;
  }
  .filter-box label { font-weight: 500; color: #333; margin-right: 4px; }

  /* 조회 버튼 */
  .search-btn-wrap div.stButton > button {
    background: #e8e8e8; color: #333; border: 1px solid #aaa;
    border-radius: 3px; padding: 4px 16px; font-size: 12px;
    font-weight: 600;
  }

  /* 메인 테이블 */
  .tbl-wrap { overflow-x: auto; margin-top: 6px; }
  table.main-tbl {
    border-collapse: collapse; width: 100%; font-size: 11px;
    border: 1px solid #999;
  }
  table.main-tbl th {
    background: #f0f0f0; color: #333; font-weight: 600;
    padding: 4px 6px; border: 1px solid #bbb;
    text-align: center; white-space: nowrap; font-size: 11px;
    position: sticky; top: 0; z-index: 2;
  }
  table.main-tbl td {
    padding: 3px 5px; border: 1px solid #ccc;
    white-space: nowrap; font-size: 11px; color: #333;
  }
  table.main-tbl td.num { text-align: right; }
  table.main-tbl td.center { text-align: center; }
  table.main-tbl td.left { text-align: left; }

  /* 상품 구분 행 - 첫 행 */
  table.main-tbl tr.prod-first td { border-top: 2px solid #888; }

  /* POS판매 행 강조 */
  table.main-tbl tr.row-pos td { background: #ffe0e0; }
  table.main-tbl tr.row-pos td.type-label { background: #ffcccc; color: #c00; font-weight: 600; }

  /* 구분 라벨 */
  table.main-tbl td.type-label {
    text-align: center; font-weight: 500; background: #fafafa;
    min-width: 55px;
  }

  /* 0값 스타일 */
  table.main-tbl td.zero-val { color: #bbb; }

  /* 발주주체 셀 */
  table.main-tbl td.owner-cell {
    font-weight: 500; font-size: 10px; color: #555;
    vertical-align: bottom; padding-bottom: 2px;
  }

  /* 상태 배지 */
  .st-badge {
    display: inline-block; padding: 1px 6px; border-radius: 2px;
    font-size: 10px; font-weight: 600;
  }
  .st-badge.신상품 { background: #d4edda; color: #155724; }
  .st-badge.단종대기 { background: #f8d7da; color: #721c24; }
  .st-badge.정상 { background: #e2e3e5; color: #383d41; }

  /* selectbox 크기 조정 */
  .stSelectbox > div > div { font-size: 12px !important; }
  .stMultiSelect > div > div { font-size: 12px !important; }
  .stCheckbox label { font-size: 12px !important; }

  /* 로딩 스피너 숨김 */
  div[data-testid="stStatusWidget"] { display: none; }

  /* 상품 이미지 */
  table.main-tbl td.img-cell {
    text-align: center; vertical-align: middle; padding: 2px;
  }
  table.main-tbl td.img-cell img {
    width: 48px; height: 48px; object-fit: contain;
    border: 1px solid #ddd; border-radius: 3px; background: #fff;
  }
  table.main-tbl td.img-cell .img-placeholder {
    width: 48px; height: 48px; background: #f0f0f0;
    border: 1px solid #ddd; border-radius: 3px;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 18px; color: #bbb;
  }

  /* 아이패드 최적화 */
  @media (max-width: 1024px) {
    table.main-tbl th, table.main-tbl td { padding: 2px 3px; font-size: 10px; }
    table.main-tbl td.img-cell img { width: 36px; height: 36px; }
  }
</style>
""", unsafe_allow_html=True)


# ─── Google Sheets 연결 ──────────────────────────────────────────
SHEET_ID = "1MZrzRkcbA7tcF8GiP5iQGOAWRtwfxyL3-_4h2-2k76o"

@st.cache_resource(ttl=300)
def get_gsheet_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

@st.cache_data(ttl=300)
def load_data():
    try:
        client = get_gsheet_client()
        sh = client.open_by_key(SHEET_ID)
        ws = sh.get_worksheet(0)
        data = ws.get_all_values()
        if not data or len(data) < 2:
            return pd.DataFrame()
        df = pd.DataFrame(data[1:], columns=data[0])
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Google Sheets 연결 오류: {e}")
        return pd.DataFrame()


# ─── 월 컬럼 목록 생성 (24/11 ~ 26/04) ─────────────────────────
def gen_month_labels():
    months = []
    for y in range(24, 27):
        for m in range(1, 13):
            lbl = f"{y:02d}/{m:02d}"
            months.append(lbl)
            if y == 26 and m == 4:
                return months
    return months

ALL_MONTHS = gen_month_labels()
ROW_TYPES = ["발주", "입고", "출고", "POS판매", "물류재고", "매장재고", "보유매장", "미입고"]


def get_col(df, name):
    if name in df.columns:
        return name
    for c in df.columns:
        if name in c or c in name:
            return c
    return None


def safe_int(v):
    try:
        return int(float(str(v).replace(",", ""))) if v not in ("", None) else 0
    except:
        return 0


def get_monthly_val(row, row_type, month):
    col = f"{row_type}_{month}"
    if col in row.index:
        return safe_int(row[col])
    return 0


def fmt_num(v):
    """숫자 포맷: 0이면 0, 아니면 천단위 콤마"""
    if v == 0:
        return "0"
    return f"{v:,}"


# ─── 헤더 ───────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
  <span class="dot">●</span>
  <h1>발주관리표2</h1>
</div>
""", unsafe_allow_html=True)

# ─── 데이터 로드 ─────────────────────────────────────────────────
with st.spinner("데이터 불러오는 중..."):
    df_raw = load_data()

if df_raw.empty:
    st.warning("데이터가 없습니다. Google Sheets 연결 및 데이터를 확인해주세요.")
    st.stop()

# ─── 컬럼명 파악 ─────────────────────────────────────────────────
col_담당 = get_col(df_raw, "담당")
col_대분류 = get_col(df_raw, "대분류")
col_중분류 = get_col(df_raw, "중분류")
col_소분류 = get_col(df_raw, "소분류")
col_품명 = get_col(df_raw, "품명")
col_품번 = get_col(df_raw, "품번")
col_상태 = get_col(df_raw, "상태")
col_발주주체 = get_col(df_raw, "발주주체")
col_발주구분 = get_col(df_raw, "발주구분")
col_판매가 = get_col(df_raw, "판매가")
col_구입가 = get_col(df_raw, "구입가")
col_사진주소 = get_col(df_raw, "사진주소")
col_업체명 = get_col(df_raw, "업체명")
col_관계사팀 = get_col(df_raw, "관계사팀")
col_등급 = get_col(df_raw, "등급")
col_정상재고 = get_col(df_raw, "정상재고") or get_col(df_raw, "정상 재고")
col_일출고량 = get_col(df_raw, "일출고량") or get_col(df_raw, "일출고")
col_미입고 = get_col(df_raw, "미입고")
col_입고예정 = get_col(df_raw, "입고예정")
col_SN통화 = get_col(df_raw, "통화") or get_col(df_raw, "S/N단가_통화")
col_SN금액 = get_col(df_raw, "금액") or get_col(df_raw, "S/N단가_금액")
col_SN재고일 = get_col(df_raw, "재고 일수") or get_col(df_raw, "재고일") or get_col(df_raw, "S/N단가_재고일")

# ─── 필터 UI (샘플 사진 스타일) ──────────────────────────────────

# 1행: 등록일자, 상품담당자, 수입구분
r1c1, r1c2, r1c3, r1c4 = st.columns([1.2, 1, 1, 1])
with r1c1:
    등록일자 = st.text_input("등록일자", value="2025/04", disabled=True)
with r1c2:
    담당_options = ["- 전체 -"]
    if col_담당:
        vals = sorted(df_raw[col_담당].dropna().unique().tolist())
        담당_options += [v for v in vals if v.strip()]
    sel_담당 = st.selectbox("상품담당자", 담당_options)
with r1c3:
    수입구분_options = ["- 전체 -"]
    sel_수입구분 = st.selectbox("수입구분", 수입구분_options)
with r1c4:
    pass

# 2행: 상태, 단종예정포함, 관계사팀, 결품상태
r2c1, r2c2, r2c3, r2c4 = st.columns([1.2, 1, 1, 1])
with r2c1:
    상태_options = ["전체"]
    if col_상태:
        vals = sorted(df_raw[col_상태].dropna().unique().tolist())
        상태_options += [v for v in vals if v.strip()]
    sel_상태 = st.selectbox("상태", 상태_options)
with r2c2:
    단종포함 = st.checkbox("단종예정포함", value=True)
with r2c3:
    관계사팀_options = ["- 전체 -"]
    if col_관계사팀:
        vals = sorted(df_raw[col_관계사팀].dropna().unique().tolist())
        관계사팀_options += [v for v in vals if v.strip()]
    sel_관계사팀 = st.selectbox("관계사팀", 관계사팀_options)
with r2c4:
    결품_options = ["- 전체 -"]
    sel_결품 = st.selectbox("결품상태", 결품_options)

# 3행: 상품등급, 납품업체
r3c1, r3c2, r3c3, r3c4 = st.columns([1.2, 1, 1, 1])
with r3c1:
    등급_options = ["- 전체 -"]
    if col_등급:
        vals = sorted(df_raw[col_등급].dropna().unique().tolist())
        등급_options += [v for v in vals if v.strip()]
    sel_등급 = st.selectbox("상품등급", 등급_options)
with r3c2:
    업체_options = ["전체"]
    if col_업체명:
        vals = sorted(df_raw[col_업체명].dropna().unique().tolist())
        업체_options += [v for v in vals if v.strip()]
    sel_업체 = st.selectbox("납품업체", 업체_options)
with r3c3:
    pass
with r3c4:
    pass

# 4행: 상품분류 (대/중/소)
r4c1, r4c2, r4c3, r4c4 = st.columns([1.2, 1, 1, 1])
with r4c1:
    대분류_options = ["전체"]
    if col_대분류:
        vals = sorted(df_raw[col_대분류].dropna().unique().tolist())
        대분류_options += [v for v in vals if v.strip()]
    sel_대분류 = st.selectbox("상품분류(대)", 대분류_options)
with r4c2:
    중분류_options = ["전체"]
    if col_중분류:
        df_f = df_raw if sel_대분류 == "전체" else df_raw[df_raw[col_대분류] == sel_대분류]
        vals = sorted(df_f[col_중분류].dropna().unique().tolist())
        중분류_options += [v for v in vals if v.strip()]
    sel_중분류 = st.selectbox("상품분류(중)", 중분류_options)
with r4c3:
    소분류_options = ["전체"]
    if col_소분류:
        df_f2 = df_raw.copy()
        if sel_대분류 != "전체" and col_대분류:
            df_f2 = df_f2[df_f2[col_대분류] == sel_대분류]
        if sel_중분류 != "전체" and col_중분류:
            df_f2 = df_f2[df_f2[col_중분류] == sel_중분류]
        vals = sorted(df_f2[col_소분류].dropna().unique().tolist())
        소분류_options += [v for v in vals if v.strip()]
    sel_소분류 = st.selectbox("상품분류(소)", 소분류_options)
with r4c4:
    pass

# 5행: 품번 검색
r5c1, r5c2, r5c3, r5c4 = st.columns([1.2, 1, 1, 1])
with r5c1:
    품번검색 = st.text_input("품번", placeholder="품번 입력")
with r5c2:
    pass
with r5c3:
    pass
with r5c4:
    pass

# 발주주체 체크박스
st.markdown("---")
chk_c1, chk_c2, chk_c3, chk_c4, chk_c5 = st.columns([0.6, 0.8, 0.8, 0.8, 0.8])
with chk_c1:
    st.markdown("**발주주체**")
with chk_c2:
    chk_발주팀 = st.checkbox("발주팀", value=True)
with chk_c3:
    chk_MD = st.checkbox("MD", value=True)
with chk_c4:
    chk_재발주불가 = st.checkbox("재발주불가", value=True)
with chk_c5:
    chk_재발주보류 = st.checkbox("재발주보류", value=True)

# 정렬조건 + 조회 버튼
sort_c1, sort_c2, btn_c = st.columns([1, 1, 1])
with sort_c1:
    정렬조건 = st.selectbox("정렬조건", ["품번별", "품명별", "판매가별"])
with btn_c:
    search_btn = st.button("🔍 조회", use_container_width=True)

st.markdown("---")

# ─── 필터 적용 ──────────────────────────────────────────────────
df = df_raw.copy()

# 담당자
if sel_담당 != "- 전체 -" and col_담당:
    df = df[df[col_담당] == sel_담당]

# 상태
if sel_상태 != "전체" and col_상태:
    df = df[df[col_상태] == sel_상태]
if not 단종포함 and col_상태:
    df = df[df[col_상태] != "단종대기"]

# 관계사팀
if sel_관계사팀 != "- 전체 -" and col_관계사팀:
    df = df[df[col_관계사팀] == sel_관계사팀]

# 등급
if sel_등급 != "- 전체 -" and col_등급:
    df = df[df[col_등급] == sel_등급]

# 업체
if sel_업체 != "전체" and col_업체명:
    df = df[df[col_업체명] == sel_업체]

# 대분류
if sel_대분류 != "전체" and col_대분류:
    df = df[df[col_대분류] == sel_대분류]
if sel_중분류 != "전체" and col_중분류:
    df = df[df[col_중분류] == sel_중분류]
if sel_소분류 != "전체" and col_소분류:
    df = df[df[col_소분류] == sel_소분류]

# 품번 검색
if 품번검색 and col_품번:
    df = df[df[col_품번].astype(str).str.contains(품번검색, na=False)]

# 발주주체 필터
if col_발주주체:
    allowed = []
    if chk_발주팀:
        allowed.append("발주팀")
    if chk_MD:
        allowed.append("MD")
    if chk_재발주불가:
        allowed.append("재발주불가")
    if chk_재발주보류:
        allowed.append("재발주보류")
    if allowed:
        df = df[df[col_발주주체].isin(allowed)]
    else:
        df = df.iloc[0:0]

# 정렬
if 정렬조건 == "품번별" and col_품번:
    df = df.sort_values(col_품번)
elif 정렬조건 == "품명별" and col_품명:
    df = df.sort_values(col_품명)
elif 정렬조건 == "판매가별" and col_판매가:
    df["_판매가_sort"] = df[col_판매가].apply(lambda x: safe_int(x))
    df = df.sort_values("_판매가_sort", ascending=False)
    df = df.drop(columns=["_판매가_sort"])

df = df.reset_index(drop=True)

# ─── 월 범위 선택 ────────────────────────────────────────────────
with st.expander("📅 조회 월 범위 선택", expanded=False):
    mc1, mc2 = st.columns(2)
    with mc1:
        start_month = st.selectbox("시작 월", ALL_MONTHS, index=max(0, len(ALL_MONTHS) - 6))
    with mc2:
        end_month = st.selectbox("종료 월", ALL_MONTHS, index=len(ALL_MONTHS) - 1)

si = ALL_MONTHS.index(start_month) if start_month in ALL_MONTHS else 0
ei = ALL_MONTHS.index(end_month) if end_month in ALL_MONTHS else len(ALL_MONTHS) - 1
if si > ei:
    si, ei = ei, si
sel_months = ALL_MONTHS[si : ei + 1]

# ─── 결과 카운트 ─────────────────────────────────────────────────
st.markdown(f"**조회 결과: 총 {len(df)}개 상품**")

if df.empty:
    st.info("조회 결과가 없습니다.")
    st.stop()

# ─── 테이블 HTML 생성 (샘플 사진 스타일) ─────────────────────────

def build_table_html(df, months):
    """샘플 사진과 동일한 테이블 레이아웃 생성"""
    num_months = len(months)

    # 헤더 행
    header1 = """
    <tr>
      <th rowspan="2" style="min-width:35px">순번</th>
      <th rowspan="2" style="min-width:55px">사진</th>
      <th rowspan="2" style="min-width:55px">발주구분</th>
      <th rowspan="2" style="min-width:75px">품번</th>
      <th rowspan="2" style="min-width:160px">품명</th>
      <th colspan="2" style="min-width:80px">?입원가</th>
      <th rowspan="2" style="min-width:50px">기본정보<br>가용재고</th>
      <th rowspan="2" style="min-width:45px">가용<br>일수</th>
      <th rowspan="2" style="min-width:45px">일평균<br>출고량</th>
      <th rowspan="2" style="min-width:45px">발주<br>미입고</th>
      <th rowspan="2" style="min-width:140px">상태정보</th>
      <th rowspan="2" style="min-width:55px">구분</th>
      <th rowspan="2" style="min-width:50px">합계</th>
    """
    for m in months:
        header1 += f'<th rowspan="2" style="min-width:42px">{m}</th>'
    header1 += "</tr>"

    header2 = """
    <tr>
      <th>판매가</th>
      <th>통화 / 금액</th>
    </tr>
    """

    # 데이터 행
    body_rows = ""
    for idx, (_, row) in enumerate(df.iterrows()):
        품명 = row[col_품명] if col_품명 else ""
        품번 = row[col_품번] if col_품번 else ""
        상태 = row[col_상태] if col_상태 else ""
        발주주체 = row[col_발주주체] if col_발주주체 else ""
        발주구분 = row[col_발주구분] if col_발주구분 else ""
        판매가 = row[col_판매가] if col_판매가 else ""
        구입가 = row[col_구입가] if col_구입가 else ""
        미입고_val = row[col_미입고] if col_미입고 else ""
        입고예정_val = row[col_입고예정] if col_입고예정 else ""
        정상재고_val = row[col_정상재고] if col_정상재고 else "0"
        일출고량_val = row[col_일출고량] if col_일출고량 else "0"
        sn_통화 = row[col_SN통화] if col_SN통화 else ""
        sn_금액 = row[col_SN금액] if col_SN금액 else ""
        사진주소 = row[col_사진주소] if col_사진주소 else ""

        # 이미지 HTML
        if 사진주소 and str(사진주소).strip().startswith("http"):
            img_html = f'<img src="{사진주소}" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'inline-flex\'"/><span class="img-placeholder" style="display:none">📦</span>'
        else:
            img_html = '<span class="img-placeholder">📦</span>'

        # 상태 배지
        badge_cls = ""
        if 상태 in ("신상품", "단종대기", "정상"):
            badge_cls = 상태
        상태_html = f'<span class="st-badge {badge_cls}">{상태}</span>' if 상태 else ""

        # 상태정보 텍스트
        미입고_int = safe_int(미입고_val)
        상태정보 = str(입고예정_val) if 입고예정_val else ""

        num_row_types = len(ROW_TYPES)
        seq_num = idx + 1

        for ri, rt in enumerate(ROW_TYPES):
            is_first = ri == 0
            is_pos = rt == "POS판매"
            tr_class_parts = []
            if is_first:
                tr_class_parts.append("prod-first")
            if is_pos:
                tr_class_parts.append("row-pos")
            tr_class = f' class="{" ".join(tr_class_parts)}"' if tr_class_parts else ""

            cells = ""

            if is_first:
                rs = num_row_types
                cells += f'<td class="center" rowspan="{rs}">{seq_num}</td>'
                cells += f'<td class="img-cell" rowspan="{rs}">{img_html}</td>'
                cells += f'<td class="center" rowspan="{rs}">{상태_html}<br>{발주구분}</td>'
                cells += f'<td class="center" rowspan="{rs}" style="font-family:monospace;font-size:10px">{품번}</td>'
                cells += f'<td class="left" rowspan="{rs}" style="font-size:10px">{품명}</td>'
                cells += f'<td class="num" rowspan="{rs}">{fmt_num(safe_int(판매가))}</td>'
                cells += f'<td class="center" rowspan="{rs}" style="font-size:10px">{sn_통화}<br>{fmt_num(safe_int(sn_금액))}</td>'
                cells += f'<td class="num" rowspan="{rs}">{fmt_num(safe_int(정상재고_val))}</td>'
                cells += f'<td class="num" rowspan="{rs}"></td>'
                cells += f'<td class="num" rowspan="{rs}">{fmt_num(safe_int(일출고량_val))}</td>'
                cells += f'<td class="num" rowspan="{rs}">{fmt_num(미입고_int)}</td>'
                cells += f'<td class="left" rowspan="{rs}" style="font-size:10px">{상태정보}</td>'

            # 구분 라벨
            type_cls = "type-label"
            cells += f'<td class="{type_cls}">{rt}</td>'

            # 합계
            total = sum(get_monthly_val(row, rt, m) for m in months)
            total_cls = "num zero-val" if total == 0 else "num"
            cells += f'<td class="{total_cls}">{fmt_num(total)}</td>'

            # 월별 값
            for m in months:
                v = get_monthly_val(row, rt, m)
                val_cls = "num zero-val" if v == 0 else "num"
                cells += f'<td class="{val_cls}">{fmt_num(v)}</td>'

            body_rows += f"<tr{tr_class}>{cells}</tr>\n"

        # 발주주체 행 (상품 하단)
        body_rows += f"""
        <tr>
          <td colspan="5" class="owner-cell">{발주주체}</td>
          <td class="num">{fmt_num(safe_int(구입가))}</td>
          <td></td><td></td><td></td><td></td>
          <td class="num">{fmt_num(미입고_int)}</td>
          <td></td><td></td><td></td>
          {"".join('<td></td>' for _ in months)}
        </tr>
        """

    html = f"""
    <div class="tbl-wrap">
      <table class="main-tbl">
        <thead>{header1}{header2}</thead>
        <tbody>{body_rows}</tbody>
      </table>
    </div>
    """
    return html


# ─── 테이블 렌더링 ───────────────────────────────────────────────
table_html = build_table_html(df, sel_months)
st.markdown(table_html, unsafe_allow_html=True)

# 하단 여백
st.markdown("<br><br>", unsafe_allow_html=True)
