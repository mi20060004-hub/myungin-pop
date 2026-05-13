import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 인증 및 시트 연결 (시트 ID 방식) ---
def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

gc = get_gspread_client()
SHEET_ID = "1ST-zbOoIoP5MvWkoTCFNDvi76yavH8pu2Ak7kudyzBM"
sh = gc.open_by_key(SHEET_ID)

# 탭 가져오기 (띄어쓰기 없는 이름 기준)
worksheet = sh.worksheet('현재생산중')
log_sheet = sh.worksheet('공정이력')
master_sheet = sh.worksheet('제품마스터')

# --- 2. 디자인 설정 ---
st.set_page_config(layout="wide", page_title="명인제약 POP 시스템")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .process-card {
        background-color: white; padding: 20px; border-radius: 10px;
        border-left: 5px solid #007bff; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .status-badge {
        padding: 5px 10px; border-radius: 15px; font-size: 0.8em; font-weight: bold;
    }
    </style>
    """, unsafe_allow_config=True)

st.title("🏭 명인제약 생산 시점 관리 시스템 (POP)")

# --- 3. 데이터 로드 및 시각화 (블록 형태) ---
data = worksheet.get_all_records()
df = pd.DataFrame(data)

if not df.empty:
    cols = st.columns(3) # 3열로 공정 블록 배치
    for idx, row in df.iterrows():
        with cols[idx % 3]:
            st.markdown(f"""
                <div class="process-card">
                    <h3>{row['공정명']}</h3>
                    <p><b>제품명:</b> {row['제품명']}</p>
                    <p><b>지시수량:</b> {row['지시수량']} / <b>생산수량:</b> {row['생산수량']}</p>
                    <span class="status-badge" style="background-color: {'#e1f5fe' if row['상태']=='대기' else '#fff3e0'};">
                        ● {row['상태']}
                    </span>
                </div>
                """, unsafe_allow_config=True)
            if st.button(f"{row['공정명']} 작업 시작", key=f"btn_{idx}"):
                st.success(f"{row['공정명']} 작업을 시작합니다!")
else:
    st.info("현재 가동 중인 공정이 없습니다. 구글 시트에 데이터를 입력해 주세요.")
