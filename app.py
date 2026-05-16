import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 구글 시트 연결 설정 ---
def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Streamlit Secrets에 저장된 서비스 계정 정보 사용
    credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(credentials)

def load_data(sheet_name):
    client = get_gspread_client()
    # 시트 URL은 본인의 시트 URL로 수정하거나 Secrets에 저장하세요.
    sh = client.open_by_url(st.secrets["gsheet_url"])
    worksheet = sh.worksheet(sheet_name)
    data = worksheet.get_all_records()
    return pd.DataFrame(data), worksheet

# --- 2. 메인 화면 구성 ---
st.set_page_config(page_title="명인제약 POP 시스템", layout="wide")
st.title("🏭 명인제약 생산 시점 관리 (통합형)")

# 데이터 로드
try:
    master_df, _ = load_data("product_master")
    history_df, history_worksheet = load_data("product_history")
    
    # --- 현재 현황 필터링 (중요 로직) ---
    # 상태가 '완료'가 아닌 것들만 추출하여 현황판 구성
    # (각 제조번호별로 가장 마지막 행이 현재 상태임)
    current_production = history_df[history_df['상태'] != '완료'].copy()
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()

# --- 3. 사이드바: 신규 생산 등록 ---
with st.sidebar:
    st.header("➕ 신규 생산 등록")
    with st.form("add_form", clear_on_submit=True):
        new_lot = st.text_input("제조번호")
        selected_product = st.selectbox("제품명 선택", master_df['제품명'].unique())
        lot_type = st.selectbox("로트유형", ["동시PV1", "일반", "기타"])
        remarks = st.text_area("비고")
        
        submit_button = st.form_submit_button("등록")
        
        if submit_button:
            if new_lot and selected_product:
                # 첫 공정(보통 과립)을 '대기' 상태로 history에 첫 기록
                new_row = [new_lot, selected_product, "과립공정", "대기", "", "", "", lot_type, remarks]
                history_worksheet.append_row(new_row)
                st.success(f"{new_lot} 등록 완료! 페이지를 새로고침하세요.")
                st.rerun()

# --- 4. 메인 화면: 실시간 생산 현황 ---
st.subheader("📊 실시간 생산 공정 현황")

if not current_production.empty:
    for index, row in current_production.iterrows():
        with st.expander(f"📦 {row['제조번호']} - {row['제품명']} ({row['공정명']})", expanded=True):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("현재 공정", row['공정명'])
            with col2:
                status_color = "🔵" if row['상태'] == "진행중" else "⚪"
                st.write(f"**상태:** {status_color} {row['상태']}")
            with col3:
                st.write(f"**시작시간:** {row['시작시간']}")
            
            # 제어 버튼 로직
            with col4:
                # 1. 공정 시작 버튼
                if row['상태'] == "대기":
                    if st.button("공정 시작", key=f"start_{row['제조번호']}"):
                        # 해당 행을 찾아서 '진행중'으로 업데이트 및 시작시간 기록
                        # (gspread는 인덱스가 2부터 시작: 헤더1 + 0번인덱스=2)
                        row_idx = index + 2 
                        now = datetime.now().strftime('%Y-%m-%d %H:%M')
                        history_worksheet.update_cell(row_idx, 4, "진행중")
                        history_worksheet.update_cell(row_idx, 5, now)
                        st.rerun()
                
                # 2. 공정 완료 버튼
                elif row['상태'] == "진행중":
                    if st.button("공정 완료", key=f"end_{row['제조번호']}"):
                        row_idx = index + 2
                        now = datetime.now().strftime('%Y-%m-%d %H:%M')
                        
                        # 소요시간 계산
                        start_time = datetime.strptime(row['시작시간'], '%Y-%m-%d %H:%M')
                        end_time = datetime.strptime(now, '%Y-%m-%d %H:%M')
                        duration = str(end_time - start_time)
                        
                        # 현재 행을 '완료'로 업데이트
                        history_worksheet.update_cell(row_idx, 4, "완료")
                        history_worksheet.update_cell(row_idx, 6, now)
                        history_worksheet.update_cell(row_idx, 7, duration)
                        
                        # [다음 공정 자동 생성 로직]
                        # 실제 운영 시에는 마스터 데이터의 공정 순서를 참조하여 다음 행을 '대기'로 insert 합니다.
                        # 여기서는 예시로 '완료' 처리만 진행합니다.
                        st.rerun()
else:
    st.info("현재 진행 중인 생산 공정이 없습니다.")

# --- 5. 하단: 전체 이력 보기 ---
st.divider()
st.subheader("📋 전체 공정 이력 (누적)")
st.dataframe(history_df.sort_index(ascending=False), use_container_width=True)

### 🛠️ 적용 방법
1. 구글 시트에서 **`product_master`**와 **`product_history`** 시트를 준비합니다.
2. 위 코드를 `app.py`에 붙여넣습니다.
3. **Streamlit Cloud Settings**의 **Secrets**에 다음 두 가지가 정확히 들어있는지 확인하세요.
   * `gsheet_url`: 구글 시트의 전체 주소
   * `gcp_service_account`: 구글 클라우드에서 받은 서비스 계정 JSON 내용 전체
4. `requirements.txt`에 `gspread`, `google-auth`, `pandas`가 포함되어 있는지 확인합니다.

이제 이 시스템을 사용하면 **공정이 끝날 때마다 데이터가 사라지지 않고 아래로 차곡차곡 쌓이게 됩니다.** 이 상태에서 나중에 Supabase로 옮기는 것은 식은 죽 먹기입니다! 코드를 적용해 보시고 잘 작동하는지 말씀해 주세요.
