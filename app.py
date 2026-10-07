import streamlit as st

# --- 1. 페이지 설정 ---
st.set_page_config(layout="wide", page_title="명인제약 생산 시점 관리")

# --- 2. 안내 화면 CSS 및 UI ---
st.markdown("""
<style>
.stApp {
    background: linear-gradient(rgba(15, 23, 42, 0.8), rgba(15, 23, 42, 0.8)), 
                url('https://github.com/mi20060004-hub/myungin-pop/blob/main/%EB%AA%85%EC%9D%B8%EB%B0%94%ED%83%95_%EC%99%80%EC%9D%B4%EB%93%9C33.jpg?raw=true');
    background-size: cover; background-position: center; background-repeat: no-repeat;
}
.notice-container {
    text-align: center;
    padding: 60px 20px;
    margin-top: 80px;
}
.main-msg {
    color: #ffffff;
    font-size: 42px;
    font-weight: 900;
    line-height: 1.5;
    text-shadow: 0 4px 10px rgba(0,0,0,0.8);
    margin-bottom: 40px;
}
.link-box {
    display: inline-block;
    background: linear-gradient(135deg, #ff6b00 0%, #ff4500 100%);
    color: #ffffff !important;
    font-size: 24px;
    font-weight: 900;
    padding: 25px 40px;
    border-radius: 16px;
    text-decoration: none;
    box-shadow: 0 10px 30px rgba(255, 107, 0, 0.6);
    border: 3px solid #ffffff;
    transition: all 0.2s ease-in-out;
}
.link-box:hover {
    transform: scale(1.03);
    background: linear-gradient(135deg, #ff8533 0%, #ff5722 100%);
}
</style>

<div class="notice-container">
    <div class="main-msg">
        리뉴얼된 생산시점관리로 접속하십시오.
    </div>
    <div style="margin-top: 30px;">
        <a class="link-box" href="https://myungin-pop-management-three.vercel.app" target="_blank">
            🔗 접속 주소: https://myungin-pop-management-three.vercel.app/
        </a>
    </div>
</div>
""", unsafe_allow_html=True)

st.stop()
