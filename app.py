import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client

# --- 1. 페이지 설정 ---
st.set_page_config(layout="wide", page_title="명인제약 생산 시점 관리")

# --- 2. CSS 스타일 (글자 크기 및 입체 버튼 디자인 100% 유지) ---
st.markdown("""
<style>
.fixed-header {
    position: fixed; 
    top: 0; 
    left: 0; 
    right: 0; 
    height: 66px; 
    background-color: #1e3a8a; 
    z-index: 999998; 
    display: flex; 
    align-items: center; 
    padding: 0 30px; 
    box-shadow: 0 4px 10px rgba(0,0,0,0.3); 
}
.main-title-text {
    color: white !important; 
    font-size: 28px !important; 
    font-weight: 800; 
    margin: 0; 
    flex-grow: 1; 
}
.main .block-container { padding-top: 100px !important; }

.stage-bar {
    color: white; 
    padding: 8px 13px; 
    border-radius: 6px; 
    font-size: 18px; 
    font-weight: 700; 
    margin-top: 20px; 
    margin-bottom: 10px; 
}

.sb-0, .sb-1, .sb-2, .sb-3, .sb-4, .sb-5, .sb-6, .sb-7, .sb-8, .sb-9 { 
    background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%); 
}

/* 설비 글자 크기 16px 유지 */
.machine-title {
    background: #f1f5f9; 
    text-align: center; 
    font-size: 16px !important; 
    font-weight: 800; 
    border-radius: 6px; 
    margin-bottom: 8px; 
    border: 2px solid #cbd5e1; 
    min-height: 40px; 
    display: flex; 
    align-items: center; 
    justify-content: center; 
    color: #1e293b; 
}

.status-bar { font-size: 10px; font-weight: 800; color: white; text-align: center; padding: 3px 0; border-radius: 3px; margin-bottom: 5px; }
.bg-waiting { background-color: #3b82f6; }
.bg-progress { background-color: #ef4444; }
.bg-paused { background-color: #f59e0b; }

/* 블록 안의 글자 크기 15px 유지 */
.card-text-10px { font-size: 15px !important; font-weight: 800; margin: 0; text-align: center; line-height: 1.2; }
.card-text-l-10px { font-size: 15px !important; color: #1e40af; font-weight: 700; text-align: center; margin: 0; line-height: 1.2; }
.info-text-10px { font-size: 10px !important; color: #475569; margin: 1px 0; text-align: center; line-height: 1.2; }
.lot-type-highlight { font-size: 15px !important; color: #ef4444 !important; font-weight: 800 !important; text-align: center; margin: 1px 0; line-height: 1.2; }

/* 완료된 공정 이력 표 안의 글자 크기 16px 유지 */
div[data-testid="stDataFrame"] td, div[data-testid="stDataFrame"] th {font-size: 16px !important; }

/* 버튼 글자 크기 15px 및 입체 섀도우 유지 */
div.stButton > button, div.stPopover > button {
    padding: 4px 10px !important; 
    font-size: 15px !important; 
    font-weight: 700 !important;
    min-height: 32px !important; 
    line-height: 1.2 !important;
    background-color: #ffffff !important;
    color: #1e3a8a !important;
    border: 2px solid #1e3a8a !important;
    box-shadow: 0 4px 0px #1e3a8a !important; 
    border-radius: 6px !important;
    transition: all 0.05s ease-in-out;
    width: 100% !important; 
}

div.stButton > button:hover, div.stPopover > button:hover {
    background-color: #f8fafc !important;
}
div.stButton > button:active, div.stPopover > button:active {
    transform: translateY(3px) !important;
    box-shadow: 0 1px 0px #1e3a8a !important;
}
</style>
""", unsafe_allow_html=True)

# --- 3. Supabase DB 연결 ---
@st.cache_resource
def init_supabase():
    url: str = st.secrets["supabase"]["url"]
    key: str = st.secrets["supabase"]["key"]
    return create_client(url, key)

try:
    supabase: Client = init_supabase()
