import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# --- 1. [수정] Streamlit Cloud용 인증 및 시트 연결 ---
# GitHub에 키를 올리지 않고 Streamlit Secrets를 사용하는 방식입니다.
def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    # Streamlit Cloud의 Advanced Settings > Secrets에 저장할 데이터 이름입니다.
    if "gcp_service_account" in st.secrets:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], 
            scopes=scopes
        )
    else:
        st.error("❌ Streamlit Cloud의 Secrets 설정에서 구글 인증 키(gcp_service_account)를 찾을 수 없습니다.")
        st.stop()
    return gspread.authorize(creds)

gc = get_gspread_client()

def safe_get_all_values(worksheet):
    if worksheet is None: return []
    try: return worksheet.get_all_values()
    except: return []

try:
    # 시트 이름이 다를 경우를 대비한 예외 처리
    sh = gc.open('생산관리_시스템')
except:
    try: sh = gc.open('생산관리_SYSTEM')
    except:
        st.error("❌ '생산관리_시스템' 구글 시트 파일을 찾을 수 없습니다. 서비스 계정 이메일에 시트가 공유되었는지 확인하세요.")
        st.stop()

def get_ws(name):
    try: return sh.worksheet(name)
    except: return None

worksheet = get_ws('현재생산중')
log_sheet = get_ws('공정이력')
master_sheet = get_ws('제품마스터')

# --- 2. 유틸리티 함수 및 설정 ---
def get_now_kst():
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst).strftime('%Y-%m-%d KST %H:%M:%S')

def parse_time(t_str):
    if not t_str: return None
    try: return datetime.strptime(t_str, '%Y-%m-%d KST %H:%M:%S')
    except: return None

stage_colors = {"과립": "#E0F2FE", "건조": "#FEF3C7", "정립": "#DCFCE7", "혼합": "#F3E8FF", "타정": "#FFE4E6", "캡슐": "#E0E7FF", "코팅": "#F1F5F9"}
stage_border_colors = {"과립": "#0EA5E9", "건조": "#D97706", "정립": "#16A34A", "혼합": "#9333EA", "타정": "#E11D48", "캡슐": "#4F46E5", "코팅": "#475569"}
machine_map = {
    "과립": ["P100", "KM100", "SM100", "P400", "GS400", "SM600", "글라트유동층", "GPCG2", "구형과립기", "롤러컴팩터"],
    "건조": ["트레이1호", "트레이2호", "트레이3호", "트레이4호", "트레이5호", "트레이6호", "트레이7호", "다산유동층", "D600"],
    "정립": ["Comil0112", "Comil0212", "Comil0312", "파워밀", "오실레이터"],
    "혼합": ["드럼혼합기", "PM1000", "PM2000"],
    "타정": ["킬리안", "63S-1", "41S", "63S-3", "PR1023", "MRC45", "MRC45S", "63S-2", "31S", "PH300"],
    "캡슐": ["SF150", "보쉬충전기", "PTK충전기", "SF35"],
    "코팅": ["SFC150FH", "SFC170FH", "SFC170FSH", "SFC130FSH", "V150", "SFC80"]
}
STAGES = list(machine_map.keys())

# --- 3. 스타일 디자인 (기존 완벽한 디자인 유지) ---
st.set_page_config(layout="wide", page_title="명인제약 생산 시점 관리 시스템")

