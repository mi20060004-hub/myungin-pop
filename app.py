import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 구글 시트 연결 설정 ---
def get_gspread_client():
    # Streamlit Secrets에 저장된 서비스 계정 정보 사용
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(credentials)

def load_data(sheet_name):
    client = get_gspread_client()
    # Secrets에 저장된 구글 시트 URL 사용
    sh = client.open_by_url(st.secrets["gsheet_url"])
    worksheet = sh.worksheet(sheet_name)
    data = worksheet.get_all_records()
    return pd.DataFrame(data), worksheet

# --- 2. 페이지 설정 ---
st.set_page_config(page_title="명인제약 생산관리 시스템", layout="wide")
st.title("🏭 명인제약 생산 시점 관리 (통합 이력형)")

# 데이터 로드
try:
    master_df, _ = load_data("product_master")
    history_df, history_worksheet = load_data("product_history")
    
    # 실시간 현황 필터링: '완료'되지 않은 공정만 추출
    current_production = history_df[history_df['상태'] != '완료'].copy()
except Exception as e:
    st.error(f"데이터 로딩 오류: {e}")
    st.info("구글 시트의 탭 이름이 'product_master'와 'product_history'인지 확인하세요.")
    st.stop()

# --- 3. 사이드바: 신규 생산 등록 ---
with st.sidebar:
    st.header("➕ 신규 생산 등록")
    with st.form("add_form", clear_on_submit=True):
        new_lot = st.text_input("제조번호 (LOT)")
        selected_product = st.selectbox("제품명", master_df['제품명'].unique())
        lot_type = st.selectbox("로트유형", ["일반", "동시PV1", "기타"])
        remarks = st.text_area("비고")
        
        submit = st.form_submit_button("등록하기")
        
        if submit:
            if new_lot and selected_product:
                # 새로운 공정 시작 시 '과립공정'을 기본으로 '대기' 상태 생성
                # 컬럼 순서: 제조번호, 제품명, 공정명, 상태, 시작시간, 종료시간, 소요시간, 로트유형, 비고
                new_row = [new_lot, selected_product, "과립공정", "대기", "", "", "", lot_type, remarks]
                history_worksheet.append_row(new_row)
                st.success(f"LOT {new_lot} 등록 완료!")
                st.rerun()
            else:
                st.warning("제조번호를 입력해 주세요.")

# --- 4. 메인 화면: 실시간 공정 현황판 ---
st.subheader("📊 실시간 생산 현황")

if not current_production.empty:
    for index, row in current_production.iterrows():
        # gspread 인덱스 계산 (Pandas index + 2)
        row_idx = index + 2
        
        with st.expander(f"📦 {row['제조번호']} - {row['제품명']} (현재: {row['공정명']})", expanded=True):
            c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
            
            with c1:
                st.write(f"**상태:** {row['상태']}")
                st.write(f"**유형:** {row['로트유형']}")
            with c2:
                st.write(f"**시작시간:** {row['시작시간'] if row['시작시간'] else '-'}")
            with c3:
                st.write(f"**비고:** {row['비고']}")
                
            with c4:
                # [시작] 버튼
                if row['상태'] == "대기":
                    if st.button("▶️ 공정 시작", key=f"start_{index}"):
                        now = datetime.now().strftime('%Y-%m-%d %H:%M')
                        history_worksheet.update_cell(row_idx, 4, "진행중") # 상태
                        history_worksheet.update_cell(row_idx, 5, now)       # 시작시간
                        st.rerun()
                
                # [완료] 버튼
                elif row['상태'] == "진행중":
                    if st.button("✅ 공정 완료", key=f"end_{index}"):
                        now = datetime.now().strftime('%Y-%m-%d %H:%M')
                        
                        # 소요시간 계산
                        start_dt = datetime.strptime(row['시작시간'], '%Y-%m-%d %H:%M')
                        end_dt = datetime.strptime(now, '%Y-%m-%d %H:%M')
                        duration = str(end_dt - start_dt)
                        
                        history_worksheet.update_cell(row_idx, 4, "완료")   # 상태
                        history_worksheet.update_cell(row_idx, 6, now)       # 종료시간
                        history_worksheet.update_cell(row_idx, 7, duration)  # 소요시간
                        st.rerun()
else:
    st.info("현재 가동 중인 생산 라인이 없습니다. 사이드바에서 신규 등록을 해주세요.")

# --- 5. 하단: 전체 누적 이력 조회 ---
st.divider()
st.subheader("📋 전체 생산 이력 리포트")
st.dataframe(history_df.sort_index(ascending=False), use_container_width=True)

### 💡 마지막 체크리스트
1. **구글 시트**: 아래 탭 2개만 남기고 나머지는 삭제하세요.
   * `product_master`: 기존 제품 정보 유지
   * `product_history`: 1행에 제가 드린 컬럼명 입력 (제조번호, 제품명, 공정명, 상태, 시작시간, 종료시간, 소요시간, 로트유형, 비고)
2. **깃허브**: 위 코드를 복사해서 `app.py`에 붙여넣고 **Commit changes**를 누르세요.
3. **스트림릿**: 앱을 새로고침하고 테스트 데이터를 넣어보세요!

이제 모든 준비가 끝났습니다. 코드를 적용해 보시고 궁금한 점이 생기면 언제든 말씀해 주세요!_
