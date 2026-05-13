import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 페이지 설정 ---
st.set_page_config(
    layout="wide", 
    page_title="명인제약 생산 시점 관리",
    initial_sidebar_state="expanded"
)

# --- 2. CSS 스타일 (파란색 대형 헤더 및 버튼 절대 위치 고정) ---
st.markdown("""
    <style>
    /* 1. 상단 고정 블루 헤더 바 */
    .fixed-header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 60px;
        background-color: #1e3a8a; /* 명인제약 진한 파란색 */
        z-index: 999998;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    
    /* 2. 제목 스타일 (글씨 더 크게) */
    .main-title-text {
        position: fixed;
        top: 20px;
        left: 40px;
        color: white !important;
        font-size: 30px !important; /* 글씨 크기 더 확대 */
        font-weight: 900;
        z-index: 999999;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        white-space: nowrap;
    }

    /* 3. 버튼 위치 강제 고정 (제목 우측) */
    .fixed-button-box {
        position: fixed;
        top: 35px; /* 제목 높이에 맞춰 조정 */
        left: 560px; /* 제목이 끝나는 지점 우측으로 고정 */
        z-index: 999999;
    }

    /* 4. 메인 컨텐츠 상단 여백 */
    .main .block-container {
        padding-top: 130px !important;
    }

    /* 5. 공정 가로 바 디자인 */
    .stage-bar {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
        padding: 10px 20px;
        border-radius: 8px;
        font-size: 20px;
        font-weight: 700;
        margin-top: 30px;
        margin-bottom: 20px;
        width: 100%;
        display: block;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: left;
    }

    /* 6. 설비 타이틀 및 기타 스타일 유지 */
    .machine-title {
        background: #f8fafc; padding: 4px; text-align: center; font-size: 11px; font-weight: 700;
        border-radius: 4px; margin-bottom: 8px; border: 1px solid #cbd5e1;
        min-height: 28px; display: flex; align-items: center; justify-content: center;
    }
    .status-bar { font-size: 10px; font-weight: 800; color: white; text-align: center; padding: 2px 0; border-radius: 3px; margin-bottom: 4px; }
    .bg-waiting { background-color: #3b82f6; } .bg-progress { background-color: #ef4444; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 인증 및 시트 연결 ---
@st.cache_resource
def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

gc = get_gspread_client()
SHEET_ID = "1ST-zbOoIoP5MvWkoTCFNDvi76yavH8pu2Ak7kudyzBM"
sh = gc.open_by_key(SHEET_ID)

worksheet = sh.worksheet('현재생산중')
log_sheet = sh.worksheet('공정이력')
master_sheet = sh.worksheet('제품마스터')

# --- 4. 데이터 로드 함수 ---
def get_now_kst():
    return (datetime.now(timezone(timedelta(hours=9)))).strftime('%Y-%m-%d KST %H:%M:%S')

def load_data():
    m_values = master_sheet.get_all_values()
    master_dict = {str(r[0]).strip(): {s: [m.strip() for m in str(val).split(',') if m.strip()] 
                   for s, val in zip(list(machine_map.keys()), r[3:10])} for r in m_values[1:] if r and r[0]}
    c_values = worksheet.get_all_values()
    curr_df = pd.DataFrame([{'Lot':r[0],'제품':r[1],'공정':r[2],'상태':r[3],'메모':r[8] if len(r)>8 else '','Row':i+2, '설비':r[9] if len(r)>9 else ""} 
                            for i,r in enumerate(c_values[1:]) if r and r[0]])
    return master_dict, curr_df

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
master_dict, curr_df = load_data()

# --- 5. 상단 헤더 렌더링 (제목 + 버튼) ---
if 'page' not in st.session_state: st.session_state.page = 'main'

# 파란 배경 바와 제목 출력
st.markdown('<div class="fixed-header"></div>', unsafe_allow_html=True)
st.markdown('<p class="main-title-text">명인제약 생산 시점 관리</p>', unsafe_allow_html=True)

# 버튼을 제목 우측에 강제 배치
st.markdown('<div class="fixed-button-box">', unsafe_allow_html=True)
btn_text = "현황판 돌아가기" if st.session_state.page == 'history' else "완료 이력 확인"
if st.button(btn_text, key="top_history_btn"):
    st.session_state.page = 'history' if st.session_state.page == 'main' else 'main'
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# --- 6. 사이드바 구성 ---
with st.sidebar:
    st.header("🏭 제조 투입")
    st.divider()
    sel_p = st.selectbox("제품명 선택", list(master_dict.keys()) if master_dict else ["데이터 없음"])
    lot_in = st.text_input("제조번호(Lot) 입력")
    type_in = st.radio("제품 구분", ["일반제품", "PV"], horizontal=True)
    memo_in = st.text_area("상세설명 (메모)", placeholder="특이사항을 입력하세요")
    
    if st.button("➕ 대기열 추가", use_container_width=True):
        if lot_in:
            if 'pending' not in st.session_state: st.session_state.pending = []
            st.session_state.pending.append({'제품': sel_p, 'Lot': lot_in, '구분': type_in, '메모': memo_in})
            st.rerun()
            
    if 'pending' in st.session_state and st.session_state.pending:
        if st.button("🚀 전체 투입 확정", type="primary", use_container_width=True):
            for p in st.session_state.pending:
                f_stg = next((s for s in STAGES if master_dict.get(p['제품'], {}).get(s)), "과립")
                f_m = master_dict[p['제품']][f_stg][0] if master_dict[p['제품']][f_stg] else ""
                worksheet.append_row([p['Lot'], p['제품'], f_stg, "대기", "", get_now_kst(), "0", p['구분'], p['메모'], f_m])
            st.session_state.pending = []
            st.rerun()
    st.divider()
    st.subheader("📊 실시간 공정 현황")
    for stage in STAGES:
        count = len(curr_df[curr_df['공정'] == stage]) if not curr_df.empty else 0
        st.write(f"**{stage}:** {count}건")

# --- 7. 페이지 컨텐츠 ---
current_page = st.session_state.get('page', 'main')

if current_page == 'main':
    for stage in STAGES:
        st.markdown(f'<div class="stage-bar">▶ {stage} 공정</div>', unsafe_allow_html=True)
        cols = st.columns(10)
        for m_idx, machine in enumerate(machine_map[stage]):
            with cols[m_idx]:
                st.markdown(f"<div class='machine-title'>{machine}</div>", unsafe_allow_html=True)
                m_items = curr_df[(curr_df['공정'] == stage) & (curr_df['설비'] == machine)] if not curr_df.empty else pd.DataFrame()
                
                if m_items.empty:
                    st.markdown("<div style='text-align:center; color:#e2e8f0; font-size:10px;'>-</div>", unsafe_allow_html=True)
                else:
                    for _, row in m_items.iterrows():
                        with st.container(border=True):
                            st.markdown(f"<div style='font-size:11px; font-weight:800; text-align:center;'>{row['제품']}</div>", unsafe_allow_html=True)
                            st.markdown(f"<div style='font-size:11px; font-weight:900; color:#1e40af; text-align:center;'>{row['Lot']}</div>", unsafe_allow_html=True)
                            if row['메모']: st.caption(f"📝 {row['메모']}")
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
                                        worksheet.update_cell(row['Row'], 3, next_stg)
                                        worksheet.update_cell(row['Row'], 4, "대기")
                                        worksheet.update_cell(row['Row'], 5, "")
                                        worksheet.update_cell(row['Row'], 10, master_dict[row['제품']][next_stg][0])
                                    else:
                                        log_sheet.append_row([row['Lot'], row['제품'], "생산완료", "", get_now_kst(), "완료"])
                                        worksheet.delete_rows(row['Row'])
                                    st.rerun()
else:
    st.header("📋 공정 이력 리스트")
    log_data = log_sheet.get_all_values()
    if len(log_data) > 1:
        st.dataframe(pd.DataFrame(log_data[1:], columns=log_data[0]), use_container_width=True)
