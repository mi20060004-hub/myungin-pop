import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 페이지 설정 ---
st.set_page_config(layout="wide", page_title="명인제약 생산 시점 관리")

# --- 2. CSS 스타일 (헤더 높이 66px로 축소 및 폰트 조정) ---
st.markdown("""
    <style>
    .fixed-header {
        position: fixed; top: 0; left: 0; right: 0; height: 66px;
        background-color: #1e3a8a; z-index: 999998;
        display: flex; align-items: center; padding: 0 30px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }
    .header-title {
        color: white !important; font-size: 24px !important; font-weight: 800; margin: 0;
        flex-grow: 1;
    }
    .main .block-container { padding-top: 90px !important; }
    
    /* 공정 바 스타일 */
    .stage-bar {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        color: white; padding: 10px 20px; border-radius: 8px;
        font-size: 20px; font-weight: 700; margin-top: 20px; margin-bottom: 10px;
    }
    
    .machine-title {
        background: #f1f5f9; text-align: center; font-size: 11px; font-weight: 700;
        border-radius: 4px; margin-bottom: 8px; border: 1px solid #cbd5e1; min-height: 35px;
        display: flex; align-items: center; justify-content: center; color: #334155;
    }
    
    .status-bar { font-size: 10px; font-weight: 800; color: white; text-align: center; padding: 3px 0; border-radius: 3px; margin-bottom: 5px; }
    .bg-waiting { background-color: #3b82f6; } 
    .bg-progress { background-color: #ef4444; }
    .bg-paused { background-color: #f59e0b; }

    .card-text-10px { font-size: 10px !important; font-weight: 800; margin: 0; text-align: center; line-height: 1.2; }
    .card-text-l-10px { font-size: 10px !important; color: #1e40af; font-weight: 700; text-align: center; margin: 0; line-height: 1.2; }
    .info-text-10px { font-size: 10px !important; color: #475569; margin: 1px 0; text-align: center; line-height: 1.2; }

    div.stButton > button {
        padding: 2px 4px !important;
        font-size: 10px !important;
        min-height: 20px !important;
    }
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

# --- 4. 공정 매핑 ---
MACHINE_MAP = {
    "과립공정": ["P100", "SM100", "P400", "GS400", "SM600", "KM10", "글라트유동층", "GPCG2", "구형과립기", "롤러컴팩터"],
    "건조공정": ["트레이1호", "트레이2호", "트레이3호", "트레이4호", "트레이5호", "트레이6호", "트레이7호", "다산유동층", "D600"],
    "정립공정": ["Comil0112", "Comil0212", "Comil0312", "파워밀"],
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
    # 현재생산중 구조: Lot(0), 제품(1), 공정(2), 상태(3), 시작(4), 종료(5), 최초시작(6), 인쇄종료(7), 유형(8), 특이사항(9), 설비(10)
    curr_df = pd.DataFrame([{'Lot':r[0],'제품':r[1],'공정':r[2],'상태':r[3],'최초시작':r[6],'인쇄종료':r[7],'유형':r[8],'특이사항':r[9],'Row':i+2, '설비':str(r[10]).strip() if len(r)>10 else ""} for i,r in enumerate(c_values[1:]) if r and len(r) > 1])
    
    l_values = log_sheet.get_all_values()
    log_df = pd.DataFrame([{'Lot': r[0], '제품': r[1]} for r in l_values[1:] if r and len(r) > 1]) if len(l_values) > 1 else pd.DataFrame(columns=['Lot', '제품'])
    
    return master_dict, curr_df, log_df

master_dict, curr_df, log_df = load_data()

# --- 5. 화면 렌더링 ---
if 'page' not in st.session_state: st.session_state.page = 'main'
if 'pending_lots' not in st.session_state: st.session_state.pending_lots = []

# 슬림 헤더
st.markdown(f"""
    <div class="fixed-header">
        <div class="header-title">명인제약 생산 시점 관리</div>
    </div>
    """, unsafe_allow_html=True)

# 헤더 위 버튼 (절대 위치)
st.markdown('<div style="position: fixed; top: 18px; right: 30px; z-index: 999999;">', unsafe_allow_html=True)
if st.button("완료된 공정 확인" if st.session_state.page == 'main' else "현황판 돌아가기", key="nav_btn"):
    st.session_state.page = 'history' if st.session_state.page == 'main' else 'main'
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# --- 6. 사이드바 ---
with st.sidebar:
    st.header("🏭 제조 투입")
    sel_p = st.selectbox("제품명 선택", list(master_dict.keys()), key="sel_p_w")
    lot_in = st.text_input("제조번호(Lot) 입력", key="lot_in_w").strip()
    lot_type = st.selectbox("로트 유형 선택", ["일반로트", "동시PV1", "동시PV2", "동시PV3", "예측PV1", "예측PV2", "예측PV3"], key="type_w")
    note_in = st.text_area("공정 특이사항 입력", key="note_w")
    
    is_dup = ((curr_df['제품'] == sel_p) & (curr_df['Lot'] == lot_in)).any() or ((log_df['제품'] == sel_p) & (log_df['Lot'] == lot_in)).any() or any(p['제품'] == sel_p and p['Lot'] == lot_in for p in st.session_state.pending_lots)

    f_stg = next((s for s in TARGET_STAGES if master_dict[sel_p][s]), TARGET_STAGES[0])
    f_ms = master_dict[sel_p][f_stg]
    
    if lot_in and is_dup:
        st.error("⚠️ 중복 데이터")
    else:
        if len(f_ms) > 1:
            with st.popover("➕ 대기열 추가 (설비 선택)", use_container_width=True):
                for m in f_ms:
                    if st.button(m, key=f"in_{m}"):
                        st.session_state.pending_lots.append({'제품': sel_p, 'Lot': lot_in, '유형': lot_type, '비고': note_in, '설비': m})
                        st.session_state.lot_in_w = ""; st.session_state.note_w = ""; st.rerun()
        else:
            if st.button("➕ 투입 대기열 추가", use_container_width=True):
                if lot_in:
                    st.session_state.pending_lots.append({'제품': sel_p, 'Lot': lot_in, '유형': lot_type, '비고': note_in, '설비': f_ms[0] if f_ms else ""})
                    st.session_state.lot_in_w = ""; st.session_state.note_w = ""; st.rerun()

    if st.session_state.pending_lots:
        st.write("---")
        if st.button("🚀 전체 투입 확정", type="primary", use_container_width=True):
            for p in st.session_state.pending_lots:
                f_s = next((s for s in TARGET_STAGES if master_dict[p['제품']][s]), TARGET_STAGES[0])
                # 최초 투입 시: 제조번호(0), 제품(1), 공정(2), 상태(3), 시작(4), 종료(5), 최초시작(6), 인쇄종료(7), 유형(8), 비고(9), 설비(10)
                worksheet.append_row([p['Lot'], p['제품'], f_s, "대기", "", "", "", "", p['유형'], p['비고'], p['설비']])
            st.session_state.pending_lots = []
            st.rerun()

# --- 7. 메인 화면 ---
if st.session_state.page == 'main':
    for stage in TARGET_STAGES:
        st.markdown(f'<div class="stage-bar">▶ {stage}</div>', unsafe_allow_html=True)
        cols = st.columns(10)
        for idx, machine in enumerate(MACHINE_MAP[stage]):
            with cols[idx]:
                st.markdown(f"<div class='machine-title'>{machine}</div>", unsafe_allow_html=True)
                m_items = curr_df[(curr_df['공정'] == stage) & (curr_df['설비'] == machine.strip())]
                for _, row in m_items.iterrows():
                    with st.container(border=True):
                        st.markdown(f"<p class='card-text-10px'>{row['제품']}</p>", unsafe_allow_html=True)
                        st.markdown(f"<p class='card-text-l-10px'>{row['Lot']}</p>", unsafe_allow_html=True)
                        st.markdown(f"<p class='info-text-10px'>{row['유형']}</p>", unsafe_allow_html=True)
                        if row['특이사항']: st.markdown(f"<p class='info-text-10px'>{row['특이사항']}</p>", unsafe_allow_html=True)
                        
                        status = row['상태']
                        cls = "bg-waiting" if status == '대기' else "bg-progress" if status == '진행중' else "bg-paused"
                        st.markdown(f"<div class='status-bar {cls}'>{status}</div>", unsafe_allow_html=True)
                        
                        if status == '대기':
                            if st.button("시작", key=f"s_{row['Lot']}_{stage}"):
                                worksheet.update_cell(row['Row'], 4, "진행중")
                                # [핵심] 과립공정(최초) 시작 시 7번째 열(Column G)에 시간 기록
                                if stage == "과립공정": worksheet.update_cell(row['Row'], 7, get_now_kst())
                                st.rerun()
                        elif status == '진행중':
                            c1, c2 = st.columns(2)
                            with c1: 
                                if st.button("대기", key=f"p_{row['Lot']}_{stage}"):
                                    worksheet.update_cell(row['Row'], 4, "일시정지"); st.rerun()
                            with c2:
                                n_idx = TARGET_STAGES.index(stage) + 1
                                next_stg = next((TARGET_STAGES[i] for i in range(n_idx, len(TARGET_STAGES)) if master_dict[row['제품']][TARGET_STAGES[i]]), None)
                                
                                if next_stg:
                                    n_ms = master_dict[row['제품']][next_stg]
                                    if len(n_ms) > 1:
                                        with st.popover("완료", use_container_width=True):
                                            for nm in n_ms:
                                                if st.button(nm, key=f"nx_{row['Lot']}_{nm}"):
                                                    # [핵심] 인쇄공정(9단계) 완료 시 8번째 열(Column H)에 종료시간 기록
                                                    if stage == "인쇄공정": worksheet.update_cell(row['Row'], 8, get_now_kst())
                                                    worksheet.update_cell(row['Row'], 3, next_stg)
                                                    worksheet.update_cell(row['Row'], 4, "대기")
                                                    worksheet.update_cell(row['Row'], 11, nm)
                                                    st.rerun()
                                    else:
                                        if st.button("완료", key=f"e_{row['Lot']}_{stage}"):
                                            if stage == "인쇄공정": worksheet.update_cell(row['Row'], 8, get_now_kst())
                                            worksheet.update_cell(row['Row'], 3, next_stg)
                                            worksheet.update_cell(row['Row'], 4, "대기")
                                            worksheet.update_cell(row['Row'], 11, n_ms[0] if n_ms else "")
                                            st.rerun()
                                else: # 외관선별공정(마지막) 완료
                                    if st.button("완료", key=f"f_{row['Lot']}_{stage}"):
                                        # [핵심] 공정이력으로 이동 (제조번호, 제품명, 공정, 시작시간, 완료시간, 소요시간, 유형, 비고)
                                        # 시간 계산
                                        start_t = datetime.strptime(row['최초시작'], '%Y-%m-%d %H:%M:%S')
                                        end_t = datetime.strptime(row['인쇄종료'], '%Y-%m-%d %H:%M:%S')
                                        duration = str(end_t - start_t).split('.')[0]
                                        
                                        log_sheet.append_row([row['Lot'], row['제품'], "생산완료", row['최초시작'], row['인쇄종료'], duration, row['유형'], row['특이사항']])
                                        worksheet.delete_rows(row['Row'])
                                        st.rerun()
                        elif status == '일시정지':
                            if st.button("재개", key=f"r_{row['Lot']}_{stage}"):
                                worksheet.update_cell(row['Row'], 4, "진행중"); st.rerun()
else:
    st.header("📋 공정 완료 이력")
    history_data = log_sheet.get_all_values()
    if len(history_data) > 1:
        st.dataframe(pd.DataFrame(history_data[1:], columns=history_data[0]), use_container_width=True)
    else:
        st.info("완료된 공정 이력이 없습니다.")
