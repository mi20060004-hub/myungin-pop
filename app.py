import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client

# --- 1. 페이지 설정 ---
st.set_page_config(layout="wide", page_title="명인제약 생산 시점 관리")

# --- 2. CSS 스타일 ---
st.markdown("""
<style>
html { scroll-behavior: smooth; }
.fixed-header {
    position: fixed; top: 0; left: 0; right: 0; height: 66px; 
    background-color: #1e3a8a; z-index: 999998; 
    display: flex; align-items: center; padding: 0 30px; 
    box-shadow: 0 4px 10px rgba(0,0,0,0.3); 
}
.main-title-text {
    color: white !important; font-size: 28px !important; 
    font-weight: 800; margin: 0; flex-grow: 1; 
}
.main .block-container { padding-top: 100px !important; }
.stage-bar {
    scroll-margin-top: 80px;
    color: white; padding: 8px 13px; border-radius: 6px; 
    font-size: 18px; font-weight: 700; margin-top: 20px; margin-bottom: 10px; 
    background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
}
.machine-title {
    background: #f1f5f9; text-align: center; font-size: 16px !important; 
    font-weight: 800; border-radius: 6px; margin-bottom: 8px; 
    border: 2px solid #cbd5e1; min-height: 40px; 
    display: flex; align-items: center; justify-content: center; color: #1e293b; 
}
.card-text-10px { font-size: 15px !important; font-weight: 800; margin: 0; text-align: center; line-height: 1.2; }
.card-text-l-10px { font-size: 15px !important; color: #1e40af; font-weight: 700; text-align: center; margin: 0; line-height: 1.2; }
.card-text-date { font-size: 12px !important; color: #64748b; font-weight: 700; text-align: center; margin: 1px 0; line-height: 1.2; }
.info-text-10px { font-size: 10px !important; color: #475569; margin: 1px 0; text-align: center; line-height: 1.2; }
.stock-red { font-size: 12px !important; color: #ef4444 !important; font-weight: 800 !important; text-align: center; margin: 1px 0; line-height: 1.2; }
.stock-green { font-size: 12px !important; color: #004d40 !important; font-weight: 800 !important; text-align: center; margin: 1px 0; line-height: 1.2; }
.stock-black { font-size: 12px !important; color: #1e293b !important; font-weight: 800 !important; text-align: center; margin: 1px 0; line-height: 1.2; }
.wip-blue { font-size: 12px !important; color: #2563eb !important; font-weight: 800 !important; text-align: center; margin: 1px 0; line-height: 1.2; }
.wip-black { font-size: 12px !important; color: #475569 !important; font-weight: 800 !important; text-align: center; margin: 1px 0; line-height: 1.2; }
.lot-type-highlight { font-size: 15px !important; color: #ef4444 !important; font-weight: 800 !important; text-align: center; margin: 1px 0; line-height: 1.2; }
.status-bar { font-size: 10px; font-weight: 800; color: white; text-align: center; padding: 2px 0; border-radius: 3px; margin-bottom: 3px; }
.bg-waiting { background-color: #3b82f6; }
.bg-progress { background-color: #ef4444; }
.bg-paused { background-color: #f59e0b; }
div[data-testid="stDataFrame"] td, div[data-testid="stDataFrame"] th { font-size: 16px !important; }
div[data-testid="stVerticalBlock"] > div { margin-bottom: 0px !important; padding-bottom: 0px !important; margin-top: 0px !important; padding-top: 0px !important; }
div[data-testid="stVerticalBlock"] > div[style*="min-height: 1rem"] { min-height: 0px !important; height: 0px !important; margin: 0px !important; padding: 0px !important; display: none !important; }
.main div[data-testid="stVerticalBlock"] [data-testid="stElementContainer"],
.main div[data-testid="stVerticalBlock"] div[data-testid="stButton"],
.main div[data-testid="stVerticalBlock"] div[data-testid="stPopover"],
.main div[data-testid="stVerticalBlock"] div[data-testid="stPopover"] > div:first-child,
.main div[data-testid="stVerticalBlock"] div[data-testid="stPopover"] data-inline-label {
    min-height: 16px !important; height: 16px !important; max-height: 16px !important; margin: 0px 0px 2px 0px !important; padding: 0px !important; display: flex !important; align-items: center !important;
}
.main div[data-testid="stVerticalBlock"] button,
.main div[data-testid="stVerticalBlock"] button[data-testid="stBaseButton-secondary"],
.main div[data-testid="stVerticalBlock"] button[data-testid="stBaseButton-element"],
.main div[data-testid="stVerticalBlock"] div.stButton > button {
    padding-top: 0px !important; padding-bottom: 0px !important; padding-left: 2px !important; padding-right: 2px !important;
    margin: 0px !important; font-size: 11px !important; font-weight: 800 !important; 
    height: 16px !important; min-height: 16px !important; max-height: 16px !important; 
    line-height: 16px !important; display: inline-flex !important; align-items: center !important; justify-content: center !important; 
    box-sizing: border-box !important; width: 100% !important; border-radius: 4px !important;
}
.main div[data-testid="stVerticalBlock"] div[data-testid="stPopover"] button p {
    margin: 0px !important; padding: 0px !important; line-height: 16px !important; font-size: 11px !important; font-weight: 800 !important; display: flex !important; align-items: center !important; justify-content: center !important;
}
.search-highlighted {
    border: 3px solid #ff6b00 !important;
    box-shadow: 0 0 15px rgba(255, 107, 0, 0.8) !important;
    transform: scale(1.02);
    transition: all 0.2s ease-in-out;
}
.search-dimmed {
    opacity: 0.4 !important;
    transition: opacity 0.2s ease-in-out;
}
</style>
""", unsafe_allow_html=True)

