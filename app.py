import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 페이지 설정 ---
st.set_page_config(layout="wide", page_title="명인제약 생산 시점 관리")

# --- 2. CSS 스타일 ---
st.markdown("""
    <style>
    .fixed-header {
        position: fixed; top: 0; left: 0; right: 0; height: 100px;
        background-color: #1e3a8a; z-index: 999998;
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    .main-title-text { color: white !important; font-size: 42px !important; font-weight: 900; margin: 0; }
    .main .block-container { padding-top: 130px !important; }
    .stage-bar {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        color: white; padding: 12px 20px; border-radius: 8px;
        font-size: 22px; font-weight: 700; margin-top: 30px; margin-bottom: 15px;
    }
    .machine-title {
        background: #f1f5f9; text-align: center; font-size: 11px; font-weight: 700;
        border-radius: 4px; margin-bottom: 8px; border: 1px solid #cbd5e1; min-height: 35px;
        display: flex; align-items: center; justify-content: center; color: #334155;
    }
    .status-bar { font-size: 10px; font-weight: 800; color: white; text-align: center; padding: 3px 0; border-radius: 3px; margin-bottom: 5px; }
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

# --- 4. 공정 및 설비 매핑 (영문명 통일 완료) ---
MACHINE_MAP = {
    "과립공정": ["P100", "SM100", "P400", "GS400", "SM600", "KM10", "글라트유동층", "GPCG2", "구형과립기", "롤러컴팩터"],
    "건조공정": ["트레이1호", "트레이2호", "트레이3호", "트레이4호", "트레이5호", "트레이6호", "트레이7호", "다산유동층", "D600"],
    "정립공정": ["Comil0112", "Comil0212", "Comil0312", "파워밀"], # 코밀 -> Comil로 수정
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
    header = [h.strip() for h in m_values[0]]
    col_map = {stage: header.index(stage) if stage in header else -1 for stage in TARGET_STAGES}
    master_dict = {str(r[0]).strip(): {s: [m.strip() for m in str(r[col_map[s]]).split(',') if m.strip()] for s in TARGET_STAGES} for r in m_values[1:] if r and r[0]}
    
    c_values = worksheet.get_all_values()
    curr_df = pd.DataFrame([{'Lot':r[0],'제품':r[1],'공정':r[2],'상태':r[3],'유형':r[7],'특이사항':r[8],'Row':i+2, '설비':str(r[9]).strip() if len(r)>9 else ""} for i,r in enumerate(c_values[1:]) if r and len(r) > 1])
    
    l_values = log_sheet.get_all_values()
    log_df = pd.DataFrame([{'Lot': r[0], '제품': r[1]} for r in l_values[1:] if r and len(r) > 1]) if len(l_values) > 1 else pd.DataFrame(columns=['Lot', '제품'])
    
    return master_dict, curr_df, log_df

master_dict, curr_df, log_df = load_data()

# --- 5. 세션 상태 ---
if 'pending_lots' not in st.session_state: st.session_state.pending_lots = []

# --- 6. 헤더 ---
st.markdown('<div class="fixed-header"><p class="main-title-text">명인제약 생산 시점 관리</p></div>', unsafe_allow_html=True)

# --- 7. 사이드바 ---
with st.sidebar:
    st.header("🏭 제조 투입")
    sel_p = st.selectbox("제품명 선택", list(master_dict.keys()))
    lot_in = st.text_input("제조번호(Lot) 입력").strip()
    lot_type = st.selectbox("로트 유형 선택", ["일반로트", "동시PV1", "동시PV2", "동시PV3", "예측PV1", "예측PV2", "예측PV3"])
    note_in = st.text_area("공정 특이사항 입력")
    
    is_duplicate = False
    if lot_in:
        is_duplicate = ((curr_df['제품'] == sel_p) & (curr_df['Lot'] == lot_in)).any() or ((log_df['제품'] == sel_p) & (log_df['Lot'] == lot_in)).any() or any(p['제품'] == sel_p and p['Lot'] == lot_in for p in st.session_state.pending_lots)

    f_stg = next((s for s in TARGET_STAGES if master_dict[sel_p][s]), TARGET_STAGES[0])
    f_machines = master_dict[sel_p][f_stg]
    
    if lot_in and is_duplicate:
        st.error(f"⚠️ {sel_p} ({lot_in}) 중복")
    elif lot_in:
        if len(f_machines) > 1:
            with st.popover("➕ 대기열 추가 (설비 선택)", use_container_width=True):
                for m in f_machines:
                    if st.button(m, key=f"init_{m}"):
                        st.session_state.pending_lots.append({'제품': sel_p, 'Lot': lot_in, '유형': lot_type, '비고': note_in, '설비': m})
                        st.rerun()
        else:
            if st.button("➕ 투입 대기열 추가", use_container_width=True):
                st.session_state.pending_lots.append({'제품': sel_p, 'Lot': lot_in, '유형': lot_type, '비고': note_in, '설비': f_machines[0] if f_machines else ""})
                st.rerun()
            
    if st.session_state.pending_lots:
        st.write("---")
        for idx, p in enumerate(st.session_state.pending_lots):
            st.info(f"{idx+1}. {p['제품']} ({p['Lot']})")
        if st.button("🚀 전체 투입 확정", type="primary", use_container_width=True):
            for p in st.session_state.pending_lots:
                f_stg_p = next((s for s in TARGET_STAGES if master_dict[p['제품']][s]), TARGET_STAGES[0])
                worksheet.append_row([p['Lot'], p['제품'], f_stg_p, "대기", "", get_now_kst(), "0", p['유형'], p['비고'], p['설비']])
            st.session_state.pending_lots = []
            st.rerun()
        if st.button("🗑️ 비우기", use_container_width=True):
            st.session_state.pending_lots = []
            st.rerun()

    st.divider()
    st.write(f"**전체 총합:** {len(curr_df)}건")
    for stage in TARGET_STAGES:
        st.write(f"- {stage}: {len(curr_df[curr_df['공정'] == stage])}건")

# --- 8. 메인 현황판 (10열 고정) ---
for stage in TARGET_STAGES:
    st.markdown(f'<div class="stage-bar">▶ {stage}</div>', unsafe_allow_html=True)
    cols = st.columns(10)
    for idx, machine in enumerate(MACHINE_MAP[stage]):
        with cols[idx]:
            st.markdown(f"<div class='machine-title'>{machine}</div>", unsafe_allow_html=True)
            # 설비명 비교 시 공백 제거하여 매칭 확률 높임
            m_items = curr_df[(curr_df['공정'] == stage) & (curr_df['설비'] == machine.strip())]
            for _, row in m_items.iterrows():
                with st.container(border=True):
                    st.markdown(f"<p style='font-size:11px; font-weight:800; margin:0;'>{row['제품']}</p>", unsafe_allow_html=True)
                    st.markdown(f"<p style='font-size:10px; color:#1e40af;'>{row['Lot']}</p>", unsafe_allow_html=True)
                    cls = "bg-waiting" if row['상태'] == '대기' else "bg-progress"
                    st.markdown(f"<div class='status-bar {cls}'>{row['상태']}</div>", unsafe_allow_html=True)
                    
                    if row['상태'] == '대기':
                        if st.button("시작", key=f"s_{row['Lot']}_{stage}_{machine}"):
                            worksheet.update_cell(row['Row'], 4, "진행중")
                            worksheet.update_cell(row['Row'], 5, get_now_kst())
                            st.rerun()
                    else:
                        n_idx = TARGET_STAGES.index(stage) + 1
                        next_stg = next((TARGET_STAGES[i] for i in range(n_idx, len(TARGET_STAGES)) if master_dict[row['제품']][TARGET_STAGES[i]]), None)
                        if next_stg:
                            n_machines = master_dict[row['제품']][next_stg]
                            if len(n_machines) > 1:
                                with st.popover("완료", use_container_width=True):
                                    for nm in n_machines:
                                        if st.button(nm, key=f"nxt_{row['Lot']}_{nm}"):
                                            worksheet.update_cell(row['Row'], 3, next_stg)
                                            worksheet.update_cell(row['Row'], 4, "대기")
                                            worksheet.update_cell(row['Row'], 5, "")
                                            worksheet.update_cell(row['Row'], 10, nm)
                                            st.rerun()
                            else:
                                if st.button("완료", key=f"e_{row['Lot']}_{stage}_{machine}"):
                                    worksheet.update_cell(row['Row'], 3, next_stg)
                                    worksheet.update_cell(row['Row'], 4, "대기")
                                    worksheet.update_cell(row['Row'], 5, "")
                                    worksheet.update_cell(row['Row'], 10, n_machines[0] if n_machines else "")
                                    st.rerun()
                        else:
                            if st.button("완료", key=f"fin_{row['Lot']}_{stage}"):
                                log_sheet.append_row([row['Lot'], row['제품'], "생산완료", "", get_now_kst()])
                                worksheet.delete_rows(row['Row'])
                                st.rerun()
