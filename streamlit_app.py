"""
올리브영 프로모션 대시보드 (배포용 단일 페이지)
- 구글 시트 raw_total 실시간 연동
- 로컬: ~/.claude OAuth 토큰 / 클라우드: Streamlit Secrets 서비스계정
"""
import pandas as pd
import plotly.express as px
import streamlit as st

from gsheet_source import load_sheet
from preprocess_oy import clean

SPREADSHEET_ID = "16x2eJrpKkKX8o--4u4PPwTfDjCEdi6wAloXRlpzQrxo"
SHEET_NAME = "raw_total"

st.set_page_config(page_title="올리브영 프로모션 대시보드", page_icon="🛍️", layout="wide")

PLOT = dict(color_discrete_sequence=px.colors.qualitative.Set2)


def fmt(n, unit=""):
    if pd.isna(n):
        return "-"
    return f"{n:,.0f}{unit}"


col_l, col_r = st.columns([5, 1])
with col_l:
    st.title("🛍️ 올리브영 프로모션 대시보드")
    st.caption("구글 시트 `raw_total` 실시간 연동 (5분 캐시) · 버튼으로 즉시 새로고침 가능")
with col_r:
    st.write("")
    if st.button("🔄 새로고침"):
        load_sheet.clear()
        st.rerun()

try:
    raw = load_sheet(SPREADSHEET_ID, SHEET_NAME)
except Exception as e:
    st.error(f"구글 시트 로드 실패: {e}")
    st.stop()

if raw.empty:
    st.warning("시트에 데이터가 없습니다.")
    st.stop()

df = clean(raw)

# ------------------------------------------------------------------ 사이드바 필터
st.sidebar.header("필터")

dmin, dmax = df["일자"].min(), df["일자"].max()
if pd.notna(dmin) and dmin != dmax:
    date_range = st.sidebar.date_input("기간", (dmin, dmax), min_value=dmin, max_value=dmax)
    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        df = df[(df["일자"] >= pd.Timestamp(date_range[0])) & (df["일자"] <= pd.Timestamp(date_range[1]))]


def multi(col, label):
    if col not in df.columns:
        return None
    opts = sorted([o for o in df[col].dropna().unique().tolist() if o != ""])
    return st.sidebar.multiselect(label, opts, default=opts)


for col, label in [("프로모션", "프로모션"), ("채널", "채널"), ("매체", "매체"), ("품목", "품목")]:
    sel = multi(col, label)
    if sel is not None:
        df = df[df[col].isin(sel)]

if df.empty:
    st.warning("필터 결과가 없습니다. 조건을 넓혀주세요.")
    st.stop()

# ------------------------------------------------------------------ KPI
tot_cost = df["비용"].sum()
tot_rev = df["매출"].sum()
tot_imp = df["노출수"].sum()
tot_clk = df["클릭수"].sum()
tot_buy = df["구매"].sum()
roas = (tot_rev / tot_cost * 100) if tot_cost else 0
ctr = (tot_clk / tot_imp * 100) if tot_imp else 0
cpc = (tot_cost / tot_clk) if tot_clk else 0

st.subheader("핵심 지표")
c = st.columns(4)
c[0].metric("총 비용", fmt(tot_cost, "원"))
c[1].metric("총 매출", fmt(tot_rev, "원"))
c[2].metric("ROAS", fmt(roas, "%"))
c[3].metric("구매", fmt(tot_buy, "건"))
c = st.columns(4)
c[0].metric("노출", fmt(tot_imp))
c[1].metric("클릭", fmt(tot_clk))
c[2].metric("CTR", f"{ctr:.2f}%")
c[3].metric("CPC", fmt(cpc, "원"))

st.divider()

# ------------------------------------------------------------------ 프로모션별
st.subheader("프로모션별 성과")
promo = df.groupby("프로모션", as_index=False).agg(비용=("비용", "sum"), 매출=("매출", "sum"), 구매=("구매", "sum"))
promo["ROAS(%)"] = (promo["매출"] / promo["비용"] * 100).round(0)
promo = promo.sort_values("매출", ascending=False)
fig = px.bar(
    promo.melt(id_vars="프로모션", value_vars=["비용", "매출"]),
    x="프로모션", y="value", color="variable", barmode="group",
    title="프로모션별 비용 vs 매출", labels={"value": "원", "variable": ""}, **PLOT,
)
st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------ 매체별 / 품목별
col1, col2 = st.columns(2)
with col1:
    ch = df.groupby("매체", as_index=False).agg(비용=("비용", "sum"), 매출=("매출", "sum"))
    ch["ROAS(%)"] = (ch["매출"] / ch["비용"] * 100).round(0)
    fig = px.bar(ch, x="매체", y="ROAS(%)", color="매체", title="매체별 ROAS", text="ROAS(%)", **PLOT)
    st.plotly_chart(fig, use_container_width=True)
with col2:
    if "품목" in df.columns:
        item = df.groupby("품목", as_index=False).agg(매출=("매출", "sum"))
        item = item.sort_values("매출", ascending=False).head(10)
        fig = px.bar(item, x="매출", y="품목", orientation="h", title="품목별 매출 Top 10", **PLOT)
        fig.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------ 캠페인 Top
st.subheader("캠페인별 매출 Top 15")
cmp = df.groupby("캠페인", as_index=False).agg(비용=("비용", "sum"), 매출=("매출", "sum"), 구매=("구매", "sum"))
cmp["ROAS(%)"] = (cmp["매출"] / cmp["비용"] * 100).round(0)
cmp = cmp.sort_values("매출", ascending=False).head(15)
fig = px.bar(cmp, x="매출", y="캠페인", orientation="h", color="ROAS(%)",
             color_continuous_scale="Blues", title="캠페인별 매출 Top 15")
fig.update_yaxes(categoryorder="total ascending")
st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------ 소재 Top
st.subheader("광고소재별 매출 Top 15")
mat = df.groupby(["광고소재", "매체"], as_index=False).agg(비용=("비용", "sum"), 매출=("매출", "sum"))
mat["ROAS(%)"] = (mat["매출"] / mat["비용"] * 100).round(0)
mat = mat.sort_values("매출", ascending=False).head(15)
fig = px.bar(mat, x="매출", y="광고소재", color="매체", orientation="h",
             title="광고소재별 매출 Top 15", **PLOT)
fig.update_yaxes(categoryorder="total ascending")
st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------ 시계열
if df["일자"].nunique() > 1:
    st.subheader("일자별 추이")
    ts = df.groupby("일자", as_index=False).agg(비용=("비용", "sum"), 매출=("매출", "sum"))
    fig = px.line(ts, x="일자", y=["비용", "매출"], markers=True, title="일자별 비용·매출", **PLOT)
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------ 원본 테이블
st.subheader("원본 데이터")
st.caption(f"{len(df):,}행")
st.dataframe(df, use_container_width=True, height=400)