st.markdown(f"""
    <style>
    .stApp {{ background-color: #ffffff; }}
    [data-testid="stHeader"] {{ display: none; }}
    
    .fixed-header {{
        position: fixed; top: 0; left: 0; right: 0; height: 80px; background-color: white;
        display: flex; align-items: center; justify-content: space-between;
        padding: 0 40px; z-index: 999999; border-bottom: 3px solid #1e293b;
    }}
    .header-left {{ display: flex; align-items: center; gap: 20px; }}
    .header-title {{ font-size: 28px !important; font-weight: 900; color: #1e293b; white-space: nowrap; }}
    .header-credit {{ font-size: 12px; color: #94a3b8; font-weight: 500; align-self: flex-end; margin-bottom: 20px; }}
    
    .stButton > button[kind="primary"] {{
        position: fixed; top: 18px; left: 480px; 
        z-index: 1000000; height: 44px !important; width: auto !important;
        padding: 0 25px !important; font-size: 16px !important; font-weight: 800 !important;
    }}
    
    div[data-testid="stDialog"] .stButton > button {{
        position: static !important;
        width: 100% !important;
        margin-top: 10px !important;
    }}
    
    .main-content {{ margin-top: 100px; }}
    
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        border: 6px solid #b8c1cf !important; border-left: 12px solid #1e40af !important;
        border-radius: 10px !important; background-color: #ffffff !important; 
        margin-bottom: 15px !important; padding: 0 !important;
    }}

    .machine-title {{ 
        background: #f8fafc; padding: 2px; text-align: center; font-size: 11px; font-weight: 700; 
        border-radius: 4px; margin-bottom: 8px; border: 2px solid #cbd5e1;
        min-height: 28px; display: flex; align-items: center; justify-content: center; 
    }}

    button[kind="secondary"] {{
        height: 22px !important; min-height: 22px !important; border: 1.5px solid #94a3b8 !important;
        border-radius: 4px !important; background: linear-gradient(180deg, #ffffff 0%, #d1d5db 100%) !important;
        box-shadow: 0 3px 0 #94a3b8, 0 4px 6px rgba(0,0,0,0.1) !important; padding: 0 !important; transition: all 0.05s ease !important;
    }}
    button[kind="secondary"]:active {{ box-shadow: 0 1px 0 #94a3b8 !important; transform: translateY(2px) !important; }}
    button[kind="secondary"] p {{ font-size: 11px !important; font-weight: 900; line-height: 22px !important; }}

    section[data-testid="stSidebar"] button {{
        height: 22px !important; min-height: 22px !important; line-height: 1 !important;
        padding: 0px 10px !important; font-size: 11px !important; font-weight: 800 !important; color: #000000 !important;
    }}
    
    section[data-testid="stSidebar"] .stButton button[key*="del_"] {{ height: 22px !important; min-height: 22px !important; padding: 0 !important; }}

    .block-prod-name {{ font-size: 11px !important; font-weight: 800; color: #1e293b; text-align: center; }}
    .block-batch-no {{ font-size: 11px !important; font-weight: 900; color: #1e40af; text-align: center; display: block; }}
    .status-bar {{ font-size: 10px; font-weight: 800; color: white; text-align: center; padding: 1px 0; border-radius: 3px; margin-bottom: 4px; }}
    .bg-waiting {{ background-color: #3b82f6; }} .bg-progress {{ background-color: #ef4444; }} .bg-pause {{ background-color: #f59e0b; }}
    </style>
    """, unsafe_allow_html=True)

# --- 4. 데이터 로딩 ---
def load_data():
    m_values = safe_get_all_values(master_sheet)
    master_dict = {}
    if len(m_values) > 1:
        for r in m_values[1:]:
            p_name = str(r[0]).strip()
            if p_name:
                master_dict[p_name] = {s: [m.strip() for m in str(val).split(',') if m.strip()] for s, val in zip(STAGES, r[3:10])}
    c_values = safe_get_all_values(worksheet)
    curr_rows = [{'Lot':str(r[0]),'제품':str(r[1]),'공정':str(r[2]),'상태':str(r[3]),'시작':str(r[4]),'최초시작시간':str(r[5]),'누적시간':str(r[6]),'유형':str(r[7]),'비고':str(r[8]),'Row':i+2, '설비':str(r[9]) if len(r)>9 else ""} for i,r in enumerate(c_values[1:]) if r and r[0]]
    l_values = safe_get_all_values(log_sheet)
    history_lots = [str(r[0]).strip() for r in l_values[1:] if r]
    return master_dict, pd.DataFrame(curr_rows), history_lots

master_dict, curr_df, history_lots = load_data()

if 'page' not in st.session_state: st.session_state.page = 'main'
if 'pending_lots' not in st.session_state: st.session_state.pending_lots = []
if 'injection_queue' not in st.session_state: st.session_state.injection_queue = []

# --- 5. 상단 헤더 ---
st.markdown(f'''
    <div class="fixed-header">
        <div class="header-left">
            <div class="header-title">🏭 명인제약 생산 시점 관리 시스템</div>
        </div>
        <div class="header-credit">제작: 생산1팀, 2026</div>
    </div>
''', unsafe_allow_html=True)

btn_label = "📊 이력 및 완료 확인" if st.session_state.page == 'main' else "⬅️ 현황판 돌아가기"
if st.button(btn_label, type="primary"):
    st.session_state.page = 'history' if st.session_state.page == 'main' else 'main'
    st.rerun()

st.markdown("<div class='main-content'>", unsafe_allow_html=True)

