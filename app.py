import streamlit as st
import pandas as pd
import gspread
from io import StringIO
from google.oauth2.service_account import Credentials

# ─── 페이지 설정 ───────────────────────────────────────────────
st.set_page_config(
    page_title="발주관리표2",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
  html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; font-size: 12px; }
  .stApp { background: #f5f5f5; }

  .page-header {
    display: flex; align-items: center; gap: 8px;
    padding: 8px 16px; margin-bottom: 12px;
  }
  .page-header .dot { color: #e53e3e; font-size: 18px; }
  .page-header h1 { font-size: 1.1rem; font-weight: 700; margin: 0; color: #1a1a1a; }

  /* 필터 영역 */
  .filter-area {
    background: white; border: 1px solid #ccc;
    padding: 12px 16px; margin-bottom: 10px;
    border-radius: 4px;
  }

  /* 조회 버튼 */
  div.stButton > button {
    background: #1a3a5c; color: white; border: none;
    border-radius: 4px; padding: 6px 24px;
    font-weight: 600; font-size: 13px; cursor: pointer;
  }
  div.stButton > button:hover { background: #2d6a9f; }

  /* 결과 테이블 */
  .tbl-wrap { overflow-x: auto; margin-top: 6px; }
  table.main-tbl {
    border-collapse: collapse; width: 100%;
    font-size: 11px; border: 1px solid #999;
  }
  table.main-tbl th {
    background: #dce6f1; color: #1a1a1a; font-weight: 600;
    padding: 5px 6px; border: 1px solid #bbb;
    text-align: center; white-space: nowrap;
    position: sticky; top: 0; z-index: 2;
  }
  table.main-tbl td {
    padding: 3px 5px; border: 1px solid #ccc;
    white-space: nowrap; font-size: 11px; color: #333;
  }
  table.main-tbl td.num { text-align: right; }
  table.main-tbl td.center { text-align: center; }
  table.main-tbl td.left { text-align: left; }

  /* 상품 첫 행 구분선 */
  table.main-tbl tr.prod-first td { border-top: 2px solid #666; }

  /* POS판매 행 강조 */
  table.main-tbl tr.row-pos td { background: #ffe0e0; }
  table.main-tbl tr.row-pos td.type-label {
    background: #ffcccc; color: #c00; font-weight: 700;
  }

  /* 구분 라벨 셀 */
  table.main-tbl td.type-label {
    text-align: center; font-weight: 500;
    background: #f8f8f8; min-width: 55px;
  }

  /* 0값 */
  table.main-tbl td.zero-val { color: #ccc; }

  /* 발주주체 행 */
  table.main-tbl tr.owner-row td {
    background: #f0f4f8; font-size: 10px;
    color: #555; font-weight: 500;
    border-top: 1px dashed #bbb;
  }

  /* 상품 사진 */
  table.main-tbl td.img-cell {
    text-align: center; vertical-align: middle;
    padding: 3px; background: #fff;
  }
  table.main-tbl td.img-cell img {
    width: 54px; height: 54px; object-fit: contain;
    border: 1px solid #e0e0e0; border-radius: 3px;
    background: #fff; display: block; margin: auto;
  }
  table.main-tbl th.img-th { min-width: 62px; }

  /* 상태 배지 */
  .st-badge {
    display: inline-block; padding: 1px 5px;
    border-radius: 2px; font-size: 10px; font-weight: 600;
  }
  .st-badge.신상품 { background: #d4edda; color: #155724; }
  .st-badge.단종대기 { background: #f8d7da; color: #721c24; }
  .st-badge.정상 { background: #e2e3e5; color: #383d41; }
  .st-badge.기타 { background: #fff3cd; color: #856404; }

  .stSelectbox > div > div { font-size: 12px !important; }
  div[data-testid="stStatusWidget"] { display: none; }

  @media (max-width: 1024px) {
    table.main-tbl th, table.main-tbl td { padding: 2px 3px; font-size: 10px; }
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
    """
    구글 시트 구조:
      행0 (row1): 카테고리 — 구분, S/N단가, 발주, 입고, 출고, POS판매, 물류재고, 매장재고, 보유매장, 미입고
      행1 (row2): 세부 컬럼명 — 발주주체, 발주구분, 품번, 품명, ... 24/11, 24/12, ...
      행2~  : 실제 데이터

    월별 컬럼은 '카테고리_월' 형태로 생성 (예: 발주_24/11, POS판매_25/03)
    기본 정보 컬럼은 세부 컬럼명 그대로 사용
    중복 컬럼명은 _2, _3 suffix로 처리
    """
    try:
        client = get_gsheet_client()
        sh = client.open_by_key(SHEET_ID)
        ws = sh.get_worksheet(0)
        data = ws.get_all_values()
        if not data or len(data) < 3:
            return pd.DataFrame()

        row0 = data[0]  # 카테고리 행
        row1 = data[1]  # 세부 컬럼명 행

        columns = []
        last_cat = ""
        for i in range(len(row1)):
            cat = row0[i].strip() if i < len(row0) else ""
            sub = row1[i].strip() if row1[i].strip() else ""
            if cat:
                last_cat = cat

            # 월 패턴 감지 (예: 24/11, 25/03)
            is_month = (len(sub) == 5 and sub[2] == "/" and
                        sub[:2].isdigit() and sub[3:].isdigit())

            if is_month and last_cat and last_cat not in ("구분", ""):
                col_name = f"{last_cat}_{sub}"
            else:
                col_name = sub if sub else f"_col_{i}"

            # 중복 방지
            base = col_name
            n = 2
            while col_name in columns:
                col_name = f"{base}_{n}"
                n += 1
            columns.append(col_name)

        df = pd.DataFrame(data[2:], columns=columns)
        # 빈 행 제거 (품번이 없는 행)
        if "품번" in df.columns:
            df = df[df["품번"].str.strip() != ""]
        df = df.reset_index(drop=True)
        return df

    except Exception as e:
        st.error(f"Google Sheets 연결 오류: {e}")
        return pd.DataFrame()


# ─── 유틸 함수 ───────────────────────────────────────────────────
ROW_TYPES = ["발주", "입고", "출고", "POS판매", "물류재고", "매장재고", "보유매장", "미입고"]


def detect_months(df):
    """데이터에 실제 존재하는 월 컬럼을 자동 감지하여 정렬된 리스트로 반환"""
    found = set()
    for c in df.columns:
        for rt in ROW_TYPES:
            prefix = f"{rt}_"
            if c.startswith(prefix):
                m = c[len(prefix):]
                if len(m) == 5 and m[2] == "/" and m[:2].isdigit() and m[3:].isdigit():
                    found.add(m)
    return sorted(found)


def get_col(df, *names):
    """여러 후보 이름 중 첫 번째로 매칭되는 컬럼 반환 (월별 컬럼 제외)"""
    for name in names:
        # 정확히 일치하는 컬럼 우선
        if name in df.columns:
            return name
    for name in names:
        # 부분 매칭 (월별 컬럼 제외)
        for c in df.columns:
            if "_" in c and "/" in c:
                continue  # 월별 컬럼 제외
            if c == name:
                return c
    for name in names:
        # 포함 관계 매칭 (월별 컬럼 제외) — 짧은 이름이 긴 컬럼명에 포함되는 경우만
        for c in df.columns:
            if "_" in c and "/" in c:
                continue
            # 컬럼명이 검색어를 포함하는 경우 (예: "정상 재고" contains "재고")
            if name in c:
                return c
    return None


def safe_int(v):
    try:
        if v in ("", None):
            return 0
        return int(float(str(v).replace(",", "")))
    except:
        return 0


def get_monthly_val(row, row_type, month):
    col = f"{row_type}_{month}"
    if col in row.index:
        return safe_int(row[col])
    return 0


def fmt_num(v):
    if v == 0:
        return "0"
    return f"{v:,}"


def unique_vals(df, col):
    """컬럼의 고유값 정렬 리스트 반환"""
    if col is None:
        return []
    return sorted([v for v in df[col].dropna().unique() if str(v).strip()])


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
col_담당     = get_col(df_raw, "담당")
col_대분류   = get_col(df_raw, "대분류")
col_중분류   = get_col(df_raw, "중분류")
col_소분류   = get_col(df_raw, "소분류")
col_품명     = get_col(df_raw, "품명")
col_품번     = get_col(df_raw, "품번")
col_상태     = get_col(df_raw, "상태")
col_발주주체 = get_col(df_raw, "발주주체")
col_발주구분 = get_col(df_raw, "발주구분")
col_판매가   = get_col(df_raw, "판매가")
col_구입가   = get_col(df_raw, "구입가")
col_사진주소 = get_col(df_raw, "사진주소")
col_업체명   = get_col(df_raw, "업체명")
col_관계사팀 = get_col(df_raw, "관계사팀")
col_정상재고 = get_col(df_raw, "정상재고", "정상 재고")
col_일출고량 = get_col(df_raw, "일출고량", "일출고")
col_미입고   = get_col(df_raw, "미입고")
col_입고예정 = get_col(df_raw, "입고예정")
col_SN통화   = get_col(df_raw, "통화")
col_SN금액   = get_col(df_raw, "금액")


# ─── 필터 UI ────────────────────────────────────────────────────
# 1행: 대분류, 중분류, 소분류
fc1, fc2, fc3 = st.columns(3)

with fc1:
    opts_대 = ["전체"] + unique_vals(df_raw, col_대분류)
    sel_대분류 = st.selectbox("대분류", opts_대)

with fc2:
    df_f = df_raw if sel_대분류 == "전체" else df_raw[df_raw[col_대분류] == sel_대분류]
    opts_중 = ["전체"] + unique_vals(df_f, col_중분류)
    sel_중분류 = st.selectbox("중분류", opts_중)

with fc3:
    df_f2 = df_raw
    if sel_대분류 != "전체" and col_대분류:
        df_f2 = df_f2[df_f2[col_대분류] == sel_대분류]
    if sel_중분류 != "전체" and col_중분류:
        df_f2 = df_f2[df_f2[col_중분류] == sel_중분류]
    opts_소 = ["전체"] + unique_vals(df_f2, col_소분류)
    sel_소분류 = st.selectbox("소분류", opts_소)

# 2행: 담당자, 관계사팀, 업체
fc4, fc5, fc6 = st.columns(3)

with fc4:
    opts_담당 = ["전체"] + unique_vals(df_raw, col_담당)
    sel_담당 = st.selectbox("담당자", opts_담당)

with fc5:
    opts_관계사 = ["전체"] + unique_vals(df_raw, col_관계사팀)
    sel_관계사팀 = st.selectbox("관계사팀", opts_관계사)

with fc6:
    opts_업체 = ["전체"] + unique_vals(df_raw, col_업체명)
    sel_업체 = st.selectbox("업체", opts_업체)

# 조회 버튼 — 누를 때만 필터 결과를 session_state에 저장
_, btn_col, _ = st.columns([3, 1, 3])
with btn_col:
    do_search = st.button("🔍 조회", use_container_width=True)

st.markdown("---")

if do_search:
    df = df_raw
    if sel_대분류 != "전체" and col_대분류:
        df = df[df[col_대분류] == sel_대분류]
    if sel_중분류 != "전체" and col_중분류:
        df = df[df[col_중분류] == sel_중분류]
    if sel_소분류 != "전체" and col_소분류:
        df = df[df[col_소분류] == sel_소분류]
    if sel_담당 != "전체" and col_담당:
        df = df[df[col_담당] == sel_담당]
    if sel_관계사팀 != "전체" and col_관계사팀:
        df = df[df[col_관계사팀] == sel_관계사팀]
    if sel_업체 != "전체" and col_업체명:
        df = df[df[col_업체명] == sel_업체]
    df = df.reset_index(drop=True)
    st.session_state["filtered_df"] = df

# 이전 조회 결과가 있으면 표시, 없으면 안내
if "filtered_df" not in st.session_state:
    st.info("필터를 선택한 후 🔍 조회 버튼을 눌러주세요.")
    st.stop()

df = st.session_state["filtered_df"]
sel_months = detect_months(df_raw)

st.markdown(f"**조회 결과: 총 {len(df)}개 상품**")

if df.empty:
    st.info("조회 결과가 없습니다.")
    st.stop()


# ─── 테이블 HTML 생성 ────────────────────────────────────────────
@st.cache_data(ttl=300)
def build_table(_df_json, months_tuple, col_map):
    """
    캐싱을 위해 df를 JSON 문자열로, months를 tuple로 받음.
    col_map은 컬럼명 매핑 dict.
    """
    df = pd.read_json(StringIO(_df_json), dtype=str)
    months = list(months_tuple)

    month_ths = []
    for m in months:
        month_ths.append(f'<th rowspan="2" style="min-width:44px;text-align:center">{m}</th>')
    month_ths_row1 = "".join(month_ths)

    header = f"""
    <thead>
      <tr>
        <th rowspan="2" style="min-width:30px">순번</th>
        <th rowspan="2" class="img-th">사진</th>
        <th rowspan="2" style="min-width:65px">상태<br>발주구분</th>
        <th rowspan="2" style="min-width:80px">품번</th>
        <th rowspan="2" style="min-width:160px">품명</th>
        <th rowspan="2" style="min-width:52px">판매가</th>
        <th colspan="2" style="min-width:90px;text-align:center">S/N단가</th>
        <th rowspan="2" style="min-width:48px">가용<br>재고</th>
        <th rowspan="2" style="min-width:44px">일평균<br>출고</th>
        <th rowspan="2" style="min-width:44px">발주<br>미입고</th>
        <th rowspan="2" style="min-width:140px">상태정보</th>
        <th rowspan="2" style="min-width:52px">구분</th>
        {month_ths_row1}
      </tr>
      <tr>
        <th style="min-width:40px">통화</th>
        <th style="min-width:50px">금액</th>
      </tr>
    </thead>
    """

    # 컬럼 매핑 로컬 변수
    c_품명 = col_map.get("품명")
    c_품번 = col_map.get("품번")
    c_상태 = col_map.get("상태")
    c_발주주체 = col_map.get("발주주체")
    c_발주구분 = col_map.get("발주구분")
    c_판매가 = col_map.get("판매가")
    c_구입가 = col_map.get("구입가")
    c_미입고 = col_map.get("미입고")
    c_입고예정 = col_map.get("입고예정")
    c_정상재고 = col_map.get("정상재고")
    c_일출고량 = col_map.get("일출고량")
    c_SN통화 = col_map.get("SN통화")
    c_SN금액 = col_map.get("SN금액")
    c_사진주소 = col_map.get("사진주소")

    badge_map = {"신상품": "신상품", "단종대기": "단종대기", "정상": "정상"}
    rs = len(ROW_TYPES)
    row_parts = []

    # 월별 컬럼 존재 여부를 미리 계산
    month_cols = {}
    for rt in ROW_TYPES:
        month_cols[rt] = {m: f"{rt}_{m}" for m in months}

    df_cols_set = set(df.columns)

    for idx, (_, row) in enumerate(df.iterrows()):
        품명     = str(row[c_품명])     if c_품명     else ""
        품번     = str(row[c_품번])     if c_품번     else ""
        상태     = str(row[c_상태])     if c_상태     else ""
        발주주체 = str(row[c_발주주체]) if c_발주주체 else ""
        발주구분 = str(row[c_발주구분]) if c_발주구분 else ""
        판매가   = str(row[c_판매가])   if c_판매가   else ""
        구입가   = str(row[c_구입가])   if c_구입가   else ""
        미입고_v = safe_int(row[c_미입고])   if c_미입고   else 0
        입고예정 = str(row[c_입고예정]) if c_입고예정 else ""
        정상재고 = safe_int(row[c_정상재고]) if c_정상재고 else 0
        일출고   = safe_int(row[c_일출고량]) if c_일출고량 else 0
        sn_통화  = str(row[c_SN통화])   if c_SN통화   else ""
        sn_금액  = safe_int(row[c_SN금액]) if c_SN금액 else 0
        사진주소 = str(row[c_사진주소]).strip() if c_사진주소 else ""

        badge_cls = badge_map.get(상태, "기타")
        badge_html = f'<span class="st-badge {badge_cls}">{상태}</span>'

        if 사진주소.startswith("http"):
            img_html = (
                f'<img src="{사진주소}" '
                f'onerror="this.style.display=\'none\'" '
                f'alt="{품번}" />'
            )
        else:
            img_html = '<span style="color:#ccc;font-size:18px">📷</span>'

        seq = idx + 1

        # 첫 행 공통 셀 (한 번만 생성)
        first_cells = (
            f'<td class="center" rowspan="{rs}">{seq}</td>'
            f'<td class="img-cell" rowspan="{rs}">{img_html}</td>'
            f'<td class="center" rowspan="{rs}">{badge_html}<br><small style="color:#666">{발주구분}</small></td>'
            f'<td class="center" rowspan="{rs}" style="font-family:monospace;font-size:10px">{품번}</td>'
            f'<td class="left"   rowspan="{rs}" style="font-size:10px">{품명}</td>'
            f'<td class="num"    rowspan="{rs}">{fmt_num(safe_int(판매가))}</td>'
            f'<td class="center" rowspan="{rs}" style="font-size:10px">{sn_통화}</td>'
            f'<td class="num"    rowspan="{rs}">{fmt_num(sn_금액)}</td>'
            f'<td class="num"    rowspan="{rs}">{fmt_num(정상재고)}</td>'
            f'<td class="num"    rowspan="{rs}">{fmt_num(일출고)}</td>'
            f'<td class="num"    rowspan="{rs}">{fmt_num(미입고_v)}</td>'
            f'<td class="left"   rowspan="{rs}" style="font-size:10px">{입고예정}</td>'
        )

        for ri, rt in enumerate(ROW_TYPES):
            is_first = ri == 0
            is_pos   = rt == "POS판매"
            tr_cls = ""
            if is_first and is_pos:
                tr_cls = ' class="prod-first row-pos"'
            elif is_first:
                tr_cls = ' class="prod-first"'
            elif is_pos:
                tr_cls = ' class="row-pos"'

            parts = []
            if is_first:
                parts.append(first_cells)

            parts.append(f'<td class="type-label">{rt}</td>')

            mc = month_cols[rt]
            for m in months:
                col_name = mc[m]
                if col_name in df_cols_set:
                    v = safe_int(row[col_name])
                else:
                    v = 0
                if v == 0:
                    parts.append('<td class="num zero-val">0</td>')
                else:
                    parts.append(f'<td class="num">{v:,}</td>')

            row_parts.append(f"<tr{tr_cls}>{''.join(parts)}</tr>")

        # 발주주체 행
        empty_month_tds = '<td></td>' * len(months)
        row_parts.append(
            f'<tr class="owner-row">'
            f'<td></td><td></td>'
            f'<td colspan="2" style="padding-left:6px">{발주주체}</td>'
            f'<td class="left" style="font-size:10px">{품명[:15]}</td>'
            f'<td class="num">{fmt_num(safe_int(구입가))}</td>'
            f'<td></td><td></td><td></td><td></td>'
            f'<td class="num">{fmt_num(미입고_v)}</td>'
            f'<td></td><td></td>'
            f'{empty_month_tds}'
            f'</tr>'
        )

    return f"""
    <div class="tbl-wrap">
      <table class="main-tbl">
        {header}
        <tbody>{"".join(row_parts)}</tbody>
      </table>
    </div>
    """


# ─── 렌더링 ─────────────────────────────────────────────────────
col_map = {
    "품명": col_품명, "품번": col_품번, "상태": col_상태,
    "발주주체": col_발주주체, "발주구분": col_발주구분,
    "판매가": col_판매가, "구입가": col_구입가,
    "미입고": col_미입고, "입고예정": col_입고예정,
    "정상재고": col_정상재고, "일출고량": col_일출고량,
    "SN통화": col_SN통화, "SN금액": col_SN금액,
    "사진주소": col_사진주소,
}
table_html = build_table(df.to_json(), tuple(sel_months), col_map)
st.markdown(table_html, unsafe_allow_html=True)