# --- 3. Supabase DB 연결 ---
@st.cache_resource
def init_supabase():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"🔗 데이터베이스 연결 실패: {e}")
    st.stop()

# --- 4. 설정 및 데이터 로직 ---
MACHINE_MAP = {
    "칭량공정": [], 
    "과립공정": ["P100", "SM100", "P400", "GS400", "SM600", "KM10", "글라트유동층", "GPCG2", "구형과립기", "롤러컴팩터"],
    "건조공정": ["트레이1호", "트레이2호", "트레이3호", "트레이4호", "트레이5호", "트레이6호", "트레이7호", "다산유동층", "D600"],
    "정립혼합대기창고": [],
    "정립공정": ["Comil0112", "Comil0212", "Comil0312", "파워밀"],
    "혼합공정": ["PM1000", "PM2000", "드럼혼합기"],
    "반제품창고": [],  
    "타정공정": ["킬리안", "63S-3", "41S", "63S-1", "PR1023", "MRC45", "45S", "63S-2", "31S", "PH300"],
    "캡슐공정": ["SF150N", "보쉬충전기", "PTK충전기", "SF35"],
    "질량선별공정": ["CWI150", "세종질량선별기"],
    "코팅공정": ["SFC150FH", "SFC170FH", "SFC170FSH", "SFC130FSH", "V150", "SFC80", "수동코팅기"],
    "인쇄공정": ["정제인쇄기"],
    "외관선별공정": ["비즈윌구형", "비즈윌신형", "엔클로니구형", "엔클로니신형", "수동선별기", "캡슐외관선별기"]
}
TARGET_STAGES = list(MACHINE_MAP.keys())

def get_now_kst(): return datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M')
def get_today_date_kst(): return datetime.now(timezone(timedelta(hours=9))).date()

def get_elapsed_days_str(date_val):
    if pd.isna(date_val): return ""
    date_str = str(date_val).strip()
    if not date_str or date_str.upper() == "NONE" or date_str == "-": return ""
    try:
        target_dt = datetime.strptime(date_str[:10], '%Y-%m-%d').date()
        today_dt = get_today_date_kst()
        return f" ({(today_dt - target_dt).days}일째)"
    except: return ""

