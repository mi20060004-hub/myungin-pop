import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 페이지 설정 및 디자인 (과립공정 스타일 프레임 정의) ---
st.set_page_config(layout="wide", page_title="명인제약 생산 시점 관리")

st.markdown("""
<style>
    /* 고정 헤더 디자인 */
    .fixed-header {
        position: fixed; top: 0; left: 0; right: 0; height: 66px; 
        background-color: #1e3a8a; z-index: 999998; 
        display: flex; align-items: center; padding: 0 30px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    .main-title-text { color: white !important; font-size: 24px !important; font-weight: 800; margin: 0; }
    
    /* 메인 컨테이너 여백 */
    .main .block-container { padding-top: 80px !important; }

    /* 모든 공정에 적용할 고정 프레임 박스 */
    .kanban-column-box {
        background-color: #f8fafc;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #cbd5e1;
        min-height: 450px;
        margin-bottom: 20px;
    }

    /* 상단 블루 공정 헤더 */
    .kanban-header {
        background-color: #1e40af;
        color: white;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        font-weight: 700;
        font-size: 14px;
        margin-bottom: 15px;
    }
    
    /* 과립공정 표준 LOT 카드 디자인 */
    .lot-card {
        background-color: white;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
        border-left: 5px solid #3b82f6;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-right: 1px solid #e2e8f0;
        border-top: 1px solid #e2e8f0;
        border-bottom: 1px solid #e2e8f0;
    }
    .status-badge {
        font-size: 11px;
        padding: 3px 6px;
        border-radius: 4px;
        color: white;
        font-weight: 700;
    }
    .bg-waiting { background-color: #64748b; }
    .bg-progress { background-color: #ef4444; }
    
    /* 공정이 비어있을 때 틀을 유지하기 위한 투명한 텍스트 */
    .empty-text {
        text-align: center;
        color: #94a3b8;
        font-size: 13px;
        padding-top: 40px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 구글 시트 연결 ---
def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

try:
    gc = get_gspread_client()
    SHEET_ID = "1yZGPeS_HSTo7xjXJym7yv2-kjx9m06Ob6d81tVGV7G8"
    sh = gc.open_by_key(SHEET_ID)
    history_sheet = sh.worksheet('product_history')
    master_sheet = sh.worksheet('product_master')
except Exception as e:
    st.error(f"구글 시트 연결 실패: {e}")
    st.stop()

# --- 3. 데이터 로드 및 처리 ---
def get_now_kst():
    return (datetime.now(timezone(timedelta(hours=9)))).strftime('%Y-%m-%d %H:%M')

@st.cache_data(ttl=2)
def load_data():
    m_values = master_sheet.get_all_values()
    master_list = [r[0] for r in m_values[1:] if r]
    
    h_values = history_sheet.get_all_values()
    if len(h_values) > 1:
        data = []
        for i, r in enumerate(h_values[1:]):
            data.append({
                'Lot': r[0], '제품': r[1], '공정': r[2], '상태': r[3],
                '시작': r[4], '종료': r[5], '소요': r[6], '유형': r[7], '비고': r[8], 'Row': i + 2
            })
        df = pd.DataFrame(data)
    else:
        df = pd.DataFrame(columns=['Lot', '제품', '공정', '상태', '시작', '종료', '소요', '유형', '비고', 'Row'])
    return master_list, df

master_products, history_df = load_data()
active_df = history_df[history_df['상태'] != '완료']

# --- 4. 사이드바 (제조 투입 메뉴) ---
with st.sidebar:
    st.markdown("### 📋 제조 투입")
    with st.form("input_form", clear_on_submit=True):
        sel_p = st.selectbox("제품명 선택", master_products)
        lot_in = st.text_input("제조번호 입력")
        lot_type = st.selectbox("로트 유형 선택", ["일반", "동시PV1", "동시PV2", "동시PV3"])
        note_in = st.text_area("공정 특이사항 입력")
        add_queue = st.form_submit_button("➕ 투입 대기열에 포함")
        
    if 'queue' not in st.session_state: st.session_state.queue = []
    
    if add_queue and lot_in:
        st.session_state.queue.append({'Lot': lot_in, '제품': sel_p, '유형': lot_type, '비고': note_in})
        st.rerun()

    if st.session_state.queue:
        st.divider()
        st.write("**투입 대기열**")
        for q in st.session_state.queue:
            st.caption(f"{q['Lot']} | {q['제품']}")
        
        c1, c2 = st.columns(2)
        if c1.button("전체 삭제", use_container_width=True):
            st.session_state.queue = []
            st.rerun()
        if c2.button("전체 투입", type="primary", use_container_width=True):
            for q in st.session_state.queue:
                history_sheet.append_row([q['Lot'], q['제품'], "과립공정", "대기", "", "", "", q['유형'], q['비고']])
            st.session_state.queue = []
            st.success("투입 완료!")
            st.rerun()

    st.divider()
    st.markdown("### 📊 공정 현황")
    st.write(f"실시간 공정 수량: **{len(active_df)}건**")
    
    STAGES = ["과립공정", "건조공정", "정립공정", "혼합공정", "타정공정", "캡슐공정", "질량선별공정", "인쇄공정", "외관선별공정"]
    for s in STAGES:
        cnt = len(active_df[active_df['공정'] == s])
        st.write(f"- {s}: {cnt}건")

# --- 5. 메인 화면 (과립공정 스타일로 9개 칸막이 올 통일) ---
st.markdown('<div class="fixed-header"><p class="main-title-text">명인제약 생산 시점 관리</p></div>', unsafe_allow_html=True)

# 가로로 정렬된 9개의 동일한 컬럼 생성
cols = st.columns(len(STAGES))

for i, stage in enumerate(STAGES):
    with cols[i]:
        # 대괄호 안쪽 전체를 하나의 회색 컨테이너 프레임으로 감싸 과립공정과 완벽 동기화
        st.markdown(f'<div class="kanban-column-box">', unsafe_allow_html=True)
        
        # 공정 제목 헤더
        st.markdown(f'<div class="kanban-header">{stage}</div>', unsafe_allow_html=True)
        
        # 해당 공정 데이터 추출
        items = active_df[active_df['공정'] == stage]
        
        if items.empty:
            # 데이터가 없을 때도 과립공정 형태를 유지하며 깔끔하게 텍스트 출력
            st.markdown("<p class='empty-text'>대기 작업 없음</p>", unsafe_allow_html=True)
        else:
            for _, row in items.iterrows():
                # 표준화된 LOT 카드 출력
                st.markdown(f"""
                <div class="lot-card">
                    <p style="font-size:14px; font-weight:800; margin:0; color:#1e3a8a;">{row['Lot']}</p>
                    <p style="font-size:12px; color:#334155; font-weight:700; margin:3px 0;">{row['제품']}</p>
                    <p style="font-size:11px; color:#64748b; margin-bottom:8px;">{row['유형']}</p>
                    <span class="status-badge {'bg-progress' if row['상태']=='진행중' else 'bg-waiting'}">{row['상태']}</span>
                </div>
                """, unsafe_allow_html=True)
                
                # 시작 / 완료 제어 버튼
                if row['상태'] == "대기":
                    if st.button("시작", key=f"btn_s_{row['Row']}", use_container_width=True):
                        history_sheet.update_cell(row['Row'], 4, "진행중")
                        history_sheet.update_cell(row['Row'], 5, get_now_kst())
                        st.rerun()
                elif row['상태'] == "진행중":
                    if st.button("완료", key=f"btn_e_{row['Row']}", use_container_width=True):
                        now = get_now_kst()
                        # 1. 현재 공정 마감
                        history_sheet.update_cell(row['Row'], 4, "완료")
                        history_sheet.update_cell(row['Row'], 6, now)
                        
                        # 2. 다음 공정 자동 이동
                        current_idx = STAGES.index(stage)
                        if current_idx < len(STAGES) - 1:
                            next_stage = STAGES[current_idx + 1]
                            history_sheet.append_row([row['Lot'], row['제품'], next_stage, "대기", "", "", "", row['유형'], row['비고']])
                        st.rerun()
                        
        st.markdown('</div>', unsafe_allow_html=True) # 프레임 박스 마감

# --- 6. 하단 전체 이력 ---
with st.expander("📝 전체 생산 이력 리포트 보기"):
    st.dataframe(history_df.sort_index(ascending=False), use_container_width=True)
