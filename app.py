import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 페이지 설정 ---
st.set_page_config(layout="wide", page_title="명인제약 생산 시점 관리")

# --- 2. CSS 스타일 (블록 너비 고정 및 디자인 유지) ---
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
    
    /* 공정 바 스타일 */
    .stage-bar {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        color: white; padding: 12px 20px; border-radius: 8px;
        font-size: 22px; font-weight: 700; margin-top: 30px; margin-bottom: 15px;
    }
    
    /* 설비 타이틀 스타일 (너비 최적화) */
    .machine-title {
        background: #f1f5f9; text-align: center; font-size: 11px; font-weight: 700;
        border-radius: 4px; margin-bottom: 8px; border: 1px solid #cbd5e1; min-height: 35px;
        display: flex; align-items: center; justify-content: center; color: #334155;
        overflow: hidden; text-overflow: ellipsis;
    }
    
    /* 상태 바 */
    .status-bar { font-size: 10px; font-weight: 800; color: white; text-align: center; padding: 3px 0; border-radius: 3px; margin-bottom: 5px; }
    .bg-waiting { background-color: #3b82f6; } 
    .bg-progress { background-color: #ef4444; }
    
    /* 제품 카드 내 텍스트 크기 미세 조정 */
    .card-text-p { font-size: 11px; font-weight: 800; margin: 0; text-align: center; }
    .card-text-l { font-size: 10px; color: #1e40af; font-weight: 700; text-align: center; }
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

# --- 4. 공정 및 설비 매핑 ---
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

# --- 5. 세션 상태 관리 ---
if 'page' not in st.session_state: st.session_state.page = 'main'
if 'pending_lots' not in st.session_state: st.session_state.pending_lots = []

# --- 6. 상단 헤더 ---
st.markdown('<div class="fixed-header"><p class="main-title-text">명인제약 생산 시점 관리</p></div>', unsafe_allow_html=True)

st.markdown('<div style="position: fixed; top: 32px; left: 50%; margin-left: 320px; z-index: 999999;">', unsafe_allow_html=True)
if st.button("완료 이력 확인" if st.session_state.page == 'main' else "현황판 돌아가기"):
    st.session_state.page = 'history' if st.session_state.page == 'main' else 'main'
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# --- 7. 사이드바 (다중 투입 및 실시간 통계) ---
with st.sidebar:
    st.header("🏭 제조 투입")
    st.divider()
    sel_p = st.selectbox("제품명 선택", list(master_dict.keys()))
    lot_in = st.text_input("제조번호(Lot) 입력")
    
    if st.button("➕ 투입 대기열에 추가", use_container_width=True):
        if lot_in and sel_p:
            st.session_state.pending_lots.append({'제품': sel_p, 'Lot': lot_in})
            st.rerun()
    
    if st.session_state.pending_lots:
        st.info(f"현재 {len(st.session_state.pending_lots)}건 대기 중")
        for idx, item in enumerate(st.session_state.pending_lots):
            st.caption(f"{idx+1}. {item['제품']} ({item['Lot']})")
        
        if st.button("🚀 전체 투입 확정", type="primary", use_container_width=True):
            for p in st.session_state.pending_lots:
                p_name = p['제품']
                f_stg = next((s for s in TARGET_STAGES if master_dict[p_name][s]), TARGET_STAGES[0])
                f_m = master_dict[p_name][f_stg][0] if master_dict[p_name][f_stg] else ""
                worksheet.append_row([p['Lot'], p_name, f_stg, "대기", "", get_now_kst(), "0", "일반", "", f_m])
            st.session_state.pending_lots = []
            st.rerun()
        
        if st.button("🗑️ 비우기", use_container_width=True):
            st.session_state.pending_lots = []
            st.rerun()

    st.divider()
    st.subheader("📊 실시간 현황 통계")
    total_count = len(curr_df)
    st.write(f"**전체 공정 총합:** {total_count}건")
    for stage in TARGET_STAGES:
        s_count = len(curr_df[curr_df['공정'] == stage])
        st.write(f"- {stage}: {s_count}건")

# --- 8. 메인 현황판 (10열 고정 레이아웃) ---
if st.session_state.page == 'main':
    for stage in TARGET_STAGES:
        st.markdown(f'<div class="stage-bar">▶ {stage}</div>', unsafe_allow_html=True)
        
        # [핵심 변경] 무조건 10개의 컬럼을 생성하여 너비를 고정합니다.
        cols = st.columns(10)
        
        machines = MACHINE_MAP[stage]
        for idx, machine in enumerate(machines):
            # 10개까지만 첫 줄에 배치 (초과 시 로직은 필요에 따라 확장 가능하나 현재 데이터는 모두 10개 이하)
            with cols[idx]:
                st.markdown(f"<div class='machine-title'>{machine}</div>", unsafe_allow_html=True)
                m_items = curr_df[(curr_df['공정'] == stage) & (curr_df['설비'] == machine)]
                
                if not m_items.empty:
                    for _, row in m_items.iterrows():
                        with st.container(border=True):
                            st.markdown(f"<p class='card-text-p'>{row['제품']}</p>", unsafe_allow_html=True)
                            st.markdown(f"<p class='card-text-l'>{row['Lot']}</p>", unsafe_allow_html=True)
                            cls = "bg-waiting" if row['상태'] == '대기' else "bg-progress"
                            st.markdown(f"<div class='status-bar {cls}'>{row['상태']}</div>", unsafe_allow_html=True)
                            
                            if row['상태'] == '대기':
                                if st.button("시작", key=f"s_{row['Lot']}_{stage}_{machine}"):
                                    worksheet.update_cell(row['Row'], 4, "진행중")
                                    worksheet.update_cell(row['Row'], 5, get_now_kst())
                                    st.rerun()
                            else:
                                if st.button("완료", key=f"e_{row['Lot']}_{stage}_{machine}"):
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
