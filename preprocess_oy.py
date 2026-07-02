"""
raw_total 시트(프로모션·캠페인·광고그룹·소재 단위) 전처리
"""
import numpy as np
import pandas as pd

NUM_COLS = ["노출수", "클릭수", "비용", "구매", "매출"]


def _safe_div(a, b):
    return (a / b).replace([np.inf, -np.inf], np.nan)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in NUM_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c].replace("", pd.NA), errors="coerce").fillna(0)
    if "일자" in df.columns:
        df["일자"] = pd.to_datetime(df["일자"], errors="coerce")
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
