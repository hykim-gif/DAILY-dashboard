"""
summary 탭에서 프로모션별 예산을 파싱.
summary는 사람이 보는 리포트 형식(병합셀·총계행)이라, '예산' 헤더 열을 찾은 뒤
그 열에 숫자가 채워진 행(=각 프로모션의 예산 행)만 골라낸다. 행 위치에 의존하지 않아 견고함.
"""
from gsheet_source import load_values


def _num(s):
    if s is None:
        return None
    s = str(s).replace(",", "").replace("₩", "").strip()
    if s in ("", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def get_promo_budgets(spreadsheet_id: str, sheet_name: str = "summary") -> dict:
    """{프로모션명: {'예산': float, 'start': str, 'end': str}} 반환."""
    vals = load_values(spreadsheet_id, sheet_name)
    hdr_idx = col_promo = col_budget = None
    col_start = col_end = None
    for i, row in enumerate(vals):
        if "예산" in row and "프로모션" in row:
            hdr_idx = i
            col_promo = row.index("프로모션")
            col_budget = row.index("예산")
            col_start = row.index("start date") if "start date" in row else None
            col_end = row.index("end date") if "end date" in row else None
            break

    budgets = {}
    if hdr_idx is None:
        return budgets

    for row in vals[hdr_idx + 1:]:
        name = (row[col_promo].strip() if col_promo < len(row) else "")
        if not name or name.endswith("총계"):
            continue
        b = _num(row[col_budget]) if col_budget < len(row) else None
        if b is None:
            continue
        start = row[col_start] if (col_start is not None and col_start < len(row)) else ""
        end = row[col_end] if (col_end is not None and col_end < len(row)) else ""
        budgets[name] = {"예산": b, "start": start, "end": end}
    return budgets
