import streamlit st
import pandas as pd
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client

# --- 1. 페이지 설정 ---
st.set_page_config(layout="wide", page_title="명인제약 생산 시점 관리")

# --- 2. CSS 스타일 (최신 stColumn 규격 반영: 균등 길이 + 22px 대형 4색 입체 메뉴 원천 고정) ---
st.markdown("""
<style>
/* 헤더 설정 */
.fixed-header {
    position: fixed; top: 0; left: 0; right: 0; height: 66px; 
    background-color: #1e3a8a; z-index: 999998; 
    display: flex; align-items: center; padding: 0 30px; 
    box-shadow: 0 4px 10px rgba(0,0,0,0.3); 
}
.main-title-text {
    color: white !important; font-size: 28px !important; 
    font-weight: 800; margin: 0; flex-grow: 1; 
}
.main .block-container { padding-top: 100px !important; }

/* 공정 바 및 설비 타이틀 */
.stage-bar {
    color: white; padding: 8px 13px; border-radius: 6px; 
    font-size: 18px; font-weight: 700; margin-top: 20px; margin-bottom: 10px; 
}
.sb-0, .sb-1, .sb-2, .sb-3, .sb-4, .sb-5, .sb-6, .sb-7, .sb-8, .sb-9 { 
    background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%); 
}
.machine-title {
    background: #f1f5f9; text-align: center; font-size: 16px !important; 
    font-weight: 800; border-radius: 6px; margin-bottom: 8px; 
    border: 2px solid #cbd5e1; min-height: 40px; 
    display: flex; align-items: center; justify-content: center; color: #1e293b; 
}

/* 블록 내부 텍스트 규칙 (15px 유지) */
.card-text-10px { font-size: 15px !important; font-weight: 800; margin: 0; text-align: center; line-height: 1.2; }
.card-text-l-10px { font-size: 15px !important; color: #1e40af; font-weight: 700; text-align: center; margin: 0; line-height: 1.2; }
.info-text-10px { font-size: 10px !important; color: #475569; margin: 1px 0; text-align: center; line-height: 1.2; }
.lot-type-highlight { font-size: 15px !important; color: #ef4444 !important; font-weight: 800 !important; text-align: center; margin: 1px 0; line-height: 1.2; }
.status-bar { font-size: 10px; font-weight: 800; color: white; text-align: center; padding: 3px 0; border-radius: 3px; margin-bottom: 5px; }
.bg-waiting { background-color: #3b82f6; }
.bg-progress { background-color: #ef4444; }
.bg-paused { background-color: #f59e0b; }

/* 표 글자 크기 (16px 유지) */
div[data-testid="stDataFrame"] td, div[data-testid="stDataFrame"] th { font-size: 16px !important; }

/* 블록 내부 액션 버튼 (13px 콤팩트 스타일 고정) */
div.stButton > button, div[data-testid="stPopover"] button {
    padding: 2px 4px !important; font-size: 13px !important; font-weight: 700 !important;
    height: 30px !important; min-height: 30px !important; line-height: 1.2 !important;
    background-color: #ffffff !important; color: #1e3a8a !important;
    border: 2px solid #1e3a8a !important; box-shadow: 0 3px 0px #1e3a8a !important; 
    border-radius: 6px !important; transition: all 0.05s ease-in-out;
    width: 100% !important; display: flex !important; align-items: center !important; justify-content: center !important;
}

/* 최신 stColumn 껍질 내부의 모든 네비게이션 단추 서식 강제 장악 */
div[data-testid="stColumn"] button {
    height: 65px !important;
    font-size: 22px !important;
    font-weight: 900 !important; 
    border-radius: 10px !important;
    letter-spacing: -0.5px !important;
    white-space: nowrap !important;
    display: flex !important; align-items: center !important; justify-content: center !important;
    transition: all 0.05s ease-in-out !important;
}

/* 4색 다이렉트 컬러 매핑 */
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(1) button {
    background-color: #2563eb !important; color: white !important; 
    border: 2px solid #1e40af !important; box-shadow: 0 6px 0px #1e40af !important;
}
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2) button {
    background-color: #059669 !important; color: white !important; 
    border: 2px solid #047857 !important; box-shadow: 0 6px 0px #047857 !important;
}
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(3) button {
    background-color: #d97706 !important; color: white !important; 
    border: 2px solid #b45309 !important; box-shadow: 0 6px 0px #b45309 !important;
}
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(4) button {
    background-color: #7c3aed !important; color: white !important; 
    border: 2px solid #6d28d9 !important; box-shadow: 0 6px 0px #6d28d9 !important;
}

div[data-testid="stColumn"] button:hover { filter: brightness(1.1) !important; color: white !important; }
div[data-testid="stColumn"] button:active { transform: translateY(4px) !important; box-shadow: 0 2px 0px rgba(0,0,0,0.2) !important; }
div[data-testid="stPopover"] svg { display: none !important; }
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

# --- 4. 데이터 로직 ---
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
    master_dict = {str(r.get("제품명")).strip(): {s: [m.strip() for m in str(r.get(s, "")).split(',') if m.strip()] for s in TARGET_STAGES} for r in m_data.data}
    h_data = supabase.table("product_history").select("*").execute()
    if not h_data.data:
        return master_dict, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    all_raw_df = pd.DataFrame(h_data.data)
    if 'id' in all_raw_df.columns: all_raw_df['Row'] = all_raw_df['id']
    curr_df = all_raw_df[~all_raw_df['상태'].isin(['완료', '1팀종료'])].copy()
    log_df = all_raw_df[all_raw_df['상태'].isin(['완료', '1팀종료'])].copy()
    return master_dict, curr_df, log_df, all_raw_df

master_dict, curr_df, log_df, all_raw_df = load_data()

if 'pending_lots' not in st.session_state: st.session_state.pending_lots = []
if 'view' not in st.session_state: st.session_state.view = 'main'
if 'reset_lot' not in st.session_state: st.session_state.reset_lot = ""
if 'reset_type' not in st.session_state: st.session_state.reset_type = "일반로트"
if 'reset_note' not in st.session_state: st.session_state.reset_note = ""

# --- 5. 헤더 및 균등 대형 네비게이션 바 ---
st.markdown(f'<div class="fixed-header"><p class="main-title-text">명인제약 생산 시점 관리</p></div>', unsafe_allow_html=True)

nav_cols = st.columns([1, 1, 1, 1])
with nav_cols[0]:
    if st.button("실시간 현황판", key="nav_1", use_container_width=True): st.session_state.view = 'main'; st.rerun()
with nav_cols[1]:
    if st.button("완료된 공정 확인", key="nav_2", use_container_width=True): st.session_state.view = 'history'; st.rerun()
with nav_cols[2]:
    if st.button("완료된 공정 확인(선별)", key="nav_3", use_container_width=True): st.session_state.view = 'selection'; st.rerun()
with nav_cols[3]:
    if st.button("모든 공정 이력 확인", key="nav_4", use_container_width=True): st.session_state.view = 'all_history'; st.rerun()

# --- 6. 사이드바 (원본 100% 보존) ---
with st.sidebar:
    st.header("🏭 제조 투입")
    sel_p = st.selectbox("제품명 선택", list(master_dict.keys()), key="sel_p_widget")
    lot_in = st.text_input("제조번호(Lot) 입력", key="lot_in_widget", value=st.session_state.reset_lot).strip()
    lot_type = st.selectbox("로트 유형 선택", ["일반로트", "동시PV1", "동시PV2", "동시PV3", "예측PV1", "예측PV2", "예측PV3"], key="lot_type_widget")
    note_in = st.text_area("공정 특이사항 입력", key="note_in_widget", value=st.session_state.reset_note)
    
    is_duplicate = lot_in and ((not curr_df.empty and ((curr_df['Lot'] == lot_in) & (curr_df['제품'] == sel_p)).any()) or any(p['Lot'] == lot_in and p['제품'] == sel_p for p in st.session_state.pending_lots))
    f_stg = next((s for s in TARGET_STAGES if master_dict[sel_p][s]), TARGET_STAGES[0])
    f_machines = master_dict[sel_p][f_stg]
    
    if lot_in and is_duplicate: st.error("⚠️ 중복 데이터")
    elif lot_in:
        if len(f_machines) > 1:
            with st.popover("➕ 대기열 추가", use_container_width=True):
                for m in f_machines:
                    if st.button(m, key=f"init_{m}_{sel_p}_{lot_in}"):
                        st.session_state.pending_lots.append({'제품': sel_p, 'Lot': lot_in, '유형': lot_type, '특이사항': note_in, '설비': m})
                        st.session_state.reset_lot = ""; st.rerun()
        else:
            if st.button("➕ 투입 대기열 추가", use_container_width=True):
                st.session_state.pending_lots.append({'제품': sel_p, 'Lot': lot_in, '유형': lot_type, '특이사항': note_in, '설비': f_machines[0] if f_machines else ""})
                st.session_state.reset_lot = ""; st.rerun()

    if st.session_state.pending_lots:
        st.write("---")
        for idx, p in enumerate(st.session_state.pending_lots):
            c1, c2 = st.columns([8, 2])
            c1.info(f"{p['제품']} | {p['Lot']}")
            if c2.button("❌", key=f"del_{idx}"): st.session_state.pending_lots.pop(idx); st.rerun()
        if st.button("🚀 전체 투입 확정", type="primary", use_container_width=True):
            for p in st.session_state.pending_lots:
                supabase.table("product_history").insert({"Lot": p['Lot'], "제품": p['제품'], "공정": next((s for s in TARGET_STAGES if master_dict[p['제품']][s]), TARGET_STAGES[0]), "상태": "대기", "유형": p['유형'], "특이사항": p['특이사항'], "설비": p['설비']}).execute()
            st.session_state.pending_lots = []; st.rerun()

    st.divider()
    st.write(f"**가동 건수**")
    for stage in TARGET_STAGES:
        st.write(f"- {stage}: {len(curr_df[curr_df['공정'] == stage]) if not curr_df.empty else 0}건")

    st.write("---")
    with st.popover("🔒 데이터 초기화", use_container_width=True):
        input_pwd = st.text_input("비밀번호 입력", type="password")
        if st.button("🚨 초기화 실행", type="primary", use_container_width=True):
            if input_pwd == "1234":
                supabase.table("product_history").delete().neq("Lot", "sys_clear").execute()
                st.rerun()

# --- 7. 메인 콘텐츠 및 제목 연동 ---
if st.session_state.view == 'main':
    for idx_stage, stage in enumerate(TARGET_STAGES):
        stage_count = len(curr_df[curr_df['공정'] == stage]) if not curr_df.empty else 0
        st.markdown(f'<div class="stage-bar sb-{idx_stage}">▶ {stage} ({stage_count}건)</div>', unsafe_allow_html=True)
        cols = st.columns(10)
        for idx, machine in enumerate(MACHINE_MAP[stage]):
            with cols[idx]:
                st.markdown(f"<div class='machine-title'>{machine}</div>", unsafe_allow_html=True)
                m_items = curr_df[(curr_df['공정'] == stage) & (curr_df['설비'] == machine.strip())] if not curr_df.empty else pd.DataFrame()
                for _, row in m_items.iterrows():
                    with st.container(border=True):
                        st.markdown(f"<p class='card-text-10px'>{row['제품']}</p>", unsafe_allow_html=True)
                        st.markdown(f"<p class='card-text-l-10px'>{row['Lot']}</p>", unsafe_allow_html=True)
                        if row['유형'] not in ['일반로트', '일반', '']: st.markdown(f"<p class='lot-type-highlight'>{row['유형']}</p>", unsafe_allow_html=True)
                        if row['특이사항']: st.markdown(f"<p class='info-text-10px'>📝 {row['특이사항']}</p>", unsafe_allow_html=True)
                        st.markdown(f"<div class='status-bar {'bg-waiting' if row['상태']=='대기' else 'bg-progress' if row['상태']=='진행중' else 'bg-paused'}'>{row['상태']}</div>", unsafe_allow_html=True)
                        
                        if row['상태'] == '대기':
                            b1, b2 = st.columns(2)
                            if b1.button("시작", key=f"s_{row['Row']}"): supabase.table("product_history").update({"상태": "진행중", "시작시간": get_now_kst()}).eq("id", row['Row']).execute(); st.rerun()
                            with b2.popover("변경"):
                                for nm in master_dict.get(row['제품'], {}).get(stage, []):
                                    if nm != row['설비'] and st.button(nm, key=f"ch_{row['Row']}_{nm}"): supabase.table("product_history").update({"설비": nm}).eq("id", row['Row']).execute(); st.rerun()
                        elif row['상태'] == '진행중':
                            if st.button("대기", key=f"p_{row['Row']}"): supabase.table("product_history").update({"상태": "지연"}).eq("id", row['Row']).execute(); st.rerun()
                            
                            # --- [추적 오류 완벽 보정] 비어있는 중간 공정이 있어도 끝까지 스캔하여 다음 공정을 찾아냄 ---
                            n_stg = None
                            for i in range(TARGET_STAGES.index(stage) + 1, len(TARGET_STAGES)):
                                if master_dict.get(row['제품'], {}).get(TARGET_STAGES[i]): 
                                    n_stg = TARGET_STAGES[i]
                                    break # 설비가 지정된 유효한 다음 공정을 찾으면 중단
                                    
                            n_machines = master_dict.get(row['제품'], {}).get(n_stg, []) if n_stg else []
                            if len(n_machines) > 1:
                                with st.popover("완료"):
                                    for nm in n_machines:
                                        if st.button(nm, key=f"next_{row['Row']}_{nm}"):
                                            dur = str(datetime.strptime(get_now_kst(), '%Y-%m-%d %H:%M') - datetime.strptime(row['시작시간'], '%Y-%m-%d %H:%M'))
                                            supabase.table("product_history").update({"상태": "1팀종료" if n_stg == "외관선별공정" else "완료", "종료시간": get_now_kst(), "소요시간": dur}).eq("id", row['Row']).execute()
                                            supabase.table("product_history").insert({"Lot": row['Lot'], "제품": row['제품'], "공정": n_stg, "상태": "대기", "유형": row['유형'], "특이사항": row['특이사항'], "설비": nm}).execute(); st.rerun()
                            else:
                                if st.button("완료", key=f"e_{row['Row']}"):
                                    dur = str(datetime.strptime(get_now_kst(), '%Y-%m-%d %H:%M') - datetime.strptime(row['시작시간'], '%Y-%m-%d %H:%M'))
                                    supabase.table("product_history").update({"상태": "1팀종료" if n_stg == "외관선별공정" else "완료", "종료시간": get_now_kst(), "소요시간": dur}).eq("id", row['Row']).execute()
                                    if n_stg: supabase.table("product_history").insert({"Lot": row['Lot'], "제품": row['제품'], "공정": n_stg, "상태": "대기", "유형": row['유형'], "특이사항": row['특이사항'], "설비": n_machines[0] if n_machines else ""}).execute(); st.rerun()
                        elif row['상태'] == '지연':
                            if st.button("재시작", key=f"r_{row['Row']}"): supabase.table("product_history").update({"상태": "진행중"}).eq("id", row['Row']).execute(); st.rerun()
else:
    title_map = {"history": "완료된 공정 확인", "selection": "완료된 공정 확인(선별)", "all_history": "모든 공정 이력 확인"}
    st.header(f"📋 {title_map[st.session_state.view]}")
    
    display_df = log_df[log_df['상태'] == '1팀종료'] if st.session_state.view == 'history' else log_df[(log_df['공정'] == '외관선별공정') & (log_df['상태'] == '완료')] if st.session_state.view == 'selection' else all_raw_df
    if not display_df.empty:
        sel_filter = st.selectbox("🔍 제품명 검색", ["전체 보기"] + sorted(display_df['제품'].unique().tolist()), key=f"filter_{st.session_state.view}")
        if sel_filter != "전체 보기": display_df = display_df[display_df['제품'] == sel_filter]
        st.dataframe(display_df[['Lot', '제품', '공정', '상태', '시작시간', '종료시간', '소요시간', '유형', '특이사항', '설비']].sort_index(ascending=False), use_container_width=True)
    else: st.info("데이터가 없습니다.")
