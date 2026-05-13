import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 인증 및 시트 연결 (시트 ID 방식) ---
def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    if "gcp_service_account" in st.secrets:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    else:
        st.error("❌ Streamlit Cloud의 Secrets 설정 확인 필요")
        st.stop()
    return gspread.authorize(creds)

gc = get_gspread_client()

# 사용자님의 정확한 시트 ID (주소창에서 추출함)
SHEET_ID = "1ST-zbOoIoP5MvWkoTCFNDvi76yavH8pu2Ak7kudyzBM"

try:
    sh = gc.open_by_key(SHEET_ID)
except Exception as e:
    st.error(f"❌ 시트 권한 에러: 서비스 계정 이메일이 시트에 '편집자'로 공유되었는지 확인하세요. ({e})")
    st.stop()

def get_ws(name):
    try: return sh.worksheet(name)
    except: return None

# 탭 이름은 띄어쓰기 없이 설정됨
worksheet = get_ws('현재생산중')
log_sheet = get_ws('공정이력')
master_sheet = get_ws('제품마스터')

if not worksheet:
    st.error("❌ '현재생산중' 탭을 찾을 수 없습니다. 구글 시트 하단 탭 이름을 '현재생산중'으로 수정하세요.")
    st.stop()

# --- 2. 유틸리티 함수 ---
def get_now_kst():
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst).strftime('%Y-%m-%d KST %H:%M:%S')

def parse_time(t_str):
    if not t_str: return None
    try: return datetime.strptime(t_str, '%Y-%m-%d KST %H:%M:%S')
    except: return None

# --- 3. 스타일 및 디자인 설정 (기존 레이아웃 유지) ---
st.set_page_config(layout="wide", page_title="명인제약 생산 시점 관리 시스템")

# (이하 사용자님의 기존 디자인 및 로직 코드가 이어집니다...)
st.title("🏭 명인제약 생산 현황판")
st.write(f"최종 업데이트: {get_now_kst()}")

# 샘플 데이터 출력 테스트
data = worksheet.get_all_records()
if data:
    st.table(pd.DataFrame(data))
else:
    st.info("현재 생산 중인 내역이 없습니다.")