except Exception as e:
    st.error(f"🔗 데이터베이스 연결 실패: {e}")
    st.stop()

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
    m_data = supabase.table("product_master").select("*").execute()
    master_dict = {}
    for r in m_data.data:
        p_name = str(r.get("제품명")).strip()
        master_dict[p_name] = {}
        for stage in TARGET_STAGES:
            m_list = r.get(stage, "")
            master_dict[p_name][stage] = [m.strip() for m in str(m_list).split(',') if m.strip()] if m_list else []

    h_data = supabase.table("product_history").select("*").execute()
    if not h_data.data:
        curr_df = pd.DataFrame(columns=['Lot', '제품', '공정', '상태', '시작시간', '종료시간', '소요시간', '유형', '특이사항', '설비', 'id'])
        log_df = pd.DataFrame(columns=['Lot', '제품', '공정', '상태', '시작시간', '종료시간', '소요시간', '유형', '특이사항', '설비'])
    else:
        all_df = pd.DataFrame(h_data.data)
        if 'id' in all_df.columns:
            all_df['Row'] = all_df['id']
        curr_df = all_df[~all_df['상태'].isin(['완료', '1팀종료'])].copy()
        log_df = all_df[all_df['상태'].isin(['완료', '1팀종료'])].copy()
        
    return master_dict, curr_df, log_df

master_dict, curr_df, log_df = load_data()

if 'pending_lots' not in st.session_state:
    st.session_state.pending_lots = []
if 'view' not in st.session_state:
    st.session_state.view = 'main'

if 'reset_lot' not in st.session_state: st.session_state.reset_lot = ""
if 'reset_type' not in st.session_state: st.session_state.reset_type = "일반로트"
if 'reset_note' not in st.session_state: st.session_state.reset_note = ""

def handle_add_queue(p_name, lot, l_type, note, machine):
    if lot:
        st.session_state.pending_lots.append({'제품': p_name, 'Lot': lot, '유형': l_type, '특이사항': note, '설비': machine})
        st.session_state.reset_lot = ""
        st.session_state.reset_type = "일반로트"
        st.session_state.reset_note = ""

# --- 5. 헤더 부분 ---
st.markdown(f"""
<div class="fixed-header">
    <p class="main-title-text">명인제약 생산 시점 관리</p>
</div>
""", unsafe_allow_html=True)

nav_cols = st.columns([1.5, 1.8, 2.2, 5])
with nav_cols[0]:
    if st.button("실시간 현황판", key="btn_nav_main"):
        st.session_state.view = 'main'
        st.rerun()
with nav_cols[1]:
    if st.button("완료된 공정 확인", key="btn_nav_history"):
        st.session_state.view = 'history'
        st.rerun()
with nav_cols[2]:
    if st.button("완료된 공정 확인(선별)", key="btn_nav_selection"):
        st.session_state.view = 'selection'
        st.rerun()

