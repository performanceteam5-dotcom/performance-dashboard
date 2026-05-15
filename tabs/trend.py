import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_loader import CHANNEL_COLORS


def render(df: pd.DataFrame):
    metric_map = {
        "ROAS": ("구매매출", "비용", "roas"),
        "비용": ("비용", None, "sum"),
        "매출": ("구매매출", None, "sum"),
        "가입수": ("af_회원가입", None, "sum"),
        "구매수": ("구매", None, "sum"),
    }
    col1, col2 = st.columns([2, 1])
    with col1:
        sel_metric = st.selectbox("지표", list(metric_map.keys()), key="trend_metric")
    with col2:
        split_weekday = st.toggle("평일/주말 분리", key="trend_split")

    # 채널별 주간 ROAS 추이
    st.subheader("채널별 ROAS 주간 추이 (최근 4주)")
    week_df = df.copy()
    week_df["주차"] = week_df["일"].dt.to_period("W").apply(lambda p: p.start_time)
    week_roas = (
        week_df.groupby(["주차", "채널"])
        .apply(lambda x: x["구매매출"].sum() / x["비용"].sum() if x["비용"].sum() else None)
        .reset_index(name="ROAS")
        .dropna()
    )
    if not week_roas.empty:
        week_roas = week_roas[week_roas["주차"] >= week_roas["주차"].max() - pd.Timedelta(weeks=3)]
        color_map = {ch: CHANNEL_COLORS.get(ch, "#aaa") for ch in week_roas["채널"].unique()}
        fig_week = px.line(
            week_roas, x="주차", y="ROAS", color="채널",
            color_discrete_map=color_map, markers=True,
            title="채널별 주간 ROAS"
        )
        fig_week.add_hline(y=4.0, line_dash="dash", line_color="#2ecc71", annotation_text="양호 4.0")
        fig_week.add_hline(y=2.0, line_dash="dash", line_color="#e74c3c", annotation_text="개선필요 2.0")
        st.plotly_chart(fig_week, use_container_width=True)

    # 일별 선택 지표 추이
    st.subheader(f"일별 {sel_metric} 추이")
    daily = df.copy()
    if split_weekday:
        daily["구분"] = daily["일"].dt.dayofweek.apply(lambda d: "주말" if d >= 5 else "평일")
        group_cols = ["일", "채널", "구분"]
    else:
        group_cols = ["일", "채널"]

    y_col, denom_col, mode = metric_map[sel_metric]
    if mode == "roas":
        daily_grp = (
            daily.groupby(group_cols)
            .apply(lambda x: x[y_col].sum() / x[denom_col].sum() if x[denom_col].sum() else None)
            .reset_index(name=sel_metric)
            .dropna()
        )
    else:
        daily_grp = daily.groupby(group_cols)[y_col].sum().reset_index()
        daily_grp = daily_grp.rename(columns={y_col: sel_metric})

    color_col = "구분" if split_weekday else "채널"
    fig_daily = px.line(
        daily_grp, x="일", y=sel_metric, color=color_col,
        facet_col="채널" if split_weekday else None,
        markers=True, title=f"일별 {sel_metric}"
    )
    st.plotly_chart(fig_daily, use_container_width=True)

    # 전체 일별 비용·매출·ROAS 콤보 차트
    st.subheader("전체 일별 비용·매출·ROAS")
    total = df.groupby("일").agg(비용=("비용", "sum"), 매출=("구매매출", "sum")).reset_index()
    total["ROAS"] = total["매출"] / total["비용"]
    fig_combo = go.Figure()
    fig_combo.add_trace(go.Bar(x=total["일"], y=total["비용"], name="비용", marker_color="#3498db"))
    fig_combo.add_trace(go.Bar(x=total["일"], y=total["매출"], name="매출", marker_color="#2ecc71"))
    fig_combo.add_trace(go.Scatter(
        x=total["일"], y=total["ROAS"], name="ROAS",
        mode="lines+markers", yaxis="y2", line=dict(color="#e74c3c", width=2)
    ))
    fig_combo.update_layout(
        barmode="group",
        yaxis=dict(title="금액(₩)"),
        yaxis2=dict(overlaying="y", side="right", title="ROAS"),
    )
    st.plotly_chart(fig_combo, use_container_width=True)
