import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 페이지 설정 ---
st.set_page_config(layout="wide", page_title="명인제약 생산 시점 관리")

# --- 2. CSS 스타일 (대형 블루 헤더 & 디자인) ---
st.markdown("""
    <style>
    .fixed-header {
        position: fixed; top: 0; left: 0; right: 0; height: 100px;
        background-color: #1e3a8a; z-index: 999998;
        display: flex; align-items: center; justify-content: center;
    }
    .main-title-text {
        color: white !important; font-size: 40px !important; font-weight: 900; margin: 0;
    }
    .main .block-container { padding-top: 130px !important; }
    .stage-bar {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        color: white; padding: 10px 20px; border-radius: 8px;
        font-size: 20px; font-weight: 700; margin-top: 25px; margin-bottom: 15px;
    }
    .machine-title {
        background: #f8fafc; text-align: center; font-size: 11px; font-weight: 700;
        border-radius: 4px; margin-bottom: 8px; border: 1px solid #cbd5e1; min-height: 30px;
        display: flex; align-items: center; justify-content: center;
    }
    .status-bar { font-size: 10px; font-weight: 800; color: white; text-align: center; padding: 2px 0; border-radius: 3px; }
    .bg-waiting { background-color: #3b82f6; } .bg-progress { background-color: #ef4444; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 인증 및 시트 연결 ---
@st.cache_resource
def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

gc = get_gspread_client()
SHEET_ID = "1ST-zbOoIoP5MvWkoTCFNDvi76yavH8pu2Ak7kudyzBM"
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.worksheet('현재생산중')
log_sheet = sh.worksheet('공정이력')
master_sheet = sh.worksheet('제품마스터')

# --- 4. 데이터 로드 (방법 B 적용) ---
def get_now_kst():
    return (datetime.now(timezone(timedelta(hours=9)))).strftime('%Y-%m-%d %H:%M:%S')

# 사용자님이 알려주신 10개 공정 리스트
TARGET_STAGES = ["과립공정", "건조공정", "정립공정", "혼합공정", "타정공정", "캡슐공정", "질량선별공정", "코팅공정", "인쇄공정", "외관선별공정"]

def load_data():
    m_values = master_sheet.get_all_values()
    if not m_values: return {}, pd.DataFrame()
    
    header = [h.strip() for h in m_values[0]]
    col_map = {stage: header.index(stage) if stage in header else -1 for stage in TARGET_STAGES}

    master_dict = {}
    for r in m_values[1:]:
        if not r or not r[0]: continue
        p_name = r[0].strip()
        master_dict[p_name] = {s: [m.strip() for m in str(r[col_map[s]]).split(',') if m.strip()] if col_map[s] != -1 and len(r) > col_map[s] else [] for s in TARGET_STAGES}

    c_values = worksheet.get_all_values()
    curr_df = pd.DataFrame([{'Lot':r[0],'제품':r[1],'공정':r[2],'상태':r[3],'Row':i+2, '설비':r[9] if len(r)>9 else ""} for i,r in enumerate(c_values[1:]) if r and r[0]])
    return master_dict, curr_df

# --- [중요] 설비 리스트는 집에 오셔서 알려주시면 여기에 채워 넣을게요! ---
machine_map = {stage: ["설비 대기중"] for stage in TARGET_STAGES} 

master_dict, curr_df = load_data()

# --- 5. 헤더 & 네비게이션 ---
st.markdown('<div class="fixed-header"><div class="header-content"><p class="main-title-text">명인제약 생산 시점 관리</p></div></div>', unsafe_allow_html=True)
if 'page' not in st.session_state: st.session_state.page = 'main'

# --- 6. 사이드바 & 메인 로직 (생략 - 기존과 동일하되 TARGET_STAGES 연동) ---
# (공간상 핵심 로직 위주로 구성했습니다)

with st.sidebar:
    st.header("🏭 제조 투입")
    sel_p = st.selectbox("제품명 선택", list(master_dict.keys()) if master_dict else ["데이터 없음"])
    lot_in = st.text_input("제조번호(Lot) 입력")
    if st.button("🚀 투입 확정"):
        f_stg = next((s for s in TARGET_STAGES if master_dict[sel_p][s]), TARGET_STAGES[0])
        f_m = master_dict[sel_p][f_stg][0] if master_dict[sel_p][f_stg] else ""
        worksheet.append_row([lot_in, sel_p, f_stg, "대기", "", get_now_kst(), "0", "일반", "", f_m])
        st.rerun()

# 메인 현황판
if st.session_state.page == 'main':
    for stage in TARGET_STAGES:
        st.markdown(f'<div class="stage-bar">▶ {stage}</div>', unsafe_allow_html=True)
        cols = st.columns(10)
        # machine_map에 따라 설비 버튼 생성 로직...
