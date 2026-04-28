import streamlit as st
import pandas as pd

# ─── 페이지 설정 ───────────────────────────────────────────────
st.set_page_config(
    page_title="발주관리표2",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── 로그인 ────────────────────────────────────────────────────
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if st.session_state["authenticated"]:
        return True
    st.markdown("<h2 style='text-align:center;margin-top:80px'>🔒 발주관리표2</h2>",
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        pw = st.text_input("비밀번호를 입력하세요", type="password", key="pw_input")
        if st.button("로그인", use_container_width=True):
            if pw == st.secrets.get("app_password", ""):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")
    return False

if not check_password():
    st.stop()

# ─── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
  html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; font-size: 12px; }
  .stApp { background: #f5f5f5; }
  .page-header { display:flex; align-items:center; gap:8px; padding:8px 16px; margin-bottom:12px; }
  .page-header .dot { color:#e53e3e; font-size:18px; }
  .page-header h1 { font-size:1.1rem; font-weight:700; margin:0; color:#1a1a1a; }
  div.stButton > button { background:#1a3a5c; color:white; border:none; border-radius:4px; padding:6px 24px; font-weight:600; font-size:13px; }
  div.stButton > button:hover { background:#2d6a9f; }
  .tbl-wrap { overflow-x:auto; margin-top:6px; }
  table.main-tbl { border-collapse:collapse; width:100%; font-size:11px; border:1px solid #999; }
  table.main-tbl th { background:#dce6f1; color:#1a1a1a; font-weight:600; padding:5px 6px; border:1px solid #bbb; text-align:center; white-space:nowrap; position:sticky; top:0; z-index:2; }
  table.main-tbl td { padding:3px 5px; border:1px solid #ccc; white-space:nowrap; font-size:11px; color:#333; }
  table.main-tbl td.num { text-align:right; }
  table.main-tbl td.center { text-align:center; }
  table.main-tbl td.left { text-align:left; }
  table.main-tbl tr.prod-first td { border-top:2px solid #666; }
  table.main-tbl tr.row-pos td { background:#ffe0e0; }
  table.main-tbl tr.row-pos td.type-label { background:#ffcccc; color:#c00; font-weight:700; }
  table.main-tbl td.type-label { text-align:center; font-weight:500; background:#f8f8f8; min-width:55px; }
  table.main-tbl td.zero-val { color:#ccc; }
  table.main-tbl tr.owner-row td { background:#f0f4f8; font-size:10px; color:#555; font-weight:500; border-top:1px dashed #bbb; }
  table.main-tbl td.img-cell { text-align:center; vertical-align:middle; padding:3px; background:#fff; }
  table.main-tbl td.img-cell img { width:54px; height:54px; object-fit:contain; border:1px solid #e0e0e0; border-radius:3px; background:#fff; display:block; margin:auto; }
  table.main-tbl th.img-th { min-width:62px; }
  .st-badge { display:inline-block; padding:1px 5px; border-radius:2px; font-size:10px; font-weight:600; }
  .st-badge.신상품 { background:#d4edda; color:#155724; }
  .st-badge.단종대기 { background:#f8d7da; color:#721c24; }
  .st-badge.정상 { background:#e2e3e5; color:#383d41; }
  .st-badge.기타 { background:#fff3cd; color:#856404; }
  .stSelectbox > div > div { font-size:12px !important; }
  div[data-testid="stStatusWidget"] { display:none; }
  .photo-panel { background:white; border:1px solid #ddd; border-radius:6px; padding:12px; }
  @media (max-width:1024px) { table.main-tbl th, table.main-tbl td { padding:2px 3px; font-size:10px; } }
</style>
""", unsafe_allow_html=True)

# ─── 로컬 CSV 로드 ────────────────────────────────────────────────
DATA_FILE = "BJZ_utf8.csv"

@st.cache_data
def load_data():
    """로컬 CSV 파일에서 데이터 로드. 행0=카테고리, 행1=세부컬럼, 행2~=데이터"""
    try:
        raw = pd.read_csv(DATA_FILE, header=None, dtype=str, keep_default_na=False)
        if len(raw) < 3:
            return pd.DataFrame()

        row0 = raw.iloc[0].tolist()
        row1 = raw.iloc[1].tolist()
        columns = []
        last_cat = ""
        for i in range(len(row1)):
            cat = str(row0[i]).strip() if i < len(row0) else ""
            sub = str(row1[i]).strip()
            if cat:
                last_cat = cat
            is_month = (len(sub) == 5 and sub[2] == "/" and
                        sub[:2].isdigit() and sub[3:].isdigit())
            if is_month and last_cat and last_cat not in ("구분", ""):
                col_name = f"{last_cat}_{sub}"
            else:
                col_name = sub if sub else f"_col_{i}"
            base = col_name
            n = 2
            while col_name in columns:
                col_name = f"{base}_{n}"
                n += 1
            columns.append(col_name)

        df = pd.DataFrame(raw.iloc[2:].values, columns=columns)
        if "품번" in df.columns:
            df = df[df["품번"].str.strip() != ""]
        return df.reset_index(drop=True)
    except FileNotFoundError:
        return pd.DataFrame()
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return pd.DataFrame()


# ─── 유틸 함수 ───────────────────────────────────────────────────
ROW_TYPES = ["발주", "입고", "출고", "POS판매", "물류재고", "매장재고", "보유매장", "미입고"]

def detect_months(df):
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
    for name in names:
        if name in df.columns:
            return name
    for name in names:
        for c in df.columns:
            if "_" in c and "/" in c:
                continue
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

def fmt_num(v):
    if v == 0:
        return "0"
    return f"{v:,}"

def unique_vals(df, col):
    if col is None:
        return []
    return sorted([v for v in df[col].dropna().unique() if str(v).strip()])


# ─── 테이블 HTML 생성 (캐싱 없이 직접 DataFrame 사용) ─────────
def build_table(df, months, col_map):
    month_ths = "".join(
        f'<th rowspan="2" style="min-width:44px;text-align:center">{m}</th>'
        for m in months
    )
    header = f"""<thead><tr>
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
        {month_ths}
      </tr><tr>
        <th style="min-width:40px">통화</th>
        <th style="min-width:50px">금액</th>
      </tr></thead>"""

    c = col_map
    badge_map = {"신상품": "신상품", "단종대기": "단종대기", "정상": "정상"}
    rs = len(ROW_TYPES)
    parts = []
    df_cols = set(df.columns)

    # 월별 컬럼명 미리 계산
    mc = {}
    for rt in ROW_TYPES:
        mc[rt] = [f"{rt}_{m}" for m in months]

    for idx in range(len(df)):
        row = df.iloc[idx]
        품명 = str(row[c["품명"]]) if c["품명"] else ""
        품번 = str(row[c["품번"]]) if c["품번"] else ""
        상태 = str(row[c["상태"]]) if c["상태"] else ""
        발주주체 = str(row[c["발주주체"]]) if c["발주주체"] else ""
        발주구분 = str(row[c["발주구분"]]) if c["발주구분"] else ""
        판매가 = str(row[c["판매가"]]) if c["판매가"] else ""
        구입가 = str(row[c["구입가"]]) if c["구입가"] else ""
        미입고_v = safe_int(row[c["미입고"]]) if c["미입고"] else 0
        입고예정 = str(row[c["입고예정"]]) if c["입고예정"] else ""
        정상재고 = safe_int(row[c["정상재고"]]) if c["정상재고"] else 0
        일출고 = safe_int(row[c["일출고량"]]) if c["일출고량"] else 0
        sn_통화 = str(row[c["SN통화"]]) if c["SN통화"] else ""
        sn_금액 = safe_int(row[c["SN금액"]]) if c["SN금액"] else 0
        사진주소 = str(row[c["사진주소"]]).strip() if c["사진주소"] else ""

        badge_cls = badge_map.get(상태, "기타")
        badge_html = f'<span class="st-badge {badge_cls}">{상태}</span>'

        if 사진주소.startswith("http"):
            img_html = f'<img src="{사진주소}" onerror="this.style.display=\'none\'" alt="{품번}"/>'
        else:
            img_html = '<span style="color:#ccc;font-size:18px">📷</span>'

        seq = idx + 1
        first_cells = (
            f'<td class="center" rowspan="{rs}">{seq}</td>'
            f'<td class="img-cell" rowspan="{rs}">{img_html}</td>'
            f'<td class="center" rowspan="{rs}">{badge_html}<br><small style="color:#666">{발주구분}</small></td>'
            f'<td class="center" rowspan="{rs}" style="font-family:monospace;font-size:10px">{품번}</td>'
            f'<td class="left" rowspan="{rs}" style="font-size:10px">{품명}</td>'
            f'<td class="num" rowspan="{rs}">{fmt_num(safe_int(판매가))}</td>'
            f'<td class="center" rowspan="{rs}" style="font-size:10px">{sn_통화}</td>'
            f'<td class="num" rowspan="{rs}">{fmt_num(sn_금액)}</td>'
            f'<td class="num" rowspan="{rs}">{fmt_num(정상재고)}</td>'
            f'<td class="num" rowspan="{rs}">{fmt_num(일출고)}</td>'
            f'<td class="num" rowspan="{rs}">{fmt_num(미입고_v)}</td>'
            f'<td class="left" rowspan="{rs}" style="font-size:10px">{입고예정}</td>'
        )

        for ri, rt in enumerate(ROW_TYPES):
            is_first = ri == 0
            is_pos = rt == "POS판매"
            tr_cls = ""
            if is_first and is_pos:
                tr_cls = ' class="prod-first row-pos"'
            elif is_first:
                tr_cls = ' class="prod-first"'
            elif is_pos:
                tr_cls = ' class="row-pos"'

            cells = []
            if is_first:
                cells.append(first_cells)
            cells.append(f'<td class="type-label">{rt}</td>')

            for col_name in mc[rt]:
                if col_name in df_cols:
                    v = safe_int(row[col_name])
                else:
                    v = 0
                if v == 0:
                    cells.append('<td class="num zero-val">0</td>')
                else:
                    cells.append(f'<td class="num">{v:,}</td>')

            parts.append(f"<tr{tr_cls}>{''.join(cells)}</tr>")

        # 발주주체 행
        empty_tds = '<td></td>' * len(months)
        parts.append(
            f'<tr class="owner-row"><td></td><td></td>'
            f'<td colspan="2" style="padding-left:6px">{발주주체}</td>'
            f'<td class="left" style="font-size:10px">{품명[:15]}</td>'
            f'<td class="num">{fmt_num(safe_int(구입가))}</td>'
            f'<td></td><td></td><td></td><td></td>'
            f'<td class="num">{fmt_num(미입고_v)}</td>'
            f'<td></td><td></td>{empty_tds}</tr>'
        )

    return f'<div class="tbl-wrap"><table class="main-tbl">{header}<tbody>{"".join(parts)}</tbody></table></div>'


# ─── 헤더 ───────────────────────────────────────────────────────
st.markdown('<div class="page-header"><span class="dot">●</span><h1>발주관리표2</h1></div>',
            unsafe_allow_html=True)

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

col_map = {
    "품명": col_품명, "품번": col_품번, "상태": col_상태,
    "발주주체": col_발주주체, "발주구분": col_발주구분,
    "판매가": col_판매가, "구입가": col_구입가,
    "미입고": col_미입고, "입고예정": col_입고예정,
    "정상재고": col_정상재고, "일출고량": col_일출고량,
    "SN통화": col_SN통화, "SN금액": col_SN금액,
    "사진주소": col_사진주소,
}

# ─── 필터 UI ────────────────────────────────────────────────────
sel_품번검색 = st.text_input("🔎 품번 검색", placeholder="품번 입력 (부분 검색 가능)")

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

fc4, fc5, fc6 = st.columns(3)
with fc4:
    sel_담당 = st.selectbox("담당자", ["전체"] + unique_vals(df_raw, col_담당))
with fc5:
    sel_관계사팀 = st.selectbox("관계사팀", ["전체"] + unique_vals(df_raw, col_관계사팀))
with fc6:
    sel_업체 = st.selectbox("업체", ["전체"] + unique_vals(df_raw, col_업체명))

_, btn_col, _ = st.columns([3, 1, 3])
with btn_col:
    do_search = st.button("🔍 조회", use_container_width=True)

st.markdown("---")

# ─── 필터 적용 ──────────────────────────────────────────────────
if do_search:
    df = df_raw
    if sel_품번검색.strip() and col_품번:
        df = df[df[col_품번].str.contains(sel_품번검색.strip(), case=False, na=False)]
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

if "filtered_df" not in st.session_state:
    st.info("필터를 선택한 후 🔍 조회 버튼을 눌러주세요.")
    st.stop()

df = st.session_state["filtered_df"]
sel_months = detect_months(df_raw)

st.markdown(f"**조회 결과: 총 {len(df)}개 상품**")

if df.empty:
    st.info("조회 결과가 없습니다.")
    st.stop()

# ─── 사진 미리보기 (사이드바) ────────────────────────────────────
with st.sidebar:
    st.markdown("### 📷 상품 사진")
    if col_품번 and col_사진주소 and len(df) > 0:
        품번_list = df[col_품번].tolist()
        품명_list = df[col_품명].tolist() if col_품명 else [""] * len(품번_list)
        선택옵션 = [f"{p} | {n}" for p, n in zip(품번_list, 품명_list)]
        sel_idx = st.selectbox("상품 선택", range(len(선택옵션)),
                               format_func=lambda i: 선택옵션[i])
        사진url = str(df.iloc[sel_idx][col_사진주소]).strip()
        st.markdown(f"**{품번_list[sel_idx]}**")
        st.caption(품명_list[sel_idx])
        if 사진url.startswith("http"):
            st.image(사진url, use_container_width=True)
        else:
            st.info("사진 없음")
    else:
        st.info("조회된 상품이 없습니다.")

# ─── 테이블 렌더링 ──────────────────────────────────────────────
table_html = build_table(df, sel_months, col_map)
st.markdown(table_html, unsafe_allow_html=True)
