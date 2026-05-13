import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 페이지 기본 설정 (Colab 스타일 테마) ---
st.set_page_config(layout="wide", page_title="명인제약 생산 관리 시스템")

# CSS: Colab에서 보던 깔끔한 블록 디자인 재현
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stApp { max-width: 1200px; margin: 0 auto; }
    .process-container {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        border-top: 5px solid #1E3A8A;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        transition: transform 0.2s;
    }
    .process-container:hover { transform: translateY(-5px); }
    .status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: bold;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 인증 및 구글 시트 연결 (Streamlit Cloud 전용) ---
def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    # Streamlit Secrets에 저장된 정보를 사용하여 인증
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

try:
    gc = get_gspread_client()
    # 사용자님의 고유 시트 ID
    SHEET_ID = "1ST-zbOoIoP5MvWkoTCFNDvi76yavH8pu2Ak7kudyzBM"
    sh = gc.open_by_key(SHEET_ID)
    worksheet = sh.worksheet('현재생산중')
except Exception as e:
    st.error(f"⚠️ 연결 오류: 시트 ID나 권한을 확인하세요. ({e})")
    st.stop()

# --- 3. 데이터 로드 및 전처리 ---
def load_data():
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    # 컬럼명의 앞뒤 공백을 제거하여 KeyError 방지
    df.columns = [c.strip() for c in df.columns]
    return df

df = load_data()

# --- 4. 메인 화면 구성 ---
st.title("🏭 명인제약 생산 시점 관리(POP) 시스템")
kst_now = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S')
st.write(f"⏱️ 현재 시간(KST): {kst_now}")
st.divider()

if not df.empty:
    # 3열 배치를 통해 Colab의 시각적 레이아웃 재현
    cols = st.columns(3)
    
    for idx, row in df.iterrows():
        # 상태에 따른 색상 정의
        status = str(row.get('상태', '대기')).strip()
        bg_color = "#6c757d" # 기본 회색
        if status == "진행중": bg_color = "#28a745" # 초록
        elif status == "대기": bg_color = "#ffc107" # 노랑
        elif status == "완료": bg_color = "#007bff" # 파랑

        with cols[idx % 3]:
            # HTML 카드로 공정 정보 표시
            st.markdown(f"""
                <div class="process-container">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <h2 style="margin:0; font-size: 22px; color: #1E3A8A;">{row.get('공정', '알 수 없음')}</h2>
                        <span class="status-badge" style="background-color: {bg_color};">{status}</span>
                    </div>
                    <p style="margin: 5px 0;"><b>📦 제품명:</b> {row.get('제품명', '-')}</p>
                    <p style="margin: 5px 0;"><b>🔢 제조번호:</b> {row.get('제조번호', '-')}</p>
                </div>
            """, unsafe_allow_html=True)
            
            # 작업 제어 버튼
            btn_label = "🏁 작업 종료" if status == "진행중" else "🚀 작업 시작"
            if st.button(btn_label, key=f"btn_{idx}", use_container_width=True):
                new_status = "완료" if status == "진행중" else "진행중"
                
                # 구글 시트 업데이트 (실제 데이터 반영)
                # '상태' 열이 D열(4번째)이라고 가정할 때의 로직
                row_idx = idx + 2 # 헤더(1) + 인덱스(0부터 시작)
                worksheet.update_cell(row_idx, 4, new_status) # 4번째 열(상태) 업데이트
                
                st.success(f"[{row.get('공정')}] 상태가 '{new_status}'(으)로 변경되었습니다!")
                st.rerun() # 화면 새로고침

else:
    st.warning("조회된 생산 데이터가 없습니다. 구글 시트를 확인해 주세요.")

# 하단 정보
st.sidebar.header("시스템 정보")
st.sidebar.info("본 시스템은 구글 시트와 실시간으로 동기화됩니다.")
if st.sidebar.button("🔄 강제 새로고침"):
    st.rerun()
