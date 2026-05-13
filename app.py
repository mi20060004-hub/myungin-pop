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

# 탭 가져오기
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
    """, unsafe_allow_config=True)

st.title("🏭 명인제약 생산 시점 관리 시스템 (POP)")

# --- 3. 데이터 로드 및 시각화 (사용자 시트 컬럼 반영) ---
data = worksheet.get_all_records()
df = pd.DataFrame(data)

if not df.empty:
    # 컬럼명이 시트와 일치하는지 확인 (제조번호, 제품명, 공정, 상태 등)
    cols = st.columns(3) 
    for idx, row in df.iterrows():
        # 상태에 따른 색상 지정
        status_color = "#6c757d" # 기본 회색
        if row['상태'] == '진행중': status_color = "#28a745" # 초록
        elif row['상태'] == '대기': status_color = "#ffc107" # 노랑

        with cols[idx % 3]:
            st.markdown(f"""
                <div class="process-card">
                    <div style="display:flex; justify-content:between; align-items:center;">
                        <h3 style="margin:0;">{row['공정']}</h3>
                        <span class="status-badge" style="background-color: {status_color}; margin-left:10px;">
                            {row['상태']}
                        </span>
                    </div>
                    <hr style="margin:10px 0;">
                    <p><b>제조번호:</b> {row['제조번호']}</p>
                    <p><b>제품명:</b> {row['제품명']}</p>
                    <p><b>현재시간:</b> {datetime.now().strftime('%H:%M:%S')}</p>
                </div>
                """, unsafe_allow_config=True)
            
            # 작업 버튼
            if st.button(f"{row['공정']} ({row['제조번호']}) 작업 관리", key=f"btn_{idx}"):
                st.info(f"'{row['공정']}' 공정의 세부 기록 기능을 준비 중입니다.")
else:
    st.info("현재 가동 중인 공정이 없습니다. 구글 시트 '현재생산중' 탭에 데이터를 입력해 주세요.")