@st.cache_data(ttl=60)
def load_data():
    m_data = supabase.table("product_master").select("*").execute()
    master_dict = {
        str(r.get("제품명", "")).strip(): {s: [m.strip() for m in str(r.get(s, "")).split(',') if m.strip()] if r.get(s) and str(r.get(s)) not in ["None", "-"] else [] for s in TARGET_STAGES}
        for r in m_data.data if str(r.get("제품명", "")).strip()
    }
    
    stock_dict = {}
    s_data = supabase.table("product_stock").select("적요, \"재고 월수\", \"재공 월수\"").order("id", desc=True).execute()
    for s_row in s_data.data:
        p_name = str(s_row['적요']).replace(" ", "").strip()
        if p_name not in stock_dict:
            stock_dict[p_name] = {"재고": str(s_row.get('재고 월수', '정보없음')).strip(), "재공": str(s_row.get('재공 월수', '정보없음')).strip()}
            
    h_data = supabase.table("product_history").select("*").execute()
    all_raw_df = pd.DataFrame(h_data.data) if h_data.data else pd.DataFrame()
    if not all_raw_df.empty and 'id' in all_raw_df.columns: all_raw_df['Row'] = all_raw_df['id']
    
    curr_df = all_raw_df[~all_raw_df['상태'].isin(['완료', '1팀종료'])].copy() if not all_raw_df.empty else pd.DataFrame()
    log_df = all_raw_df[all_raw_df['상태'].isin(['완료', '1팀종료'])].copy() if not all_raw_df.empty else pd.DataFrame()
    return master_dict, stock_dict, curr_df, log_df, all_raw_df

master_dict, stock_dict, curr_df, log_df, all_raw_df = load_data()

if 'pending_lots' not in st.session_state: st.session_state.pending_lots = []
if 'view' not in st.session_state: st.session_state.view = 'main'
if 'reset_lot' not in st.session_state: st.session_state.reset_lot = ""
if 'reset_note' not in st.session_state: st.session_state.reset_note = ""

# --- 5. UI 렌더링 ---
st.markdown(f'<div class="fixed-header"><p class="main-title-text">명인제약 생산 시점 관리</p></div>', unsafe_allow_html=True)
nav_cols = st.columns(4)
nav_buttons = [("실시간 현황판", 'main'), ("완료된 공정 확인", 'history'), ("완료된 공정 확인(선별)", 'selection'), ("모든 공정 이력 확인", 'all_history')]
for i, (label, val) in enumerate(nav_buttons):
    if nav_cols[i].button(label, key=f"nav_{i}", use_container_width=True): st.session_state.view = val; st.rerun()

# --- 6. 사이드바 ---
with st.sidebar:
    st.header("🏭 제조 투입")
    sel_p = st.selectbox("제품명 선택", list(master_dict.keys()), key="sel_p_widget")
    lot_in = st.text_input("제조번호(Lot) 입력", value=st.session_state.reset_lot, key="lot_in_widget").strip()
    date_in = st.date_input("제조일자 선택", value=get_today_date_kst(), key="date_in_widget")
    lot_type = st.selectbox("로트 유형 선택", ["일반로트", "동시PV1", "동시PV2", "동시PV3", "예측PV1", "예측PV2", "예측PV3"], key="lot_type_widget")
    note_in = st.text_area("공정 특이사항 입력", value=st.session_state.reset_note, key="note_in_widget")
    
    if lot_in and st.button("➕ 투입 대기열 추가", use_container_width=True):
        st.session_state.pending_lots.append({'제품': sel_p, 'Lot': lot_in, '제조일자': str(date_in), '유형': lot_type, '특이사항': note_in})
        st.session_state.reset_lot = ""; st.rerun()

    for idx, p in enumerate(st.session_state.pending_lots):
        c1, c2 = st.columns([8, 2])
        c1.info(f"{p['제품']} | {p['Lot']}")
        if c2.button("❌", key=f"del_{idx}"): st.session_state.pending_lots.pop(idx); st.rerun()
        
    if st.session_state.pending_lots and st.button("🚀 전체 투입 확정", type="primary", use_container_width=True):
        for p in st.session_state.pending_lots:
            supabase.table("product_history").insert({"Lot": p['Lot'], "제품": p['제품'], "공정": "칭량공정", "상태": "대기", "제조일자": p['제조일자'], "유형": p['유형'], "특이사항": p['특이사항'], "설비": ""}).execute()
        st.session_state.pending_lots = []; st.rerun()

    search_keyword = st.text_input("🔍 현황판 제품 위치 추적", placeholder="제품명 또는 Lot 검색", key="live_search_box").strip() if st.session_state.view == 'main' else ""
    
    with st.popover("🔒 데이터 초기화", use_container_width=True):
        if st.text_input("비밀번호", type="password") == "1234" and st.button("🚨 초기화 실행"):
            supabase.table("product_history").delete().neq("Lot", "sys_clear").execute(); st.rerun()

