import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 구글 시트 연결 설정 ---
def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(credentials)

def load_data(sheet_name):
    client = get_gspread_client()
    sh = client.open_by_url(st.secrets["gsheet_url"])
    worksheet = sh.worksheet(sheet_name)
    data = worksheet.get_all_records()
    return pd.DataFrame(data), worksheet

# --- 2. 페이지 설정 ---
st.set_page_config(page_title="명인제약 생산관리 시스템", layout="wide")
st.title("🏭 명인제약 생산 시점 관리 (칸반보드형)")

# 데이터 로드
try:
    master_df, _ = load_data("product_master")
    history_df, history_worksheet = load_data("product_history")
    
    # 완료되지 않은 실시간 가동 공정만 추출
    if not history_df.empty:
        current_production = history_df[history_df['상태'] != '완료'].copy()
    else:
        current_production = pd.DataFrame()
except Exception as e:
    st.error(f"데이터 로딩 오류: {e}")
    st.info("구글 시트의 탭 이름이 'product_master'와 'product_history'인지 확인하세요.")
    st.stop()

# --- 3. 사이드바: 신규 생산 등록 ---
with st.sidebar:
    st.header("➕ 신규 생산 등록")
    with st.form("add_form", clear_on_submit=True):
        new_lot = st.text_input("제조번호 (LOT)")
        selected_product = st.selectbox("제품명", master_df['제품명'].unique()) if not master_df.empty else st.selectbox("제품명", ["등록된 제품 없음"])
        lot_type = st.selectbox("로트유형", ["일반", "동시PV1", "기타"])
        remarks = st.text_area("비고")
        
        submit = st.form_submit_button("등록하기")
        
        if submit:
            if new_lot and selected_product and selected_product != "등록된 제품 없음":
                # 신규 등록 시 무조건 첫 공정인 '과립공정'의 '대기' 상태로 시작
                new_row = [new_lot, selected_product, "과립공정", "대기", "", "", "", lot_type, remarks]
                history_worksheet.append_row(new_row)
                st.success(f"LOT {new_lot} 등록 완료!")
                st.rerun()
            else:
                st.warning("제조번호와 제품명을 올바르게 선택해 주세요.")

# --- 4. 메인 화면: 공정별 칸반보드 현황판 ---
st.subheader("📊 공정별 실시간 이동 현황")

# 제약 공정 단계 정의
stages = ["과립공정", "타정공정", "포장공정"]
cols = st.columns(len(stages))

for i, stage in enumerate(stages):
    with cols[i]:
        # 공정별 구역 헤더 디자인
        st.markdown(f"### 🛑 {stage}")
        st.divider()
        
        # 해당 공정에 속한 데이터 필터링
        if not current_production.empty:
            stage_df = current_production[current_production['공정명'] == stage]
        else:
            stage_df = pd.DataFrame()
            
        if not stage_df.empty:
            for index, row in stage_df.iterrows():
                row_idx = index + 2  # 구글 시트 행 인덱스 계산
                
                # 상태별 카드 색상 구분 감성
                status_emoji = "⏳" if row['상태'] == "대기" else "⚡"
                
                # 개별 제품 카드 박스
                with st.container(border=True):
                    st.markdown(f"**{status_emoji} LOT: {row['제조번호']}**")
                    st.text(f"품명: {row['제품명']}")
                    st.caption(f"유형: {row['로트유형']} | 상태: {row['상태']}")
                    if row['비고']:
                        st.caption(f"💬 {row['비고']}")
                        
                    # 카드 내부 제어 버튼
                    if row['상태'] == "대기":
                        if st.button("▶️ 공정시작", key=f"start_{index}", use_container_width=True):
                            now = datetime.now().strftime('%Y-%m-%d %H:%M')
                            history_worksheet.update_cell(row_idx, 4, "진행중") # 상태 -> 진행중
                            history_worksheet.update_cell(row_idx, 5, now)       # 시작시간 입력
                            st.rerun()
                            
                    elif row['상태'] == "진행중":
                        if st.button("✅ 공정완료", key=f"end_{index}", use_container_width=True):
                            now = datetime.now().strftime('%Y-%m-%d %H:%M')
                            
                            # 소요시간 자동 계산
                            try:
                                start_dt = datetime.strptime(row['시작시간'], '%Y-%m-%d %H:%M')
                                end_dt = datetime.strptime(now, '%Y-%m-%d %H:%M')
                                duration = str(end_dt - start_dt)
                            except:
                                duration = "-"
                                
                            # 현재 공정을 '완료'로 바꾸고 종료 기록
                            history_worksheet.update_cell(row_idx, 4, "완료")
                            history_worksheet.update_cell(row_idx, 6, now)
                            history_worksheet.update_cell(row_idx, 7, duration)
                            
                            # [다음 공정 자동 이동 로직]
                            # 과립공정 완료 -> 타정공정 대기로 신규 행 추가
                            # 타정공정 완료 -> 포장공정 대기로 신규 행 추가
                            if stage == "과립공정":
                                next_row = [row['제조번호'], row['제품명'], "타정공정", "대기", "", "", "", row['로트유형'], row['비고']]
                                history_worksheet.append_row(next_row)
                            elif stage == "타정공정":
                                next_row = [row['제조번호'], row['제품명'], "포장공정", "대기", "", "", "", row['로트유형'], row['비고']]
                                history_worksheet.append_row(next_row)
                                
                            st.rerun()
        else:
            st.caption("공정 비어있음")

# --- 5. 하단: 전체 누적 이력 조회 ---
st.divider()
st.subheader("📋 전체 생산 이력 리포트")
if not history_df.empty:
    st.dataframe(history_df.sort_index(ascending=False), use_container_width=True)
else:
    st.write("누적된 생산 이력이 없습니다.")
