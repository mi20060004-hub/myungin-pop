import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 페이지 설정 ---
st.set_page_config(layout="wide", page_title="명인제약 생산 시점 관리")

# --- 2. CSS 스타일 (공정바 높이 유지, 모든 공정바 색상을 블루 계열로 통일) ---
st.markdown("""
<style>
.fixed-header {position: fixed; top: 0; left: 0; right: 0; height: 66px; background-color: #1e3a8a; z-index: 999998; display: flex; align-items: center; padding: 0 30px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
.main-title-text {color: white !important; font-size: 28px !important; font-weight: 800; margin: 0; flex-grow: 1; }
.main .block-container { padding-top: 100px !important; }

/* 공정명 막대 높이 및 스타일 유지 */
.stage-bar {
    color: white; 
    padding: 8px 13px; 
    border-radius: 6px; 
    font-size: 18px; 
    font-weight: 700; 
    margin-top: 20px; 
    margin-bottom: 10px; 
}

/* 알록달록한 색상을 걷어내고 모두 신뢰감 있는 파란색(블루) 계열 그라디언트로 통일 */
.sb-0, .sb-1, .sb-2, .sb-3, .sb-4, .sb-5, .sb-6, .sb-7, .sb-8, .sb-9 { 
    background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%); 
}

.machine-title {background: #f1f5f9; text-align: center; font-size: 13px; font-weight: 700; border-radius: 4px; margin-bottom: 8px; border: 1px solid #cbd5e1; min-height: 35px; display: flex; align-items: center; justify-content: center; color: #334155; }
.status-bar { font-size: 10px; font-weight: 800; color: white; text-align: center; padding: 3px 0; border-radius: 3px; margin-bottom: 5px; }
.bg-waiting { background-color: #3b82f6; }
.bg-progress { background-color: #ef4444; }
.bg-paused { background-color: #f59e0b; }

.card-text-10px { font-size: 15px !important; font-weight: 800; margin: 0; text-align: center; line-height: 1.2; }
.card-text-l-10px { font-size: 15px !important; color: #1e40af; font-weight: 700; text-align: center; margin: 0; line-height: 1.2; }
.info-text-10px { font-size: 11px !important; color: #ef4444; margin: 1px 0; text-align: center; line-height: 1.2; }
.lot-type-highlight { font-size: 11px !important; color: #ef4444 !important; font-weight: 800 !important; text-align: center; margin: 1px 0; line-height: 1.2; }

/* 버튼 크기 및 폰트 80% 축소 입체감 스타일 유지 */
div.stButton > button {
    padding: 1.5px 3.2px !important; 
    font-size: 8px !important; 
    min-height: 16px !important; 
    line-height: 1.2 !important;
    border: 1px solid #94a3b8 !important;
    box-shadow: 0 2px 0px rgba(0,0,0,0.15) !important;
    border-radius: 4px !important;
    transition: all 0.1s ease;
}
div.stButton > button:active {
    transform: translateY(1px);
    box-shadow: 0 0px 0px rgba(0,0,0,0) !important;
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

history_sheet = sh.worksheet('product_history')
master_sheet = sh.worksheet('product_master')

# --- 4. 공정 및 설비 매핑 ---
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
    return (datetime.now(timezone(timedelta(hours=9)))).strftime('%Y-%m-%d %H:%M')

def load_data():
    m_values = master_sheet.get_all_values()
    header = [h.strip() for h in m_values[0]]
    col_map = {stage: header.index(stage) if stage in header else -1 for stage in TARGET_STAGES}
    master_dict = {str(r[0]).strip(): {s: [m.strip() for m in str(r[col_map[s]]).split(',') if m.strip()] for s in TARGET_STAGES} for r in m_values[1:] if r and r[0]}
    
    h_values = history_sheet.get_all_values()
    if len(h_values) <= 1:
        curr_df = pd.DataFrame(columns=['Lot', '제품', '공정', '상태', '시작시간', '종료시간', '소요시간', '유형', '특이사항', '설비', 'Row'])
        log_df = pd.DataFrame(columns=['Lot', '제품', '공정', '상태', '시작시간', '종료시간', '소요시간', '유형', '특이사항', '설비'])
    else:
        data_list = []
        for i, r in enumerate(h_values[1:]):
            if r and len(r) >= 4:
                data_list.append({
                    'Lot': str(r[0]).strip(), '제품': str(r[1]).strip(), '공정': str(r[2]).strip(), '상태': str(r[3]).strip(),
                    '시작시간': r[4] if len(r) > 4 else "", '종료시간': r[5] if len(r) > 5 else "", '소요시간': r[6] if len(r) > 6 else "",
                    '유형': r[7] if len(r) > 7 else "", '특이사항': r[8] if len(r) > 8 else "", '설비': str(r[9]).strip() if len(r) > 9 else "",
                    'Row': i + 2
                })
        all_df = pd.DataFrame(data_list)
        curr_df = all_df[all_df['상태'] != '완료'].copy()
        log_df = all_df[all_df['상태'] == '완료'].copy()
        
    return master_dict, curr_df, log_df

master_dict, curr_df, log_df = load_data()

if 'pending_lots' not in st.session_state:
    st.session_state.pending_lots = []
if 'view' not in st.session_state:
    st.session_state.view = 'main'
if 'selected_next_machines' not in st.session_state:
    st.session_state.selected_next_machines = {}

# 초기화 세션 상태 정의
if 'reset_lot' not in st.session_state: st.session_state.reset_lot = ""
if 'reset_type' not in st.session_state: st.session_state.reset_type = "일반로트"
if 'reset_note' not in st.session_state: st.session_state.reset_note = ""

def handle_add_queue(p_name, lot, l_type, note, machine):
    if lot:
        st.session_state.pending_lots.append({'제품': p_name, 'Lot': lot, '유형': l_type, '비고': note, '설비': machine})
        # 투입 대기열에 포함 완료 후 입력 컴포넌트 데이터 강제 초기화 리셋
        st.session_state.reset_lot = ""
        st.session_state.reset_type = "일반로트"
        st.session_state.reset_note = ""

# --- 5. 헤더 ---
st.markdown(f'<div class="fixed-header"><p class="main-title-text">명인제약 생산 시점 관리</p></div>', unsafe_allow_html=True)
st.markdown('<div style="position: fixed; top: 18px; right: 30px; z-index: 999999;">', unsafe_allow_html=True)
if st.button("완료된 공정 확인" if st.session_state.view == 'main' else "실시간 현황판", key="nav_btn"):
    st.session_state.view = 'history' if st.session_state.view == 'main' else 'main'
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# --- 6. 사이드바 ---
with st.sidebar:
    st.header("🏭 제조 투입")
    sel_p = st.selectbox("제품명 선택", list(master_dict.keys()), key="sel_p_widget")
    
    # 세션 상태값 연동을 통해 대기열 추가 시 즉시 입력란 비워지도록 바인딩
    lot_in = st.text_input("제조번호(Lot) 입력", key="lot_in_widget", value=st.session_state.reset_lot).strip()
    lot_type = st.selectbox("로트 유형 선택", ["일반로트", "동시PV1", "동시PV2", "동시PV3", "예측PV1", "예측PV2", "예측PV3"], key="lot_type_widget", index=["일반로트", "동시PV1", "동시PV2", "동시PV3", "예측PV1", "예측PV2", "예측PV3"].index(st.session_state.reset_type))
    note_in = st.text_area("공정 특이사항 입력", key="note_in_widget", value=st.session_state.reset_note)
    
    is_duplicate = False
    if lot_in:
        is_duplicate = (not curr_df.empty and ((curr_df['Lot'] == lot_in) & (curr_df['공정'] == "과립공정")).any()) or \
                       any(p['Lot'] == lot_in for p in st.session_state.pending_lots)
                       
    f_stg = next((s for s in TARGET_STAGES if master_dict[sel_p][s]), TARGET_STAGES[0])
    f_machines = master_dict[sel_p][f_stg]
    
    if lot_in and is_duplicate:
        st.error("⚠️ 중복 데이터 (동일 LOT 공정 진행 중)")
    elif lot_in:
        if len(f_machines) > 1:
            with st.popover("➕ 대기열 추가 (설비 선택)", use_container_width=True):
                for m in f_machines:
                    if st.button(m, key=f"init_{m}_{lot_in}"):
                        handle_add_queue(sel_p, lot_in, lot_type, note_in, m)
                        st.rerun()
        else:
            if st.button("➕ 투입 대기열 추가", use_container_width=True):
                handle_add_queue(sel_p, lot_in, lot_type, note_in, f_machines[0] if f_machines else "")
                st.rerun()

    if st.session_state.pending_lots:
        st.write("---")
        st.subheader("📝 투입 대기 리스트")
        for idx, p in enumerate(st.session_state.pending_lots):
            st.info(f"{idx+1}. {p['제품']} | {p['Lot']} ({p['설비']})")
        if st.button("🚀 전체 투입 확정", type="primary", use_container_width=True):
            for p in st.session_state.pending_lots:
                f_stg_p = next((s for s in TARGET_STAGES if master_dict[p['제품']][s]), TARGET_STAGES[0])
                history_sheet.append_row([p['Lot'], p['제품'], f_stg_p, "대기", "", "", "", p['유형'], p['비고'], p['설비']])
            st.session_state.pending_lots = []
            st.rerun()
            
    st.divider()
    st.write(f"**실시간 가동 총합:** {len(curr_df)}건")
    
    # 사이드바 하단에 총합 뿐만 아니라 [각 공정별 제품 수량]도 누락 없이 표시 처리
    for stage in TARGET_STAGES:
        count = len(curr_df[curr_df['공정'] == stage]) if not curr_df.empty else 0
        st.write(f"- {stage}: {count}건")

# --- 7. 메인 화면 ---
if st.session_state.view == 'main':
    for idx_stage, stage in enumerate(TARGET_STAGES):
        st.markdown(f'<div class="stage-bar sb-{idx_stage}">▶ {stage}</div>', unsafe_allow_html=True)
        cols = st.columns(10)
        
        for idx, machine in enumerate(MACHINE_MAP[stage]):
            with cols[idx]:
                st.markdown(f"<div class='machine-title'>{machine}</div>", unsafe_allow_html=True)
                m_items = curr_df[(curr_df['공정'] == stage) & (curr_df['설비'] == machine.strip())] if not curr_df.empty else pd.DataFrame()
                
                for _, row in m_items.iterrows():
                    with st.container(border=True):
                        st.markdown(f"<p class='card-text-10px'>{row['제품']}</p>", unsafe_allow_html=True)
                        st.markdown(f"<p class='card-text-l-10px'>{row['Lot']}</p>", unsafe_allow_html=True)
                        st.markdown(f"<p class='info-text-10px'>{row['유형']}</p>", unsafe_allow_html=True)
                        
                        # 설비 블록 안에 [공정특이사항(비고) 내용]이 선명하게 노출되도록 텍스트 렌더링
                        if row['특이사항']:
                            st.markdown(f"<p class='info-text-10px' style='color:#b45309; font-weight:700;'>📝 {row['특이사항']}</p>", unsafe_allow_html=True)
                            
                        st.markdown(f"<div class='status-bar {'bg-waiting' if row['상태']=='대기' else 'bg-progress' if row['상태']=='진행중' else 'bg-paused'}'>{row['상태']}</div>", unsafe_allow_html=True)
                        
                        # --- 제어 버튼 영역 (시작, 대기, 재시작, 완료) ---
                        if row['상태'] == '대기':
                            if st.button("시작", key=f"s_{row['Lot']}_{stage}_{machine}", use_container_width=True):
                                now_time = get_now_kst()
                                history_sheet.update_cell(int(row['Row']), 4, "진행중")
                                history_sheet.update_cell(int(row['Row']), 5, now_time)
                                st.rerun()
                                
                        elif row['상태'] == '진행중':
                            if st.button("대기", key=f"p_{row['Lot']}_{stage}_{machine}", use_container_width=True):
                                history_sheet.update_cell(int(row['Row']), 4, "지연")
                                st.rerun()
                                
                            n_idx = TARGET_STAGES.index(stage) + 1
                            next_stg = None
                            for i in range(n_idx, len(TARGET_STAGES)):
                                if master_dict[row['제품']][TARGET_STAGES[i]]:
                                    next_stg = TARGET_STAGES[i]
                                    break
                            
                            next_machines = master_dict[row['제품']][next_stg] if next_stg else []
                            
                            if len(next_machines) > 1:
                                with st.popover("완료", use_container_width=True):
                                    st.caption("다음 공정 설비 선택")
                                    for nm in next_machines:
                                        if st.button(nm, key=f"next_{nm}_{row['Lot']}_{stage}"):
                                            now_time = get_now_kst()
                                            try:
                                                start_dt = datetime.strptime(row['시작시간'], '%Y-%m-%d %H:%M')
                                                end_dt = datetime.strptime(now_time, '%Y-%m-%d %H:%M')
                                                duration = str(end_dt - start_dt)
                                            except:
                                                duration = "-"
                                            
                                            history_sheet.update_cell(int(row['Row']), 4, "완료")
                                            history_sheet.update_cell(int(row['Row']), 6, now_time)
                                            history_sheet.update_cell(int(row['Row']), 7, duration)
                                            
                                            history_sheet.append_row([row['Lot'], row['제품'], next_stg, "대기", "", "", "", row['유형'], row['특이사항'], nm])
                                            st.rerun()
                            else:
                                if st.button("완료", key=f"e_{row['Lot']}_{stage}_{machine}", use_container_width=True):
                                    now_time = get_now_kst()
                                    try:
                                        start_dt = datetime.strptime(row['시작시간'], '%Y-%m-%d %H:%M')
                                        end_dt = datetime.strptime(now_time, '%Y-%m-%d %H:%M')
                                        duration = str(end_dt - start_dt)
                                    except:
                                        duration = "-"
                                        
                                    history_sheet.update_cell(int(row['Row']), 4, "완료")
                                    history_sheet.update_cell(int(row['Row']), 6, now_time)
                                    history_sheet.update_cell(int(row['Row']), 7, duration)
                                    
                                    if next_stg:
                                        next_m = next_machines[0] if next_machines else ""
                                        history_sheet.append_row([row['Lot'], row['제품'], next_stg, "대기", "", "", "", row['유형'], row['특이사항'], next_m])
                                    st.rerun()
                                    
                        elif row['상태'] == '지연':
                            if st.button("재시작", key=f"r_{row['Lot']}_{stage}_{machine}", use_container_width=True):
                                history_sheet.update_cell(int(row['Row']), 4, "진행중")
                                st.rerun()
else:
    st.header("📋 완료된 공정 이력 리포트")
    if not log_df.empty:
        st.dataframe(log_df[['Lot', '제품', '공정', '상태', '시작시간', '종료시간', '소요시간', '유형', '특이사항', '설비']].sort_index(ascending=False), use_container_width=True)
    else:
        st.info("기록된 완료 이력이 존재하지 않습니다.")
