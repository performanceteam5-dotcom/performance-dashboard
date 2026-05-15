import streamlit as st
import pandas as pd
import io
from data_loader import ROAS_GOOD, ROAS_WATCH


def _build_summary(df: pd.DataFrame, group_by: str) -> pd.DataFrame:
    grp = df.groupby(group_by).agg(
        비용=("비용", "sum"),
        매출=("구매매출", "sum"),
        노출=("노출", "sum"),
        클릭=("클릭", "sum"),
        구매=("구매", "sum"),
        가입=("af_회원가입", "sum"),
    ).reset_index()
    grp["ROAS"] = (grp["매출"] / grp["비용"]).round(2)
    grp["CPA"] = (grp["비용"] / grp["구매"]).round(0)
    grp["가입_CPA"] = (grp["비용"] / grp["가입"]).round(0)
    grp["CTR(%)"] = (grp["클릭"] / grp["노출"] * 100).round(2)
    return grp.sort_values("ROAS", ascending=False)


def _auto_comment(df: pd.DataFrame, group_by: str) -> str:
    summary = _build_summary(df, group_by)
    lines = []

    best = summary.iloc[0]
    lines.append(f"✅ 최상위 {group_by}: {best[group_by]} — ROAS {best['ROAS']:.2f}")

    for _, row in summary[summary["ROAS"] < ROAS_WATCH].iterrows():
        lines.append(f"🔴 {row[group_by]} ROAS {row['ROAS']:.2f} — 개선 필요")

    for _, row in summary[(summary["ROAS"] >= ROAS_WATCH) & (summary["ROAS"] < ROAS_GOOD)].iterrows():
        lines.append(f"🟡 {row[group_by]} ROAS {row['ROAS']:.2f} — 관찰 필요")

    total_cost = df["비용"].sum()
    total_rev = df["구매매출"].sum()
    total_roas = total_rev / total_cost if total_cost else 0
    lines.append(
        f"\n📊 전체 ROAS: {total_roas:.2f} | "
        f"총 비용: ₩{total_cost/1e4:.0f}만 | "
        f"총 매출: ₩{total_rev/1e4:.0f}만"
    )
    return "\n".join(lines)


def _to_csv(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")
    return buf.getvalue()


def render(df: pd.DataFrame):
    col1, col2 = st.columns(2)
    with col1:
        group_by = st.selectbox("집계 기준", ["채널", "캠페인", "캠페인목적", "소재유형"], key="rpt_group")
    with col2:
        if "캠페인목적" in df.columns:
            purposes = ["전체"] + sorted(df["캠페인목적"].dropna().unique().tolist())
        else:
            purposes = ["전체"]
        sel_purpose = st.selectbox("캠페인 목적 필터", purposes, key="rpt_purpose")

    rdf = df.copy()
    if sel_purpose != "전체" and "캠페인목적" in rdf.columns:
        rdf = rdf[rdf["캠페인목적"] == sel_purpose]

    # 집계 테이블
    summary = _build_summary(rdf, group_by)
    st.subheader("집계 테이블")
    st.dataframe(summary, use_container_width=True, hide_index=True)

    # 자동 코멘트
    st.subheader("자동 성과 코멘트")
    comment = _auto_comment(rdf, group_by)
    st.code(comment, language=None)

    # CSV 다운로드
    st.markdown("---")
    st.download_button(
        label="📥 CSV 다운로드 (엑셀용)",
        data=_to_csv(summary),
        file_name=f"report_{group_by}.csv",
        mime="text/csv",
    )
