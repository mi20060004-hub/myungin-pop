import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 인증 및 시트 연결 (Streamlit Secrets 방식) ---
def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    # Colab의 default() 대신 st.secrets를 사용하여 보안 인증
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

gc = get_gspread_client()

def safe_get_all_values(worksheet):
    if worksheet is None: return []
    try: return worksheet.get_all_values()
    except: return []

# 시트 열기 (Colab과 동일한 파일명 찾기)
try:
    sh = gc.open('생산관리_시스템')
except:
    try: sh = gc.open('생산관리_SYSTEM')
    except:
        st.error("❌ '생산관리_시스템' 구글 시트 파일을 찾을 수 없습니다.")
        st.stop()

worksheet = sh.worksheet('현재생산중')
log_sheet = sh.worksheet('공정이력')
master_sheet = sh.worksheet('제품마스터')

# --- 2. 유틸리티 함수 및 설정 (Colab 로직 유지) ---
def get_now_kst():
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst).strftime('%Y-%m-%d KST %H:%M:%S')

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

# --- 3. 스타일 디자인 (Colab 디자인 100% 재현) ---
st.set_page_config(layout="wide", page_title="명인제약 생산 시점 관리 시스템", initial_sidebar_state="expanded")

st.markdown(f"""
    <style>
    .stApp {{ background-color: #ffffff; }}
    [data-testid="stHeader"] {{ display: none; }}
    .fixed-header {{
        position: fixed; top: 0; left: 0; right: 0; height: 80px; background-color: white;
        display: flex; align-items: center; justify-content: center;
        z-index: 1000; border-bottom: 3px solid #1e293b;
    }}
    .header-title {{ font-size: 28px !important; font-weight: 900; color: #1e3a8a; }}
    .main-content {{ margin-top: 100px; }}
    .machine-title {{
        background: #f8fafc; padding: 2px; text-align: center; font-size: 11px; font-weight: 700;
        border-radius: 4px; margin-bottom: 8px; border: 1px solid #cbd5e1;
        min-height: 28px; display: flex; align-items: center; justify-content: center;
    }}
    .status-bar {{ font-size: 10px; font-weight: 800; color: white; text-align: center; padding: 1px 0; border-radius: 3px; margin-bottom: 4px; }}
    .bg-waiting {{ background-color: #3b82f6; }} .bg-progress {{ background-color: #ef4444; }} .bg-pause {{ background-color: #f59e0b; }}
    .stage-title {{ padding: 5px 15px; font-weight: 800; margin-top: 20px; border-radius: 4px; }}
    </style>
    <div class="fixed-header"><div class="header-title">🏭 명인제약 생산 시점 관리 시스템</div></div>
    """, unsafe_allow_html=True)

# --- 4. 데이터 로딩 ---
def load_data():
    m_values = safe_get_all_values(master_sheet)
    master_dict = {str(r[0]).strip(): {s: [m.strip() for m in str(val).split(',') if m.strip()] for s, val in zip(STAGES, r[3:10])} for r in m_values[1:] if r and r[0]}
    c_values = safe_get_all_values(worksheet)
    curr_df = pd.DataFrame([{'Lot':str(r[0]),'제품':str(r[1]),'공정':str(r[2]),'상태':str(r[3]),'시작':str(r[4]),'최초시작시간':str(r[5]),'유형':str(r[7]),'비고':str(r[8]),'Row':i+2, '설비':str(r[9]) if len(r)>9 else ""} for i,r in enumerate(c_values[1:]) if r and r[0]])
    l_values = safe_get_all_values(log_sheet)
    history_lots = [str(r[0]).strip() for r in l_values[1:] if r]
    return master_dict, curr_df, history_lots

master_dict, curr_df, history_lots = load_data()

# 세션 상태 초기화
if 'page' not in st.session_state: st.session_state.page = 'main'
if 'injection_queue' not in st.session_state: st.session_state.injection_queue = []

# --- 5. 다이얼로그 (Colab @st.dialog 재현) ---
@st.dialog("다음 공정 장비 선택")
def select_next_machine_dialog(row, next_stg, m_list):
    st.write(f"📂 **{row['제품']}** (Lot: {row['Lot']})")
    target_m = st.selectbox("사용할 장비 선택", m_list)
    if st.button("이동 확정", use_container_width=True, type="primary"):
        log_sheet.append_row([row['Lot'], row['제품'], row['공정'], row['시작'], get_now_kst(), "공정이동", row['유형'], row['비고']])
        worksheet.update_cell(row['Row'], 3, next_stg)
        worksheet.update_cell(row['Row'], 4, "대기")
        worksheet.update_cell(row['Row'], 10, target_m)
        st.rerun()

