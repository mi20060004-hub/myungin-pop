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
    .main-title-text { color: white !important; font-size: 40px !important; font-weight: 900; margin: 0; }
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

# --- 4. 데이터 로드 로직 ---
TARGET_STAGES = ["과립공정", "건조공정", "정립공정", "혼합공정", "타정공정", "캡슐공정", "질량선별공정", "코팅공정", "인쇄공정", "외관선별공정"]

def load_data():
    # 1. 제품마스터 읽기
    m_values = master_sheet.get_all_values()
    if not m_values: return {}, pd.DataFrame()
    
    header = [h.strip() for h in m_values[0]]
    # 제품명이 A열(0번 인덱스)에 있는지 확인
    col_map = {stage: header.index(stage) if stage in header else -1 for stage in TARGET_STAGES}

    master_dict = {}
    for r in m_values[1:]:
        if not r or not r[0]: continue  # A열(제품명)이 비어있으면 건너뜀
        p_name = str(r[0]).strip()     # A열에서 제품명을 가져옴
        master_dict[p_name] = {}
        for stage in TARGET_STAGES:
            idx = col_map[stage]
            # 해당 공정 열에서 설비 리스트 추출
            master_dict[p_name][stage] = [m.strip() for m in str(r[idx]).split(',') if m.strip()] if idx != -1 and len(r) > idx else []

    # 2. 현재생산중 읽기
    c_values = worksheet.get_all_values()
    curr_df = pd.DataFrame([{'Lot':r[0],'제품':r[1],'공정':r[2],'상태':r[3]} for r in c_values[1:] if r and r[0]])
    return master_dict, curr_df

master_dict, curr_df = load_data()

# --- 5. 화면 렌더링 ---
st.markdown('<div class="fixed-header"><p class="main-title-text">명인제약 생산 시점 관리</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("🏭 제조 투입")
    # A열에서 읽어온 '가펜틴캡슐300mg' 등의 이름이 드롭다운에 표시됩니다.
    sel_p = st.selectbox("제품명 선택", list(master_dict.keys()) if master_dict else ["데이터 로드 실패"])
    lot_in = st.text_input("제조번호(Lot) 입력")
    if st.button("🚀 투입 확정"):
        st.success(f"{sel_p} (Lot: {lot_in}) 투입 정보가 시트에 반영됩니다.")

for stage in TARGET_STAGES:
    st.markdown(f'<div class="stage-bar">▶ {stage}</div>', unsafe_allow_html=True)
    st.write(f"{stage}에 배치된 설비가 여기에 표시됩니다.")
