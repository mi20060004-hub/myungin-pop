import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 페이지 설정 및 디자인 (Colab 스타일 100% 이식) ---
st.set_page_config(layout="wide", page_title="명인제약 생산 시점 관리 시스템")

# CSS 스타일 적용
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    [data-testid="stHeader"] { display: none; }
    .fixed-header {
        position: fixed; top: 0; left: 0; right: 0; height: 80px; background-color: white;
        display: flex; align-items: center; justify-content: space-between;
        padding: 0 40px; z-index: 999; border-bottom: 3px solid #1e293b;
    }
    .header-title { font-size: 28px !important; font-weight: 900; color: #1e293b; }
    .main-content { margin-top: 100px; }
    .machine-title {
        background: #f8fafc; padding: 2px; text-align: center; font-size: 11px; font-weight: 700;
        border-radius: 4px; margin-bottom: 8px; border: 2px solid #cbd5e1;
        min-height: 28px; display: flex; align-items: center; justify-content: center;
    }
    .status-bar { font-size: 10px; font-weight: 800; color: white; text-align: center; padding: 2px 0; border-radius: 3px; margin-bottom: 4px; }
    .bg-waiting { background-color: #3b82f6; } .bg-progress { background-color: #ef4444; } .bg-pause { background-color: #f59e0b; }
    .block-prod-name { font-size: 11px !important; font-weight: 800; color: #1e293b; text-align: center; }
    .block-batch-no { font-size: 11px !important; font-weight: 900; color: #1e40af; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 인증 및 시트 연결 로직 ---
def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    # Colab의 default() 대신 Streamlit Secrets 사용
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

gc = get_gspread_client()
try:
    sh = gc.open('생산관리_시스템')
except:
    sh = gc.open_by_key("1ST-zbOoIoP5MvWkoTCFNDvi76yavH8pu2Ak7kudyzBM")

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

# --- 4. 데이터 로딩 함수 ---
def get_now_kst():
    return (datetime.now(timezone(timedelta(hours=9)))).strftime('%Y-%m-%d KST %H:%M:%S')

def load_data():
    m_values = master_sheet.get_all_values()
    master_dict = {str(r[0]).strip(): {s: [m.strip() for m in str(val).split(',') if m.strip()] 
                   for s, val in zip(STAGES, r[3:10])} for r in m_values[1:] if r[0]}
    
    c_values = worksheet.get_all_values()
    curr_df = pd.DataFrame([{'Lot':r[0],'제품':r[1],'공정':r[2],'상태':r[3],'시작':r[4],'최초시작시간':r[5],'Row':i+2, '설비':r[9] if len(r)>9 else ""} 
                            for i,r in enumerate(c_values[1:]) if r and r[0]])
    return master_dict, curr_df

master_dict, curr_df = load_data()

# --- 5. 세션 상태 관리 ---
if 'page' not in st.session_state: st.session_state.page = 'main'
if 'pending_lots' not in st.session_state: st.session_state.pending_lots = []

# --- 6. UI 레이아웃 및 로직 ---
st.markdown('<div class="fixed-header"><div class="header-title">🏭 명인제약 생산 시점 관리 시스템</div></div>', unsafe_allow_html=True)
st.markdown('<div class="main-content">', unsafe_allow_html=True)

# 페이지 전환 버튼 (고정 위치 스타일)
if st.button("📊 이력 확인" if st.session_state.page == 'main' else "⬅️ 현황판", type="primary"):
    st.session_state.page = 'history' if st.session_state.page == 'main' else 'main'
    st.rerun()

if st.session_state.page == 'main':
    # 사이드바: 신규 투입
    with st.sidebar:
        st.header("🆕 로트 신규 투입")
        sel_p = st.selectbox("제품명 선택", list(master_dict.keys()))
        lot_in = st.text_input("제조번호 입력")
        if st.button("➕ 대기열 추가"):
            if lot_in:
                st.session_state.pending_lots.append({'제품': sel_p, 'Lot': lot_in, '유형': '일반로트', '비고': ''})
                st.rerun()
        
        # 대기열 및 투입 로직
        if st.session_state.pending_lots:
            if st.button("🚀 전체 투입"):
                for p in st.session_state.pending_lots:
                    f_stg = next((s for s in STAGES if master_dict[p['제품']][s]), "과립")
                    m = master_dict[p['제품']][f_stg][0]
                    worksheet.append_row([p['Lot'], p['제품'], f_stg, "대기", "", get_now_kst(), "0", p['유형'], p['비고'], m])
                st.session_state.pending_lots = []
                st.rerun()

    # 메인 현황판 (10열 설비 배치)
    for stage in STAGES:
        st.subheader(f"🔹 {stage}")
        cols = st.columns(10)
        for m_idx, machine in enumerate(machine_map[stage]):
            with cols[m_idx]:
                st.markdown(f"<div class='machine-title'>{machine}</div>", unsafe_allow_html=True)
                m_items = curr_df[(curr_df['공정'] == stage) & (curr_df['설비'] == machine)]
                for _, row in m_items.iterrows():
                    with st.container(border=True):
                        st.markdown(f"<div class='block-prod-name'>{row['제품']}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='block-batch-no'>{row['Lot']}</div>", unsafe_allow_html=True)
                        cls = "bg-waiting" if row['상태'] == '대기' else "bg-progress"
                        st.markdown(f"<div class='status-bar {cls}'>{row['상태']}</div>", unsafe_allow_html=True)
                        
                        if row['상태'] == '대기':
                            if st.button("시작", key=f"s_{row['Lot']}"):
                                worksheet.update_cell(row['Row'], 4, "진행중")
                                worksheet.update_cell(row['Row'], 5, get_now_kst())
                                st.rerun()
                        elif row['상태'] == '진행중':
                            if st.button("완료", key=f"e_{row['Lot']}"):
                                # 다음 공정 이동 또는 완료 로직
                                n_idx = STAGES.index(stage) + 1
                                next_stg = next((STAGES[i] for i in range(n_idx, len(STAGES)) if master_dict[row['제품']][STAGES[i]]), None)
                                if next_stg:
                                    worksheet.update_cell(row['Row'], 3, next_stg)
                                    worksheet.update_cell(row['Row'], 4, "대기")
                                    worksheet.update_cell(row['Row'], 10, master_dict[row['제품']][next_stg][0])
                                else:
                                    log_sheet.append_row([row['Lot'], row['제품'], "생산완료", row['최초시작시간'], get_now_kst()])
                                    worksheet.delete_rows(row['Row'])
                                st.rerun()
else:
    # 이력 페이지
    st.header("📋 공정 이력")
    log_data = log_sheet.get_all_values()
    if len(log_data) > 1:
        st.dataframe(pd.DataFrame(log_data[1:], columns=log_data[0]), use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)