# --- 6. 사이드바 ---
with st.sidebar:
    st.header("🏭 제조 투입")
    sel_p = st.selectbox("제품명 선택", list(master_dict.keys()), key="sel_p_widget")
    
    lot_in = st.text_input("제조번호(Lot) 입력", key="lot_in_widget", value=st.session_state.reset_lot).strip()
    lot_type = st.selectbox("로트 유형 선택", ["일반로트", "동시PV1", "동시PV2", "동시PV3", "예측PV1", "예측PV2", "예측PV3"], key="lot_type_widget", index=["일반로트", "동시PV1", "동시PV2", "동시PV3", "예측PV1", "예측PV2", "예측PV3"].index(st.session_state.reset_type))
    note_in = st.text_area("공정 특이사항 입력", key="note_in_widget", value=st.session_state.reset_note)
    
    is_duplicate = False
    if lot_in:
        dup_curr = (not curr_df.empty and ((curr_df['Lot'] == lot_in) & (curr_df['제품'] == sel_p)).any())
        dup_log = (not log_df.empty and ((log_df['Lot'] == lot_in) & (log_df['제품'] == sel_p)).any())
        dup_queue = any(p['Lot'] == lot_in and p['제품'] == sel_p for p in st.session_state.pending_lots)
        
        is_duplicate = dup_curr or dup_log or dup_queue
                       
    f_stg = next((s for s in TARGET_STAGES if master_dict[sel_p][s]), TARGET_STAGES[0])
    f_machines = master_dict[sel_p][f_stg]
    
    if lot_in and is_duplicate:
        st.error("⚠️ 중복 데이터 (동일 제품 및 LOT 공정 진행/종료됨)")
    elif lot_in:
        if len(f_machines) > 1:
            with st.popover("➕ 대기열 추가 (설비 선택)", use_container_width=True):
                for m in f_machines:
                    if st.button(m, key=f"init_{m}_{sel_p}_{lot_in}"):
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
            del_cols = st.columns([8, 2])
            with del_cols[0]:
                st.info(f"{idx+1}. {p['제품']} | {p['Lot']} ({p['설비']})")
            with del_cols[1]:
                if st.button("❌", key=f"del_item_{idx}_{p['Lot']}_{p['제품']}"):
                    st.session_state.pending_lots.pop(idx)
                    st.rerun()
        btn_cols = st.columns(2)
        with btn_cols[0]:
            if st.button("🚀 전체 투입 확정", type="primary", use_container_width=True):
                for p in st.session_state.pending_lots:
                    f_stg_p = next((s for s in TARGET_STAGES if master_dict[p['제품']][s]), TARGET_STAGES[0])
                    supabase.table("product_history").insert({
                        "Lot": p['Lot'], "제품": p['제품'], "공정": f_stg_p, "상태": "대기",
                        "시작시간": "", "종료시간": "", "소요시간": "", "유형": p['유형'], "특이사항": p['특이사항'], "설비": p['설비']
                    }).execute()
                st.session_state.pending_lots = []
                st.rerun()
        with btn_cols[1]:
            if st.button("🗑️ 전체 비우기", type="secondary", use_container_width=True):
                st.session_state.pending_lots = []
                st.rerun()
    st.divider()
    st.write(f"**실시간 가동 총합:** {len(curr_df)}건")
    for stage in TARGET_STAGES:
        count = len(curr_df[curr_df['공정'] == stage]) if not curr_df.empty else 0
        st.write(f"- {stage}: {count}건")

