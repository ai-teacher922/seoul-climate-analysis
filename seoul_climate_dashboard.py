"""서울 연평균기온 변화 대시보드

실행 방법(내 컴퓨터) : streamlit run seoul_climate_dashboard.py
필요한 파일        : seoul_temperature.csv (이 파이썬 파일과 같은 폴더)
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="서울 연평균기온 변화", page_icon="🌡️", layout="wide")

DATA_FILE = "seoul_temperature.csv"
MIN_DAYS = 360  # 관측일이 이보다 적은 해는 연평균이 한쪽 계절로 치우치므로 제외할 수 있게 함


# ─────────────────────────────────────────────
# 1. 데이터 불러오기
# ─────────────────────────────────────────────
@st.cache_data
def load_data(path):
    # utf-8-sig : 파일 맨 앞의 보이지 않는 표시(BOM)를 지워서 첫 열 이름이 정확히 '날짜'가 되게 함
    df = pd.read_csv(path, encoding="utf-8-sig")

    # 날짜 앞의 탭 문자를 지우고 날짜 형식으로 바꿈
    # errors="coerce" : 날짜가 비어 있는 줄(파일 마지막 줄)은 오류 대신 빈 값(NaT)으로 바꿈
    df["날짜"] = pd.to_datetime(df["날짜"].astype(str).str.strip(), errors="coerce")
    df = df.dropna(subset=["날짜"])

    df["연도"] = df["날짜"].dt.year
    return df


@st.cache_data
def make_yearly(df):
    # 연도별 평균기온과, 그 해에 기온 값이 있는 날(관측일) 수
    yearly = df.groupby("연도").agg(
        연평균기온=("평균기온(℃)", "mean"),
        관측일수=("평균기온(℃)", "count"),
    )
    # 자료가 아예 없는 해도 빠짐없이 한 줄씩 있도록 채움 (그래프에서 빈 기간이 끊겨 보이게 하기 위함)
    all_years = range(int(df["연도"].min()), int(df["연도"].max()) + 1)
    yearly = yearly.reindex(all_years)
    yearly["관측일수"] = yearly["관측일수"].fillna(0).astype(int)
    yearly.index.name = "연도"
    return yearly


df = load_data(DATA_FILE)
yearly = make_yearly(df)


# ─────────────────────────────────────────────
# 2. 사이드바 만들기
# ─────────────────────────────────────────────
st.sidebar.header("설정")

first_year = int(yearly.index.min())
last_year = int(yearly.index.max())
start, end = st.sidebar.slider(
    "연도 범위",
    min_value=first_year,
    max_value=last_year,
    value=(first_year, last_year),
)

exclude_partial = st.sidebar.checkbox(
    f"관측일이 {MIN_DAYS}일 미만인 해는 연평균에서 제외",
    value=True,
    help="일부 달만 기록된 해는 연평균이 실제보다 높거나 낮게 나옵니다.",
)

# 그래프에 쓸 연평균 : 체크하면 자료가 부족한 해를 빈 값으로 바꿈
plot_data = yearly.copy()
if exclude_partial:
    plot_data.loc[plot_data["관측일수"] < MIN_DAYS, "연평균기온"] = None

# 5년 이동평균 : 그 해를 가운데에 두고 앞뒤 2년씩, 5년 값이 모두 있을 때만 계산
plot_data["5년 이동평균"] = (
    plot_data["연평균기온"].rolling(window=5, center=True, min_periods=5).mean()
)

view = plot_data.loc[start:end]
selected = df[df["연도"].between(start, end)]


# ─────────────────────────────────────────────
# 3. 차트 그리기
# ─────────────────────────────────────────────
st.title("서울 연평균기온 변화")
st.caption(
    f"기상청 서울(지점 108) 일별 기온 · 선택 구간 {start}년 ~ {end}년"
)

# 선택 구간의 평균·최고·최저 기온
if selected["평균기온(℃)"].notna().sum() == 0:
    st.warning("선택한 구간에는 기온 자료가 없습니다. 연도 범위를 넓혀 주세요.")
    st.stop()

avg_temp = selected["평균기온(℃)"].mean()
hottest = selected.loc[selected["최고기온(℃)"].idxmax()]
coldest = selected.loc[selected["최저기온(℃)"].idxmin()]

col1, col2, col3 = st.columns(3)
col1.metric("평균기온 (일평균의 평균)", f"{avg_temp:.2f}℃")
col2.metric("최고기온", f"{hottest['최고기온(℃)']:.1f}℃")
col2.caption(f"{hottest['날짜']:%Y년 %m월 %d일}")
col3.metric("최저기온", f"{coldest['최저기온(℃)']:.1f}℃")
col3.caption(f"{coldest['날짜']:%Y년 %m월 %d일}")

# 연도별 평균기온 꺾은선 + 5년 이동평균선
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=view.index,
        y=view["연평균기온"],
        mode="lines+markers",
        name="연평균기온",
        line=dict(color="#90a4ae", width=1.5),
        marker=dict(size=4),
        hovertemplate="%{y:.2f}℃",
    )
)
fig.add_trace(
    go.Scatter(
        x=view.index,
        y=view["5년 이동평균"],
        mode="lines",
        name="5년 이동평균",
        line=dict(color="#e65100", width=3),
        hovertemplate="%{y:.2f}℃",
    )
)
fig.update_layout(
    title="연도별 평균기온과 5년 이동평균",
    xaxis_title="연도",
    yaxis_title="평균기온(℃)",
    hovermode="x unified",
    legend=dict(orientation="h", y=1.08, x=0),
    height=480,
    margin=dict(l=60, r=30, t=80, b=50),
)
st.plotly_chart(fig)

# 그래프에서 빠진 해 안내
missing_years = view.index[view["연평균기온"].isna()].tolist()
if missing_years:
    st.caption(
        "연평균이 표시되지 않은 해 : "
        + ", ".join(str(y) for y in missing_years)
        + " (기온 자료가 없거나, 관측일이 부족해 제외한 해. 1950~1953년은 한국전쟁으로 관측이 중단된 시기)"
    )

with st.expander("연도별 데이터 표 보기"):
    table = view.copy()
    table["연평균기온"] = table["연평균기온"].round(2)
    table["5년 이동평균"] = table["5년 이동평균"].round(2)
    st.dataframe(table)
