"""
raw_total 시트(프로모션·캠페인·광고그룹·소재 단위) 전처리
"""
import numpy as np
import pandas as pd

NUM_COLS = ["노출수", "클릭수", "비용", "구매", "매출"]


def _safe_div(a, b):
    return (a / b).replace([np.inf, -np.inf], np.nan)


_MISSING_PROMO = {"", "#N/A", "#n/a", "nan", "none", "-"}


def _fill_promotion(df: pd.DataFrame) -> pd.DataFrame:
    """메타 캠페인은 네이밍 규칙상 프로모션명이 캠페인명 3번째 토큰(0-based index 2)에 고정.
    예) 2607_OY_올영픽특가_녹두선_구매 -> 올영픽특가.
    프로모션 값이 비었거나 #N/A인 메타 행에 한해 캠페인 3번째 토큰으로 보정한다.
    (구글 등 다른 매체나 이미 값이 있는 행은 건드리지 않음)"""
    if not {"프로모션", "캠페인", "매체"} <= set(df.columns):
        return df
    promo = df["프로모션"].astype(str).str.strip()
    missing = promo.str.lower().isin(_MISSING_PROMO)
    is_meta = df["매체"].astype(str).str.strip().str.lower().eq("meta")
    token3 = df["캠페인"].astype(str).str.split("_").str[2]
    fillable = missing & is_meta & token3.notna() & token3.astype(str).str.len().gt(0)
    df.loc[fillable, "프로모션"] = token3[fillable]
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in NUM_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c].replace("", pd.NA), errors="coerce").fillna(0)
    if "일자" in df.columns:
        df["일자"] = pd.to_datetime(df["일자"], errors="coerce")
    df = _fill_promotion(df)
    return _add_metrics(df)


def _add_metrics(df: pd.DataFrame) -> pd.DataFrame:
    if {"클릭수", "노출수"} <= set(df.columns):
        df["CTR(%)"] = (_safe_div(df["클릭수"], df["노출수"]) * 100).round(2)
    if {"비용", "클릭수"} <= set(df.columns):
        df["CPC"] = _safe_div(df["비용"], df["클릭수"]).round(0)
    if {"비용", "노출수"} <= set(df.columns):
        df["CPM"] = (_safe_div(df["비용"], df["노출수"]) * 1000).round(0)
    if {"구매", "클릭수"} <= set(df.columns):
        df["CVR(%)"] = (_safe_div(df["구매"], df["클릭수"]) * 100).round(2)
    if {"비용", "구매"} <= set(df.columns):
        df["CPA"] = _safe_div(df["비용"], df["구매"]).round(0)
    if {"매출", "비용"} <= set(df.columns):
        df["ROAS(%)"] = (_safe_div(df["매출"], df["비용"]) * 100).round(0)
    return df
