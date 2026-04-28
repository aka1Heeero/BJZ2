import streamlit as st
import pandas as pd
import gspread
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
def gen_month_labels():
    months = []
    for y in range(24, 27):
        for m in range(1, 13):
            months.append(f"{y:02d}/{m:02d}")
            if y == 26 and m == 4:
                return months
    return months


ALL_MONTHS = gen_month_labels()
ROW_TYPES = ["발주", "입고", "출고", "POS판매", "물류재고", "매장재고", "보유매장", "미입고"]


def get_col(df, *names):
    """여러 후보 이름 중 첫 번째로 매칭되는 컬럼 반환 (월별 컬럼 제외)"""
    for name in names:
        if name in df.columns:
            return name
    for name in names:
        for c in df.columns:
            if "_" in c and "/" in c:
                continue  # 월별 컬럼 제외
            if name == c or name in c or c in name:
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
    df_f2 = df_raw.copy()
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

# 조회 버튼
_, btn_col, _ = st.columns([3, 1, 3])
with btn_col:
    st.button("🔍 조회", use_container_width=True)

st.markdown("---")


# ─── 필터 적용 ──────────────────────────────────────────────────
df = df_raw.copy()

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
sel_months = ALL_MONTHS[si: ei + 1]

st.markdown(f"**조회 결과: 총 {len(df)}개 상품**")

if df.empty:
    st.info("조회 결과가 없습니다.")
    st.stop()


# ─── 사진 팝업 (session_state) ───────────────────────────────────
if "photo_url" not in st.session_state:
    st.session_state.photo_url = None
if "photo_name" not in st.session_state:
    st.session_state.photo_name = ""

if st.session_state.photo_url:
    with st.container():
        col_img, col_close = st.columns([4, 1])
        with col_img:
            st.markdown(f"**📷 {st.session_state.photo_name}**")
            st.image(st.session_state.photo_url, width=280)
        with col_close:
            if st.button("✕ 닫기"):
                st.session_state.photo_url = None
                st.session_state.photo_name = ""
                st.rerun()
    st.markdown("---")


