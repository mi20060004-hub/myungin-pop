import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 페이지 설정 ---
st.set_page_config(layout="wide", page_title="명인제약 생산 시점 관리")

# --- 2. CSS 스타일 (해상도 적응형 블루 헤더 & 10단계 공정 최적화) ---
st.markdown("""
    <style>
    .fixed-header {
        position: fixed; top: 0; left: 0; right: 0; height: 100px;
        background-color: #1e3a8a; z-index: 999998;
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    .header-content {
        display: flex; align-items: center; justify-content: center;
        width: 100%; max-width: 1200px; gap: 40px;
    }
    .main-title-text {
        color: white !important; font-size: 44px !important; font-weight: 900;
        margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    .main .block-container { padding-top: 130px !important; }
    .stage-bar {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        color: white; padding: 12px 20px; border-radius: 8px;
        font-size: 22px; font-weight: 700; margin-top: 30px; margin-bottom: 20px;
    }
    .machine-title {
        background: #f8fafc; text-align: center; font-size: 12px; font-weight: 700;
        border-radius: 4px; margin-bottom: 8px; border: 1px solid #cbd5e1; min-height: 32px;
        display: flex; align-items: center; justify-content: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 인증 및 시트 연결 (캐시 없이 실시간 로드) ---
def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

gc = get_gspread_client()
# 파일명을 다시 "생산관리_시스템"으로 인식하도록 ID 설정
SHEET_ID = "1yZGPeS_HSTo7xjXJym7yv2-kjx9m06Ob6d81tVGV7G8" 
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.worksheet('현재생산중')
log_sheet = sh.worksheet('공정이력')
master_sheet = sh.worksheet('제품마스터')

# --- 4. 데이터 로드 (확장된 10개 공정) ---
def get_now_kst():
    return (datetime.now(timezone(timedelta(hours=9)))).strftime('%Y-%m-%d %H:%M:%S')

# 사용자님이 설정한 10개 공정명
TARGET_STAGES = ["과립공정", "건조공정", "정립공정", "혼합공정", "타정공정", "캡슐공정", "질량선별공정", "코팅공정", "인쇄공정", "외관선별공정"]

def load_data():
    m_values = master_sheet.get_all_values()
    if not m_values: return {}, pd.DataFrame()
    
    header = [h.strip() for h in m_values[0]]
    col_map = {stage: header.index(stage) if stage in header else -1 for stage in TARGET_STAGES}

    master_dict = {}
    for r in m_values[1:]:
        if not r or not r[0]: continue 
        p_name = str(r[0]).strip() # A열에서 제품명 로드
        master_dict[p_name] = {}
        for stage in TARGET_STAGES:
            idx = col_map[stage]
            master_dict[p_name][stage] = [m.strip() for m in str(r[idx]).split(',') if m.strip()] if idx != -1 and len(r) > idx else []

    c_values = worksheet.get_all_values()
    curr_df = pd.DataFrame([{'Lot':r[0],'제품':r[1],'공정':r[2],'상태':r[3]} for r in c_values[1:] if r and r[0]])
    return master_dict, curr_df

master_dict, curr_df = load_data()

# --- 5. 상단 헤더 렌더링 ---
if 'page' not in st.session_state: st.session_state.page = 'main'
st.markdown('<div class="fixed-header"><div class="header-content"><p class="main-title-text">명인제약 생산 시점 관리</p></div></div>', unsafe_allow_html=True)

# 버튼 절대 위치 고정 (제목 우측)
st.markdown('<div style="position: fixed; top: 32px; left: 50%; margin-left: 280px; z-index: 999999;">', unsafe_allow_html=True)
btn_label = "현황판 돌아가기" if st.session_state.page == 'history' else "완료 이력 확인"
if st.button(btn_label, key="nav_btn"):
    st.session_state.page = 'history' if st.session_state.page == 'main' else 'main'
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# --- 6. 사이드바 (제조 투입) ---
with st.sidebar:
    st.header("🏭 제조 투입")
    st.divider()
    p_list = list(master_dict.keys())
    sel_p = st.selectbox("제품명 선택", p_list if p_list else ["데이터 로드 중..."])
    lot_in = st.text_input("제조번호(Lot) 입력")
    if st.button("🚀 투입 확정", use_container_width=True):
        if lot_in and sel_p:
            # 첫 번째 유효 공정 찾기
            f_stg = next((s for s in TARGET_STAGES if master_dict[sel_p][s]), TARGET_STAGES[0])
            f_m = master_dict[sel_p][f_stg][0] if master_dict[sel_p][f_stg] else ""
            worksheet.append_row([lot_in, sel_p, f_stg, "대기", "", get_now_kst(), "0", "일반", "", f_m])
            st.success(f"{sel_p} 투입 완료")
            st.rerun()

# --- 7. 메인 현황판 ---
if st.session_state.page == 'main':
    for stage in TARGET_STAGES:
        st.markdown(f'<div class="stage-bar">▶ {stage}</div>', unsafe_allow_html=True)
        # 설비별 버튼 렌더링 로직 (나중에 설비 목록 주시면 이 부분을 더 구체화해 드릴게요!)
        st.caption(f"{stage}의 상세 설비 현황을 준비 중입니다.")
else:
    st.header("📋 공정 완료 이력")
    st.dataframe(pd.DataFrame(log_sheet.get_all_values()[1:]), use_container_width=True)
