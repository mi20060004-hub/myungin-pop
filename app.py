import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client

# --- 1. 페이지 설정 ---
st.set_page_config(layout="wide", page_title="명인제약 생산 시점 관리")

# --- 2. 🔒 URL 쿼리 파라미터 기반 새로고침 유지형 로그인 로직 ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

query_params = st.query_params
if query_params.get("auth") == "success":
    st.session_state.authenticated = True

if not st.session_state.authenticated:
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(15, 23, 42, 0.6), rgba(15, 23, 42, 0.6)), 
                    url('https://github.com/mi20060004-hub/myungin-pop/blob/main/%EB%AA%85%EC%9D%B8%EB%B0%94%ED%83%95_%EC%99%80%EC%9D%B4%EB%93%9C33.jpg?raw=true');
        background-size: cover; background-position: center; background-repeat: no-repeat;
    }
    
    .custom-login-box {
        background-color: #ffffff !important;
        padding: 35px !important;
        border-radius: 16px !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3) !important;
        border: 1px solid #e2e8f0;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1.5, 1, 1.5])
    
    with col2:
        st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
        
        st.markdown("""
        <div class="custom-login-box">
            <div style='text-align: center; padding-bottom: 15px;'>
                <h2 style='color: #1e3a8a; font-weight: 800; margin-bottom: 5px;'>명인제약 생산시점관리</h2>
                <p style='color: #64748b; font-size: 15px; margin: 0;'>MYUNG-IN Pharm POP System</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            st.markdown("<p style='font-weight: 400; color: #ffffff; margin-top: 15px; margin-bottom: 5px; font-size: 15px;'>🔒 비밀번호는 '2026' 입니다.</p>", unsafe_allow_html=True)
            input_pw = st.text_input("비밀번호 입력", type="password", label_visibility="collapsed", placeholder="비밀번호를 입력하세요")
            
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("로그인", type="primary", use_container_width=True):
                correct_pw = st.secrets.get("auth", {}).get("password", "1234")
                if input_pw == correct_pw:
                    st.session_state.authenticated = True
                    st.query_params["auth"] = "success"
                    st.rerun()
                else:
                    st.error("❌ 비밀번호가 올바르지 않습니다.")
                    
        st.markdown("<p style='text-align: center; color: #ffffff; font-size: 12px; margin-top: 20px; text-shadow: 0 2px 4px rgba(0,0,0,0.5);'>Developed by JK / Production Dept.</p>", unsafe_allow_html=True)
        
    st.stop()

# --- 🌟 업데이트 안내 팝업 (st.dialog 활용) ---
@st.dialog("✨ [시스템 업데이트 안내] 새로운 기능 추가")
def show_update_dialog():
    st.markdown("""
    ### 🚀 업데이트 주요 기능
    1. 로그인 기능이 추가되었습니다.
    2. 칭량공정 이전 '계획공정'이 추가되었습니다.
    3. 현황판 제품 위치추적 기능이 강화되었습니다.
    4. 공정중인 제품블록에 특이사항을 입력하는 기능이 추가되었습니다.
    5. 제품블록에 이전공정 완료 후 며칠이 지났는지 표시됩니다.
    """)
    
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    
    if st.button("확인 (팝업 닫기)", type="primary", use_container_width=True):
        st.session_state.update_dialog_shown = True
        st.rerun()

if "update_dialog_shown" not in st.session_state:
    st.session_state.update_dialog_shown = False

if st.session_state.authenticated and not st.session_state.update_dialog_shown:
    show_update_dialog()

# --- 3. CSS 스타일 ---
st.markdown("""
<style>
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

.stage-bar {
    scroll-margin-top: 80px;
    color: white; padding: 8px 13px; border-radius: 6px; 
    font-size: 18px; font-weight: 700; margin-top: 20px; margin-bottom: 10px; 
    background: linear-gradient(90deg, #334155 0%, #64748b 100%);
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
.info-text-10px { font-size: 10px !important; color: #ef4444 !important; font-weight: 800 !important; margin: 1px 0; text-align: center; line-height: 1.2; }

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

# --- 4. Supabase DB 연결 ---
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

# --- 5. 데이터 로직 ---
MACHINE_MAP = {
    "계획공정": [],  
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

def get_prev_stage_elapsed_str(all_df, lot_num, prod_name, target_stages):
    if all_df.empty or not lot_num or not prod_name:
        return ""
    prev_logs = all_df[
        (all_df['Lot'].astype(str).str.strip() == str(lot_num).strip()) & 
        (all_df['제품'].astype(str).str.strip() == str(prod_name).strip()) & 
        (all_df['공정'].isin(target_stages)) & 
        (all_df['상태'].isin(['완료', '1팀종료', '종료']))
    ]
    if prev_logs.empty:
        return ""
    
    prev_logs = prev_logs.copy()
    prev_logs['종료dt'] = pd.to_datetime(prev_logs['종료시간'], errors='coerce')
    prev_logs = prev_logs.sort_values(by='종료dt', ascending=False)
    
    latest_row = prev_logs.iloc[0]
    end_time_str = str(latest_row.get('종료시간', ''))
    if not end_time_str or end_time_str == 'nan' or end_time_str == 'NaT':
        return ""
    
    try:
        target_dt = datetime.strptime(end_time_str[:10], '%Y-%m-%d').date()
        today_dt = get_today_date_kst()
        delta_days = (today_dt - target_dt).days
        return f"+{delta_days}일"
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

    curr_res = supabase.table("product_history").select("*").not_.in_("상태", ["완료", "1팀종료", "폐기"]).order("priority", desc=True).order("id", desc=True).execute()
    
    curr_df = pd.DataFrame(curr_res.data) if curr_res.data else pd.DataFrame()
    if not curr_df.empty and 'id' in curr_df.columns:
        curr_df['Row'] = curr_df['id']

    log_res = supabase.table("product_history").select("*").in_("상태", ["완료", "1팀종료"]).order("id", desc=True).limit(500).execute()
    log_df = pd.DataFrame(log_res.data) if log_res.data else pd.DataFrame()
    if not log_df.empty and 'id' in log_df.columns:
        log_df['Row'] = log_df['id']

    all_raw_df = pd.concat([curr_df, log_df], ignore_index=True) if not curr_df.empty or not log_df.empty else pd.DataFrame()

    return master_dict, stock_dict, curr_df, log_df, all_raw_df

master_dict, stock_dict, curr_df, log_df, all_raw_df = load_data()

def update_priority(row, direction, df_in_stage):
    stage_df = df_in_stage[df_in_stage['공정'] == row['공정']].sort_values(
        by=['상태', 'priority', 'id'], 
        ascending=[False, False, False]
    )
    items = stage_df.to_dict('records')
    idx = next((i for i, item in enumerate(items) if item['Row'] == row['Row']), -1)
    
    if idx == -1: return

    if direction == "up":
        target_idx = idx - 1
    elif direction == "down":
        target_idx = idx + 1
    elif direction == "top":
        non_progress = [i for i, item in enumerate(items) if str(item['상태']).strip() != "진행중"]
        if not non_progress: return
        target_idx = non_progress[0]
        if target_idx == idx: return
    else:
        return

    if 0 <= target_idx < len(items) and target_idx != idx:
        target_item = items[target_idx]
        if str(target_item['상태']).strip() == "진행중" and direction != "top": return

        old_p = row.get('priority', 0) if pd.notna(row.get('priority')) else 0
        target_p = target_item.get('priority', 0) if pd.notna(target_item.get('priority')) else 0

        if direction in ["up", "down"]:
            new_old_p = target_p if target_p != old_p else old_p + 1
            new_target_p = old_p if target_p != old_p else target_p - 1
            
            supabase.table("product_history").update({"priority": new_old_p}).eq("id", row['Row']).execute()
            supabase.table("product_history").update({"priority": new_target_p}).eq("id", target_item['Row']).execute()
            
        elif direction == "top":
            new_priority = target_p + 1
            supabase.table("product_history").update({"priority": new_priority}).eq("id", row['Row']).execute()

        st.rerun()

if 'pending_lots' not in st.session_state: st.session_state.pending_lots = []
if 'view' not in st.session_state: st.session_state.view = 'main'
if 'reset_lot' not in st.session_state: st.session_state.reset_lot = ""
if 'reset_type' not in st.session_state: st.session_state.reset_type = "일반로트"
if 'reset_note' not in st.session_state: st.session_state.reset_note = ""

# --- 6. 헤더 및 상단 메뉴 바 ---
st.markdown(f'<div class="fixed-header"><p class="main-title-text">명인제약 생산 시점 관리 (MYUNG-IN Pharm POP System)</p></div>', unsafe_allow_html=True)
nav_cols = st.columns(5) 
with nav_cols[0]:
    if st.button("📊 실시간 현황판", key="n1", use_container_width=True): st.session_state.view = 'main'; st.rerun()
with nav_cols[1]:
    if st.button("✅ 1팀 공정 완료", key="nav_2", use_container_width=True): st.session_state.view = 'history'; st.rerun()
with nav_cols[2]:
    if st.button("🏷️ 선별 공정 완료", key="nav_3", use_container_width=True): st.session_state.view = 'selection'; st.rerun()
with nav_cols[3]:
    if st.button("🗃️ 전체 공정 이력", key="nav_4", use_container_width=True): st.session_state.view = 'all_history'; st.rerun()
with nav_cols[4]:
    st.link_button("🌐 일일 재고/재공", "https://myungin-pp.appsmith.com/app/untitled-application-1/page1-6a27d4bd9e8e4df7ae2343bf?environment=production", use_container_width=True)

# --- 7. 사이드바 ---
with st.sidebar:
    st.header("📋 1. 계획 투입 (사전 등록)")
    plan_p = st.selectbox("제품명 선택", list(master_dict.keys()), key="plan_p_widget")
    plan_lot = st.text_input("제조번호(Lot) 입력", key="plan_lot_widget").strip()
    plan_date = st.date_input("제조일자(예정) 선택", value=get_today_date_kst(), key="plan_date_widget")
    plan_date_str = plan_date.strftime('%Y-%m-%d')
    plan_type = st.selectbox("로트 유형 선택", ["일반로트", "동시PV1", "동시PV2", "동시PV3", "예측PV1", "예측PV2", "예측PV3"], key="plan_type_widget")
    plan_note = st.text_area("공정 특이사항 입력", key="plan_note_widget")
    
    is_plan_duplicate = plan_lot and ((not curr_df.empty and ((curr_df['Lot'] == plan_lot) & (curr_df['제품'].str.strip() == plan_p.strip())).any()))
    
    if plan_lot and is_plan_duplicate: 
        st.error("⚠️ 중복된 로트 데이터 존재")
    elif plan_lot:
        if st.button("➕ 계획공정 대기열 추가", use_container_width=True):
            sub_df = curr_df[curr_df['공정'] == "계획공정"]
            new_p = int(sub_df['priority'].min()) - 1 if not sub_df.empty and pd.notna(sub_df['priority'].min()) else 0
            supabase.table("product_history").insert({
                "Lot": plan_lot, "제품": plan_p.strip(), "공정": "계획공정", 
                "상태": "대기", "제조일자": plan_date_str, "유형": plan_type, 
                "특이사항": plan_note, "설비": "", "priority": new_p
            }).execute()
            st.success("계획공정에 등록되었습니다!")
            st.rerun()

    # 이미 등록된 계획 수정용 섹션
    planned_items_edit = curr_df[curr_df['공정'] == '계획공정'] if not curr_df.empty else pd.DataFrame()
    if not planned_items_edit.empty:
        with st.expander("✏️ 등록된 생산 계획 수정", expanded=False):
            planned_items_edit['수정표시'] = planned_items_edit['제품'].astype(str).str.strip() + " | " + planned_items_edit['Lot'].astype(str).str.strip()
            edit_options = planned_items_edit['수정표시'].tolist()
            selected_edit_label = st.selectbox("수정할 계획 선택", ["선택하세요"] + edit_options, key="select_plan_to_edit")
            
            if selected_edit_label != "선택하세요":
                target_edit_row = planned_items_edit[planned_items_edit['수정표시'] == selected_edit_label].iloc[0]
                
                up_lot = st.text_input("제조번호 수정", value=str(target_edit_row['Lot']), key="up_lot_val")
                
                raw_d = str(target_edit_row['제조일자'])
                default_d = datetime.strptime(raw_d[:10], '%Y-%m-%d').date() if len(raw_d) >= 10 else get_today_date_kst()
                up_date = st.date_input("제조일자 수정", value=default_d, key="up_date_val")
                up_date_str = up_date.strftime('%Y-%m-%d')
                
                type_list = ["일반로트", "동시PV1", "동시PV2", "동시PV3", "예측PV1", "예측PV2", "예측PV3"]
                cur_t = str(target_edit_row['유형'])
                t_idx = type_list.index(cur_t) if cur_t in type_list else 0
                up_type = st.selectbox("로트 유형 수정", type_list, index=t_idx, key="up_type_val")
                
                cur_n = str(target_edit_row['특이사항'])
                if cur_n == 'nan' or cur_n == 'None': cur_n = ""
                up_note = st.text_area("특이사항 수정", value=cur_n, key="up_note_val")
                
                if st.button("💾 수정 내용 저장", use_container_width=True):
                    supabase.table("product_history").update({
                        "Lot": up_lot.strip(),
                        "제조일자": up_date_str,
                        "유형": up_type,
                        "특이사항": up_note
                    }).eq("id", target_edit_row['Row']).execute()
                    st.success("계획 정보가 수정되었습니다!")
                    st.rerun()

    st.divider()

    st.header("🏭 2. 현장 제조 투입 (칭량공정)")
    planned_items = curr_df[curr_df['공정'] == '계획공정'] if not curr_df.empty else pd.DataFrame()
    
    if not planned_items.empty:
        planned_items['선택표시'] = planned_items['제품'].astype(str).str.strip() + " | " + planned_items['Lot'].astype(str).str.strip() + " (" + planned_items['제조일자'].astype(str).str.strip() + ")"
        plan_options = planned_items['선택표시'].tolist()
        
        selected_plan_label = st.selectbox("투입할 계획 선택", ["선택하세요"] + plan_options, key="select_plan_to_weigh")
        
        if selected_plan_label != "선택하세요":
            target_plan_row = planned_items[planned_items['선택표시'] == selected_plan_label].iloc[0]
            
            st.markdown("<p style='font-size:13px; font-weight:700; color:#1e3a8a; margin-bottom:0px;'>투입 시 최종 확인/수정</p>", unsafe_allow_html=True)
            edit_date = st.date_input("실제 제조일자 선택", value=datetime.strptime(str(target_plan_row['제조일자']), '%Y-%m-%d').date() if pd.notna(target_plan_row['제조일자']) and len(str(target_plan_row['제조일자'])) >= 10 else get_today_date_kst(), key="edit_exec_date")
            edit_date_str = edit_date.strftime('%Y-%m-%d')
            
            type_list = ["일반로트", "동시PV1", "동시PV2", "동시PV3", "예측PV1", "예측PV2", "예측PV3"]
            cur_t2 = str(target_plan_row['유형'])
            t_idx2 = type_list.index(cur_t2) if cur_t2 in type_list else 0
            edit_type = st.selectbox("로트 유형 확인/수정", type_list, index=t_idx2, key="edit_exec_type")
            
            curr_note_val = str(target_plan_row.get('특이사항', ''))
            if curr_note_val == 'nan' or curr_note_val == 'None': curr_note_val = ""
            edit_note = st.text_area("특이사항 확인/수정", value=curr_note_val, key="edit_exec_note")
            
            if st.button("🚀 칭량공정 투입 확정", type="primary", use_container_width=True):
                p_name = target_plan_row['제품'].strip()
                l_num = target_plan_row['Lot'].strip()
                row_id = target_plan_row['Row']
                
                weigh_sub = curr_df[curr_df['공정'] == "칭량공정"]
                new_weigh_p = int(weigh_sub['priority'].min()) - 1 if not weigh_sub.empty and pd.notna(weigh_sub['priority'].min()) else 0
                
                supabase.table("product_history").insert({
                    "Lot": l_num, "제품": p_name, "공정": "칭량공정", "상태": "대기", 
                    "제조일자": edit_date_str, "유형": edit_type, "특이사항": edit_note, 
                    "설비": "", "priority": new_weigh_p
                }).execute()
                
                supabase.table("product_history").update({
                    "상태": "완료", "종료시간": get_now_kst(), "소요시간": "계획투입완료"
                }).eq("id", row_id).execute()
                
                st.success("칭량공정으로 투입되었습니다!")
                st.rerun()
    else:
        st.caption("계획공정에 대기 중인 항목이 없습니다.")

    st.divider()
    
    search_keyword = ""
    if st.session_state.view == 'main':
        st.markdown("<div style='font-size:16px; font-weight:800; color:#ff6b00; margin-bottom:5px;'>🔍 현황판 제품 위치 추적</div>", unsafe_allow_html=True)
        search_keyword = st.text_input("검색어 입력 (제품명 또는 Lot)", placeholder="예: 톨비스정 또는 26001", key="live_search_box").strip()
        
        if search_keyword and not curr_df.empty:
            kw = search_keyword.lower()
            matched_search_df = curr_df[
                curr_df['제품'].astype(str).str.lower().str.contains(kw) | 
                curr_df['Lot'].astype(str).str.lower().str.contains(kw)
            ]
            
            if not matched_search_df.empty:
                st.markdown(f"<div style='background-color: #fff7ed; border: 1px solid #fdba74; padding: 8px; border-radius: 6px; font-size: 12px; margin-bottom: 10px; color: #c2410c;'><b>📍 검색 결과 위치 안내 ({len(matched_search_df)}건)</b><br>", unsafe_allow_html=True)
                for _, r in matched_search_df.iterrows():
                    p_name = r.get('제품', '')
                    l_num = r.get('Lot', '')
                    st_name = r.get('공정', '')
                    eq_name = str(r.get('설비', '')).strip()
                    location_desc = f"{st_name} ({eq_name})" if eq_name and eq_name != 'nan' else st_name
                    st.markdown(f"- <b>{p_name}</b> (Lot: {l_num}) &rarr; <span style='color: #0284c7; font-weight:700;'>{location_desc}</span>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='background-color: #f1f5f9; padding: 6px; border-radius: 6px; font-size: 11px; margin-bottom: 10px; color: #64748b;'>일치하는 가동 랏이 없습니다.</div>", unsafe_allow_html=True)
                
        st.divider()

    if st.session_state.view == 'main':
        # 칭량공정부터 외관선별공정까지의 가동 건수만 합산
        active_stages_for_count = [s for s in TARGET_STAGES if s != "계획공정"]
        total_active_count = len(curr_df[curr_df['공정'].isin(active_stages_for_count)]) if not curr_df.empty else 0
        
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

        st.markdown("<div style='font-size:16px; font-weight:800; color:#1e3a8a; margin-bottom:5px;'>📝 공정 특이사항 수정</div>", unsafe_allow_html=True)
        if not curr_df.empty:
            curr_df['목록표시'] = curr_df['제품'].astype(str).str.strip() + " | " + curr_df['Lot'].astype(str).str.strip() + " (" + curr_df['공정'].astype(str).str.strip() + ")"
            target_lot_options = curr_df['목록표시'].tolist()
            
            selected_target_label = st.selectbox("수정할 제품(LOT) 선택", ["선택하세요"] + target_lot_options, key="edit_note_select")
            
            if selected_target_label != "선택하세요":
                selected_row = curr_df[curr_df['목록표시'] == selected_target_label].iloc[0]
                current_note = str(selected_row.get('특이사항', ''))
                if current_note == 'nan' or current_note == 'None': current_note = ""
                
                if "target_note_val" not in st.session_state or st.session_state.get("prev_selected_label") != selected_target_label:
                    st.session_state.target_note_val = current_note
                    st.session_state.prev_selected_label = selected_target_label

                def sync_note_input():
                    st.session_state.target_note_val = st.session_state.live_textarea_key

                st.text_area(
                    "변경할 특이사항 입력", 
                    value=st.session_state.target_note_val, 
                    key="live_textarea_key", 
                    on_change=sync_note_input
                )
                
                if st.button("💾 특이사항 저장", use_container_width=True):
                    final_note = st.session_state.get("live_textarea_key", st.session_state.target_note_val)
                    supabase.table("product_history").update({"특이사항": final_note}).eq("id", selected_row['Row']).execute()
                    st.success("특이사항이 수정되었습니다!")
                    st.rerun()
        else:
            st.caption("수정 가능한 가동 중인 랏이 없습니다.")

        st.write("---")
        
    with st.popover("🔒 데이터 초기화", use_container_width=True):
        input_pwd = st.text_input("비밀번호 입력", type="password")
        if st.button("🚨 초기화 실행", type="primary", use_container_width=True):
            if input_pwd == "1234":
                supabase.table("product_history").delete().neq("Lot", "sys_clear").execute()
                st.rerun()

    st.markdown("<div style='text-align: center; color: #94a3b8; font-size: 12px; margin-top: 30px; line-height: 1.4;'>Ver 2.15 / Developed by JK / Production Dept.</div>", unsafe_allow_html=True)

# --- 8. 재고 및 재공 월수 통합 출력 엔진 헬퍼 함수 ---
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
        try: html_str += f"<p class='wip-blue'>재공: {w_val}개월</p>"
        except ValueError: html_str += f"<p class='wip-blue'>재공: {w_val}</p>"
        
    return html_str

# --- 9. 메인 콘텐츠 및 현황판 렌더링 ---
if st.session_state.view == 'main':
    for idx_stage, stage in enumerate(TARGET_STAGES):
        stage_count = len(curr_df[curr_df['공정'] == stage]) if not curr_df.empty else 0
        stage_id = stage.replace(" ", "")
        
        # '계획공정' 렌더링 (블록에 로트 유형 및 특이사항 표시 적용)
        if stage == "계획공정":
            with st.expander(f"▶ {stage} ({stage_count}건)", expanded=True):
                m_items = pd.DataFrame()
                if not curr_df.empty:
                    m_items = curr_df[curr_df['공정'] == stage].copy()
                    if not m_items.empty:
                        m_items = m_items.sort_values(by=['상태', 'priority'], ascending=[False, False])
                
                if not m_items.empty:
                    total_items = len(m_items)
                    for chunk_idx in range(0, total_items, 10):
                        chunk_df = m_items.iloc[chunk_idx:chunk_idx+10]
                        cols = st.columns(10)
                        for idx, (_, row) in enumerate(chunk_df.iterrows()):
                            with cols[idx]:
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
                                    st.markdown(f"<p class='card-text-10px'>{prod_name}</p>", unsafe_allow_html=True)
                                    st.markdown(f"<p class='card-text-l-10px'>{lot_num}</p>", unsafe_allow_html=True)
                                    
                                    p_date = str(row.get('제조일자', '')).strip() if not pd.isna(row.get('제조일자')) else ""
                                    if p_date and p_date.upper() != "NONE" and p_date != "-":
                                        st.markdown(f"<p class='card-text-date'>예정일: {p_date}</p>", unsafe_allow_html=True)
                                        
                                    st.markdown(render_stock_and_wip_html(prod_name), unsafe_allow_html=True)
                                    
                                    # 일반로트가 아닌 경우에만 로트 유형 표시
                                    r_type = str(row.get('유형', '')).strip()
                                    if r_type and r_type not in ['일반로트', '일반', 'nan', 'None', '-']:
                                        st.markdown(f"<p class='lot-type-highlight'>{r_type}</p>", unsafe_allow_html=True)
                                        
                                    # 공정 특이사항 표시
                                    r_note = str(row.get('특이사항', '')).strip()
                                    if r_note and r_note != 'nan' and r_note != 'None':
                                        st.markdown(f"<p class='info-text-10px'>📝 {r_note}</p>", unsafe_allow_html=True)
                                        
                                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.caption("등록된 생산 계획이 없습니다.")
            continue

        # 일반 공정들 바 렌더링
        st.markdown(f'<div id="{stage_id}" class="stage-bar">▶ {stage} ({stage_count}건)</div>', unsafe_allow_html=True)
        
        m_items = pd.DataFrame()
        if not curr_df.empty:
            m_items = curr_df[curr_df['공정'] == stage].copy()
            if not m_items.empty:
                m_items = m_items.sort_values(by=['상태', 'priority'], ascending=[False, False])
        
        if stage in ["칭량공정", "정립혼합대기창고", "반제품창고"]:
            if not m_items.empty:
                total_items = len(m_items)
                for chunk_idx in range(0, total_items, 10):
                    chunk_df = m_items.iloc[chunk_idx:chunk_idx+10]
                    cols = st.columns(10)
                    for idx, (_, row) in enumerate(chunk_df.iterrows()):
                        with cols[idx]:
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

                                c_move1, c_move2, c_move3 = st.columns(3)
                                with c_move1:
                                    if st.button("↑", key=f"up_{row['Row']}"):
                                        update_priority(row, "up", m_items)
                                with c_move2:
                                    if st.button("↓", key=f"down_{row['Row']}"):
                                        update_priority(row, "down", m_items)
                                with c_move3:
                                    if st.button("▲", key=f"top_{row['Row']}"):
                                        update_priority(row, "top", m_items)
                                        
                                c_type = "" if pd.isna(row['유형']) else str(row['유형'])
                                c_note = "" if pd.isna(row['특이사항']) else str(row['특이사항'])
                                c_date_val = "" if pd.isna(row.get('제조일자')) else str(row.get('제조일자'))
                                
                                if stage == "정립혼합대기창고":
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
                                                    sub_df = curr_df[(curr_df['공정'] == target_stage) & (curr_df['설비'].str.strip() == pm_clean)]
                                                    new_p = int(sub_df['priority'].min()) - 1 if not sub_df.empty and pd.notna(sub_df['priority'].min()) else 0
                                                    supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": target_stage, "상태": "대기", "제조일자": c_date_val, "유형": c_type, "특이사항": c_note, "설비": pm_clean, "priority": new_p}).execute()
                                                    supabase.table("product_history").update({"상태": "완료", "종료시간": get_now_kst(), "소요시간": "창고출고"}).eq("id", row['Row']).execute()
                                                    st.rerun()
                                        else:
                                            st.caption("다음 공정 설비 없음")
                                            if st.button("강제 캡슐공정 이동", key=f"wh_wh_force_{row['Row']}", use_container_width=True):
                                                sub_df = curr_df[curr_df['공정'] == "캡슐공정"]
                                                new_p = int(sub_df['priority'].min()) - 1 if not sub_df.empty and pd.notna(sub_df['priority'].min()) else 0
                                                supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": "캡슐공정", "상태": "대기", "제조일자": c_date_val, "유형": c_type, "특이사항": c_note, "설비": "", "priority": new_p}).execute()
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
                                                    sub_df = curr_df[(curr_df['공정'] == next_pop_stage) & (curr_df['설비'].str.strip() == pm_clean)]
                                                    new_p = int(sub_df['priority'].min()) - 1 if not sub_df.empty and pd.notna(sub_df['priority'].min()) else 0
                                                    supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": next_pop_stage, "상태": "대기", "제조일자": c_date_val, "유형": c_type, "특이사항": c_note, "설비": pm_clean, "priority": new_p}).execute()
                                                    supabase.table("product_history").update({"상태": "완료", "종료시간": get_now_kst(), "소요시간": "창고출고"}).eq("id", row['Row']).execute()
                                                    st.rerun()
                                        else:
                                            st.caption("지정 설비 없음")
                                            if st.button("강제 타정공정 이동", key=f"wh_force_{row['Row']}", use_container_width=True):
                                                sub_df = curr_df[curr_df['공정'] == "타정공정"]
                                                new_p = int(sub_df['priority'].min()) - 1 if not sub_df.empty and pd.notna(sub_df['priority'].min()) else 0
                                                supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": "타정공정", "상태": "대기", "제조일자": c_date_val, "유형": c_type, "특이사항": c_note, "설비": "", "priority": new_p}).execute()
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
                                                sub_df = curr_df[curr_df['공정'] == "정립혼합대기창고"]
                                                new_p = int(sub_df['priority'].min()) - 1 if not sub_df.empty and pd.notna(sub_df['priority'].min()) else 0
                                                supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": "정립혼합대기창고", "상태": "대기", "제조일자": c_date_val, "유형": c_type, "특이사항": c_note, "설비": "", "priority": new_p}).execute()
                                            else:
                                                n_stg = None
                                                for i in range(idx_stage + 1, len(TARGET_STAGES)):
                                                    check_stage = TARGET_STAGES[i].strip()
                                                    if master_dict.get(prod_name, {}).get(check_stage):
                                                        n_stg = check_stage
                                                        break
                                                next_m = master_dict.get(prod_name, {}).get(n_stg, [])[0].strip() if (n_stg and master_dict.get(prod_name, {}).get(n_stg, [])) else ""
                                                if n_stg:
                                                    if next_m:
                                                        sub_df = curr_df[(curr_df['공정'] == n_stg) & (curr_df['설비'].str.strip() == next_m.strip())]
                                                    else:
                                                        sub_df = curr_df[curr_df['공정'] == n_stg]
                                                    new_p = int(sub_df['priority'].min()) - 1 if not sub_df.empty and pd.notna(sub_df['priority'].min()) else 0
                                                    supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": n_stg, "상태": "대기", "제조일자": c_date_val, "유형": c_type, "특이사항": c_note, "설비": next_m, "priority": new_p}).execute()
                                            
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
                                
                                if stage in ["타정공정", "캡슐공정"]:
                                    prev_elapsed_suffix = get_prev_stage_elapsed_str(all_raw_df, lot_num, prod_name, ["혼합공정"])
                                    if prev_elapsed_suffix:
                                        st.markdown(f"<p class='card-text-date' style='color:#059669; font-weight:800;'>(혼합후{prev_elapsed_suffix})</p>", unsafe_allow_html=True)
                                elif stage == "코팅공정":
                                    prev_elapsed_suffix = get_prev_stage_elapsed_str(all_raw_df, lot_num, prod_name, ["타정공정"])
                                    if prev_elapsed_suffix:
                                        st.markdown(f"<p class='card-text-date' style='color:#059669; font-weight:800;'>(타정후{prev_elapsed_suffix})</p>", unsafe_allow_html=True)
                                elif stage == "외관선별공정":
                                    prev_elapsed_suffix = get_prev_stage_elapsed_str(all_raw_df, lot_num, prod_name, ["코팅공정", "타정공정", "질량선별공정", "인쇄공정"])
                                    if prev_elapsed_suffix:
                                        st.markdown(f"<p class='card-text-date' style='color:#059669; font-weight:800;'>(직전공정완료후{prev_elapsed_suffix})</p>", unsafe_allow_html=True)

                                st.markdown(render_stock_and_wip_html(prod_name), unsafe_allow_html=True)
                                
                                if row['유형'] not in ['일반로트', '일반', '']: st.markdown(f"<p class='lot-type-highlight'>{row['유형']}</p>", unsafe_allow_html=True)
                                if row['특이사항'] and not pd.isna(row['특이사항']): st.markdown(f"<div class='info-text-10px'>📝 {row['특이사항']}</div>", unsafe_allow_html=True)
                                st.markdown(f"<div class='status-bar {'bg-waiting' if row['상태']=='대기' else 'bg-progress' if row['상태']=='진행중' else 'bg-paused'}'>{row['상태']}</div>", unsafe_allow_html=True)
                                
                                c_move1, c_move2, c_move3 = st.columns(3)
                                with c_move1:
                                    if st.button("↑", key=f"up_eq_{row['Row']}"):
                                        update_priority(row, "up", m_specific_items)
                                with c_move2:
                                    if st.button("↓", key=f"down_eq_{row['Row']}"):
                                        update_priority(row, "down", m_specific_items)
                                with c_move3:
                                    if st.button("▲", key=f"top_eq_{row['Row']}"):
                                        update_priority(row, "top", m_specific_items)
                                        
                                c_type = "" if pd.isna(row['유형']) else str(row['유형'])
                                c_note = "" if pd.isna(row['특이사항']) else str(row['특이사항'])
                                c_date_val = "" if pd.isna(row.get('제조일자')) else str(row.get('제조일자'))
                                
                                if row['상태'] == '대기':
                                    c1, c2 = st.columns(2)
                                    with c1:
                                        if st.button("시작", key=f"start_act_{row['Row']}", use_container_width=True): 
                                            supabase.table("product_history").update({"상태": "진행중", "시작시간": get_now_kst()}).eq("id", row['Row']).execute()
                                            st.rerun()
                                    with c2:
                                        with st.popover("변경", use_container_width=True):
                                            valid_machines = master_dict.get(prod_name, {}).get(stage, [])
                                            for nm in valid_machines:
                                                nm_clean = nm.strip()
                                                if nm_clean.upper() != str(row['설비']).strip().upper() and st.button(nm_clean, key=f"ch_act_{row['Row']}_{nm_clean}", use_container_width=True): 
                                                    supabase.table("product_history").update({"설비": nm_clean}).eq("id", row['Row']).execute()
                                                    st.rerun()
                                elif row['상태'] == '진행중':
                                    c1, c2 = st.columns(2)
                                    with c1:
                                        if st.button("대기", key=f"pause_act_{row['Row']}", use_container_width=True): 
                                            supabase.table("product_history").update({"상태": "지연"}).eq("id", row['Row']).execute()
                                            st.rerun()
                                    with c2:
                                        if stage == "건조공정":
                                            if st.button("완료", key=f"end_act_{row['Row']}", use_container_width=True):
                                                dur = str(datetime.strptime(get_now_kst(), '%Y-%m-%d %H:%M') - datetime.strptime(row['시작시간'], '%Y-%m-%d %H:%M'))
                                                sub_df = curr_df[curr_df['공정'] == "정립혼합대기창고"]
                                                new_p = int(sub_df['priority'].min()) - 1 if not sub_df.empty and pd.notna(sub_df['priority'].min()) else 0
                                                supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": "정립혼합대기창고", "상태": "대기", "제조일자": c_date_val, "유형": c_type, "특이사항": c_note, "설비": "", "priority": new_p}).execute()
                                                supabase.table("product_history").update({"상태": "완료", "종료시간": get_now_kst(), "소요시간": dur}).eq("id", row['Row']).execute()
                                                st.rerun()
                                        elif stage == "혼합공정":
                                            if st.button("완료", key=f"end_act_{row['Row']}", use_container_width=True):
                                                dur = str(datetime.strptime(get_now_kst(), '%Y-%m-%d %H:%M') - datetime.strptime(row['시작시간'], '%Y-%m-%d %H:%M'))
                                                sub_df = curr_df[curr_df['공정'] == "반제품창고"]
                                                new_p = int(sub_df['priority'].min()) - 1 if not sub_df.empty and pd.notna(sub_df['priority'].min()) else 0
                                                supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": "반제품창고", "상태": "대기", "제조일자": c_date_val, "유형": c_type, "특이사항": c_note, "설비": "", "priority": new_p}).execute()
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
                                                            sub_df = curr_df[(curr_df['공정'] == n_stg) & (curr_df['설비'].str.strip() == nm_clean)]
                                                            new_p = int(sub_df['priority'].min()) - 1 if not sub_df.empty and pd.notna(sub_df['priority'].min()) else 0
                                                            supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": n_stg, "상태": "대기", "제조일자": c_date_val, "유형": c_type, "특이사항": c_note, "설비": nm_clean, "priority": new_p}).execute()
                                                            supabase.table("product_history").update({"상태": "1팀종료" if "외관선별" in str(n_stg) else "완료", "종료시간": get_now_kst(), "소요시간": dur}).eq("id", row['Row']).execute()
                                                            st.rerun()
                                            else:
                                                if st.button("완료", key=f"end_act_{row['Row']}", use_container_width=True):
                                                    dur = str(datetime.strptime(get_now_kst(), '%Y-%m-%d %H:%M') - datetime.strptime(row['시작시간'], '%Y-%m-%d %H:%M'))
                                                    if n_stg: 
                                                        next_m = n_machines[0].strip() if n_machines else ""
                                                        sub_df = curr_df[(curr_df['공정'] == n_stg) & (curr_df['설비'].str.strip() == next_m)]
                                                        new_p = int(sub_df['priority'].min()) - 1 if not sub_df.empty and pd.notna(sub_df['priority'].min()) else 0
                                                        supabase.table("product_history").insert({"Lot": row['Lot'], "제품": prod_name, "공정": n_stg, "상태": "대기", "제조일자": c_date_val, "유형": c_type, "특이사항": c_note, "설비": next_m, "priority": new_p}).execute()
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
    title_map = {"history": "완료된 공정 확인", "selection": "완료된 공정 확인(선별)", "all_history": "최근 500개 공정 이력 확인"}
    st.header(f"📋 {title_map[st.session_state.view]}")
    
    if st.session_state.view == 'history':
        display_df = log_df[log_df['상태'] == '1팀종료'].copy() if not log_df.empty else pd.DataFrame()
    elif st.session_state.view == 'selection':
        display_df = log_df[(log_df['공정'] == '외관선별공정') & (log_df['상태'] == '완료')].copy() if not log_df.empty else pd.DataFrame()
    else:
        display_df = all_raw_df.copy() if not all_raw_df.empty else pd.DataFrame()
    
    if not display_df.empty:
        for col in ['제품', '공정', '유형']:
            if col in display_df.columns:
                display_df[col] = display_df[col].astype(str).str.strip()
        
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
            
            if sel_filter != "전체 보기": display_df = display_df[display_df['제품'] == sel_filter]
            if sel_stage != "전체 보기": display_df = display_df[display_df['공정'] == sel_stage]
            if sel_type != "전체 보기": display_df = display_df[display_df['유형'] == sel_type]
                
            if only_live and not curr_df.empty:
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