# --- 7. 메인 화면 ---
if st.session_state.view == 'main':
    for idx_stage, stage in enumerate(TARGET_STAGES):
        # [수정] 실시간 각 대공정별 활성화된 건수를 계산하여 바(Bar) 텍스트 옆에 동적으로 출력
        stage_count = len(curr_df[curr_df['공정'] == stage]) if not curr_df.empty else 0
        st.markdown(f'<div class="stage-bar sb-{idx_stage}">▶ {stage} ({stage_count}건)</div>', unsafe_allow_html=True)
        
        cols = st.columns(10)
        for idx, machine in enumerate(MACHINE_MAP[stage]):
            with cols[idx]:
                st.markdown(f"<div class='machine-title'>{machine}</div>", unsafe_allow_html=True)
                m_items = curr_df[(curr_df['공정'] == stage) & (curr_df['설bi'] == machine.strip())] if not curr_df.empty else pd.DataFrame()
                
                # 오타 방지용 컬럼 안전 매핑 복구
                if not curr_df.empty and '설비' in curr_df.columns:
                    m_items = curr_df[(curr_df['공정'] == stage) & (curr_df['설비'] == machine.strip())]
                    
                for _, row in m_items.iterrows():
                    with st.container(border=True):
                        st.markdown(f"<p class='card-text-10px'>{row['제품']}</p>", unsafe_allow_html=True)
                        st.markdown(f"<p class='card-text-l-10px'>{row['Lot']}</p>", unsafe_allow_html=True)
                        if row['유형'] not in ['일반로트', '일반', '']:
                            st.markdown(f"<p class='lot-type-highlight'>{row['유형']}</p>", unsafe_allow_html=True)
                        if row['특이사항']:
                            st.markdown(f"<p class='info-text-10px' style='color:#b45309; font-weight:700;'>📝 {row['특이사항']}</p>", unsafe_allow_html=True)
                        st.markdown(f"<div class='status-bar {'bg-waiting' if row['상태']=='대기' else 'bg-progress' if row['상태']=='진행중' else 'bg-paused'}'>{row['상태']}</div>", unsafe_allow_html=True)
                        if row['상태'] == '대기':
                            if st.button("시작", key=f"s_{row['제품']}_{row['Lot']}_{stage}_{machine}", use_container_width=True):
                                now_time = get_now_kst()
                                supabase.table("product_history").update({"상태": "진행중", "시작시간": now_time}).eq("id", row['Row']).execute()
                                st.rerun()
                        elif row['상태'] == '진행중':
                            if st.button("대기", key=f"p_{row['제품']}_{row['Lot']}_{stage}_{machine}", use_container_width=True):
                                supabase.table("product_history").update({"상태": "지연"}).eq("id", row['Row']).execute()
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
                                        if st.button(nm, key=f"next_{nm}_{row['제품']}_{row['Lot']}_{stage}"):
                                            now_time = get_now_kst()
                                            try:
                                                start_dt = datetime.strptime(row['시작시간'], '%Y-%m-%d %H:%M')
                                                end_dt = datetime.strptime(now_time, '%Y-%m-%d %H:%M')
                                                duration = str(end_dt - start_dt)
                                            except:
                                                duration = "-"
                                            current_status = "1팀종료" if next_stg == "외관선별공정" else "완료"
                                            supabase.table("product_history").update({"상태": current_status, "종료시간": now_time, "소요시간": duration}).eq("id", row['Row']).execute()
                                            supabase.table("product_history").insert({
                                                "Lot": row['Lot'], "제품": row['제품'], "공정": next_stg, "상태": "대기",
                                                "시작시간": "", "종료시간": "", "소요시간": "", "유형": row['유형'], "특이사항": row['특이사항'], "설비": nm
                                            }).execute()
                                            st.rerun()
                            else:
                                if st.button("완료", key=f"e_{row['제품']}_{row['Lot']}_{stage}_{machine}", use_container_width=True):
                                    now_time = get_now_kst()
                                    try:
                                        start_dt = datetime.strptime(row['시작시간'], '%Y-%m-%d %H:%M')
                                        end_dt = datetime.strptime(now_time, '%Y-%m-%d %H:%M')
                                        duration = str(end_dt - start_dt)
                                    except:
                                        duration = "-"
                                    current_status = "1팀종료" if next_stg == "외관선별공정" else "완료"
                                    supabase.table("product_history").update({"상태": current_status, "종료시간": now_time, "소요시간": duration}).eq("id", row['Row']).execute()
                                    if next_stg:
                                        next_m = next_machines[0] if next_machines else ""
                                        supabase.table("product_history").insert({
                                            "Lot": row['Lot'], "제품": row['제품'], "공정": next_stg, "상태": "대기",
                                            "시작시간": "", "종료시간": "", "소요시간": "", "유형": row['유형'], "특이사항": row['특이사항'], "설비": next_m
                                        }).execute()
                                    st.rerun()
                        elif row['상태'] == '지연':
                            if st.button("재시작", key=f"r_{row['제품']}_{row['Lot']}_{stage}_{machine}", use_container_width=True):
                                supabase.table("product_history").update({"상태": "진행중"}).eq("id", row['Row']).execute()
                                st.rerun()
# --- 8. 이력 리포트 화면 ---
else:
    if st.session_state.view == 'history':
        st.header("📋 완료된 공정 이력 리포트 (1팀)")
        team_df = log_df[log_df['상태'] == '1팀종료']
    else:
        st.header("🔍 완료된 공정 이력 리포트 (선별)")
        team_df = log_df[(log_df['공정'] == '외관선별공정') & (log_df['상태'] == '완료')]
    if not team_df.empty:
        unique_products = sorted(team_df['제품'].unique().tolist())
        sel_filter = st.selectbox("🔍 제품명으로 검색 (데이터가 많을 때 사용하세요)", ["전체 보기"] + unique_products)
        display_df = team_df.copy()
        if sel_filter != "전체 보기":
            display_df = display_df[display_df['제품'] == sel_filter]
        st.dataframe(display_df[['Lot', '제품', '공정', '상태', '시작시간', '종료시간', '소요시간', '유형', '특이사항', '설비']].sort_index(ascending=False), use_container_width=True)
    else:
        st.info("조건에 일치하는 완료 이력이 존재하지 않습니다.")
