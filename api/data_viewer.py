# data_viewer.py
import streamlit as st
import pandas as pd
import plotly.express as px
from db_manager import get_db_engine
from data_collector import collect_and_save_data

# ------------------ 데이터 로드 ------------------
def load_data_and_save_to_session():
    """데이터를 로드하고 세션 상태에 저장"""
    engine = get_db_engine()
    try:
        car_df = pd.read_sql("SELECT * FROM car_regist", engine)
        if not car_df.empty:
            car_df["year"] = car_df["reg_date"].str[:4]
            car_df["month"] = car_df["reg_date"].str[4:6]
    except Exception:
        car_df = pd.DataFrame()

    try:
        faq_df = pd.read_sql("SELECT question, answer, source FROM faq", engine)
    except Exception:
        faq_df = pd.DataFrame()

    st.session_state.car_data = car_df
    st.session_state.faq_data = faq_df
    engine.dispose()

# ------------------ 메인 페이지 ------------------
def show_main_page():
    st.markdown("<h1 style='text-align: center; color: black; font-size: 2.5rem;'>🚗 자동차 통합 정보 플랫폼</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #555;'>필요한 모든 자동차 정보를 한눈에!</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("""
            <div style="border: 2px solid #e6e6e6; border-radius: 10px; padding: 20px; text-align: center; background-color: #f9f9f9; box-shadow: 2px 2px 8px rgba(0,0,0,0.1);">
                <h3 style="margin-top:0;">📈 데이터 조회</h3>
                <p>차량 등록 통계, 연도별, 지역별 데이터를 확인하세요.</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("차량 통계 보기", key='main_data_btn', use_container_width=True):
            st.session_state.page = '데이터 조회'
            st.rerun()
    with col2:
        st.markdown("""
            <div style="border: 2px solid #e6e6e6; border-radius: 10px; padding: 20px; text-align: center; background-color: #f9f9f9; box-shadow: 2px 2px 8px rgba(0,0,0,0.1);">
                <h3 style="margin-top:0;">❓ FAQ</h3>
                <p>현대/기아차의 자주 묻는 질문을 검색하세요.</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("FAQ 검색하기", key='main_faq_btn', use_container_width=True):
            st.session_state.page = 'FAQ'
            st.rerun()

# ------------------ 데이터 조회 페이지 ------------------
def show_data_dashboard(car_df):
    st.markdown(f"""
        <div style="position: sticky; top: 0; background-color: white; padding: 1rem 0; z-index: 999; border-bottom: 1px solid #e6e6e6;">
            <h1 style='margin:0;'>📈 차량 등록 통계</h1>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        years = sorted(car_df["year"].unique())
        selected_year = st.selectbox("연도", years, key='year_select')
    with col2:
        months = sorted(car_df[car_df["year"] == selected_year]["month"].unique())
        selected_month = st.selectbox("월", months, key='month_select')
    with col3:
        sido_list = sorted(car_df["sido"].unique())
        selected_sido = st.selectbox("시도", sido_list, key='sido_select')
    with col4:
        filtered_sigungu = sorted(car_df[car_df["sido"] == selected_sido]["sigungu"].unique())
        selected_sigungu = st.selectbox("시군구", filtered_sigungu, key='sigungu_select')

    filtered_df = car_df[
        (car_df["year"] == selected_year) &
        (car_df["month"] == selected_month) &
        (car_df["sido"] == selected_sido) &
        (car_df["sigungu"] == selected_sigungu)
    ]

    if filtered_df.empty:
        st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
    else:
        tabs_car = st.tabs(["차량 종류별", "차량 용도별", "데이터 테이블"])
        with tabs_car[0]:
            st.subheader("차량 종류별 등록대수")
            chart_df = filtered_df.groupby("car_type")["count"].sum().reset_index()
            fig = px.bar(chart_df, x='car_type', y='count')
            fig.update_layout(title_text='차량 종류별 등록대수', showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        with tabs_car[1]:
            st.subheader("차량 용도별 비율")
            pie_df = filtered_df.groupby("usage_type")["count"].sum().reset_index()
            fig = px.pie(pie_df, names='usage_type', values='count', hole=0.45)
            st.plotly_chart(fig, use_container_width=True)
        with tabs_car[2]:
            st.subheader("필터링된 데이터")
            st.dataframe(filtered_df, height=400, use_container_width=True)

# ------------------ FAQ 페이지 ------------------
def show_faq_page(faq_df):
    st.markdown(f"""
        <div style="position: sticky; top: 0; background-color: white; padding: 1rem 0; z-index: 999; border-bottom: 1px solid #e6e6e6;">
            <h1 style='margin:0;'>❓ 통합 FAQ</h1>
        </div>
    """, unsafe_allow_html=True)

    search_col1, search_col2 = st.columns([1, 3])
    with search_col1:
        search_option = st.selectbox(
            "검색 범위",
            ("제목", "내용", "제목 + 내용"),
            index=0,
            key='search_option'
        )
    with search_col2:
        search_query = st.text_input(
            "궁금한 점을 입력하세요.",
            placeholder="차량 정비, 보증, 부품 등...",
            key='faq_search'
        )

    if search_query:
        if search_option == "제목":
            search_results = faq_df[faq_df['question'].str.contains(search_query, case=False, na=False)]
        elif search_option == "내용":
            search_results = faq_df[faq_df['answer'].str.contains(search_query, case=False, na=False)]
        else:
            search_results = faq_df[
                faq_df['question'].str.contains(search_query, case=False, na=False) |
                faq_df['answer'].str.contains(search_query, case=False, na=False)
            ]
        if search_results.empty:
            st.info("검색 결과가 없습니다.")
        else:
            display_paginated_faq(search_results)
    else:
        display_paginated_faq(faq_df)

# ------------------ FAQ 페이지네이션 ------------------
def display_paginated_faq(df):
    st.markdown(f"총 {len(df)}개의 FAQ가 있습니다.")
    st.markdown("---")

    page_size = 10
    total_pages = (len(df) + page_size - 1) // page_size

    if 'current_faq_page' not in st.session_state:
        st.session_state.current_faq_page = 1

    start_index = (st.session_state.current_faq_page - 1) * page_size
    end_index = start_index + page_size
    paginated_df = df.iloc[start_index:end_index]

    for _, row in paginated_df.iterrows():
        source_name = "현대차" if row['source'] == 0 else "기아차"
        with st.expander(f"**Q. {row['question']}**"):
            st.markdown(f"**출처:** _{source_name}_")
            st.write(f"**A.** {row['answer']}")

    st.markdown("---")
    page_group_size = 5
    current_group = (st.session_state.current_faq_page - 1) // page_group_size
    start_page = current_group * page_group_size + 1
    end_page = min(start_page + page_group_size - 1, total_pages)

    cols = st.columns([1] + [1] * (end_page - start_page + 1) + [1])

    with cols[0]:
        if st.button("◀️"):
            if st.session_state.current_faq_page > 1:
                st.session_state.current_faq_page -= 1
                st.rerun()

    for i in range(start_page, end_page + 1):
        with cols[i - start_page + 1]:
            if st.button(f"{i}", key=f"page_btn_{i}"):
                st.session_state.current_faq_page = i
                st.rerun()

    with cols[-1]:
        if st.button("▶️"):
            if st.session_state.current_faq_page < total_pages:
                st.session_state.current_faq_page += 1
                st.rerun()

# ------------------ 전체 대시보드 ------------------
def show_dashboard():
    st.set_page_config(page_title="자동차 통합 정보 플랫폼", layout="wide")
    if 'page' not in st.session_state:
        st.session_state.page = 'loading'
    if 'car_data' not in st.session_state:
        st.session_state.car_data = pd.DataFrame()
    if 'faq_data' not in st.session_state:
        st.session_state.faq_data = pd.DataFrame()

    if st.session_state.page == 'loading':
        with st.spinner("데이터를 로드하는 중입니다. 처음 실행 시 시간이 걸릴 수 있습니다."):
            try:
                if st.session_state.car_data.empty:
                    collect_and_save_data()
                load_data_and_save_to_session()
                if not st.session_state.car_data.empty:
                    st.session_state.page = 'main'
                    st.rerun()
                else:
                    st.error("데이터 수집에 실패했습니다. API 키와 DB 연결을 확인해주세요.")
                    st.stop()
            except Exception as e:
                st.error(f"데이터 로드 중 오류 발생: {e}")
                st.stop()
    elif st.session_state.page == 'main':
        show_main_page()
    else:
        with st.sidebar:
            st.markdown('<div style="text-align: center;"><button onclick="window.location.href=\'/\'" style="background-color: transparent; border: none; cursor: pointer;"><span style="font-size: 2rem;">🏠</span></button></div>', unsafe_allow_html=True)
            st.markdown("---")
            if st.button("📈 데이터 조회", use_container_width=True):
                st.session_state.page = '데이터 조회'
                st.rerun()
            if st.button("❓ FAQ", use_container_width=True):
                st.session_state.page = 'FAQ'
                st.rerun()

        if st.session_state.page == "데이터 조회":
            show_data_dashboard(st.session_state.car_data)
        elif st.session_state.page == "FAQ":
            show_faq_page(st.session_state.faq_data)