# --- 6. 다이얼로그 로직 ---
@st.dialog("다음 공정 장비 선택")
def select_next_machine(row, next_stg, m_list):
    st.write(f"📂 **{row['제품']}** (Lot: {row['Lot']})")
    st.write(f"**{next_stg}** 공정의 어느 장비로 이동할까요?")
    target_m = st.selectbox("사용할 장비 선택", m_list)
    if st.button("이동 확정", use_container_width=True, type="primary"):
        log_sheet.append_row([row['Lot'], row['제품'], row['공정'], row['시작'], get_now_kst(), "공정이동", row['유형'], row['비고']])
        worksheet.update_cell(row['Row'], 3, next_stg); worksheet.update_cell(row['Row'], 4, "대기")
        worksheet.update_cell(row['Row'], 5, ""); worksheet.update_cell(row['Row'], 10, target_m); st.rerun()

@st.dialog("장비 선택 투입")
def select_initial_machine_queue():
    if not st.session_state.injection_queue: st.rerun()
    item = st.session_state.injection_queue[0]
    st.write(f"📂 **{item['제품']}** (Lot: {item['Lot']})")
    st.write(f"첫 공정인 **{item['공정']}**의 투입 장비를 선택해주세요.")
    target_m = st.selectbox("투입 장비 선택", item['m_list'])
    if st.button("투입 확정", use_container_width=True, type="primary"):
        worksheet.append_row([item['Lot'], item['제품'], item['공정'], "대기", "", get_now_kst(), "0", item['유형'], item['비고'], target_m])
        st.session_state.injection_queue.pop(0)
        st.rerun()

