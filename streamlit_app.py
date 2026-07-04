"""
올리브영 프로모션 리포트 (배포용 단일 페이지)
- 실적(광고비·매출·ROAS·구매): raw_total 시트에서 집계
- 프로모션별 예산: summary 시트에서 파싱
- 로컬: ~/.claude OAuth 토큰 / 클라우드: Streamlit Secrets 서비스계정
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from gsheet_source import load_sheet
from preprocess_oy import clean
from budget_source import get_promo_budgets

SPREADSHEET_ID = "16x2eJrpKkKX8o--4u4PPwTfDjCEdi6wAloXRlpzQrxo"
RAW_SHEET = "raw_total"
SUMMARY_SHEET = "summary"

st.set_page_config(page_title="올리브영 프로모션 리포트", page_icon="📈", layout="wide")
PLOT = dict(color_discrete_sequence=px.colors.qualitative.Set2)


def won(n):
    return "-" if pd.isna(n) else f"{n:,.0f}원"


def pct(n):
    return "-" if pd.isna(n) else f"{n:,.0f}%"


# ------------------------------------------------------------------ 데이터 로드
col_l, col_r = st.columns([5, 1])
with col_l:
    st.title("📈 올리브영 프로모션 리포트")
    st.caption("실적=`raw_total` · 예산=`summary` 실시간 연동 (5분 캐시)")
with col_r:
    st.write("")
    if st.button("🔄 새로고침"):
        st.cache_data.clear()
        st.rerun()

try:
    df = clean(load_sheet(SPREADSHEET_ID, RAW_SHEET))
    budgets = get_promo_budgets(SPREADSHEET_ID, SUMMARY_SHEET)
except Exception as e:
    st.error(f"데이터 로드 실패: {e}")
    st.stop()

if df.empty:
    st.warning("raw_total 시트에 데이터가 없습니다.")
    st.stop()

# ------------------------------------------------------------------ 필터
st.sidebar.header("필터")

# 날짜 범위 (기본=전체 기간)
period_note = "전체 기간"
if "일자" in df.columns and df["일자"].notna().any():
    dmin, dmax = df["일자"].min().date(), df["일자"].max().date()
    if dmin != dmax:
        dr = st.sidebar.date_input("기간", (dmin, dmax), min_value=dmin, max_value=dmax)
        if isinstance(dr, (tuple, list)) and len(dr) == 2:
            df = df[(df["일자"] >= pd.Timestamp(dr[0])) & (df["일자"] <= pd.Timestamp(dr[1]))]
            if (dr[0], dr[1]) != (dmin, dmax):
                period_note = f"{dr[0]} ~ {dr[1]}"


def multi(col, label):
    if col not in df.columns:
        return None
    opts = sorted([o for o in df[col].dropna().unique().tolist() if o != ""])
    return st.sidebar.multiselect(label, opts, default=opts)


for col, label in [("프로모션", "프로모션"), ("매체", "매체")]:
    sel = multi(col, label)
    if sel is not None:
        df = df[df[col].isin(sel)]

if df.empty:
    st.warning("필터 결과가 없습니다.")
    st.stop()

# ------------------------------------------------------------------ 프로모션 집계 (예산 결합)
promo = df.groupby("프로모션", as_index=False).agg(
    광고비=("비용", "sum"), 매출=("매출", "sum"), 구매=("구매", "sum"), 노출=("노출수", "sum"), 클릭=("클릭수", "sum"),
)
promo["ROAS(%)"] = (promo["매출"] / promo["광고비"] * 100).round(0)
promo["예산"] = promo["프로모션"].map(lambda p: budgets.get(p, {}).get("예산"))
promo["소진율(%)"] = (promo["광고비"] / promo["예산"] * 100).round(1)
promo["기간"] = promo["프로모션"].map(
    lambda p: f"{budgets[p]['start']}~{budgets[p]['end']}" if p in budgets else ""
)
promo = promo.sort_values("매출", ascending=False).reset_index(drop=True)

# ------------------------------------------------------------------ 1. 전체 요약 스코어카드
tot_cost = df["비용"].sum()
tot_rev = df["매출"].sum()
tot_buy = df["구매"].sum()
blended_roas = (tot_rev / tot_cost * 100) if tot_cost else 0
tot_budget = promo["예산"].dropna().sum()
spend_of_budgeted = promo.loc[promo["예산"].notna(), "광고비"].sum()
burn = (spend_of_budgeted / tot_budget * 100) if tot_budget else 0

st.subheader(f"전체 요약  ·  {period_note}")
c = st.columns(4)
c[0].metric("총 광고비", won(tot_cost))
c[1].metric("총 매출", won(tot_rev))
c[2].metric("블렌디드 ROAS", pct(blended_roas))
c[3].metric("예산 소진율", pct(burn), help=f"예산 있는 프로모션 기준: {won(spend_of_budgeted)} / {won(tot_budget)}")
st.caption(f"※ 모든 수치는 선택 기간({period_note}) 기준. 소진율 = 해당 기간 광고비 ÷ summary 예산 → "
           "기간을 좁히면 소진율도 낮게 나옴. 집계 기준 차이로 공식 리포트와 소폭 다를 수 있음(추정).")

st.divider()

# ------------------------------------------------------------------ 2. 프로모션별 비교
st.subheader("프로모션별 비교")

disp = promo.copy()
disp["광고비"] = disp["광고비"].map(lambda x: f"{x:,.0f}")
disp["매출"] = disp["매출"].map(lambda x: f"{x:,.0f}")
disp["예산"] = disp["예산"].map(lambda x: "-" if pd.isna(x) else f"{x:,.0f}")
disp["ROAS(%)"] = disp["ROAS(%)"].map(lambda x: "-" if pd.isna(x) else f"{x:,.0f}%")
disp["소진율(%)"] = disp["소진율(%)"].map(lambda x: "-" if pd.isna(x) else f"{x:,.1f}%")
st.dataframe(
    disp[["프로모션", "광고비", "매출", "ROAS(%)", "예산", "소진율(%)", "기간"]],
    use_container_width=True, hide_index=True,
)

col1, col2 = st.columns(2)
with col1:
    m = promo.melt(id_vars="프로모션", value_vars=["광고비", "매출"], var_name="지표", value_name="원")
    fig = px.bar(m, x="프로모션", y="원", color="지표", barmode="group",
                 title="프로모션별 광고비 vs 매출", **PLOT)
    fig.update_layout(margin=dict(t=40))
    st.plotly_chart(fig, use_container_width=True)
with col2:
    bud = promo[promo["예산"].notna()].copy()
    fig = go.Figure()
    fig.add_bar(y=bud["프로모션"], x=bud["소진율(%)"], orientation="h",
                marker_color=["#d73027" if v > 100 else "#1a9850" for v in bud["소진율(%)"]],
                text=[f"{v:.0f}%" for v in bud["소진율(%)"]], textposition="outside")
    fig.add_vline(x=100, line_dash="dash", line_color="#888", annotation_text="예산 100%")
    fig.update_layout(title="프로모션별 예산 소진율", xaxis_title="소진율(%)",
                      yaxis=dict(categoryorder="total ascending"), margin=dict(l=10, r=40, t=40))
    st.plotly_chart(fig, use_container_width=True)

# 프로모션별 ROAS (손익분기 100% 기준선) — 광고비 스케일에 눌리지 않게 별도 표시
roas_df = promo[promo["ROAS(%)"].notna()].sort_values("ROAS(%)")
fig = go.Figure()
fig.add_bar(y=roas_df["프로모션"], x=roas_df["ROAS(%)"], orientation="h",
            marker_color=["#d73027" if v < 100 else "#4575b4" for v in roas_df["ROAS(%)"]],
            text=[f"{v:.0f}%" for v in roas_df["ROAS(%)"]], textposition="outside")
fig.add_vline(x=100, line_dash="dash", line_color="#888", annotation_text="손익분기 100%")
fig.update_layout(title="프로모션별 ROAS (100% 미만=빨강)", xaxis_title="ROAS(%)",
                  margin=dict(l=10, r=50, t=40), height=max(240, 40 * len(roas_df)))
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ------------------------------------------------------------------ 3. 프로모션 선택 → 품목 하위 비교
st.subheader("프로모션 → 품목 하위 비교")
promo_opts = promo["프로모션"].tolist()
sel_promo = st.selectbox("프로모션 선택", promo_opts)
sub = df[df["프로모션"] == sel_promo]
item = sub[sub["품목"].fillna("") != ""].groupby("품목", as_index=False).agg(
    광고비=("비용", "sum"), 매출=("매출", "sum"), 구매=("구매", "sum"),
)
if item.empty:
    st.info(f"'{sel_promo}' 에는 품목 구분 데이터가 없습니다.")
else:
    item["ROAS(%)"] = (item["매출"] / item["광고비"] * 100).round(0)
    item = item.sort_values("매출", ascending=False)
    cc1, cc2 = st.columns([3, 2])
    with cc1:
        m = item.melt(id_vars="품목", value_vars=["광고비", "매출"], var_name="지표", value_name="원")
        fig = px.bar(m, x="품목", y="원", color="지표", barmode="group",
                     title=f"[{sel_promo}] 품목별 광고비 vs 매출", **PLOT)
        fig.update_layout(margin=dict(t=40))
        st.plotly_chart(fig, use_container_width=True)
    with cc2:
        t = item.copy()
        t["광고비"] = t["광고비"].map(lambda x: f"{x:,.0f}")
        t["매출"] = t["매출"].map(lambda x: f"{x:,.0f}")
        t["ROAS(%)"] = t["ROAS(%)"].map(lambda x: "-" if pd.isna(x) else f"{x:,.0f}%")
        st.dataframe(t[["품목", "광고비", "매출", "ROAS(%)"]], use_container_width=True, hide_index=True)

# ------------------------------------------------------------------ 상세 (접기)
with st.expander("캠페인별 매출 Top 15"):
    cmp = df.groupby("캠페인", as_index=False).agg(광고비=("비용", "sum"), 매출=("매출", "sum"))
    cmp["ROAS(%)"] = (cmp["매출"] / cmp["광고비"] * 100).round(0)
    cmp = cmp.sort_values("매출", ascending=False).head(15)
    fig = px.bar(cmp, x="매출", y="캠페인", orientation="h", color="ROAS(%)",
                 color_continuous_scale="Blues", title="캠페인별 매출 Top 15")
    fig.update_yaxes(categoryorder="total ascending")
    st.plotly_chart(fig, use_container_width=True)

with st.expander("광고소재별 매출 Top 15"):
    mat = df.groupby(["광고소재", "매체"], as_index=False).agg(광고비=("비용", "sum"), 매출=("매출", "sum"))
    mat["ROAS(%)"] = (mat["매출"] / mat["광고비"] * 100).round(0)
    mat = mat.sort_values("매출", ascending=False).head(15)
    fig = px.bar(mat, x="매출", y="광고소재", color="매체", orientation="h",
                 title="광고소재별 매출 Top 15", **PLOT)
    fig.update_yaxes(categoryorder="total ascending")
    st.plotly_chart(fig, use_container_width=True)

with st.expander("원본 데이터"):
    st.caption(f"{len(df):,}행")
    st.dataframe(df, use_container_width=True, height=400)
