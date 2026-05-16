import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 페이지 설정 ---
st.set_page_config(layout="wide", page_title="명인제약 생산 시점 관리")

# --- 2. CSS 스타일 (대형 블루 헤더) ---
st.markdown("""
    <style>
    .fixed-header {
        position: fixed; top: 0; left: 0; right: 0; height: 100px;
        background-color: #1e3a8a; z-index: 999998;
        display: flex; align-items: center; justify-content: center;
    }
    .main-title-text { color: white !important; font-size: 40px !important; font-weight: 900; }
    .main .block-container { padding-top: 130px !important; }
    .stage-bar {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        color: white; padding: 10px 20px; border-radius: 8px;
        font-size: 20px; font-weight: 700; margin-top: 25px;
    }
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
master_sheet = sh.worksheet('제품마스터')

# --- 4. 데이터 로드 (확장된 10개 공정 반영) ---
# 사용자님이 시트에 적으신 공정명과 정확히 일치해야 합니다.
TARGET_STAGES = ["과립공정", "건조공정", "정립공정", "혼합공정", "타정공정", "캡슐공정", "질량선별공정", "코팅공정", "인쇄공정", "외관선별공정"]

def load_data():
    m_values = master_sheet.get_all_values()
    if not m_values: return {}, pd.DataFrame()
    
    header = [h.strip() for h in m_values[0]]
    # 공정명이 포함된 열 번호를 자동으로 찾습니다.
    col_map = {stage: header.index(stage) if stage in header else -1 for stage in TARGET_STAGES}

    master_dict = {}
    for r in m_values[1:]:
        if not r or not r[1]: continue # '제품명'은 2번째 열(index 1)에 있음
        p_name = r[1].strip()
        master_dict[p_name] = {}
        for stage in TARGET_STAGES:
            idx = col_map[stage]
            master_dict[p_name][stage] = [m.strip() for m in str(r[idx]).split(',') if m.strip()] if idx != -1 and len(r) > idx else []

    c_values = worksheet.get_all_values()
    curr_df = pd.DataFrame([{'Lot':r[0],'제품':r[1],'공정':r[2],'상태':r[3]} for r in c_values[1:] if r and r[0]])
    return master_dict, curr_df

master_dict, curr_df = load_data()

# --- 5. 화면 렌더링 ---
st.markdown('<div class="fixed-header"><p class="main-title-text">명인제약 생산 시점 관리</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("🏭 제조 투입")
    # master_dict의 키(제품명)를 드롭다운에 표시합니다.
    sel_p = st.selectbox("제품명 선택", list(master_dict.keys()) if master_dict else ["데이터 로드 실패"])
    lot_in = st.text_input("제조번호(Lot) 입력")
    if st.button("🚀 투입 확정"):
        st.success(f"{sel_p} 투입 완료!")

for stage in TARGET_STAGES:
    st.markdown(f'<div class="stage-bar">▶ {stage}</div>', unsafe_allow_html=True)
