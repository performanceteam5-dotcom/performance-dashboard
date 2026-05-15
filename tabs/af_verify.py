import streamlit as st
import pandas as pd
import plotly.express as px

_COVERAGE_OK = (70, 90)  # CLAUDE.md §5-1 정상 범위


def _coverage_status(pct: float) -> tuple[str, str]:
    if _COVERAGE_OK[0] <= pct <= _COVERAGE_OK[1]:
        return "✅ 정상", "#2ecc71"
    elif pct < _COVERAGE_OK[0]:
        return "⚠️ 낮음", "#e74c3c"
    else:
        return "⚠️ 높음 (오버카운팅?)", "#f39c12"


def _quality_checks(df: pd.DataFrame) -> list[tuple[str, str, str]]:
    checks = []

    zero_cost = int((df["비용"] == 0).sum())
    checks.append((
        "비용/노출 0인 행",
        "✅ OK" if zero_cost == 0 else f"⚠️ {zero_cost}행",
        f"비용=0 행 {zero_cost}개",
    ))

    key_cols = ["일", "채널", "캠페인", "그룹", "소재"]
    dupes = int(df.duplicated(subset=key_cols).sum())
    checks.append((
        "키 중복",
        "✅ OK" if dupes == 0 else f"⚠️ {dupes}건",
        f"(일·채널·캠페인·그룹·소재) 중복 {dupes}건",
    ))

    neg_rev = int((df["구매매출"] < 0).sum())
    checks.append((
        "음수 매출",
        "✅ OK" if neg_rev == 0 else f"⚠️ {neg_rev}행",
        f"환불 포함 가능성 {neg_rev}건",
    ))

    mean, std = df["비용"].mean(), df["비용"].std()
    outliers = int((df["비용"] > mean + 3 * std).sum())
    checks.append((
        "비용 이상치 (3σ)",
        "✅ OK" if outliers == 0 else f"⚠️ {outliers}행",
        f"평균 {mean:,.0f} + 3σ 초과 {outliers}건",
    ))

    return checks


def render(df: pd.DataFrame):
    if "af_회원가입" not in df.columns or df["af_회원가입"].isna().all():
        st.info("AppsFlyer 데이터가 없습니다. data/raw/appsflyer/ 폴더에 파일을 추가하세요.")
        # 품질 체크는 채널 데이터만으로도 실행
        st.subheader("데이터 품질 체크리스트 (CLAUDE.md §7-3)")
        for item, status, desc in _quality_checks(df):
            color = "#2ecc71" if "OK" in status else "#e74c3c"
            st.markdown(
                f"<div style='display:flex;gap:12px;padding:8px 0;border-bottom:1px solid #2d3748'>"
                f"<span style='color:{color};font-weight:700;min-width:130px'>{status}</span>"
                f"<span><b>{item}</b> — {desc}</span></div>",
                unsafe_allow_html=True,
            )
        return

    # 채널별 커버리지
    st.subheader("채널별 AF 커버리지")
    agg_cols = {
        "채널_가입": ("회원가입", "sum"),
        "af_가입": ("af_회원가입", "sum"),
        "채널_클릭": ("클릭", "sum"),
        "채널_구매": ("구매", "sum"),
        "af_구매": ("af_구매", "sum"),
        "비용": ("비용", "sum"),
    }
    if "af_클릭" in df.columns:
        agg_cols["af_클릭"] = ("af_클릭", "sum")
    if "ROAS" in df.columns:
        agg_cols["채널_ROAS"] = ("ROAS", "mean")
    if "AF_ROAS" in df.columns:
        agg_cols["af_ROAS"] = ("AF_ROAS", "mean")

    ch_cov = df.groupby("채널").agg(**agg_cols).reset_index()
    ch_cov["커버리지(%)"] = (ch_cov["af_가입"] / ch_cov["채널_가입"] * 100).round(1)
    ch_cov["가입갭(%)"] = ((ch_cov["af_가입"] - ch_cov["채널_가입"]) / ch_cov["채널_가입"] * 100).round(1)

    for _, row in ch_cov.iterrows():
        cov = row["커버리지(%)"]
        status, color = _coverage_status(cov)
        st.markdown(
            f"<div style='background:{color}11;border-left:4px solid {color};"
            f"padding:10px 16px;border-radius:6px;margin:4px 0'>"
            f"<b>{row['채널']}</b> — 커버리지 {cov:.1f}% {status}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.subheader("채널 보고 vs AF 비교")
    disp_cols = ["채널", "채널_가입", "af_가입", "커버리지(%)", "가입갭(%)", "채널_구매", "af_구매"]
    if "채널_ROAS" in ch_cov.columns:
        disp_cols += ["채널_ROAS", "af_ROAS"]
    st.dataframe(
        ch_cov[disp_cols].rename(columns={"채널_ROAS": "채널_ROAS(avg)", "af_ROAS": "AF_ROAS(avg)"}),
        use_container_width=True, hide_index=True,
    )

    fig = px.bar(
        ch_cov, x="채널", y=["채널_가입", "af_가입"], barmode="group",
        title="채널 보고 가입 vs AF 가입",
        color_discrete_sequence=["#3498db", "#e67e22"],
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("데이터 품질 체크리스트 (CLAUDE.md §7-3)")
    for item, status, desc in _quality_checks(df):
        color = "#2ecc71" if "OK" in status else "#e74c3c"
        st.markdown(
            f"<div style='display:flex;gap:12px;padding:8px 0;border-bottom:1px solid #2d3748'>"
            f"<span style='color:{color};font-weight:700;min-width:130px'>{status}</span>"
            f"<span><b>{item}</b> — {desc}</span></div>",
            unsafe_allow_html=True,
        )