# ─── 테이블 HTML 생성 ────────────────────────────────────────────
def build_table(df, months):
    # 헤더
    month_ths = "".join(
        f'<th style="min-width:42px">{m}</th>' for m in months
    )
    header = f"""
    <thead>
      <tr>
        <th rowspan="2" style="min-width:32px">순번</th>
        <th rowspan="2" style="min-width:60px">발주구분<br>상태</th>
        <th rowspan="2" style="min-width:80px">품번</th>
        <th rowspan="2" style="min-width:170px">품명</th>
        <th rowspan="2" style="min-width:55px">판매가</th>
        <th colspan="2" style="min-width:90px">S/N단가</th>
        <th rowspan="2" style="min-width:50px">가용<br>재고</th>
        <th rowspan="2" style="min-width:45px">일평균<br>출고</th>
        <th rowspan="2" style="min-width:45px">발주<br>미입고</th>
        <th rowspan="2" style="min-width:150px">상태정보</th>
        <th rowspan="2" style="min-width:55px">구분</th>
        <th rowspan="2" style="min-width:48px">합계</th>
        {month_ths.replace('rowspan="2"', '')}
      </tr>
      <tr>
        <th>통화</th>
        <th>금액</th>
      </tr>
    </thead>
    """

    rows = ""
    for idx, (_, row) in enumerate(df.iterrows()):
        품명     = str(row[col_품명]     if col_품명     else "")
        품번     = str(row[col_품번]     if col_품번     else "")
        상태     = str(row[col_상태]     if col_상태     else "")
        발주주체 = str(row[col_발주주체] if col_발주주체 else "")
        발주구분 = str(row[col_발주구분] if col_발주구분 else "")
        판매가   = str(row[col_판매가]   if col_판매가   else "")
        구입가   = str(row[col_구입가]   if col_구입가   else "")
        미입고   = safe_int(row[col_미입고]   if col_미입고   else 0)
        입고예정 = str(row[col_입고예정] if col_입고예정 else "")
        정상재고 = safe_int(row[col_정상재고] if col_정상재고 else 0)
        일출고   = safe_int(row[col_일출고량] if col_일출고량 else 0)
        sn_통화  = str(row[col_SN통화]   if col_SN통화   else "")
        sn_금액  = safe_int(row[col_SN금액] if col_SN금액 else 0)
        사진주소 = str(row[col_사진주소] if col_사진주소 else "")

        # 상태 배지
        badge_map = {"신상품": "신상품", "단종대기": "단종대기", "정상": "정상"}
        badge_cls = badge_map.get(상태, "기타")
        badge_html = f'<span class="st-badge {badge_cls}">{상태}</span>'

        # 사진 버튼 (사진주소가 있을 때만)
        has_photo = 사진주소.startswith("http")
        photo_btn = ""
        if has_photo:
            # URL과 품명을 안전하게 인코딩
            safe_url  = 사진주소.replace('"', '%22')
            safe_name = 품명.replace('"', '').replace("'", "")[:30]
            photo_btn = (
                f' <button onclick="window.parent.postMessage({{type:\'streamlit:setComponentValue\','
                f'value:{{url:\'{safe_url}\',name:\'{safe_name}\'}}}},\'*\')" '
                f'style="font-size:10px;padding:1px 5px;cursor:pointer;'
                f'border:1px solid #aaa;border-radius:3px;background:#f0f0f0">📷</button>'
            )

        rs = len(ROW_TYPES)
        seq = idx + 1

        for ri, rt in enumerate(ROW_TYPES):
            is_first = ri == 0
            is_pos   = rt == "POS판매"
            tr_cls   = []
            if is_first:
                tr_cls.append("prod-first")
            if is_pos:
                tr_cls.append("row-pos")
            tr_attr = f' class="{" ".join(tr_cls)}"' if tr_cls else ""

            cells = ""
            if is_first:
                cells += f'<td class="center" rowspan="{rs}">{seq}</td>'
                cells += f'<td class="center" rowspan="{rs}">{badge_html}<br><small>{발주구분}</small></td>'
                cells += f'<td class="center" rowspan="{rs}" style="font-family:monospace;font-size:10px">{품번}{photo_btn}</td>'
                cells += f'<td class="left"   rowspan="{rs}" style="font-size:10px;max-width:170px;overflow:hidden;text-overflow:ellipsis">{품명}</td>'
                cells += f'<td class="num"    rowspan="{rs}">{fmt_num(safe_int(판매가))}</td>'
                cells += f'<td class="center" rowspan="{rs}" style="font-size:10px">{sn_통화}</td>'
                cells += f'<td class="num"    rowspan="{rs}">{fmt_num(sn_금액)}</td>'
                cells += f'<td class="num"    rowspan="{rs}">{fmt_num(정상재고)}</td>'
                cells += f'<td class="num"    rowspan="{rs}">{fmt_num(일출고)}</td>'
                cells += f'<td class="num"    rowspan="{rs}">{fmt_num(미입고)}</td>'
                cells += f'<td class="left"   rowspan="{rs}" style="font-size:10px">{입고예정}</td>'

            # 구분 라벨
            cells += f'<td class="type-label">{rt}</td>'

            # 합계
            total = sum(get_monthly_val(row, rt, m) for m in months)
            cells += f'<td class="num {"zero-val" if total == 0 else ""}">{fmt_num(total)}</td>'

            # 월별 값
            for m in months:
                v = get_monthly_val(row, rt, m)
                cells += f'<td class="num {"zero-val" if v == 0 else ""}">{fmt_num(v)}</td>'

            rows += f"<tr{tr_attr}>{cells}</tr>\n"

        # 발주주체 행
        empty_month_tds = "".join("<td></td>" for _ in months)
        rows += (
            f'<tr class="owner-row">'
            f'<td colspan="4" style="padding-left:8px">{발주주체}</td>'
            f'<td class="num">{fmt_num(safe_int(구입가))}</td>'
            f'<td></td><td></td><td></td><td></td>'
            f'<td class="num">{fmt_num(미입고)}</td>'
            f'<td></td><td></td><td></td>'
            f'{empty_month_tds}'
            f'</tr>\n'
        )

    return f"""
    <div class="tbl-wrap">
      <table class="main-tbl">
        {header}
        <tbody>{rows}</tbody>
      </table>
    </div>
    """


# ─── 렌더링 ─────────────────────────────────────────────────────
table_html = build_table(df, sel_months)
st.markdown(table_html, unsafe_allow_html=True)

# ─── 사진 클릭 처리 (품번 selectbox 방식) ────────────────────────
st.markdown("---")
st.markdown("**📷 상품 사진 확인** — 품번을 선택하면 사진이 표시됩니다")

photo_options = []
if col_품번 and col_사진주소:
    for _, row in df.iterrows():
        pn = str(row[col_품번]).strip()
        url = str(row[col_사진주소]).strip()
        nm = str(row[col_품명] if col_품명 else "").strip()
        if pn and url.startswith("http"):
            photo_options.append((f"{pn}  {nm[:20]}", url, nm))

if photo_options:
    labels = ["— 선택 —"] + [p[0] for p in photo_options]
    sel_photo = st.selectbox("품번 선택", labels, label_visibility="collapsed")
    if sel_photo != "— 선택 —":
        matched = [p for p in photo_options if p[0] == sel_photo]
        if matched:
            _, photo_url, photo_name = matched[0]
            col_p1, col_p2 = st.columns([1, 3])
            with col_p1:
                st.image(photo_url, caption=photo_name, width=250)
else:
    st.caption("사진 주소가 있는 상품이 없습니다.")

st.markdown("<br>", unsafe_allow_html=True)
