"""
구글 시트 라이브 연동 (배포용)
- 우선순위 1: Streamlit Secrets 의 서비스계정([gcp_service_account]) → 클라우드 배포 시
- 우선순위 2: 로컬 OAuth 토큰(~/.claude/google-oauth-token.json) → 내 PC에서 개발/테스트 시
서비스계정을 쓰려면 대상 구글 시트를 서비스계정 이메일에 '뷰어'로 공유해야 함.
"""
import json
import os

import pandas as pd
import streamlit as st
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
LOCAL_TOKEN_PATH = os.environ.get(
    "GOOGLE_OAUTH_TOKEN_PATH",
    os.path.expanduser("~/.claude/google-oauth-token.json"),
)


def _get_credentials():
    # 1) 클라우드: Streamlit Secrets 의 서비스계정
    try:
        if "gcp_service_account" in st.secrets:
            from google.oauth2.service_account import Credentials as SACreds
            info = dict(st.secrets["gcp_service_account"])
            return SACreds.from_service_account_info(info, scopes=SCOPES)
    except Exception:
        pass  # secrets.toml 이 없으면 아래 로컬 토큰으로 폴백

    # 2) 로컬: OAuth 사용자 토큰
    from google.oauth2.credentials import Credentials
    with open(LOCAL_TOKEN_PATH, "r", encoding="utf-8") as f:
        info = json.load(f)
    creds = Credentials.from_authorized_user_info(info)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


@st.cache_data(ttl=300, show_spinner="구글 시트 불러오는 중...")
def load_sheet(spreadsheet_id: str, sheet_name: str) -> pd.DataFrame:
    from googleapiclient.discovery import build
    creds = _get_credentials()
    service = build("sheets", "v4", credentials=creds)
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"'{sheet_name}'!A:Z")
        .execute()
    )
    values = result.get("values", [])
    if not values:
        return pd.DataFrame()
    header, *rows = values
    width = len(header)
    rows = [r + [""] * (width - len(r)) for r in rows]
    return pd.DataFrame(rows, columns=header)


@st.cache_data(ttl=300, show_spinner=False)
def load_values(spreadsheet_id: str, sheet_name: str):
    """헤더가 불규칙한 시트(예: summary)용 — 원본 2D 리스트 그대로 반환."""
    from googleapiclient.discovery import build
    creds = _get_credentials()
    service = build("sheets", "v4", credentials=creds)
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"'{sheet_name}'!A:Z")
        .execute()
    )
    return result.get("values", [])
