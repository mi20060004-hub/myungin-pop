import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client

# --- 1. 페이지 설정 ---
st.set_page_config(layout="wide", page_title="명인제약 생산 시점 관리")

# --- 2. CSS 스타일 (버튼 초슬림 압착 및 재고/재공 텍스트 레이아웃 + 검색 하이라이트 클래스 추가) ---
st.markdown("""
<style>
/* 부드러운 스크롤 이동 효과 적용 */
html {
    scroll-behavior: smooth;
}
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

/* 자동 스크롤 시 헤더에 가려지지 않도록 상단 여백 보정 */
.stage-bar {
    scroll-margin-top: 80px;
    color: white; padding: 8px 13px; border-radius: 6px; 
    font-size: 18px; font-weight: 700; margin-top: 20px; margin-bottom: 10px; 
    background: linear-gradient(90deg, #065f46 0%, #10b981 100%);
}
.machine-title {
    background: #f1f5f9; text-align: center; font-size: 16px !important; 
    font-weight: 800; border-radius: 6px; margin-bottom: 8px; 
    border: 2px solid #cbd5e1; min-height: 40px; 
    display: flex; align-items: center; justify-content: center; color: #1e293b; 
}

.card-text-10px { font-size: 15px !important; font-weight: 800; margin: 0; text-align: center; line-height: 1.2; }
.card-text-l-10px { font-size: 15px !important; color: #1e40af; font-weight: 700; text-align: center; margin: 0; line-height: 1.2; }
.card-text-date { font-size: 12px !important; color: #64748b; font-weight: 700; text-align: center; margin: 1px 0; line-height: 1.2; }
.info-text-10px { font-size: 10px !important; color: #475569; margin: 1px 0; text-align: center; line-height: 1.2; }

/* 재고 상태별 3단 분리 클래스 */
.stock-red { font-size: 12px !important; color: #ef4444 !important; font-weight: 800 !important; text-align: center; margin: 1px 0; line-height: 1.2; }
.stock-green { font-size: 12px !important; color: #004d40 !important; font-weight: 800 !important; text-align: center; margin: 1px 0; line-height: 1.2; }
.stock-black { font-size: 12px !important; color: #1e293b !important; font-weight: 800 !important; text-align: center; margin: 1px 0; line-height: 1.2; }

.wip-blue { font-size: 12px !important; color: #2563eb !important; font-weight: 800 !important; text-align: center; margin: 1px 0; line-height: 1.2; }
.wip-black { font-size: 12px !important; color: #475569 !important; font-weight: 800 !important; text-align: center; margin: 1px 0; line-height: 1.2; }

.lot-type-highlight { font-size: 15px !important; color: #ef4444 !important; font-weight: 800 !important; text-align: center; margin: 1px 0; line-height: 1.2; }
.status-bar { font-size: 10px; font-weight: 800; color: white; text-align: center; padding: 2px 0; border-radius: 3px; margin-bottom: 3px; }
.bg-waiting { background-color: #3b82f6; }
.bg-progress { background-color: #ef4444; }
.bg-paused { background-color: #f59e0b; }

div[data-testid="stDataFrame"] td, div[data-testid="stDataFrame"] th { font-size: 16px !important; }

.main div[data-testid="stVerticalBlock"] div[data-testid="stPopover"] button p {
    margin: 0px !important; padding: 0px !important; line-height: 16px !important; font-size: 11px !important; font-weight: 800 !important; display: flex !important; align-items: center !important; justify-content: center !important;
}

/* 🌟 검색 하이라이트 CSS 스타일 강제 주입 */
.search-highlighted {
    border: 7px solid #ff6b00 !important;
    box-shadow: 0 0 15px rgba(255, 107, 0, 0.8) !important;
}

.search-dimmed {
    opacity: 0.4 !important;
    transition: opacity 0.2s ease-in-out;
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
    "정립혼합대기창고": [],
    "정립공정": ["Comil0112", "Comil0212", "Comil0312", "파워밀", "오실레이터"],
    "혼합공정": ["PM1000", "PM2000", "드럼혼합기"],
    "반제품창고": [],  
    "타정공정": ["킬리안", "63S-3", "41S", "63S-1", "PR1023", "MRC45", "45S", "63S-2", "31S", "PH300"],
    "캡슐공정": ["SF150N", "보쉬충전기", "PTK충전기", "SF35"],
    "질량선별공정": ["CWI150", "세종질량선별기"],
    "코팅공정": ["SFC150FH", "SFC170FH", "SFC170FSH", "SFC130FSH", "V150", "SFC80", "수동코팅기"],
    "인쇄공정": ["정제인쇄기"],
    "외관선별공정": ["비즈윌구형", "비즈윌신형", "엔클로니구형", "엔클로니신형", "수동선별기", "캡슐외관선별기"]
}
TARGET_STAGES = list(MACHINE_MAP.keys())

def get_now_kst():
    return (datetime.now(timezone(timedelta(hours=9)))).strftime('%Y-%m-%d %H:%M')

def get_today_date_kst():
    return datetime.now(timezone(timedelta(hours=9))).date()

def get_elapsed_days_str(date_val):
    if pd.isna(date_val):
        return ""
    date_str = str(date_val).strip()
    if not date_str or date_str.upper() == "NONE" or date_str == "-":
        return ""
    try:
        target_dt = datetime.strptime(date_str[:10], '%Y-%m-%d').date()
        today_dt = get_today_date_kst()
        delta_days = (today_dt - target_dt).days
        return f" ({delta_days}일째)"
    except Exception:
        return ""

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
        s_data = supabase.table("product_stock").select("적요, \"재고 월수\", \"재공 월수\"").order("id", desc=True).execute()
        if s_data.data:
            s_df = pd.DataFrame(s_data.data)
            s_df = s_df.drop_duplicates(subset=['적요'], keep='first')
            for _, s_row in s_df.iterrows():
                clean_stock_p = str(s_row['적요']).replace(" ", "").strip()
                stock_dict[clean_stock_p] = {
                    "재고": str(s_row.get('재고 월수', '정보없음')).strip(),
                    "재공": str(s_row.get('재공 월수', '정보없음')).strip()
                }
    except Exception:
        pass

    # [수정됨] 1000건 제한을 피하기 위해 전체 데이터를 루프를 돌며 모두 가져옴
    count_res = supabase.table("product_history").select("id", count='exact').range(0, 0).execute()
    total_count = count_res.count if count_res.count else 0
    
    all_data = []
    # 1000건씩 나누어 순차적으로 데이터를 가져와 병합
    for i in range(0, total_count, 1000):
        res = supabase.table("product_history").select("*").order("id", desc=True).range(i, i + 999).execute()
        if res.data:
            all_data.extend(res.data)
            
    if not all_data:
        return master_dict, stock_dict, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
    all_raw_df = pd.DataFrame(all_data)
    if 'id' in all_raw_df.columns: all_raw_df['Row'] = all_raw_df['id']
    
    curr_df = all_raw_df[~all_raw_df['상태'].isin(['완료', '1팀종료', '폐기'])].copy()
    log_df = all_raw_df[all_raw_df['상태'].isin(['완료', '1팀종료'])].copy()
    return master_dict, stock_dict, curr_df, log_df, all_raw_df

master_dict, stock_dict, curr_df, log_df, all_raw_df = load_data()

if 'pending_lots' not in st.session_state: st.session_state.pending_lots = []
if 'view' not in st.session_state: st.session_state.view = 'main'
if 'reset_lot' not in st.session_state: st.session_state.reset_lot = ""
if 'reset_type' not in st.session_state: st.session_state.reset_type = "일반로트"
if 'reset_note' not in st.session_state: st.session_state.reset_note = ""

# --- 5. 헤더 및 상단 메뉴 바 ---
st.markdown(f'<div class="fixed-header"><p class="main-title-text">명인제약 생산 시점 관리&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<<버튼 누르기 전 새로고침(F5)해주세요>></p></div>', unsafe_allow_html=True)
nav_cols = st.columns(5) 
with nav_cols[0]:
    if st.button("📋 실시간 현황판", key="n1", use_container_width=True): st.session_state.view = 'main'; st.rerun()
with nav_cols[1]:
    if st.button("✅ 완료된 공정 확인(1팀)", key="nav_2", use_container_width=True): st.session_state.view = 'history'; st.rerun()
with nav_cols[2]:
    if st.button("🏷️ 완료된 공정 확인(선별)", key="nav_3", use_container_width=True): st.session_state.view = 'selection'; st.rerun()
with nav_cols[3]:
    if st.button("🗃️ 모든 공정 이력 확인", key="nav_4", use_container_width=True): st.session_state.view = 'all_history'; st.rerun()
with nav_cols[4]:
    st.link_button("🌐일재고/재공현황", "https://myungin-pp.appsmith.com/app/untitled-application-1/page1-6a27d4bd9e8e4df7ae2343bf?environment=production", use_container_width=True)

# --- 6. 사이드바 ---
with st.sidebar:
    st.header("🏭 제조 투입")
    sel_p = st.selectbox("제품명 선택", list(master_dict.keys()), key="sel_p_widget")
    lot_in = st.text_input("제조번호(Lot) 입력", key="lot_in_widget", value=st.session_state.reset_lot).strip()
    
    date_in = st.date_input("제조일자 선택", value=get_today_date_kst(), key="date_in_widget")
    date_str = date_in.strftime('%Y-%m-%d')
    
    lot_type = st.selectbox("로트 유형 선택", ["일반로트", "동시PV1", "동시PV2", "동시PV3", "예측PV1", "예측PV2", "예측PV3"], key="lot_type_widget")
    note_in = st.text_area("공정 특이사항 입력", key="note_in_widget", value=st.session_state.reset_note)
    
    is_duplicate = lot_in and ((not curr_df.empty and ((curr_df['Lot'] == lot_in) & (curr_df['제품'].str.strip() == sel_p.strip())).any()) or any(p['Lot'] == lot_in and p['제품'].strip() == sel_p.strip() for p in st.session_state.pending_lots))
    
    if lot_in and is_duplicate: st.error("⚠️ 중복 데이터")
    elif lot_in:
        if st.button("➕ 투입 대기열 추가", use_container_width=True):
            st.session_state.pending_lots.append({'제품': sel_p.strip(), 'Lot': lot_in, '제조일자': date_str, '유형': lot_type, '특이사항': note_in, '설비': ""})
            st.session_state.reset_lot = ""; st.rerun()

    if st.session_state.pending_lots:
        st.write("---")
        for idx, p in enumerate(st.session_state.pending_lots):
            c1, c2 = st.columns([8, 2])
            c1.info(f"{p['제품']} | {p['Lot']} ({p['제조일자']})")
            if c2.button("❌", key=f"del_{idx}"): st.session_state.pending_lots.pop(idx); st.rerun()
        if st.button("🚀 전체 투입 확정", type="primary", use_container_width=True):
            for p in st.session_state.pending_lots:
                p_clean = p['제품'].strip()
                supabase.table("product_history").insert({"Lot": p['Lot'], "제품": p_clean, "공정": "칭량공정", "상태": "대기", "제조일자": p['제조일자'], "유형": p['유형'], "특이사항": p['특이사항'], "설비": ""}).execute()
            st.session_state.pending_lots = []; st.rerun()

    st.divider()
    
    # 🌟 [신규 추가] 실시간 현황판 제품 위치 추적 검색창
    search_keyword = ""
    if st.session_state.view == 'main':
        st.markdown("<div style='font-size:16px; font-weight:800; color:#ff6b00; margin-bottom:5px;'>🔍 현황판 제품 위치 추적</div>", unsafe_allow_html=True)
        search_keyword = st.text_input("검색어 입력 (제품명 또는 Lot)", placeholder="예: 톨비스정 또는 26001", key="live_search_box").strip()
        st.divider()

    if st.session_state.view == 'main':
        total_active_count = len(curr_df) if not curr_df.empty else 0
        st.markdown(f"<div style='font-size:16px; font-weight:800; color:#1e3a8a; margin-bottom:5px;'>실시간 가동 건수 (총 {total_active_count}건)</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:14px; font-weight:700; color:#475569; margin-bottom:8px;'>공정 바로가기 (클릭 시 이동)</div>", unsafe_allow_html=True)
        
        for stage in TARGET_STAGES:
            stage_id = stage.replace(" ", "")
            single_stage_count = len(curr_df[curr_df['공정'] == stage]) if not curr_df.empty else 0
            
            st.markdown(f"""
            <a href="#{stage_id}" target="_self" style="text-decoration:none;">
                <button style="width:100%; padding:6px 10px; margin:3px 0; font-size:14px; font-weight:800; cursor:pointer; background-color:#f8fafc; border:1px solid #cbd5e1; border-radius:6px; color:#0f172a; display:flex; justify-content:space-between; align-items:center; box-shadow:0 1px 2px rgba(0,0,0,0.05);">
                    <span>{stage}</span> 
                    <span style="background-color:#1e3a8a; color:white; padding:2px 8px; border-radius:12px; font-size:12px; font-weight:800; min-width:35px; text-align:center;">{single_stage_count}건</span>
                </button>
            </a>
            """, unsafe_allow_html=True)
        st.write("---")

    with st.popover("🔒 데이터 초기화", use_container_width=True):
        input_pwd = st.text_input("비밀번호 입력", type="password")
        if st.button("🚨 초기화 실행", type="primary", use_container_width=True):
            if input_pwd == "1234":
                supabase.table("product_history").delete().neq("Lot", "sys_clear").execute()
                st.rerun()

# --- 7. 재고 및 재공 월수 통합 출력 엔진 헬퍼 함수 ---
def render_stock_and_wip_html(prod_name):
    prod_clean = prod_name.replace(" ", "")
    stock_info = stock_dict.get(prod_clean, {"재고": "정보없음", "재공": "정보없음"})
    s_val = stock_info["재고"]
    w_val = stock_info["재공"]
    
    if s_val == "정보없음" or s_val == "None" or not s_val:
        html_str = "<p class='stock-black'>재고: 정보없음</p>"
    else:
        try:
            if float(s_val) <= 1.0: html_str = f"<p class='stock-red'>재고: {s_val}개월</p>"
            else: html_str = f"<p class='stock-green'>재고: {s_val}개월</p>"
        except ValueError: html_str = f"<p class='stock-green'>재고: {s_val}</p>"
        
    if w_val == "정보없음" or w_val == "None" or not w_val:
        html_str += "<p class='wip-black'>재공: 정보없음</p>"
    else:
        try: html_str += f"<p class='wip-blue'>재공(합산): {w_val}개월</p>"
        except ValueError: html_str += f"<p class='wip-blue'>재공(합산): {w_val}</p>"
        
    return html_str

# --- 8. 메인 콘텐츠 및 현황판 렌더링 ---
if st.session_state.view == 'main':
    for idx_stage, stage in enumerate(TARGET_STAGES):
        stage_count = len(curr_df[curr_df['공정'] == stage]) if not curr_df.empty else 0
        
        stage_id = stage.replace(" ", "")
        st.markdown(f'<div id="{stage_id}" class="stage-bar">▶ {stage} ({stage_count}건)</div>', unsafe_allow_html=True)
        
        m_items = pd.DataFrame()
        if not curr_df.empty:
            m_items = curr_df[curr_df['공정'] == stage].copy()
            
            def calculate_sort_score(row):
                p_clean = str(row['제품']).replace(" ", "").strip()
                s_val = stock_dict.get(p_clean, {"재고": "정보없음"})["재고"]
                is_progress = 0 if str(row['상태']).strip() == "진행중" else 1
                
                if s_val == "정보없음":
                    numeric_stock = -1.0
                else:
                    try:
                        numeric_stock = float(s_val)
                    except ValueError:
                        numeric_stock = 999999.0
                
                lot_str = str(row['Lot']).strip()
                try:
                    numeric_lot = float(lot_str)
                except ValueError:
                    numeric_lot = 999999.0
                        
                return (is_progress, numeric_stock, numeric_lot)

            if not m_items.empty:
                m_items['sort_score'] = m_items.apply(calculate_sort_score, axis=1)
                m_items = m_items.sort_values(by='sort_score', ascending=True).drop(columns=['sort_score'])
        
        if stage in ["칭량공정", "정립혼합대기창고", "반제품창고"]:
            if not m_items.empty:
                total_items = len(m_items)
                for chunk_idx in range(0, total_items, 10):
                    chunk_df = m_items.iloc[chunk_idx:chunk_idx+10]
                    cols = st.columns(10)
                    for idx, (_, row) in enumerate(chunk_df.iterrows()):
                        with cols[idx]:
                            # 🌟 [신규 추가] 실시간 검색 매칭 로직 판별
                            prod_name = str(row['제품']).strip()
                            lot_num = str(row['Lot']).strip()
                            
                            border_class = ""
                            if search_keyword:
                                if search_keyword.lower() in prod_name.lower() or search_keyword.lower() in lot_num.lower():
                                    border_class = "search-highlighted"
                                else:
                                    border_class = "search-dimmed"
                                    
                            with st.container(border=True):
                                # HTML Wrapper 주입하여 테두리 이중 지배 해결
                                st.markdown(f"<div class='{border_class}'>", unsafe_allow_html=True)
                                st.markdown(f"<p class='card-text-10px'>{prod_name}</p>", unsafe_allow_html=True)
                                st.markdown(f"<p class='card-text-l-10px'>{lot_num}</p>", unsafe_allow_html=True)
                                
                                p_date = str(row.get('제조일자', '')).strip() if not pd.isna(row.get('제조일자')) else ""
                                if p_date and p_date.upper() != "NONE" and p_date != "-":
                                    elapsed_suffix = get_elapsed_days_str(p_date)
                                    st.markdown(f"<p class='card-text-date'>{p_date}{elapsed_suffix}</p>", unsafe_allow_html=True)
                                
                                st.markdown(render_stock_and_wip_html(prod_name), unsafe_allow_html=True)
                                
                                if row['유형'] not in ['일반로트', '일반', '']: st.markdown(f"<p class='lot-type-highlight'>{row['유형']}</p>", unsafe_allow_html=True)
                                if row['특이사항'] and not pd.isna(row['특이사항']): st.markdown(f"<p class='info-text-10px'>📝 {row['특이사항']}</p>", unsafe_allow_html=True)
                                st.markdown(f"<div class='status-bar {'bg-waiting' if row['상태']=='대기' else 'bg-progress' if row['상태']=='진행중' else 'bg-paused'}'>{row['상태']}</div>", unsafe_allow_html=True)
                                
                                c_type = "" if pd.isna(row['유형']) else str(row['유형'])
                                c_note = "" if pd.isna(row['특이사항']) else str(row['특이사항'])
                                c_date_val = "" if pd.isna(row.get('제조일자')) else str(row.get('제조일자'))
                                
                                if stage == "정립혼합대기창고":
                                    # 1순위: 정립, 2순위: 혼합, 3순위: 캡슐 탐색
                                    target_stage = None
                                    pop_machines = []
                                    
                                    for candidate in ["정립공정", "혼합공정", "캡슐공정"]:
                                        machines = master_dict.get(prod_name, {}).get(candidate, [])
                                        if machines:
                                            target_stage = candidate
                                            pop_machines = machines
                                            break
                                    
                                    with st.popover("공정이동", use_container_width=True):
                                        if target_stage and pop_machines:
                                            for pm in pop_machines:
                                                pm_clean = pm.strip()
                                                if st.button(pm_clean, key=f"wh_wh_move_{row['Row']}_{pm_clean}", use_container_width=True):
                                                    supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": target_stage, "상태": "대기", "제조일자": c_date_val, "유형": c_type, "특이사항": c_note, "설비": pm_clean}).execute()
                                                    supabase.table("product_history").update({"상태": "완료", "종료시간": get_now_kst(), "소요시간": "창고출고"}).eq("id", row['Row']).execute()
                                                    st.rerun()
                                        else:
                                            st.caption("다음 공정 설비 없음")
                                            if st.button("강제 캡슐공정 이동", key=f"wh_wh_force_{row['Row']}", use_container_width=True):
                                                supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": "캡슐공정", "상태": "대기", "제조일자": c_date_val, "유형": c_type, "특이사항": c_note, "설비": ""}).execute()
                                                supabase.table("product_history").update({"상태": "완료", "종료시간": get_now_kst(), "소요시간": "강제출고"}).eq("id", row['Row']).execute()
                                                st.rerun()

                                elif stage == "반제품창고":
                                    next_pop_stage = None
                                    for target_next in ["타정공정", "캡슐공정"]:
                                        if master_dict.get(prod_name, {}).get(target_next):
                                            next_pop_stage = target_next
                                            break
                                    if not next_pop_stage:
                                        next_pop_stage = "타정공정"
                                        
                                    pop_machines = master_dict.get(prod_name, {}).get(next_pop_stage, [])
                                    
                                    with st.popover("공정이동", use_container_width=True):
                                        if pop_machines:
                                            for pm in pop_machines:
                                                pm_clean = pm.strip()
                                                if st.button(pm_clean, key=f"wh_move_{row['Row']}_{pm_clean}", use_container_width=True):
                                                    supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": next_pop_stage, "상태": "대기", "제조일자": c_date_val, "유형": c_type, "특이사항": c_note, "설비": pm_clean}).execute()
                                                    supabase.table("product_history").update({"상태": "완료", "종료시간": get_now_kst(), "소요시간": "창고출고"}).eq("id", row['Row']).execute()
                                                    st.rerun()
                                        else:
                                            st.caption("지정 설비 없음")
                                            if st.button("강제 타정공정 이동", key=f"wh_force_{row['Row']}", use_container_width=True):
                                                supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": "타정공정", "상태": "대기", "제조일자": c_date_val, "유형": c_type, "특이사항": c_note, "설비": ""}).execute()
                                                supabase.table("product_history").update({"상태": "완료", "종료시간": get_now_kst(), "소요시간": "강제출고"}).eq("id", row['Row']).execute()
                                                st.rerun()
                                else:
                                    if row['상태'] == '대기':
                                        if st.button("시작", key=f"start_act_{row['Row']}", use_container_width=True): 
                                            supabase.table("product_history").update({"상태": "진행중", "시작시간": get_now_kst()}).eq("id", row['Row']).execute()
                                            st.rerun()
                                    elif row['상태'] == '진행중':
                                        if st.button("대기", key=f"pause_act_{row['Row']}", use_container_width=True): 
                                            supabase.table("product_history").update({"상태": "지연"}).eq("id", row['Row']).execute()
                                            st.rerun()
                                        
                                        if st.button("완료", key=f"end_act_{row['Row']}", use_container_width=True):
                                            dur = str(datetime.strptime(get_now_kst(), '%Y-%m-%d %H:%M') - datetime.strptime(row['시작시간'], '%Y-%m-%d %H:%M'))
                                            
                                            has_granule = bool(master_dict.get(prod_name, {}).get("과립공정", []))
                                            has_dry = bool(master_dict.get(prod_name, {}).get("건조공정", []))
                                            
                                            if not has_granule and not has_dry:
                                                supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": "정립혼합대기창고", "상태": "대기", "제조일자": c_date_val, "유형": c_type, "특이사항": c_note, "설비": ""}).execute()
                                            else:
                                                n_stg = None
                                                for i in range(idx_stage + 1, len(TARGET_STAGES)):
                                                    check_stage = TARGET_STAGES[i].strip()
                                                    if master_dict.get(prod_name, {}).get(check_stage):
                                                        n_stg = check_stage
                                                        break
                                                next_m = master_dict.get(prod_name, {}).get(n_stg, [])[0].strip() if (n_stg and master_dict.get(prod_name, {}).get(n_stg, [])) else ""
                                                if n_stg:
                                                    supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": n_stg, "상태": "대기", "제조일자": c_date_val, "유형": c_type, "특이사항": c_note, "설비": next_m}).execute()
                                            
                                            supabase.table("product_history").update({"상태": "완료", "종료시간": get_now_kst(), "소요시간": dur}).eq("id", row['Row']).execute()
                                            st.rerun()
                                    elif row['상태'] == '지연':
                                        if st.button("재시작", key=f"resume_act_{row['Row']}", use_container_width=True): 
                                            supabase.table("product_history").update({"상태": "진행중"}).eq("id", row['Row']).execute()
                                            st.rerun()
                                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.caption(f"대기 중인 {stage} 작업이 없습니다.")

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
                            # 🌟 [신규 추가] 실시간 검색 매칭 로직 판별
                            prod_name = str(row['제품']).strip()
                            lot_num = str(row['Lot']).strip()
                            
                            border_class = ""
                            if search_keyword:
                                if search_keyword.lower() in prod_name.lower() or search_keyword.lower() in lot_num.lower():
                                    border_class = "search-highlighted"
                                else:
                                    border_class = "search-dimmed"
                                    
                            with st.container(border=True):
                                st.markdown(f"<div class='{border_class}'>", unsafe_allow_html=True)
                                st.markdown(f"<div class='card-text-10px'>{prod_name}</div>", unsafe_allow_html=True)
                                st.markdown(f"<div class='card-text-l-10px'>{lot_num}</div>", unsafe_allow_html=True)
                                
                                p_date = str(row.get('제조일자', '')).strip() if not pd.isna(row.get('제조일자')) else ""
                                if p_date and p_date.upper() != "NONE" and p_date != "-":
                                    elapsed_suffix = get_elapsed_days_str(p_date)
                                    st.markdown(f"<div class='machine-title' style='display:none;'></div><div class='card-text-date'>{p_date}{elapsed_suffix}</div>", unsafe_allow_html=True)
                                
                                st.markdown(render_stock_and_wip_html(prod_name), unsafe_allow_html=True)
                                
                                if row['유형'] not in ['일반로트', '일반', '']: st.markdown(f"<p class='lot-type-highlight'>{row['유형']}</p>", unsafe_allow_html=True)
                                if row['특이사항'] and not pd.isna(row['특이사항']): st.markdown(f"<div class='info-text-10px'>📝 {row['특이사항']}</div>", unsafe_allow_html=True)
                                st.markdown(f"<div class='status-bar {'bg-waiting' if row['상태']=='대기' else 'bg-progress' if row['상태']=='진행중' else 'bg-paused'}'>{row['상태']}</div>", unsafe_allow_html=True)
                                
                                c_type = "" if pd.isna(row['유형']) else str(row['유형'])
                                c_note = "" if pd.isna(row['특이사항']) else str(row['특이사항'])
                                c_date_val = "" if pd.isna(row.get('제조일자')) else str(row.get('제조일자'))
                                
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
                                    
                                    if stage == "건조공정":
                                        if st.button("완료", key=f"end_act_{row['Row']}", use_container_width=True):
                                            dur = str(datetime.strptime(get_now_kst(), '%Y-%m-%d %H:%M') - datetime.strptime(row['시작시간'], '%Y-%m-%d %H:%M'))
                                            supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": "정립혼합대기창고", "상태": "대기", "제조일자": c_date_val, "유형": c_type, "특이사항": c_note, "설비": ""}).execute()
                                            supabase.table("product_history").update({"상태": "완료", "종료시간": get_now_kst(), "소요시간": dur}).eq("id", row['Row']).execute()
                                            st.rerun()
                                    elif stage == "혼합공정":
                                        if st.button("완료", key=f"end_act_{row['Row']}", use_container_width=True):
                                            dur = str(datetime.strptime(get_now_kst(), '%Y-%m-%d %H:%M') - datetime.strptime(row['시작시간'], '%Y-%m-%d %H:%M'))
                                            supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": "반제품창고", "상태": "대기", "제조일자": c_date_val, "유형": c_type, "특이사항": c_note, "설비": ""}).execute()
                                            supabase.table("product_history").update({"상태": "완료", "종료시간": get_now_kst(), "소요시간": dur}).eq("id", row['Row']).execute()
                                            st.rerun()
                                    else:
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
                                                        dur = str(datetime.strptime(get_now_kst(), '%Y-%m-%d %H:%M' ) - datetime.strptime(row['시작시간'], '%Y-%m-%d %H:%M'))
                                                        supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": n_stg, "상태": "대기", "제조일자": c_date_val, "유형": c_type, "특이사항": c_note, "설비": nm_clean}).execute()
                                                        supabase.table("product_history").update({"상태": "1팀종료" if "외관선별" in str(n_stg) else "완료", "종료시간": get_now_kst(), "소요시간": dur}).eq("id", row['Row']).execute()
                                                        st.rerun()
                                        else:
                                            if st.button("완료", key=f"end_act_{row['Row']}", use_container_width=True):
                                                dur = str(datetime.strptime(get_now_kst(), '%Y-%m-%d %H:%M') - datetime.strptime(row['시작시간'], '%Y-%m-%d %H:%M'))
                                                if n_stg: 
                                                    next_m = n_machines[0].strip() if n_machines else ""
                                                    supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": n_stg, "상태": "대기", "제조일자": c_date_val, "유형": c_type, "특이사항": c_note, "설비": next_m}).execute()
                                                supabase.table("product_history").update({"상태": "1팀종료" if "외관선별" in str(n_stg) else "완료", "종료시간": get_now_kst(), "소요시간": dur}).eq("id", row['Row']).execute()
                                                st.rerun()
                                                
                                elif row['상태'] == '지연':
                                    if st.button("재시작", key=f"resume_act_{row['Row']}", use_container_width=True): 
                                        supabase.table("product_history").update({"상태": "진행중"}).eq("id", row['Row']).execute()
                                        st.rerun()
                                st.markdown("</div>", unsafe_allow_html=True)
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
        # 데이터 정제: 모든 컬럼의 값을 문자열로 변환하고 공백 제거 (필터 오류 방지)
        for col in ['제품', '공정', '유형']:
            if col in display_df.columns:
                display_df[col] = display_df[col].astype(str).str.strip()
        
        # 필터링용 유니크 리스트 생성 (None 제거)
        prod_list = sorted([p for p in display_df['제품'].unique() if p and p != 'nan'])
        
        if st.session_state.view == 'all_history':
            filter_cols = st.columns([4, 3, 3, 2])
            with filter_cols[0]:
                sel_filter = st.selectbox("🔍 제품명 검색", ["전체 보기"] + prod_list, key="filter_all_prod")
            with filter_cols[1]:
                sel_stage = st.selectbox("⚙️ 공정 검색", ["전체 보기"] + TARGET_STAGES, key="filter_all_stage")
            with filter_cols[2]:
                raw_types = display_df['유형'].dropna().unique().tolist()
                clean_types = sorted([t for t in raw_types if t and t != 'nan' and t.upper() != "NONE"])
                sel_type = st.selectbox("📌 유형 검색", ["전체 보기"] + clean_types, key="filter_all_type")
            with filter_cols[3]:
                only_live = st.toggle("⚡ 현재 실시간 현황판 로트만 보기", value=False)
            
            # 필터링 적용
            if sel_filter != "전체 보기": display_df = display_df[display_df['제품'] == sel_filter]
            if sel_stage != "전체 보기": display_df = display_df[display_df['공정'] == sel_stage]
            if sel_type != "전체 보기": display_df = display_df[display_df['유형'] == sel_type]
                
            if only_live and not curr_df.empty:
                # 안전한 실시간 매칭
                live_combos = (curr_df['제품'].astype(str).str.strip() + "_" + curr_df['Lot'].astype(str).str.strip() + "_" + curr_df['공정'].astype(str).str.strip()).unique().tolist()
                df_combos = (display_df['제품'] + "_" + display_df['Lot'].astype(str).str.strip() + "_" + display_df['공정'])
                display_df = display_df[df_combos.isin(live_combos)]
        else:
            sel_filter = st.selectbox("🔍 제품명 검색", ["전체 보기"] + prod_list, key=f"filter_{st.session_state.view}")
            if sel_filter != "전체 보기": 
                display_df = display_df[display_df['제품'] == sel_filter]
                
        avail_cols = [c for c in ['Lot', '제품', '제조일자', '공정', '상태', '시작시간', '종료시간', '소요시간', '유형', '특이사항', '설비'] if c in display_df.columns]
        st.dataframe(display_df[avail_cols].sort_index(ascending=False), use_container_width=True, height=600)
    else: 
        st.info("데이터가 없습니다.")



