import streamlit as st
import pandas as pd
import plotly.express as px

MIN_IMPRESSION = 100_000  # A/B 판정 최소 노출 (CLAUDE.md §6-4)


def _ab_summary(df: pd.DataFrame) -> pd.DataFrame:
    ab_df = df[df["소재AB"].notna()].copy()
    if ab_df.empty:
        return pd.DataFrame()
    grp = ab_df.groupby(["채널", "소재카테고리", "소재AB"]).agg(
        노출=("노출", "sum"),
        클릭=("클릭", "sum"),
        비용=("비용", "sum"),
        구매매출=("구매매출", "sum"),
        구매=("구매", "sum"),
    ).reset_index()
    grp["CTR(%)"] = (grp["클릭"] / grp["노출"] * 100).round(2)
    grp["CVR(%)"] = (grp["구매"] / grp["클릭"] * 100).round(2)
    grp["ROAS"] = (grp["구매매출"] / grp["비용"]).round(2)
    grp["샘플"] = grp["노출"].apply(lambda x: "✅ 충분" if x >= MIN_IMPRESSION else "⚠️ 부족")
    return grp


def render(df: pd.DataFrame):
    col1, col2, col3 = st.columns(3)
    with col1:
        channels = ["전체"] + sorted(df["채널"].dropna().unique().tolist())
        sel_ch = st.selectbox("채널", channels, key="cr_ch")
    with col2:
        seasons = ["전체"] + sorted(df["소재시즌"].dropna().unique().tolist())
        sel_season = st.selectbox("시즌", seasons, key="cr_season")
    with col3:
        cats = ["전체"] + sorted(df["소재카테고리"].dropna().unique().tolist())
        sel_cat = st.selectbox("카테고리", cats, key="cr_cat")

    cdf = df.copy()
    if sel_ch != "전체":
        cdf = cdf[cdf["채널"] == sel_ch]
    if sel_season != "전체":
        cdf = cdf[cdf["소재시즌"] == sel_season]
    if sel_cat != "전체":
        cdf = cdf[cdf["소재카테고리"] == sel_cat]

    # 소재 타입별 성과
    st.subheader("소재 타입별 성과")
    type_grp = cdf.groupby("소재유형").agg(
        노출=("노출", "sum"), 클릭=("클릭", "sum"),
        비용=("비용", "sum"), 구매매출=("구매매출", "sum"), 구매=("구매", "sum"),
    ).reset_index()
    type_grp["CTR(%)"] = (type_grp["클릭"] / type_grp["노출"] * 100).round(2)
    type_grp["CVR(%)"] = (type_grp["구매"] / type_grp["클릭"] * 100).round(2)
    type_grp["ROAS"] = (type_grp["구매매출"] / type_grp["비용"]).round(2)

    col_l, col_r = st.columns(2)
    with col_l:
        fig_roas = px.bar(
            type_grp.sort_values("ROAS", ascending=True),
            x="ROAS", y="소재유형", orientation="h",
            color="ROAS", color_continuous_scale="Blues",
            title="소재 타입별 ROAS"
        )
        st.plotly_chart(fig_roas, use_container_width=True)
    with col_r:
        fig_ctr = px.bar(
            type_grp.sort_values("CTR(%)", ascending=True),
            x="CTR(%)", y="소재유형", orientation="h",
            color="CTR(%)", color_continuous_scale="Greens",
            title="소재 타입별 CTR"
        )
        st.plotly_chart(fig_ctr, use_container_width=True)

    # A/B 판정
    st.subheader("A/B 소재 비교")
    ab = _ab_summary(cdf)
    if ab.empty:
        st.info("선택 조건에서 A/B 소재 데이터가 없습니다.")
    else:
        st.dataframe(
            ab[["채널", "소재카테고리", "소재AB", "노출", "CTR(%)", "CVR(%)", "ROAS", "샘플"]],
            use_container_width=True, hide_index=True,
        )

    # 전체 소재 랭킹
    st.subheader("소재 전체 랭킹 (ROAS 기준)")
    rank = cdf.groupby(["채널", "캠페인", "소재유형", "소재카테고리", "소재시즌", "소재AB", "소재"]).agg(
        노출=("노출", "sum"), 클릭=("클릭", "sum"),
        비용=("비용", "sum"), 구매매출=("구매매출", "sum"), 구매=("구매", "sum"),
    ).reset_index()
    rank["CTR(%)"] = (rank["클릭"] / rank["노출"] * 100).round(2)
    rank["CVR(%)"] = (rank["구매"] / rank["클릭"] * 100).round(2)
    rank["ROAS"] = (rank["구매매출"] / rank["비용"]).round(2)
    rank["CPA"] = (rank["비용"] / rank["구매"]).round(0)
    st.dataframe(
        rank[["채널", "소재유형", "소재카테고리", "소재시즌", "소재AB", "노출", "CTR(%)", "CVR(%)", "ROAS", "CPA"]]
        .sort_values("ROAS", ascending=False),
        use_container_width=True, hide_index=True,
    )