# --- 7. 메인 로직 ---
def render_stock_and_wip_html(prod_name):
    s = stock_dict.get(prod_name.replace(" ", ""), {"재고": "정보없음", "재공": "정보없음"})
    s_c = "stock-red" if s['재고'].replace('.','',1).isdigit() and float(s['재고']) <= 1.0 else "stock-green"
    return f"<p class='{s_c}'>재고: {s['재고']}개월</p><p class='wip-blue'>재공(합산): {s['재공']}개월</p>"

if st.session_state.view == 'main':
    for stage in TARGET_STAGES:
        m_items = curr_df[curr_df['공정'] == stage] if not curr_df.empty else pd.DataFrame()
        st.markdown(f'<div id="{stage.replace(" ", "")}" class="stage-bar">▶ {stage} ({len(m_items)}건)</div>', unsafe_allow_html=True)
        
        if stage in ["칭량공정", "정립혼합대기창고", "반제품창고"]:
            for i in range(0, len(m_items), 10):
                cols = st.columns(10)
                for j, (_, row) in enumerate(m_items.iloc[i:i+10].iterrows()):
                    with cols[j]:
                        is_match = search_keyword and (search_keyword.lower() in str(row['제품']).lower() or search_keyword.lower() in str(row['Lot']).lower())
                        with st.container(border=True):
                            st.markdown(f"<div class='{'search-highlighted' if is_match else 'search-dimmed' if search_keyword else ''}'>", unsafe_allow_html=True)
                            st.markdown(f"<p class='card-text-10px'>{row['제품']}</p><p class='card-text-l-10px'>{row['Lot']}</p>", unsafe_allow_html=True)
                            st.markdown(render_stock_and_wip_html(row['제품']), unsafe_allow_html=True)
                            if st.button("시작" if row['상태']=='대기' else "대기", key=f"act_{row['Row']}"):
                                new_s = "진행중" if row['상태']=='대기' else "지연"
                                supabase.table("product_history").update({"상태": new_s}).eq("id", row['Row']).execute(); st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)
        else:
            cols = st.columns(10)
            for i, machine in enumerate(MACHINE_MAP[stage][:10]):
                with cols[i]:
                    st.markdown(f"<div class='machine-title'>{machine}</div>", unsafe_allow_html=True)
                    m_data = m_items[m_items['설비'].str.strip() == machine]
                    for _, row in m_data.iterrows():
                        with st.container(border=True):
                            st.markdown(f"<p class='card-text-10px'>{row['제품']}</p><p class='card-text-l-10px'>{row['Lot']}</p>", unsafe_allow_html=True)
                            if st.button("진행", key=f"btn_{row['Row']}"): st.rerun()
else:
    # 히스토리 뷰 (생략된 부분은 동일 로직 유지)
    st.header(f"📋 {st.session_state.view}")
    if not log_df.empty: st.dataframe(log_df, use_container_width=True)
