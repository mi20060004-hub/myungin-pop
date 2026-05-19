import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client

# --- 1. 페이지 설정 ---
st.set_page_config(layout="wide", page_title="명인제약 생산 시점 관리")

# --- 2. CSS 스타일 ---
st.markdown("""
<style>
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

.stage-bar {
    color: white; padding: 8px 13px; border-radius: 6px; 
    font-size: 18px; font-weight: 700; margin-top: 20px; margin-bottom: 10px; 
    background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
}
.machine-title {
    background: #f1f5f9; text-align: center; font-size: 16px !important; 
    font-weight: 800; border-radius: 6px; margin-bottom: 8px; 
    border: 2px solid #cbd5e1; min-height: 40px; 
    display: flex; align-items: center; justify-content: center; color: #1e293b; 
}

.card-text-10px { font-size: 15px !important; font-weight: 800; margin: 0; text-align: center; line-height: 1.2; }
.card-text-l-10px { font-size: 15px !important; color: #1e40af; font-weight: 700; text-align: center; margin: 0; line-height: 1.2; }
.info-text-10px { font-size: 10px !important; color: #475569; margin: 1px 0; text-align: center; line-height: 1.2; }
/* stock-text-highlight 색상 수정: 더 잘 보이도록 어둡게 */
.stock-text-highlight { font-size: 13px !important; color: #004d40 !important; font-weight: 700 !important; text-align: center; margin: 2px 0; line-height: 1.2; }
.lot-type-highlight { font-size: 15px !important; color: #ef4444 !important; font-weight: 800 !important; text-align: center; margin: 1px 0; line-height: 1.2; }
.status-bar { font-size: 10px; font-weight: 800; color: white; text-align: center; padding: 3px 0; border-radius: 3px; margin-bottom: 5px; }
.bg-waiting { background-color: #3b82f6; }
.bg-progress { background-color: #ef4444; }
.bg-paused { background-color: #f59e0b; }

div[data-testid="stDataFrame"] td, div[data-testid="stDataFrame"] th { font-size: 16px !important; }
div[data-testid="stVerticalBlock"] > div { margin-bottom: 2px !important; }

.main div[data-testid="stVerticalBlock"] [data-testid="stElementContainer"] {
    min-height: 16px !important; height: 16px !important; margin: 0px 0px 3px 0px !important; padding: 0px !important;
}
.main div[data-testid="stVerticalBlock"] div[data-testid="stButton"],
.main div[data-testid="stVerticalBlock"] div[data-testid="stPopover"],
.main div[data-testid="stVerticalBlock"] div[data-testid="stPopover"] > div:first-child {
    min-height: 16px !important; height: 16px !important; max-height: 16px !important; margin: 0px !important; padding: 0px !important; display: flex !important; align-items: center !important;
}
.main div[data-testid="stVerticalBlock"] div.stButton > button,
.main div[data-testid="stVerticalBlock"] div[data-testid="stPopover"] button {
    padding: 0px !important; margin: 0px !important; font-size: 11px !important; font-weight: 700 !important; height: 16px !important; min-height: 16px !important; max-height: 16px !important; line-height: 14px !important; display: flex !important; align-items: center !important; justify-content: center !important; box-sizing: border-box !important; width: 100% !important;
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

# --- 4. 데이터 로직 ---
MACHINE_MAP = {
    "칭량공정": [], 
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
        p_name = str(r.get("제품명", "")).strip()
        if not p_name: continue
        stage_map = {}
        for s in TARGET_STAGES:
            raw_val = str(r.get(s, "")).strip()
            if not raw_val or raw_val.upper() == "NONE" or raw_val == "-":
                stage_map[s] = []
            else:
                machines = [m.strip() for m in raw_val.split(',') if m.strip()]
                stage_map[s] = machines
        master_dict[p_name] = stage_map

    stock_dict = {}
    try:
        # ★ 수파베이스에서 새 컬럼 명칭인 '적요', '재고 월수'를 직접 긁어오도록 연동 엔진 전면 수정
        s_data = supabase.table("product_stock").select("적요, \"재고 월수\"").order("id", desc=True).execute()
        if s_data.data:
            s_df = pd.DataFrame(s_data.data)
            s_df = s_df.drop_duplicates(subset=['적요'], keep='first')
            for _, s_row in s_df.iterrows():
                clean_stock_p = str(s_row['적요']).replace(" ", "").strip()
                stock_dict[clean_stock_p] = str(s_row['재고 월수']).strip()
    except Exception:
        pass

    h_data = supabase.table("product_history").select("*").execute()
    if not h_data.data:
        return master_dict, stock_dict, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    all_raw_df = pd.DataFrame(h_data.data)
    if 'id' in all_raw_df.columns: all_raw_df['Row'] = all_raw_df['id']
    
    curr_df = all_raw_df[~all_raw_df['상태'].isin(['완료', '1팀종료'])].copy()
    log_df = all_raw_df[all_raw_df['상태'].isin(['완료', '1팀종료'])].copy()
    return master_dict, stock_dict, curr_df, log_df, all_raw_df

master_dict, stock_dict, curr_df, log_df, all_raw_df = load_data()

if 'pending_lots' not in st.session_state: st.session_state.pending_lots = []
if 'view' not in st.session_state: st.session_state.view = 'main'
if 'reset_lot' not in st.session_state: st.session_state.reset_lot = ""
if 'reset_type' not in st.session_state: st.session_state.reset_type = "일반로트"
if 'reset_note' not in st.session_state: st.session_state.reset_note = ""

# --- 5. 헤더 및 상단 메뉴 바 ---
st.markdown(f'<div class="fixed-header"><p class="main-title-text">명인제약 생산 시점 관리</p></div>', unsafe_allow_html=True)

nav_cols = st.columns(4) 
with nav_cols[0]:
    if st.button("실시간 현황판", key="n1", use_container_width=True): st.session_state.view = 'main'; st.rerun()
with nav_cols[1]:
    if st.button("완료된 공정 확인", key="nav_2", use_container_width=True): st.session_state.view = 'history'; st.rerun()
with nav_cols[2]:
    if st.button("완료된 공정 확인(선별)", key="nav_3", use_container_width=True): st.session_state.view = 'selection'; st.rerun()
with nav_cols[3]:
    if st.button("모든 공정 이력 확인", key="nav_4", use_container_width=True): st.session_state.view = 'all_history'; st.rerun()

# --- 6. 사이드바 ---
with st.sidebar:
    st.header("🏭 제조 투입")
    sel_p = st.selectbox("제품명 선택", list(master_dict.keys()), key="sel_p_widget")
    lot_in = st.text_input("제조번호(Lot) 입력", key="lot_in_widget", value=st.session_state.reset_lot).strip()
    lot_type = st.selectbox("로트 유형 선택", ["일반로트", "동시PV1", "동시PV2", "동시PV3", "예측PV1", "예측PV2", "예측PV3"], key="lot_type_widget")
    note_in = st.text_area("공정 특이사항 입력", key="note_in_widget", value=st.session_state.reset_note)
    
    is_duplicate = lot_in and ((not curr_df.empty and ((curr_df['Lot'] == lot_in) & (curr_df['제품'].str.strip() == sel_p.strip())).any()) or any(p['Lot'] == lot_in and p['제품'].strip() == sel_p.strip() for p in st.session_state.pending_lots))
    
    if lot_in and is_duplicate: st.error("⚠️ 중복 데이터")
    elif lot_in:
        if st.button("➕ 투입 대기열 추가", use_container_width=True):
            st.session_state.pending_lots.append({'제품': sel_p.strip(), 'Lot': lot_in, '유형': lot_type, '특이사항': note_in, '설비': ""})
            st.session_state.reset_lot = ""; st.rerun()

    if st.session_state.pending_lots:
        st.write("---")
        for idx, p in enumerate(st.session_state.pending_lots):
            c1, c2 = st.columns([8, 2])
            c1.info(f"{p['제품']} | {p['Lot']}")
            if c2.button("❌", key=f"del_{idx}"): st.session_state.pending_lots.pop(idx); st.rerun()
        if st.button("🚀 전체 투입 확정", type="primary", use_container_width=True):
            for p in st.session_state.pending_lots:
                p_clean = p['제품'].strip()
                supabase.table("product_history").insert({"Lot": p['Lot'], "제품": p_clean, "공정": "칭량공정", "상태": "대기", "유형": p['유형'], "특이사항": p['특이사항'], "설비": ""}).execute()
            st.session_state.pending_lots = []; st.rerun()

    st.divider()
    total_active_count = len(curr_df) if not curr_df.empty else 0
    st.write(f"**가동 건수 (총 {total_active_count}건)**")
    for stage in TARGET_STAGES:
        st.write(f"- {stage}: {len(curr_df[curr_df['공정'] == stage]) if not curr_df.empty else 0}건")

    st.write("---")
    with st.popover("🔒 데이터 초기화", use_container_width=True):
        input_pwd = st.text_input("비밀번호 입력", type="password")
        if st.button("🚨 초기화 실행", type="primary", use_container_width=True):
            if input_pwd == "1234":
                supabase.table("product_history").delete().neq("Lot", "sys_clear").execute()
                st.rerun()

# --- 7. 메인 콘텐츠 및 현황판 렌더링 ---
if st.session_state.view == 'main':
    for idx_stage, stage in enumerate(TARGET_STAGES):
        stage_count = len(curr_df[curr_df['공정'] == stage]) if not curr_df.empty else 0
        st.markdown(f'<div class="stage-bar">▶ {stage} ({stage_count}건)</div>', unsafe_allow_html=True)
        
        m_items = pd.DataFrame()
        if not curr_df.empty:
            m_items = curr_df[curr_df['공정'] == stage]
        
        if stage == "칭량공정":
            if not m_items.empty:
                total_items = len(m_items)
                for chunk_idx in range(0, total_items, 10):
                    chunk_df = m_items.iloc[chunk_idx:chunk_idx+10]
                    cols = st.columns(10)
                    for idx, (_, row) in enumerate(chunk_df.iterrows()):
                        with cols[idx]:
                            with st.container(border=True):
                                prod_name = str(row['제품']).strip()
                                st.markdown(f"<p class='card-text-10px'>{prod_name}</p>", unsafe_allow_html=True)
                                st.markdown(f"<p class='card-text-l-10px'>{row['Lot']}</p>", unsafe_allow_html=True)
                                
                                prod_clean_key = prod_name.replace(" ", "")
                                current_stock_val = stock_dict.get(prod_clean_key, "정보없음")
                                if current_stock_val == "정보없음":
                                    st.markdown(f"<p class='stock-text-highlight'>재고: <span style='color:#ef4444;'>정보없음</span></p>", unsafe_allow_html=True)
                                else:
                                    st.markdown(f"<p class='stock-text-highlight'>재고: {current_stock_val}</p>", unsafe_allow_html=True)
                                
                                if row['유형'] not in ['일반로트', '일반', '']: st.markdown(f"<p class='lot-type-highlight'>{row['유형']}</p>", unsafe_allow_html=True)
                                if row['특이사항']: st.markdown(f"<p class='info-text-10px'>📝 {row['특이사항']}</p>", unsafe_allow_html=True)
                                st.markdown(f"<div class='status-bar {'bg-waiting' if row['상태']=='대기' else 'bg-progress' if row['상태']=='진행중' else 'bg-paused'}'>{row['상태']}</div>", unsafe_allow_html=True)
                                
                                if row['상태'] == '대기':
                                    if st.button("시작", key=f"start_act_{row['Row']}", use_container_width=True): 
                                        supabase.table("product_history").update({"상태": "진행중", "시작시간": get_now_kst()}).eq("id", row['Row']).execute()
                                        st.rerun()
                                elif row['상태'] == '진행중':
                                    if st.button("대기", key=f"pause_act_{row['Row']}", use_container_width=True): 
                                        supabase.table("product_history").update({"상태": "지연"}).eq("id", row['Row']).execute()
                                        st.rerun()
                                    
                                    n_stg = None
                                    for i in range(idx_stage + 1, len(TARGET_STAGES)):
                                        check_stage = TARGET_STAGES[i].strip()
                                        if master_dict.get(prod_name, {}).get(check_stage) or check_stage in ["과립공정"]:
                                            n_stg = check_stage
                                            break
                                            
                                    n_machines = master_dict.get(prod_name, {}).get(n_stg, []) if n_stg else []
                                    if len(n_machines) > 1:
                                        with st.popover("완료", use_container_width=True):
                                            for nm in n_machines:
                                                nm_clean = nm.strip()
                                                if st.button(nm_clean, key=f"next_act_{row['Row']}_{nm_clean}", use_container_width=True):
                                                    dur = str(datetime.strptime(get_now_kst(), '%Y-%m-%d %H:%M') - datetime.strptime(row['시작시간'], '%Y-%m-%d %H:%M'))
                                                    supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": n_stg, "상태": "대기", "유형": row['유형'], "특이사항": row['특이사항'], "설비": nm_clean}).execute()
                                                    supabase.table("product_history").update({"상태": "완료", "종료시간": get_now_kst(), "소요시간": dur}).eq("id", row['Row']).execute()
                                                    st.rerun()
                                    else:
                                        if st.button("완료", key=f"end_act_{row['Row']}", use_container_width=True):
                                            dur = str(datetime.strptime(get_now_kst(), '%Y-%m-%d %H:%M') - datetime.strptime(row['시작시간'], '%Y-%m-%d %H:%M'))
                                            next_m = n_machines[0].strip() if n_machines else ""
                                            if n_stg:
                                                supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": n_stg, "상태": "대기", "유형": row['유형'], "특이사항": row['특이사항'], "설비": next_m}).execute()
                                            supabase.table("product_history").update({"상태": "완료", "종료시간": get_now_kst(), "소요시간": dur}).eq("id", row['Row']).execute()
                                            st.rerun()
                                elif row['상태'] == '지연':
                                    if st.button("재시작", key=f"resume_act_{row['Row']}", use_container_width=True): 
                                        supabase.table("product_history").update({"상태": "진행중"}).eq("id", row['Row']).execute()
                                        st.rerun()
            else:
                st.caption("대기 중인 칭량 작업이 없습니다.")

        else:
            cols = st.columns(10)
            stage_machines = MACHINE_MAP[stage]
            for idx in range(10):
                if idx < len(stage_machines):
                    m_clean = stage_machines[idx].strip()
                    with cols[idx]:
                        st.markdown(f"<div class='machine-title'>{m_clean}</div>", unsafe_allow_html=True)
                        m_specific_items = pd.DataFrame()
                        if not m_items.empty:
                            m_specific_items = m_items[m_items['설비'].str.strip().str.upper() == m_clean.upper()]
                        
                        for _, row in m_specific_items.iterrows():
                            with st.container(border=True):
                                prod_name = str(row['제품']).strip()
                                st.markdown(f"<p class='card-text-10px'>{prod_name}</p>", unsafe_allow_html=True)
                                st.markdown(f"<p class='card-text-l-10px'>{row['Lot']}</p>", unsafe_allow_html=True)
                                
                                prod_clean_key = prod_name.replace(" ", "")
                                current_stock_val = stock_dict.get(prod_clean_key, "정보없음")
                                if current_stock_val == "정보없음":
                                    st.markdown(f"<p class='stock-text-highlight'>재고: <span style='color:#ef4444;'>정보없음</span></p>", unsafe_allow_html=True)
                                else:
                                    st.markdown(f"<p class='stock-text-highlight'>재고: {current_stock_val}</p>", unsafe_allow_html=True)
                                
                                if row['유형'] not in ['일반로트', '일반', '']: st.markdown(f"<p class='lot-type-highlight'>{row['유형']}</p>", unsafe_allow_html=True)
                                if row['특이사항']: st.markdown(f"<p class='info-text-10px'>📝 {row['특이사항']}</p>", unsafe_allow_html=True)
                                st.markdown(f"<div class='status-bar {'bg-waiting' if row['상태']=='대기' else 'bg-progress' if row['상태']=='진행중' else 'bg-paused'}'>{row['상태']}</div>", unsafe_allow_html=True)
                                
                                if row['상태'] == '대기':
                                    if st.button("시작", key=f"start_act_{row['Row']}", use_container_width=True): 
                                        supabase.table("product_history").update({"상태": "진행중", "시작시간": get_now_kst()}).eq("id", row['Row']).execute()
                                        st.rerun()
                                    with st.popover("변경", use_container_width=True):
                                        valid_machines = master_dict.get(prod_name, {}).get(stage, [])
                                        for nm in valid_machines:
                                            nm_clean = nm.strip()
                                            if nm_clean.upper() != str(row['설비']).strip().upper() and st.button(nm_clean, key=f"ch_act_{row['Row']}_{nm_clean}", use_container_width=True): 
                                                supabase.table("product_history").update({"설비": nm_clean}).eq("id", row['Row']).execute()
                                                st.rerun()
                                elif row['상태'] == '진행중':
                                    if st.button("대기", key=f"pause_act_{row['Row']}", use_container_width=True): 
                                        supabase.table("product_history").update({"상태": "지연"}).eq("id", row['Row']).execute()
                                        st.rerun()
                                    
                                    n_stg = None
                                    for i in range(idx_stage + 1, len(TARGET_STAGES)):
                                        check_stage = TARGET_STAGES[i].strip()
                                        if master_dict.get(prod_name, {}).get(check_stage):
                                            n_stg = check_stage
                                            break
                                            
                                    n_machines = master_dict.get(prod_name, {}).get(n_stg, []) if n_stg else []
                                    if len(n_machines) > 1:
                                        with st.popover("완료", use_container_width=True):
                                            for nm in n_machines:
                                                nm_clean = nm.strip()
                                                if st.button(nm_clean, key=f"next_act_{row['Row']}_{nm_clean}", use_container_width=True):
                                                    dur = str(datetime.strptime(get_now_kst(), '%Y-%m-%d %H:%M') - datetime.strptime(row['시작시간'], '%Y-%m-%d %H:%M'))
                                                    supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": n_stg, "상태": "대기", "유형": row['유형'], "특이사항": row['특이사항'], "설비": nm_clean}).execute()
                                                    supabase.table("product_history").update({"상태": "1팀종료" if "외관선별" in str(n_stg) else "완료", "종료시간": get_now_kst(), "소요시간": dur}).eq("id", row['Row']).execute()
                                                    st.rerun()
                                    else:
                                        if st.button("완료", key=f"end_act_{row['Row']}", use_container_width=True):
                                            dur = str(datetime.strptime(get_now_kst(), '%Y-%m-%d %H:%M') - datetime.strptime(row['시작시간'], '%Y-%m-%d %H:%M'))
                                            if n_stg: 
                                                next_m = n_machines[0].strip() if n_machines else ""
                                                supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": n_stg, "상태": "대기", "유형": row['유형'], "특이사항": row['특이사항'], "설비": next_m}).execute()
                                            supabase.table("product_history").update({"상태": "1팀종료" if "외관선별" in str(n_stg) else "완료", "종료시간": get_now_kst(), "소요시간": dur}).eq("id", row['Row']).execute()
                                            st.rerun()
                                elif row['상태'] == '지연':
                                    if st.button("재시작", key=f"resume_act_{row['Row']}", use_container_width=True): 
                                        supabase.table("product_history").update({"상태": "진행중"}).eq("id", row['Row']).execute()
                                        st.rerun()
                else:
                    with cols[idx]:
                        st.write("") 
else:
    title_map = {"history": "완료된 공정 확인", "selection": "완료된 공정 확인(선별)", "all_history": "모든 공정 이력 확인"}
    st.header(f"📋 {title_map[st.session_state.view]}")
    
    if st.session_state.view == 'history':
        display_df = log_df[log_df['상태'] == '1팀종료'].copy() if not log_df.empty else pd.DataFrame()
    elif st.session_state.view == 'selection':
        display_df = log_df[(log_df['공정'] == '외관선별공정') & (log_df['상태'] == '완료')].copy() if not log_df.empty else pd.DataFrame()
    else:
        display_df = all_raw_df.copy() if not all_raw_df.empty else pd.DataFrame()
    
    if not display_df.empty:
        if st.session_state.view == 'all_history':
            filter_cols = st.columns([6, 4])
            with filter_cols[0]:
                sel_filter = st.selectbox("🔍 제품명 검색", ["전체 보기"] + sorted(display_df['제품'].unique().tolist()), key=f"filter_{st.session_state.view}")
            with filter_cols[1]:
                st.write("") 
                only_live = st.toggle("⚡ 현재 실시간 현황판에 있는 로트만 보기", value=False)
            
            if sel_filter != "전체 보기": 
                display_df = display_df[display_df['제품'] == sel_filter]
                
            if only_live and not curr_df.empty:
                live_stage_combos = (curr_df['제품'].str.strip() + "_" + curr_df['Lot'].str.strip() + "_" + curr_df['공정'].str.strip()).unique().tolist()
                display_df = display_df[(display_df['제품'].str.strip() + "_" + display_df['Lot'].str.strip() + "_" + display_df['공정'].str.strip()).isin(live_stage_combos)]
        else:
            sel_filter = st.selectbox("🔍 제품명 검색", ["전체 보기"] + sorted(display_df['제품'].unique().tolist()), key=f"filter_{st.session_state.view}")
            if sel_filter != "전체 보기": 
                display_df = display_df[display_df['제품'] == sel_filter]
                
        avail_cols = [c for c in ['Lot', '제품', '공정', '상태', '시작시간', '종료시간', '소요시간', '유형', '특이사항', '설비'] if c in display_df.columns]
        st.dataframe(display_df[avail_cols].sort_index(ascending=False), use_container_width=True)
    else: 
        st.info("데이터가 없습니다.")
