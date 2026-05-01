import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from datetime import datetime, timedelta

st.set_page_config(
    page_title="BJZ2",
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
  html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; font-size: 12px; /* 전체 기본 폰트, 크기조정 */ }
  .stApp { background: #f5f5f5; }
  div.stButton > button { background:#1a3a5c; color:white; border:none; border-radius:4px; padding:6px 24px; font-weight:600; font-size:13px; /* 조회버튼, 크기조정 */ }
  div.stButton > button:hover { background:#2d6a9f; }
  .stSelectbox > div > div { font-size:12px !important; /* 필터 셀렉트박스, 크기조정 */ }
  div[data-testid="stStatusWidget"] { display:none; }
</style>
""", unsafe_allow_html=True)

# ─── xlsx 파일 로드 ─────────────────────────────────────────────
DATA_FILE = "BJZ.xlsx"

def yyyymm_to_yymm(val):
    s = str(val).strip()
    if len(s) == 5 and s[2] == "/" and s[:2].isdigit() and s[3:].isdigit():
        return s
    if len(s) == 6 and s.isdigit():
        return s[2:4] + "/" + s[4:6]
    try:
        n = int(float(s))
        if 40000 < n < 60000:
            dt = datetime(1899, 12, 30) + timedelta(days=n)
            return dt.strftime("%y/%m")
    except:
        pass
    return None

@st.cache_data
def load_data():
    try:
        raw = pd.read_excel(DATA_FILE, header=None, dtype=str, sheet_name=0)
        if len(raw) < 3:
            return pd.DataFrame()

        row0 = [str(v).strip() if pd.notna(v) and str(v) != "nan" else "" for v in raw.iloc[0]]
        row1 = [str(v).strip().replace("\n", " ") if pd.notna(v) and str(v) != "nan" else "" for v in raw.iloc[1]]

        max_cols = raw.shape[1]
        while len(row0) < max_cols: row0.append("")
        while len(row1) < max_cols: row1.append("")

        columns = []
        last_cat = ""
        for i in range(max_cols):
            cat = row0[i]
            sub = row1[i]
            if cat and cat not in ("nan", ""):
                last_cat = cat
            converted = yyyymm_to_yymm(sub)
            is_month = converted is not None
            if is_month:
                sub = converted
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
        df = df.astype(str).replace("nan", "").replace("<NA>", "")

        품번_col = None
        for c in df.columns:
            if c.strip().replace(" ", "").replace("\n", "") == "품번":
                품번_col = c
                break
        if 품번_col:
            df = df[df[품번_col].str.strip() != ""]

        return df.reset_index(drop=True)

    except FileNotFoundError:
        st.error(f"파일을 찾을 수 없습니다: {DATA_FILE}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return pd.DataFrame()

# ─── 유틸 함수 ──────────────────────────────────────────────────
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
    df_cols = list(df.columns)
    for name in names:
        if name in df_cols:
            return name
    clean_map = {}
    for c in df_cols:
        if "_" in c and "/" in c:
            continue
        clean_map[c.replace(" ", "").replace("\n", "")] = c
    for name in names:
        key = name.replace(" ", "").replace("\n", "")
        if key in clean_map:
            return clean_map[key]
    for name in names:
        for c in df_cols:
            if "_" in c and "/" in c:
                continue
            if name in c:
                return c
    return None

def safe_int(v):
    try:
        if v in ("", None, "nan", "<NA>"): return 0
        return int(float(str(v).replace(",", "")))
    except:
        return 0

def fmt_num(v):
    return "0" if v == 0 else f"{v:,}"

def unique_vals(df, col):
    if col is None: return []
    return sorted([v for v in df[col].unique()
                   if str(v).strip() and str(v) not in ("nan", "<NA>", "")])

# ─── 테이블 CSS (② 헤더 행 고정 포함) ─────────────────────────
TABLE_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
  * { font-family: 'Noto Sans KR', sans-serif; box-sizing: border-box; }
  body { margin:0; padding:0; background:#f5f5f5; }

  /* ② 헤더 고정: wrap에 overflow + max-height */
  .tbl-wrap {
    overflow-x: auto;
    overflow-y: auto;
    max-height: calc(100vh - 20px);
    margin-top: 6px;
    position: relative;
  }

  table.main-tbl { border-collapse:collapse; width:100%; font-size:11px; /* 테이블 전체 셀, 크기조정 */ border:1px solid #999; }

  /* ② sticky header */
  table.main-tbl thead th {
    background:#dce6f1; color:#1a1a1a; font-weight:600;
    padding:5px 6px; border:1px solid #bbb; text-align:center;
    white-space:nowrap; position:sticky; z-index:10;
    /* 테이블 헤더(컬럼명), 크기조정: font-size 추가 시 여기에 작성 */
  }
  /* 2행 헤더: 1행은 top:0, 2행은 1행 높이(27px) 아래 */
  table.main-tbl thead tr:nth-child(1) th { top: 0; }
  table.main-tbl thead tr:nth-child(2) th { top: 27px; }

  table.main-tbl td { padding:3px 5px; border:1px solid #ccc; white-space:nowrap; font-size:11px; /* 테이블 데이터 셀, 크기조정 */ color:#333; }
  table.main-tbl td.num { text-align:right; }
  table.main-tbl td.center { text-align:center; }
  table.main-tbl td.left { text-align:left; }
  table.main-tbl tr.prod-first td { border-top:2px solid #666; }
  table.main-tbl tr.row-pos td { background:#ffe0e0; }
  table.main-tbl tr.row-pos td.type-label { background:#ffcccc; color:#c00; font-weight:700; }
  table.main-tbl td.type-label { text-align:center; font-weight:500; background:#f8f8f8; min-width:55px; /* 구분(발주/입고 등) 라벨, 크기조정 */ }
  table.main-tbl td.zero-val { color:#ccc; }
  table.main-tbl td.img-cell { text-align:center; vertical-align:middle; padding:3px; background:#fff; cursor:pointer; }
  table.main-tbl td.img-cell img { width:60px; height:60px; /* 테이블 썸네일 이미지 크기, 크기조정 */ object-fit:contain; border:1px solid #e0e0e0; border-radius:3px; background:#fff; display:block; margin:auto; transition:transform 0.1s; }
  table.main-tbl td.img-cell img:hover { transform:scale(1.1); border-color:#1a3a5c; }
  table.main-tbl th.img-th { min-width:68px; }
  .st-badge { display:inline-block; padding:1px 5px; border-radius:2px; font-size:10px; /* 상태 뱃지(진행/신상품 등), 크기조정 */ font-weight:600; }
  .st-badge.신상품 { background:#d4edda; color:#155724; }
  .st-badge.단종대기 { background:#f8d7da; color:#721c24; }
  .st-badge.진행 { background:#e2e3e5; color:#383d41; }
  .st-badge.기타 { background:#fff3cd; color:#856404; }

  /* 확대 모달 */
  #zoom-modal {
    display:none; position:fixed; top:0; left:0; width:100%; height:100%;
    background:rgba(0,0,0,0.85); z-index:9999;
    align-items:center; justify-content:center;
  }
  #zoom-modal img { max-width:90%; max-height:85%; object-fit:contain;
    border-radius:4px; box-shadow:0 0 30px rgba(0,0,0,0.5); }
  #zoom-modal .close-btn {
    position:fixed; top:16px; right:16px; color:#fff;
    font-size:28px; cursor:pointer; line-height:1;
    background:rgba(0,0,0,0.5); border-radius:50%;
    width:48px; height:48px; display:flex;
    align-items:center; justify-content:center;
    -webkit-tap-highlight-color: transparent;
    touch-action: manipulation;
  }
</style>
"""

# ─── 테이블 HTML 생성 ───────────────────────────────────────────
def build_table(df, months, cm):
    month_ths = "".join(
        f'<th rowspan="2" style="min-width:44px;text-align:center">{m}</th>'
        for m in months
    )
    header = f"""<thead><tr>
        <th rowspan="2" style="min-width:30px">순번</th>
        <th rowspan="2" class="img-th">사진</th>
        <th rowspan="2" style="min-width:65px">상태</th>
        <th rowspan="2" style="min-width:80px">품번</th>
        <th rowspan="2" style="min-width:100px">품명</th>
        <th rowspan="2" style="min-width:52px">판매가</th>
        <th colspan="2" style="text-align:center">S/N단가</th>
        <th rowspan="2" style="min-width:48px">가용재고</th>
        <th rowspan="2" style="min-width:44px">일평균출고</th>
        <th rowspan="2" style="min-width:44px">발주미입고</th>
        <th rowspan="2" style="min-width:140px">상태정보</th>
        <th rowspan="2" style="min-width:52px">구분</th>
        {month_ths}
    </tr><tr>
        <th style="min-width:40px">통화</th>
        <th style="min-width:50px">금액</th>
    </tr></thead>"""

    badge_map = {"신상품": "신상품", "단종대기": "단종대기", "진행": "진행"}
    rs      = len(ROW_TYPES)
    parts   = []
    df_cols = set(df.columns)
    mc      = {rt: [f"{rt}_{m}" for m in months] for rt in ROW_TYPES}

    for idx in range(len(df)):
        row = df.iloc[idx]
        품명     = str(row[cm["품명"]]) if cm["품명"] else ""
        품번     = str(row[cm["품번"]]) if cm["품번"] else ""
        상태     = str(row[cm["상태"]]) if cm["상태"] else ""
        판매가   = str(row[cm["판매가"]]) if cm["판매가"] else ""
        미입고_v = safe_int(row[cm["미입고"]]) if cm["미입고"] else 0
        입고예정 = str(row[cm["입고예정"]]) if cm["입고예정"] else ""
        정상재고 = safe_int(row[cm["정상재고"]]) if cm["정상재고"] else 0
        일출고   = safe_int(row[cm["일출고량"]]) if cm["일출고량"] else 0
        sn_통화  = str(row[cm["SN통화"]]) if cm["SN통화"] else ""
        sn_금액 = str(row[cm["SN금액"]]) if cm["SN금액"] else "０"
        사진주소 = str(row[cm["사진주소"]]).strip() if cm["사진주소"] else ""

        badge_cls = badge_map.get(상태, "기타")
        seq = idx + 1

        safe_품명 = 품명.replace("'", "\\'").replace('"', '&quot;')
        safe_url  = 사진주소.replace("'", "\\'")

        if 사진주소.startswith("http"):
            img_html = (
                f'<img src="{사진주소}" '
                f'onclick="handleImgClick(event, \'{safe_url}\',\'{품번}\',\'{safe_품명[:20]}\')" '
                f'onerror="this.style.display=\'none\'" alt="{품번}"/>'
            )
        else:
            img_html = '<span style="color:#ccc;font-size:18px">📷</span>'

        first_cells = (
            f'<td class="center" rowspan="{rs}">{seq}</td>'
            f'<td class="img-cell" rowspan="{rs}">{img_html}</td>'
            f'<td class="center" rowspan="{rs}"><span class="st-badge {badge_cls}">{상태}</span></td>'
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
            is_pos   = rt == "POS판매"
            tr_cls = ""
            if is_first and is_pos:   tr_cls = ' class="prod-first row-pos"'
            elif is_first:            tr_cls = ' class="prod-first"'
            elif is_pos:              tr_cls = ' class="row-pos"'

            cells = []
            if is_first:
                cells.append(first_cells)
            cells.append(f'<td class="type-label">{rt}</td>')

            for col_name in mc[rt]:
                v = safe_int(row[col_name]) if col_name in df_cols else 0
                cells.append('<td class="num zero-val">0</td>' if v == 0
                             else f'<td class="num">{v:,}</td>')

            parts.append(f"<tr{tr_cls}>{''.join(cells)}</tr>")

    return (f'<div class="tbl-wrap">'
            f'<table class="main-tbl">{header}'
            f'<tbody>{"".join(parts)}</tbody>'
            f'</table></div>')

# ─── 헤더 ──────────────────────────────────────────────────────
st.markdown(
    '<div style="display:flex;align-items:center;gap:8px;padding:8px 16px;margin-bottom:12px">'
    '<span style="color:#e53e3e;font-size:22px">●</span>'
    '<h1 style="font-size:1.6rem;/* 제목, 크기조정 */ font-weight:700;margin:0;color:#1a1a1a">BJG2</h1>'
    '</div>',
    unsafe_allow_html=True)

# ─── 데이터 로드 ────────────────────────────────────────────────
with st.spinner("데이터 불러오는 중..."):
    df_raw = load_data()

if df_raw.empty:
    st.warning("데이터가 없습니다. BJZ.xlsx 파일을 확인해주세요.")
    st.stop()

# ─── 컬럼명 파악 ────────────────────────────────────────────────
col_담당     = get_col(df_raw, "담당")
col_중분류   = get_col(df_raw, "중분류")
col_소분류   = get_col(df_raw, "소분류")
col_품명     = get_col(df_raw, "품명")
col_품번     = get_col(df_raw, "품번")
col_상태     = get_col(df_raw, "상태")
col_판매가   = get_col(df_raw, "판매가")
col_구입가   = get_col(df_raw, "구입가")
col_사진주소 = get_col(df_raw, "사진주소")
col_업체명   = get_col(df_raw, "업체명")
col_정상재고 = get_col(df_raw, "정상재고", "정상 재고")
col_일출고량 = get_col(df_raw, "일출고량", "일출고")
col_미입고   = get_col(df_raw, "미입고")
col_입고예정 = get_col(df_raw, "입고예정")
col_SN통화   = get_col(df_raw, "통화")
col_SN금액   = get_col(df_raw, "금액")

col_map = {
    "품명": col_품명,     "품번": col_품번,     "상태": col_상태,
    "판매가": col_판매가, "구입가": col_구입가,
    "미입고": col_미입고, "입고예정": col_입고예정,
    "정상재고": col_정상재고, "일출고량": col_일출고량,
    "SN통화": col_SN통화, "SN금액": col_SN금액,
    "사진주소": col_사진주소,
}

# ─── ③ 사진 패널 HTML (iframe으로 렌더링, JS로 업데이트) ─────────
PHOTO_PANEL_HTML = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600&display=swap');
  * { font-family:'Noto Sans KR',sans-serif; box-sizing:border-box; margin:0; padding:0; }
  body { background:transparent; overflow:hidden; }
  #panel-wrap {
    width:100%; height:215px; background:#fff;
    border:1px solid #ddd; border-radius:8px; padding:8px;
    display:flex; flex-direction:column; align-items:center;
    box-shadow:0 1px 6px rgba(0,0,0,0.09);
  }
  h4 { font-size:11px; /* 사진패널 제목(📷 상품 사진), 크기조정 */ color:#1a3a5c; font-weight:600; margin-bottom:5px; }
  #panel-img-wrap {
    width:145px; height:145px; /* 사진패널 이미지 박스 크기, 크기조정 */ flex-shrink:0;
    display:flex; align-items:center; justify-content:center;
    border:1px solid #eee; border-radius:4px;
    background:#fafafa; overflow:hidden;
  }
  #panel-img-wrap img { max-width:145px; max-height:145px; /* 사진패널 이미지 최대크기, 크기조정 */ object-fit:contain; cursor:pointer; }
  #panel-noimg { color:#bbb; font-size:11px; /* 사진패널 안내문구, 크기조정 */ text-align:center; line-height:1.6; }
  #panel-pno   { font-family:monospace; font-size:10px; /* 사진패널 품번, 크기조정 */ color:#666; margin-top:3px; }
  #panel-pname { font-size:10px; /* 사진패널 품명, 크기조정 */ color:#333; text-align:center;
                 max-width:145px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
</style>
<div id="panel-wrap">
  <h4>📷 상품 사진</h4>
  <div id="panel-img-wrap">
    <div id="panel-noimg">사진 클릭 시<br>표시됩니다</div>
    <img id="panel-img" src="" style="display:none"
      onclick="openZoom(this.src)"
      onerror="this.style.display='none';
               document.getElementById('panel-noimg').style.display='block'"/>
  </div>
  <div id="panel-pno"></div>
  <div id="panel-pname"></div>
</div>
<script>
function openZoom(url) {
  try {
    var doc = window.parent.document;
    doc.getElementById('zoom-img-outer').src = url;
    doc.getElementById('zoom-modal-outer').style.display = 'flex';
  } catch(e) {}
}
</script>
"""

# ─── 확대 모달 (Streamlit 페이지 레벨) ───────────────────────────
st.markdown("""
<div id="zoom-modal-outer"
  style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;
         background:rgba(0,0,0,0.85);z-index:9999;align-items:center;justify-content:center;"
  onclick="if(event.target===this||event.target.id==='zoom-img-outer')
           this.style.display='none'">
  <span onclick="document.getElementById('zoom-modal-outer').style.display='none'"
    style="position:fixed;top:16px;right:16px;color:#fff;font-size:28px;cursor:pointer;
           background:rgba(0,0,0,0.5);border-radius:50%;width:48px;height:48px;
           display:flex;align-items:center;justify-content:center;z-index:10000">✕</span>
  <img id="zoom-img-outer" src=""
    style="max-width:90%;max-height:85%;object-fit:contain;
           border-radius:4px;box-shadow:0 0 30px rgba(0,0,0,0.5)"/>
</div>
""", unsafe_allow_html=True)

# ─── ①③ 필터 UI + 사진 패널 (같은 행 배치) ──────────────────────
filter_col, photo_col = st.columns([5, 1])

with filter_col:
    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        sel_품번검색 = st.text_input("🔎 품번 검색", placeholder="품번 입력 (부분 검색)")
    with r1c2:
        sel_진행상태 = st.selectbox("진행상태", ["전체", "진행", "신상품", "단종대기"])
    with r1c3:
        sel_중분류 = st.selectbox("중분류", ["전체"] + unique_vals(df_raw, col_중분류))

    r2c1, r2c2, r2c3 = st.columns(3)
    with r2c1:
        sel_소분류 = st.selectbox("소분류", ["전체"] + unique_vals(df_raw, col_소분류))
    with r2c2:
        sel_담당 = st.selectbox("담당자", ["전체"] + unique_vals(df_raw, col_담당))
    with r2c3:
        sel_업체 = st.selectbox("업체", ["전체"] + unique_vals(df_raw, col_업체명))

    _, btn_c, _ = st.columns([2, 1, 2])
    with btn_c:
        do_search = st.button("🔍 조회", use_container_width=True)

with photo_col:
    # ③ 사진 패널을 필터 우측 동일 위치에 배치
    components.html(PHOTO_PANEL_HTML, height=220)

st.markdown("---")

# ─── 필터 적용 ──────────────────────────────────────────────────
if do_search:
    df = df_raw.copy()
    if sel_품번검색.strip() and col_품번:
        df = df[df[col_품번].str.contains(sel_품번검색.strip(), case=False, na=False)]
    if sel_진행상태 != "전체" and col_상태:
        df = df[df[col_상태] == sel_진행상태]
    if sel_중분류 != "전체" and col_중분류:
        df = df[df[col_중분류] == sel_중분류]
    if sel_소분류 != "전체" and col_소분류:
        df = df[df[col_소분류] == sel_소분류]
    if sel_담당 != "전체" and col_담당:
        df = df[df[col_담당] == sel_담당]
    if sel_업체 != "전체" and col_업체명:
        df = df[df[col_업체명] == sel_업체]
    df = df.reset_index(drop=True)
    st.session_state["filtered_df"] = df
    st.rerun()

if "filtered_df" not in st.session_state:
    st.info("필터를 선택한 후 🔍 조회 버튼을 눌러주세요.")
    st.stop()

df = st.session_state["filtered_df"]
sel_months = detect_months(df_raw)

st.markdown(f"**조회 결과: 총 {len(df)}개 상품**")

if df.empty:
    st.info("조회 결과가 없습니다.")
    st.stop()

# ─── 테이블 렌더링 ──────────────────────────────────────────────
table_body = build_table(df, sel_months, col_map)

# 테이블 내 JS: 사진 클릭 → 사진 패널 iframe 업데이트 + 더블탭 확대
SCRIPTS = """
<div id="zoom-modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;
  background:rgba(0,0,0,0.85);z-index:9999;align-items:center;justify-content:center;">
  <span class="close-btn" ontouchend="closeZoom()" onclick="closeZoom()">✕</span>
  <img id="zoom-img" src=""/>
</div>

<script>
var lastTap = 0;

function handleImgClick(e, url, pno, pname) {
  e.preventDefault();
  var now = Date.now();
  updatePanel(url, pno, pname);
  if ((now - lastTap) < 400 && (now - lastTap) > 0) {
    zoomImg(url);
  }
  lastTap = now;
}

// 사진 패널 iframe을 찾아서 업데이트
function updatePanel(url, pno, pname) {
  try {
    var frames = window.parent.document.querySelectorAll('iframe');
    for (var i = 0; i < frames.length; i++) {
      try {
        var fdoc = frames[i].contentDocument || frames[i].contentWindow.document;
        var img = fdoc.getElementById('panel-img');
        if (img && url && url.startsWith('http')) {
          img.src = url;
          img.style.display = 'block';
          fdoc.getElementById('panel-noimg').style.display = 'none';
          var pnoEl = fdoc.getElementById('panel-pno');
          var pnameEl = fdoc.getElementById('panel-pname');
          if (pnoEl) pnoEl.innerText = pno;
          if (pnameEl) pnameEl.innerText = pname;
        }
      } catch(e2) {}
    }
  } catch(e) {}
}

function zoomImg(url) {
  if (!url || !url.startsWith('http')) return;
  document.getElementById('zoom-img').src = url;
  document.getElementById('zoom-modal').style.display = 'flex';
}

function closeZoom() {
  document.getElementById('zoom-modal').style.display = 'none';
}

document.getElementById('zoom-modal').addEventListener('touchend', function(e) {
  if (e.target === this || e.target === document.getElementById('zoom-img')) closeZoom();
});
document.getElementById('zoom-modal').addEventListener('click', function(e) {
  if (e.target === this) closeZoom();
});
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeZoom();
});
</script>
"""

full_html = TABLE_CSS + SCRIPTS + table_body
components.html(full_html, height=800, scrolling=True)
