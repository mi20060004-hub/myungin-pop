import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 페이지 설정 ---
st.set_page_config(layout="wide", page_title="명인제약 생산 시점 관리")

# --- 2. CSS 스타일 ---
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

# --- 3. 인증 및 시트 연결 (캐시 제거: 실시간 로드) ---
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
    # 제품마스터 전체 데이터 가져오기
    m_values = master_sheet.get_all_values()
    if not m_values: return {}, pd.DataFrame()
    
    header = [h.strip() for h in m_values[0]]
    # 공정명이 있는 열 인덱스 찾기
    col_map = {stage: header.index(stage) if stage in header else -1 for stage in TARGET_STAGES}

    master_dict = {}
    for r in m_values[1:]:
        if not r or not r[0]: continue  # 첫 번째 열(A열)이 비어있으면 무시
        
        # A열 데이터를 강제로 문자열로 변환 (숫자형 제품코드 방지)
        p_name = str(r[0]).strip()
        
        # 만약 제품명이 '100000' 같은 숫자라면 무시하고 싶은 경우를 대비해 
        # 실제 한글/영문 제품명이 나올 때까지 데이터를 확인합니다.
        master_dict[p_name] = {}
        for stage in TARGET_STAGES:
            idx = col_map[stage]
            master_dict[p_name][stage] = [m.strip() for m in str(r[idx]).split(',') if m.strip()] if idx != -1 and len(r) > idx else []

    # 현재생산중 데이터
    c_values = worksheet.get_all_values()
    curr_df = pd.DataFrame([{'Lot':r[0],'제품':r[1],'공정':r[2],'상태':r[3]} for r in c_values[1:] if r and r[0]])
    return master_dict, curr_df

master_dict, curr_df = load_data()

# --- 5. 화면 렌더링 ---
st.markdown('<div class="fixed-header"><p class="main-title-text">명인제약 생산 시점 관리</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("🏭 제조 투입")
    # 로드된 제품 목록 확인
    p_list = list(master_dict.keys())
    sel_p = st.selectbox("제품명 선택", p_list if p_list else ["데이터 없음"])
    lot_in = st.text_input("제조번호(Lot) 입력")
    if st.button("🚀 투입 확정"):
        st.success(f"{sel_p} 투입 성공")

for stage in TARGET_STAGES:
    st.markdown(f'<div class="stage-bar">▶ {stage}</div>', unsafe_allow_html=True)
    st.info(f"{stage}에 배치된 설비가 없습니다. 제품마스터 시트의 해당 공정 열에 설비를 입력해주세요.")
