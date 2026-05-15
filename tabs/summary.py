import streamlit as st
import pandas as pd
from data_loader import ROAS_GOOD, ROAS_WATCH, CHANNEL_COLORS, get_wow_pair

_STATUS_EMOJI = {"양호": "🟢", "관찰": "🟡", "개선필요": "🔴"}
_STATUS_COLOR = {"양호": "#2ecc71", "관찰": "#f39c12", "개선필요": "#e74c3c"}


def _agg(df: pd.DataFrame) -> dict:
    cost = df["비용"].sum()
    rev = df["구매매출"].sum()
    signup = df["af_회원가입"].sum() if "af_회원가입" in df.columns else 0
    ch_signup = df["회원가입"].sum()
    return {
        "비용": cost,
        "매출": rev,
        "ROAS": rev / cost if cost else None,
        "가입_CPA": cost / signup if signup else None,
        "af_커버리지": signup / ch_signup * 100 if ch_signup else None,
    }


def _delta_str(curr, prev) -> str:
    if prev is None or prev == 0 or curr is None:
        return ""
    pct = (curr - prev) / abs(prev) * 100
    sign = "▲" if pct > 0 else "▼"
    return f"{sign} {abs(pct):.1f}% vs 전주"


def _kpi_card(col, label: str, value, prev_value, fmt: str):
    if value is None:
        col.metric(label, "N/A")
        return
    if fmt == "won":
        display = f"₩{value/1e8:.1f}억" if value >= 1e8 else f"₩{value/1e4:.0f}만"
    elif fmt == "roas":
        display = f"{value:.2f}"
    elif fmt == "pct":
        display = f"{value:.1f}%"
    else:
        display = f"₩{value:,.0f}"
    delta = _delta_str(value, prev_value)
    col.metric(label, display, delta)


def render(df: pd.DataFrame):
    curr_df, prev_df = get_wow_pair(df)
    curr = _agg(curr_df)
    prev = _agg(prev_df)

    latest_date = df["일"].max().strftime("%Y-%m-%d")
    st.subheader(f"📅 {latest_date} 기준 (전일 성과)")

    # KPI 카드
    c1, c2, c3, c4 = st.columns(4)
    _kpi_card(c1, "총 비용", curr["비용"], prev["비용"], "won")
    _kpi_card(c2, "ROAS", curr["ROAS"], prev["ROAS"], "roas")
    _kpi_card(c3, "가입 CPA", curr["가입_CPA"], prev["가입_CPA"], "cpa")
    _kpi_card(c4, "AF 커버리지", curr["af_커버리지"], prev["af_커버리지"], "pct")

    # ROAS 신호등 배너
    roas_val = curr["ROAS"]
    if roas_val is not None:
        status = "양호" if roas_val >= ROAS_GOOD else ("관찰" if roas_val >= ROAS_WATCH else "개선필요")
        color = _STATUS_COLOR[status]
        st.markdown(
            f"<div style='background:{color}22;border-left:4px solid {color};"
            f"padding:10px 16px;border-radius:6px;margin:8px 0'>"
            f"<b>전체 ROAS {roas_val:.2f}</b> — {_STATUS_EMOJI[status]} {status}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # 채널별 상태 카드
    st.markdown("**채널별 상태**")
    ch_roas = (
        curr_df.groupby("채널")
        .apply(lambda x: x["구매매출"].sum() / x["비용"].sum() if x["비용"].sum() else None)
        .dropna()
    )
    if not ch_roas.empty:
        cols = st.columns(len(ch_roas))
        for col, (ch, roas) in zip(cols, ch_roas.items()):
            s = "양호" if roas >= ROAS_GOOD else ("관찰" if roas >= ROAS_WATCH else "개선필요")
            color = CHANNEL_COLORS.get(ch, "#aaa")
            col.markdown(
                f"<div style='background:#1a2332;border-top:3px solid {color};"
                f"padding:12px;border-radius:6px;text-align:center'>"
                f"<div style='color:{color};font-weight:700'>{ch}</div>"
                f"<div style='font-size:20px'>{_STATUS_EMOJI[s]}</div>"
                f"<div style='font-weight:700'>ROAS {roas:.2f}</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # 주의 캠페인
    camp_roas = (
        curr_df.groupby("캠페인")
        .apply(lambda x: x["구매매출"].sum() / x["비용"].sum() if x["비용"].sum() else None)
        .dropna()
        .sort_values()
    )
    warn = camp_roas[camp_roas < ROAS_GOOD]
    if warn.empty:
        st.success("모든 캠페인 ROAS 양호 (≥4.0)")
    else:
        st.markdown("**⚠️ 주의 캠페인**")
        for camp, roas in warn.items():
            s = "개선필요" if roas < ROAS_WATCH else "관찰"
            emoji = _STATUS_EMOJI[s]
            color = _STATUS_COLOR[s]
            st.markdown(
                f"<div style='background:{color}11;border-left:3px solid {color};"
                f"padding:8px 12px;border-radius:4px;margin:4px 0'>"
                f"{emoji} <b>{camp}</b> — ROAS {roas:.2f}</div>",
                unsafe_allow_html=True,
            )