# --- 7. 메인 페이지 로직 ---
if st.session_state.page == 'main':
    if st.session_state.injection_queue: select_initial_machine_queue()
    with st.sidebar:
        st.header("🆕 로트 신규 투입")
        p_list = list(master_dict.keys()) if master_dict else ["등록된 제품 없음"]
        sel_p = st.selectbox("제품명 선택", p_list)
        lot_in = st.text_input("제조번호 입력")
        type_in = st.selectbox("유형", ["일반로트", "동시PV1", "동시PV2", "동시PV3", "예측PV1", "예측PV2", "예측PV3"])
        note_in = st.text_area("비고")
        if st.button("➕ 투입 대기열에 추가", use_container_width=True):
            cleaned_lot = lot_in.strip()
            if cleaned_lot:
                already_in_production = cleaned_lot in curr_df['Lot'].values if not curr_df.empty else False
                already_in_pending = any(item['Lot'] == cleaned_lot for item in st.session_state.pending_lots)
                already_finished = cleaned_lot in history_lots
                if already_finished: st.error(f"❌ '{cleaned_lot}'은 이미 완료된 공정 이력에 존재합니다.")
                elif already_in_production: st.error(f"❌ '{cleaned_lot}'은 이미 생산 현황판에 존재합니다.")
                elif already_in_pending: st.warning(f"⚠️ '{cleaned_lot}'은 이미 투입 대기 목록에 있습니다.")
                else:
                    st.session_state.pending_lots.append({'제품': sel_p, 'Lot': cleaned_lot, '유형': type_in, '비고': note_in})
                    st.rerun()

        if st.session_state.pending_lots:
            st.markdown("---")
            st.subheader(f"📋 대기 목록")
            if st.button("🚀 전체 투입", use_container_width=True):
                temp_pending = st.session_state.pending_lots[:]
                for p_lot in temp_pending:
                    f_stg = next((s for s in STAGES if master_dict.get(p_lot['제품'], {}).get(s)), "과립")
                    m_list = master_dict[p_lot['제품']][f_stg]
                    if len(m_list) > 1:
                        st.session_state.injection_queue.append({'Lot': p_lot['Lot'], '제품': p_lot['제품'], '공정': f_stg, '유형': p_lot['유형'], '비고': p_lot['비고'], 'm_list': m_list})
                        st.session_state.pending_lots.remove(p_lot)
                    else:
                        worksheet.append_row([p_lot['Lot'], p_lot['제품'], f_stg, "대기", "", get_now_kst(), "0", p_lot['유형'], p_lot['비고'], m_list[0]])
                        st.session_state.pending_lots.remove(p_lot)
                st.rerun()
            for i, p_lot in enumerate(st.session_state.pending_lots):
                col_p, col_d = st.columns([0.8, 0.2])
                col_p.write(f"{i+1}. {p_lot['제품']} / {p_lot['Lot']}")
                if col_d.button("❌", key=f"del_{i}"):
                    st.session_state.pending_lots.pop(i); st.rerun()

        st.markdown("---")
        total_count = len(curr_df) if not curr_df.empty else 0
        st.subheader(f"📊 실시간 현황 (총 {total_count}건)")
        for stage in STAGES:
            cnt = len(curr_df[curr_df['공정'] == stage]) if not curr_df.empty else 0
            st.write(f"{stage}: {cnt}건")

    for stage in STAGES:
        bg, bc = stage_colors.get(stage, "#F1F5F9"), stage_border_colors.get(stage, "#CBD5E1")
        st.markdown(f"<div class='stage-title' style='background:{bg}; border-left:8px solid {bc}; color:{bc}; padding:5px 15px; font-weight:800; margin-top:20px;'>{stage}</div>", unsafe_allow_html=True)
        s_items = curr_df[curr_df['공정'] == stage] if not curr_df.empty else pd.DataFrame()
        cols = st.columns(10)
        for m_idx, machine in enumerate(machine_map[stage]):
            with cols[m_idx]:
                st.markdown(f"<div class='machine-title'>{machine}</div>", unsafe_allow_html=True)
                m_items = s_items[s_items['설비'] == machine] if not s_items.empty else pd.DataFrame()
                if not m_items.empty:
                    for _, row in m_items.iterrows():
                        with st.container(border=True):
                            st.markdown(f"<div class='block-prod-name'>{row['제품']}</div>", unsafe_allow_html=True)
                            st.markdown(f"<div class='block-batch-no'>{row['Lot']}</div>", unsafe_allow_html=True)
                            status_cls = "bg-waiting" if row['상태'] == '대기' else "bg-progress" if row['상태'] == '진행중' else "bg-pause"
                            st.markdown(f"<div class='status-bar {status_cls}'>{row['상태']}</div>", unsafe_allow_html=True)
                            if row['상태'] == '대기':
                                if st.button("시작", key=f"s_{row['Lot']}_{stage}", use_container_width=True):
                                    worksheet.update_cell(row['Row'], 4, "진행중"); worksheet.update_cell(row['Row'], 5, get_now_kst()); st.rerun()
                            elif row['상태'] == '진행중':
                                b1, b2 = st.columns(2)
                                with b1:
                                    if st.button("중단", key=f"p_{row['Lot']}_{stage}", use_container_width=True):
                                        worksheet.update_cell(row['Row'], 4, "중단"); st.rerun()
                                with b2:
                                    if st.button("완료", key=f"e_{row['Lot']}_{stage}", use_container_width=True):
                                        n_idx = STAGES.index(stage) + 1
                                        next_stg = next((STAGES[i] for i in range(n_idx, len(STAGES)) if master_dict.get(row['제품'], {}).get(STAGES[i])), None)
                                        if next_stg:
                                            m_list = master_dict[row['제품']][next_stg]
                                            if len(m_list) > 1: select_next_machine(row, next_stg, m_list)
                                            else:
                                                log_sheet.append_row([row['Lot'], row['제품'], stage, row['시작'], get_now_kst(), "공정이동", row['유형'], row['비고']])
                                                worksheet.update_cell(row['Row'], 3, next_stg); worksheet.update_cell(row['Row'], 4, "대기"); worksheet.update_cell(row['Row'], 10, m_list[0]); st.rerun()
                                        else:
                                            log_sheet.append_row([row['Lot'], row['제품'], "생산완료", row['최초시작시간'], get_now_kst(), "완료", row['유형'], row['비고']])
                                            worksheet.delete_rows(row['Row']); st.rerun()
                            elif row['상태'] == '중단':
                                if st.button("시작", key=f"r_{row['Lot']}_{stage}", use_container_width=True):
                                    worksheet.update_cell(row['Row'], 4, "진행중"); worksheet.update_cell(row['Row'], 5, get_now_kst()); st.rerun()
                else: st.markdown("<div style='text-align:center; color:#e2e8f0; font-size:10px;'>-</div>", unsafe_allow_html=True)
else:
    # 이력 페이지
    st.header("📋 전체 공정 이력 관리")
    log_data = safe_get_all_values(log_sheet)
    if len(log_data) > 1:
        df_log = pd.DataFrame(log_data[1:], columns=log_data[0])
        st.subheader("✅ 1. 최종 생산 완료 리스트"); st.dataframe(df_log[df_log['공정'] == '생산완료'].iloc[::-1], use_container_width=True)
        st.markdown("---"); st.subheader("⏳ 2. 공정 이동 및 진행 이력"); st.dataframe(df_log[df_log['공정'] != '생산완료'].iloc[::-1], use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)