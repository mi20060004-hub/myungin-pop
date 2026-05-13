import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 페이지 설정 및 디자인 (기본 레이아웃 복구) ---
st.set_page_config(
    layout="wide", 
    page_title="명인제약 생산 시점 관리 시스템",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    [data-testid="stHeader"] { display: none; }
    .main-title {
        text-align: center; color: #1e3a8a; font-size: 32px; font-weight: 900;
        padding: 15px 0; border-bottom: 3px solid #1e3a8a; margin-bottom: 20px;
    }
    .stage-bar {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        color: white; padding: 10px 20px; border-radius: 8px;
        font-size: 18px; font-weight: 700; margin: 20px 0; width: 100%;
    }
    .machine-title {
        background: #f8fafc; padding: 2px; text-align: center; font-size: 11px; font-weight: 700;
        border-radius: 4px; margin-bottom: 8px; border: 1px solid #cbd5e1;
        min-height: 28px; display: flex; align-items: center; justify-content: center;
    }
    .status-bar { font-size: 10px; font-weight: 800; color: white; text-align: center; padding: 2px 0; border-radius: 3px; margin-bottom: 4px; }
    .bg-waiting { background-color: #3b82f6; } .bg-progress { background-color: #ef4444; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 인증 및 시트 연결 ---
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

# --- 3. 설정 데이터 ---
machine_map = {
    "과립": ["P100", "KM100", "SM100", "P400", "GS400", "SM600", "글라트유동층", "GPCG2", "구형과립기", "롤러컴팩터"],
    "건조": ["트레이1호", "트레이2호", "트레이3호", "트레이4호", "트레이5호", "트레이6호", "트레이7호", "다산유동층", "D600"],
    "정립": ["Comil0112", "Comil0212", "Comil0312", "파워밀", "오실레이터"],
    "혼합": ["드럼혼합기", "PM1000", "PM2000"],
    "타정": ["킬리안", "63S-1", "41S", "63S-3", "PR1023", "MRC45", "MRC45S", "63S-2", "31S", "PH300"],
    "캡슐": ["SF150", "보쉬충전기", "PTK충전기", "SF35"],
    "코팅": ["SFC150FH", "SFC170FH", "SFC170FSH", "SFC130FSH", "V150", "SFC80"]
}
STAGES = list(machine_map.keys())

def get_now_kst():
    return (datetime.now(timezone(timedelta(hours=9)))).strftime('%Y-%m-%d KST %H:%M:%S')

def load_data():
    m_values = master_sheet.get_all_values()
    master_dict = {str(r[0]).strip(): {s: [m.strip() for m in str(val).split(',') if m.strip()] 
                   for s, val in zip(STAGES, r[3:10])} for r in m_values[1:] if r and r[0]}
    c_values = worksheet.get_all_values()
    curr_df = pd.DataFrame([{'Lot':r[0],'제품':r[1],'공정':r[2],'상태':r[3],'Row':i+2, '설비':r[9] if len(r)>9 else ""} 
                            for i,r in enumerate(c_values[1:]) if r and r[0]])
    return master_dict, curr_df

master_dict, curr_df = load_data()

# --- 4. 메인 화면 ---
st.markdown('<div class="main-title">🏭 명인제약 생산 시점 관리 시스템</div>', unsafe_allow_html=True)

# 사이드바: 제조 투입 (초기 버전)
with st.sidebar:
    st.header("📋 제조 투입")
    sel_p = st.selectbox("제품명 선택", list(master_dict.keys()) if master_dict else ["데이터 없음"])
    lot_in = st.text_input("제조번호(Lot) 입력")
    if st.button("🚀 즉시 투입", use_container_width=True, type="primary"):
        if lot_in.strip():
            f_stg = next((s for s in STAGES if master_dict.get(sel_p, {}).get(s)), "과립")
            f_m = master_dict[sel_p][f_stg][0] if master_dict[sel_p][f_stg] else ""
            worksheet.append_row([lot_in.strip(), sel_p, f_stg, "대기", "", get_now_kst(), "0", "일반", "", f_m])
            st.rerun()

# 메인 공정 화면
for stage in STAGES:
    st.markdown(f'<div class="stage-bar">▶ {stage} 공정</div>', unsafe_allow_html=True)
    cols = st.columns(10)
    for m_idx, machine in enumerate(machine_map[stage]):
        with cols[m_idx]:
            st.markdown(f"<div class='machine-title'>{machine}</div>", unsafe_allow_html=True)
            m_items = curr_df[(curr_df['공정'] == stage) & (curr_df['설비'] == machine)] if not curr_df.empty else pd.DataFrame()
            for _, row in m_items.iterrows():
                with st.container(border=True):
                    st.markdown(f"<div style='font-size:11px; font-weight:800; text-align:center;'>{row['제품']}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size:11px; font-weight:900; color:#1e40af; text-align:center;'>{row['Lot']}</div>", unsafe_allow_html=True)
                    cls = "bg-waiting" if row['상태'] == '대기' else "bg-progress"
                    st.markdown(f"<div class='status-bar {cls}'>{row['상태']}</div>", unsafe_allow_html=True)
                    
                    if st.button("시작" if row['상태']=='대기' else "완료", key=f"b_{row['Lot']}"):
                        if row['상태'] == '대기':
                            worksheet.update_cell(row['Row'], 4, "진행중")
                            worksheet.update_cell(row['Row'], 5, get_now_kst())
                        else:
                            # 다음 공정 자동 이동 로직
                            n_idx = STAGES.index(stage) + 1
                            next_stg = next((STAGES[i] for i in range(n_idx, len(STAGES)) if master_dict.get(row['제품'], {}).get(STAGES[i])), None)
                            if next_stg:
                                worksheet.update_cell(row['Row'], 3, next_stg)
                                worksheet.update_cell(row['Row'], 4, "대기")
                                worksheet.update_cell(row['Row'], 10, master_dict[row['제품']][next_stg][0])
                            else:
                                log_sheet.append_row([row['Lot'], row['제품'], "생산완료", "", get_now_kst()])
                                worksheet.delete_rows(row['Row'])
                        st.rerun()
