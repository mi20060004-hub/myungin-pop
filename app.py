import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 인증 및 시트 연결 ---
def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

gc = get_gspread_client()
SHEET_ID = "1ST-zbOoIoP5MvWkoTCFNDvi76yavH8pu2Ak7kudyzBM"
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.worksheet('현재생산중')

# --- 2. 디자인 설정 ---
st.set_page_config(layout="wide", page_title="명인제약 POP 시스템")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .process-card {
        background-color: white; padding: 20px; border-radius: 10px;
        border-left: 5px solid #007bff; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .status-badge {
        padding: 5px 12px; border-radius: 15px; font-size: 0.85em; font-weight: bold; color: white;
    }
    </style>
    """, unsafe_allow_html=True) # <- 이 부분이 수정되었습니다.

st.title("🏭 명인제약 생산 시점 관리 시스템 (POP)")

# --- 3. 데이터 로드 및 시각화 ---
try:
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
except Exception as e:
    st.error(f"데이터를 읽어오는데 실패했습니다: {e}")
    st.stop()

if not df.empty:
    cols = st.columns(3) 
    for idx, row in df.iterrows():
        status_color = "#6c757d" 
        if str(row.get('상태')) == '진행중': status_color = "#28a745"
        elif str(row.get('상태')) == '대기': status_color = "#ffc107"

        with cols[idx % 3]:
            st.markdown(f"""
                <div class="process-card">
                    <div style="display:flex; justify-content: space-between; align-items:center;">
                        <h3 style="margin:0;">{row.get('공정', '공정명 없음')}</h3>
                        <span class="status-badge" style="background-color: {status_color};">
                            {row.get('상태', '상태 미정')}
                        </span>
                    </div>
                    <hr style="margin:10px 0;">
                    <p><b>제조번호:</b> {row.get('제조번호', '-')}</p>
                    <p><b>제품명:</b> {row.get('제품명', '-')}</p>
                    <p style="font-size: 0.8em; color: gray;">조회시간: {datetime.now().strftime('%H:%M:%S')}</p>
                </div>
                """, unsafe_allow_html=True) # <- 이 부분도 수정되었습니다.
            
            if st.button(f"작업 관리 ({row.get('제조번호', idx)})", key=f"btn_{idx}"):
                st.info(f"'{row.get('공정')}' 공정 기록 모듈을 실행합니다.")
else:
    st.info("현재 '현재생산중' 탭에 표시할 데이터가 없습니다.")
