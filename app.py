import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 페이지 설정 ---
st.set_page_config(layout="wide", page_title="명인제약 생산 시점 관리")

# --- 2. CSS 스타일 (고정 헤더 및 설비 카드 디자인) ---
st.markdown("""
    <style>
    .fixed-header {
        position: fixed; top: 0; left: 0; right: 0; height: 100px;
        background-color: #1e3a8a; z-index: 999998;
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    .main-title-text {
        color: white !important; font-size: 42px !important; font-weight: 900; margin: 0;
    }
    .main .block-container { padding-top: 130px !important; }
    .stage-bar {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        color: white; padding: 12px 20px; border-radius: 8px;
        font-size: 22px; font-weight: 700; margin-top: 30px; margin-bottom: 15px;
    }
    .machine-title {
        background: #f1f5f9; text-align: center; font-size: 13px; font-weight: 700;
        border-radius: 4px; margin-bottom: 8px; border: 1px solid #cbd5e1; min-height: 35px;
        display: flex; align-items: center; justify-content: center; color: #334155;
    }
    .status-bar { font-size: 11px; font-weight: 800; color: white; text-align: center; padding: 3px 0; border-radius: 3px; margin-bottom: 5px; }
    .bg-waiting { background-color: #3b82f6; } 
    .bg-progress { background-color: #ef4444; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 인증 및 시트 연결 ---
def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

gc = get_gspread_client()
SHEET_ID = "1yZGPeS_HSTo7xjXJym7yv2-kjx9m06Ob6d81tVGV7G8" 
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.worksheet('현재생산중')
log_sheet = sh.worksheet('공정이력')
master_sheet = sh.worksheet('제품마스터')

# --- 4. 공정 및 설비 매핑 데이터 ---
MACHINE_MAP = {
    "과립공정": ["P100", "SM100", "P400", "GS400", "SM600", "KM10", "글라트유동층", "GPCG2", "구형과립기", "롤러컴팩터"],
    "건조공정": ["트레이1호", "트레이2호", "트레이3호", "트레이4호", "트레이5호", "트레이6호", "트레이7호", "다산유동층", "D600"],
    "정립공정": ["Comil0112", "코밀0212", "코밀0312", "파워밀"],
    "혼합공정": ["PM1000", "PM2000", "드럼혼합기"],
    "타정공정": ["킬리안", "63S-3", "41S", "63S-1", "PR1023", "MRC45", "45S", "63S-2", "31S", "PH300"],
    "캡슐공정": ["SF150N", "보쉬충전기", "PTK충전기", "SF35"],
    "질량선별공정": ["CWI150"],
    "코팅공정": ["SFC150FH", "SFC170FH", "SFC170FSH", "SFC130FSH", "V150", "SFC80", "수동코팅기"],
    "인쇄공정": ["정제인쇄기"],
    "외관선별공정": ["비즈윌구형", "비즈윌신형", "엔클로니구형", "엔클로니신형", "수동선별기", "캡슐외관선별기"]
}
TARGET_STAGES = list(MACHINE_MAP.keys())

def get_now_kst():
    return (datetime.now(timezone(timedelta(hours=9)))).strftime('%Y-%m-%d %H:%M:%S')

def load_data():
    m_values = master_sheet.get_all_values()
    if not m_values: return {}, pd.DataFrame()
    header = [h.strip() for h in m_values[0]]
    col_map = {stage: header.index(stage) if stage in header else -1 for stage in TARGET_STAGES}

    master_dict = {}
    for r in m_values[1:]:
        if not r or not r[0]: continue 
        p_name = str(r[0]).strip()
        master_dict[p_name] = {s: [m.strip() for m in str(r[col_map[s]]).split(',') if m.strip()] if col_map[s] != -1 and len(r) > col_map[s] else [] for s in TARGET_STAGES}

    c_values = worksheet.get_all_values()
    curr_df = pd.DataFrame([
        {'Lot':r[0],'제품':r[1],'공정':r[2],'상태':r[3],'Row':i+2, '설비':r[9] if len(r)>9 else ""} 
        for i,r in enumerate(c_values[1:]) if r and r[0]
    ])
    return master_dict, curr_df

master_dict, curr_df = load_data()

# --- 5. 화면 렌더링 ---
if 'page' not in st.session_state: st.session_state.page = 'main'
st.markdown('<div class="fixed-header"><p class="main-title-text">명인제약 생산 시점 관리</p></div>', unsafe_allow_html=True)

# 버튼 절대 위치 (제목 우측)
st.markdown('<div style="position: fixed; top: 32px; left: 50%; margin-left: 320px; z-index: 999999;">', unsafe_allow_html=True)
if st.button("완료 이력 확인" if st.session_state.page == 'main' else "현황판 돌아가기"):
    st.session_state.page = 'history' if st.session_state.page == 'main' else 'main'
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# --- 6. 사이드바 ---
with st.sidebar:
    st.header("🏭 제조 투입")
    sel_p = st.selectbox("제품명 선택", list(master_dict.keys()))
    lot_in = st.text_input("제조번호(Lot) 입력")
    if st.button("🚀 투입 확정", use_container_width=True):
        if lot_in and sel_p:
            f_stg = next((s for s in TARGET_STAGES if master_dict[sel_p][s]), TARGET_STAGES[0])
            f_m = master_dict[sel_p][f_stg][0] if master_dict[sel_p][f_stg] else ""
            worksheet.append_row([lot_in, sel_p, f_stg, "대기", "", get_now_kst(), "0", "일반", "", f_m])
            st.rerun()

# --- 7. 메인 현황판 ---
if st.session_state.page == 'main':
    for stage in TARGET_STAGES:
        st.markdown(f'<div class="stage-bar">▶ {stage}</div>', unsafe_allow_html=True)
        cols = st.columns(len(MACHINE_MAP[stage]) if len(MACHINE_MAP[stage]) < 10 else 10)
        for idx, machine in enumerate(MACHINE_MAP[stage]):
            with cols[idx % 10]:
                st.markdown(f"<div class='machine-title'>{machine}</div>", unsafe_allow_html=True)
                m_items = curr_df[(curr_df['공정'] == stage) & (curr_df['설비'] == machine)]
                if m_items.empty:
                    st.markdown("<div style='text-align:center; color:#cbd5e1; font-size:12px;'>-</div>", unsafe_allow_html=True)
                else:
                    for _, row in m_items.iterrows():
                        with st.container(border=True):
                            st.markdown(f"<p style='font-size:12px; font-weight:800; margin:0; text-align:center;'>{row['제품']}</p>", unsafe_allow_html=True)
                            st.markdown(f"<p style='font-size:11px; color:#1e40af; font-weight:700; text-align:center;'>{row['Lot']}</p>", unsafe_allow_html=True)
                            cls = "bg-waiting" if row['상태'] == '대기' else "bg-progress"
                            st.markdown(f"<div class='status-bar {cls}'>{row['상태']}</div>", unsafe_allow_html=True)
                            
                            if row['상태'] == '대기':
                                if st.button("시작", key=f"s_{row['Lot']}_{stage}_{machine}"):
                                    worksheet.update_cell(row['Row'], 4, "진행중")
                                    worksheet.update_cell(row['Row'], 5, get_now_kst())
                                    st.rerun()
                            else:
                                if st.button("완료", key=f"e_{row['Lot']}_{stage}_{machine}"):
                                    # 다음 공정 찾기 로직
                                    n_idx = TARGET_STAGES.index(stage) + 1
                                    next_stg = next((TARGET_STAGES[i] for i in range(n_idx, len(TARGET_STAGES)) if master_dict[row['제품']][TARGET_STAGES[i]]), None)
                                    if next_stg:
                                        worksheet.update_cell(row['Row'], 3, next_stg)
                                        worksheet.update_cell(row['Row'], 4, "대기")
                                        worksheet.update_cell(row['Row'], 5, "")
                                        worksheet.update_cell(row['Row'], 10, master_dict[row['제품']][next_stg][0])
                                    else:
                                        log_sheet.append_row([row['Lot'], row['제품'], "생산완료", "", get_now_kst()])
                                        worksheet.delete_rows(row['Row'])
                                    st.rerun()
else:
    st.header("📋 공정 완료 이력")
    st.dataframe(pd.DataFrame(log_sheet.get_all_values()), use_container_width=True)