# --- 6. 메인 로직 ---
st.markdown("<div class='main-content'>", unsafe_allow_html=True)

# 페이지 전환 버튼
if st.button("📊 이력 확인 / 현황판 전환", type="primary", key="toggle_btn"):
    st.session_state.page = 'history' if st.session_state.page == 'main' else 'main'
    st.rerun()

if st.session_state.page == 'main':
    # 사이드바: 투입
    with st.sidebar:
        st.header("🏭 제조 투입")
        sel_p = st.selectbox("제품명 선택", list(master_dict.keys()) if master_dict else ["데이터 없음"])
        lot_in = st.text_input("제조번호 입력")
        type_in = st.radio("제품 구분", ["일반로트", "PV"], horizontal=True)
        note_in = st.text_area("상세설명 (메모)")
        if st.button("➕ 투입 대기열 추가", use_container_width=True):
            if lot_in.strip() and lot_in not in curr_df['Lot'].values:
                f_stg = next((s for s in STAGES if master_dict.get(sel_p, {}).get(s)), "과립")
                f_m = master_dict[sel_p][f_stg][0] if master_dict[sel_p][f_stg] else ""
                worksheet.append_row([lot_in, sel_p, f_stg, "대기", "", get_now_kst(), "0", type_in, note_in, f_m])
                st.rerun()

    # 현황판 렌더링 (10열 배치)
    for stage in STAGES:
        bg, bc = stage_colors.get(stage, "#F1F5F9"), stage_border_colors.get(stage, "#CBD5E1")
        st.markdown(f"<div class='stage-title' style='background:{bg}; border-left:8px solid {bc}; color:{bc};'>▶ {stage} 공정</div>", unsafe_allow_html=True)
        
        cols = st.columns(10)
        s_items = curr_df[curr_df['공정'] == stage]
        for m_idx, machine in enumerate(machine_map[stage]):
            with cols[m_idx]:
                st.markdown(f"<div class='machine-title'>{machine}</div>", unsafe_allow_html=True)
                m_items = s_items[s_items['설비'] == machine]
                for _, row in m_items.iterrows():
                    with st.container(border=True):
                        st.markdown(f"<div class='block-prod-name'>{row['제품']}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='block-batch-no'>{row['Lot']}</div>", unsafe_allow_html=True)
                        cls = "bg-waiting" if row['상태'] == '대기' else "bg-progress"
                        st.markdown(f"<div class='status-bar {cls}'>{row['상태']}</div>", unsafe_allow_html=True)
                        
                        if row['상태'] == '대기':
                            if st.button("시작", key=f"s_{row['Lot']}_{stage}"):
                                worksheet.update_cell(row['Row'], 4, "진행중")
                                worksheet.update_cell(row['Row'], 5, get_now_kst())
                                st.rerun()
                        elif row['상태'] == '진행중':
                            if st.button("완료", key=f"e_{row['Lot']}_{stage}"):
                                n_idx = STAGES.index(stage) + 1
                                next_stg = next((STAGES[i] for i in range(n_idx, len(STAGES)) if master_dict.get(row['제품'], {}).get(STAGES[i])), None)
                                if next_stg:
                                    m_list = master_dict[row['제품']][next_stg]
                                    if len(m_list) > 1: select_next_machine_dialog(row, next_stg, m_list)
                                    else:
                                        log_sheet.append_row([row['Lot'], row['제품'], stage, row['시작'], get_now_kst(), "공정이동", row['유형'], row['비고']])
                                        worksheet.update_cell(row['Row'], 3, next_stg)
                                        worksheet.update_cell(row['Row'], 4, "대기")
                                        worksheet.update_cell(row['Row'], 10, m_list[0])
                                        st.rerun()
                                else:
                                    log_sheet.append_row([row['Lot'], row['제품'], "생산완료", "", get_now_kst(), "완료", row['유형'], row['비고']])
                                    worksheet.delete_rows(row['Row'])
                                    st.rerun()
else:
    st.header("📋 전체 공정 이력 리스트")
    log_data = safe_get_all_values(log_sheet)
    if len(log_data) > 1:
        st.dataframe(pd.DataFrame(log_data[1:], columns=log_data[0]).iloc[::-1], use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)
