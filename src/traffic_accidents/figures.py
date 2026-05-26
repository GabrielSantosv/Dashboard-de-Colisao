from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


COLOR_SCALE = ["#0f766e", "#17436a", "#d18a1c", "#c44935", "#5f6b76"]
SEVERITY_COLORS = {
    "Leves": "#0f766e",
    "Graves": "#d18a1c",
    "Fatais": "#c44935",
}
BASE_FONT = "Bahnschrift, Aptos, Trebuchet MS, sans-serif"
FONT_COLOR = "#e7eef5"
GRID_COLOR = "rgba(142, 177, 204, 0.12)"
MUTED_COLOR = "#9db1c4"


def _empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, x=0.5, y=0.5, showarrow=False, font=dict(size=15, color=MUTED_COLOR))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(
        height=320,
        margin=dict(l=16, r=16, t=16, b=16),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=BASE_FONT, color=FONT_COLOR),
    )
    return fig


def _apply_layout(fig: go.Figure, *, height: int, xaxis_title: str | None = None, yaxis_title: str | None = None) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        title=None,
        height=height,
        margin=dict(l=16, r=16, t=12, b=16),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=BASE_FONT, color=FONT_COLOR),
        legend_title_text="",
        colorway=COLOR_SCALE,
    )
    fig.update_xaxes(
        title=xaxis_title,
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
        showline=False,
        automargin=True,
        tickfont=dict(color=MUTED_COLOR),
        title_font=dict(color=MUTED_COLOR),
    )
    fig.update_yaxes(
        title=yaxis_title,
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
        showline=False,
        automargin=True,
        tickfont=dict(color=MUTED_COLOR),
        title_font=dict(color=MUTED_COLOR),
    )
    return fig


def monthly_line(frame: pd.DataFrame) -> go.Figure:
    if frame.empty:
        return _empty_figure("Sem registros para o filtro selecionado")

    if "month_period" in frame.columns and pd.api.types.is_datetime64_any_dtype(frame["month_period"]):
        month_names = {
            1: "jan",
            2: "fev",
            3: "mar",
            4: "abr",
            5: "mai",
            6: "jun",
            7: "jul",
            8: "ago",
            9: "set",
            10: "out",
            11: "nov",
            12: "dez",
        }
        month_frame = frame.copy()
        month_frame["month_label"] = (
            month_frame["month_period"].dt.month.map(month_names)
            + " "
            + month_frame["month_period"].dt.year.astype(str)
        )
        fig = px.line(month_frame, x="month_period", y="accidents", markers=True)
        fig.update_traces(
            line=dict(color="#0f766e", width=3),
            marker=dict(size=7, color="#37a1c4"),
            hovertemplate="%{x|%b %Y}: %{y:,} ocorrencias",
        )
        fig.update_xaxes(
            tickvals=month_frame["month_period"].tolist(),
            ticktext=month_frame["month_label"].tolist(),
        )
    else:
        fig = px.line(frame, x="month_period", y="accidents", markers=True)
        fig.update_traces(
            line=dict(color="#0f766e", width=3),
            marker=dict(size=7, color="#37a1c4"),
            hovertemplate="%{x}: %{y:,} ocorrencias",
        )

    return _apply_layout(fig, height=320, xaxis_title="Mes", yaxis_title="Ocorrencias")


def state_bar(frame: pd.DataFrame) -> go.Figure:
    if frame.empty:
        return _empty_figure("Sem UFs para exibir")

    top = frame.head(10).copy()
    top["label"] = top["accidents"].map(lambda value: f"{int(value):,}".replace(",", "."))
    fig = px.bar(top, x="accidents", y="state", orientation="h")
    fig.update_traces(marker_color="#17436a", text=top["label"], textposition="outside", cliponaxis=False)
    fig.update_xaxes(range=[0, max(top["accidents"].max() * 1.15, 1)])
    fig.update_yaxes(autorange="reversed")
    return _apply_layout(fig, height=320, xaxis_title="Ocorrencias", yaxis_title="UF")


def city_bar(frame: pd.DataFrame) -> go.Figure:
    if frame.empty:
        return _empty_figure("Sem cidades para exibir")

    top = frame.head(10).copy()
    top["label"] = top["accidents"].map(lambda value: f"{int(value):,}".replace(",", "."))
    fig = px.bar(top, x="accidents", y="city_label", orientation="h")
    fig.update_traces(marker_color="#0f766e", text=top["label"], textposition="outside", cliponaxis=False)
    fig.update_xaxes(range=[0, max(top["accidents"].max() * 1.15, 1)])
    fig.update_yaxes(autorange="reversed")
    return _apply_layout(fig, height=320, xaxis_title="Ocorrencias", yaxis_title="Cidade")


def accident_type_bar(frame: pd.DataFrame) -> go.Figure:
    if frame.empty:
        return _empty_figure("Sem causas para exibir")

    top = frame.head(10).copy()
    top["label"] = top["accidents"].map(lambda value: f"{int(value):,}".replace(",", "."))
    fig = px.bar(top, x="accidents", y="accident_type", orientation="h")
    fig.update_traces(
        marker_color="#d18a1c",
        text=top["label"],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{x:,} ocorrencias<br>%{y}",
    )
    fig.update_xaxes(range=[0, max(top["accidents"].max() * 1.15, 1)])
    fig.update_yaxes(autorange="reversed")
    return _apply_layout(fig, height=320, xaxis_title="Ocorrencias", yaxis_title="Causa")


def period_donut(frame: pd.DataFrame) -> go.Figure:
    if frame.empty:
        return _empty_figure("Sem periodos para exibir")

    fig = px.pie(
        frame,
        names="time_period",
        values="accidents",
        hole=0.62,
        color_discrete_sequence=["#17436a", "#0f766e", "#d18a1c", "#c44935", "#8a98a6"],
    )
    fig.update_traces(textinfo="percent", textposition="inside", hovertemplate="%{label}: %{value:,} ocorrencias")
    fig.update_traces(textfont=dict(color=FONT_COLOR))
    fig.update_layout(
        height=320,
        margin=dict(l=12, r=12, t=12, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=BASE_FONT, color=FONT_COLOR),
        legend=dict(orientation="v", x=1.02, y=0.5, font=dict(color=MUTED_COLOR)),
    )
    return fig


def severity_donut(frame: pd.DataFrame) -> go.Figure:
    if frame.empty:
        return _empty_figure("Sem severidade para exibir")

    labels = frame["severity_label"].astype(str).tolist()
    values = frame["accidents"].tolist()
    colors = [SEVERITY_COLORS.get(label, "#5f6b76") for label in labels]
    total = int(sum(values))

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.68,
                marker=dict(colors=colors),
                sort=False,
                direction="clockwise",
                textinfo="percent",
                textfont=dict(color=FONT_COLOR),
                hovertemplate="%{label}: %{value:,} ocorrencias",
            )
        ]
    )
    fig.add_annotation(
        text=f"<b>{total:,}</b><br><span style='font-size:12px'>ocorrencias</span>".replace(",", "."),
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=18, color=FONT_COLOR),
    )
    fig.update_layout(
        height=320,
        margin=dict(l=12, r=12, t=12, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=BASE_FONT, color=FONT_COLOR),
        legend=dict(orientation="v", x=1.02, y=0.5, font=dict(color=MUTED_COLOR)),
    )
    return fig


def hourly_heatmap(frame: pd.DataFrame) -> go.Figure:
    if "occurred_at" not in frame.columns:
        return _empty_figure("Sem datas para montar a matriz temporal")

    day_map = {
        "Monday": "Segunda",
        "Tuesday": "Terca",
        "Wednesday": "Quarta",
        "Thursday": "Quinta",
        "Friday": "Sexta",
        "Saturday": "Sabado",
        "Sunday": "Domingo",
    }
    temp = frame.dropna(subset=["occurred_at"]).assign(
        hour=lambda current: current["occurred_at"].dt.hour,
        day=lambda current: current["occurred_at"].dt.day_name().map(day_map),
    )
    pivot = (
        temp.groupby(["day", "hour"])
        .size()
        .reset_index(name="count")
        .pivot(index="day", columns="hour", values="count")
        .fillna(0)
    )
    days = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"]
    available = [day for day in days if day in pivot.index]

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.loc[available].values if not pivot.empty else [[]],
            x=pivot.columns.tolist() if not pivot.empty else [],
            y=available,
            colorscale=[
                [0.0, "#eaf1ee"],
                [0.22, "#a8cfc2"],
                [0.48, "#5aa18f"],
                [0.74, "#d18a1c"],
                [1.0, "#c44935"],
            ],
            hovertemplate="%{y} | %{x}h: %{z} ocorrencias",
            colorbar=dict(title="Volume", thickness=10),
        )
    )
    fig.update_layout(
        height=320,
        margin=dict(l=16, r=16, t=12, b=16),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=BASE_FONT, color=FONT_COLOR),
    )
    fig.update_xaxes(title="Hora do dia", showgrid=False, zeroline=False, tickfont=dict(color=MUTED_COLOR), title_font=dict(color=MUTED_COLOR))
    fig.update_yaxes(title="Dia da semana", showgrid=False, zeroline=False, tickfont=dict(color=MUTED_COLOR), title_font=dict(color=MUTED_COLOR))
    return fig


def weekend_bars(frame: pd.DataFrame) -> go.Figure:
    if frame.empty:
        return _empty_figure("Sem registros para comparar")

    fig = px.bar(frame, x="day_type", y="accidents", text="accidents")
    fig.update_traces(marker_color="#17436a", textposition="outside")
    return _apply_layout(fig, height=300, xaxis_title="Tipo de dia", yaxis_title="Ocorrencias")


def street_ranking_bar(frame: pd.DataFrame) -> go.Figure:
    if frame.empty:
        return _empty_figure("Sem vias suficientes para o recorte atual")

    top = frame.head(10).copy()
    top["label"] = top["accidents"].map(lambda value: f"{int(value):,}".replace(",", "."))
    fig = px.bar(top, x="accidents", y="location_display", orientation="h")
    fig.update_traces(
        marker_color="#2c79a6",
        text=top["label"],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}<br>%{x:,} acidentes",
    )
    fig.update_xaxes(range=[0, max(top["accidents"].max() * 1.14, 1)])
    fig.update_yaxes(autorange="reversed")
    return _apply_layout(fig, height=360, xaxis_title="Acidentes", yaxis_title="Via / local")


def street_period_stacked_bar(frame: pd.DataFrame) -> go.Figure:
    if frame.empty:
        return _empty_figure("N\u00e3o h\u00e1 registros suficientes para gerar a an\u00e1lise de ruas e avenidas no recorte atual")

    period_order = ["Madrugada", "Manh\u00e3", "Tarde", "Noite"]
    period_colors = {
        "Madrugada": "#12314b",
        "Manh\u00e3": "#1a4d73",
        "Tarde": "#2c79a6",
        "Noite": "#5ea9d0",
    }
    ordered_locations = (
        frame.sort_values("rank_order")["location_display"].drop_duplicates().tolist()
        if "rank_order" in frame.columns
        else frame["location_display"].drop_duplicates().tolist()
    )

    fig = go.Figure()
    for period in period_order:
        period_frame = frame[frame["periodo_dia"] == period]
        fig.add_trace(
            go.Bar(
                x=period_frame["accidents"],
                y=period_frame["location_display"],
                orientation="h",
                name=period,
                marker=dict(color=period_colors[period]),
                hovertemplate="%{y}<br>%{x:,} acidentes em %{fullData.name}<extra></extra>",
            )
        )

    fig.update_layout(
        barmode="stack",
        height=360,
        margin=dict(l=16, r=16, t=12, b=16),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=BASE_FONT, color=FONT_COLOR),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(color=MUTED_COLOR)),
    )
    fig.update_xaxes(
        title="Acidentes",
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
        tickfont=dict(color=MUTED_COLOR),
        title_font=dict(color=MUTED_COLOR),
    )
    fig.update_yaxes(
        title="Rua / avenida / local",
        showgrid=False,
        zeroline=False,
        tickfont=dict(color=MUTED_COLOR),
        title_font=dict(color=MUTED_COLOR),
        automargin=True,
        categoryorder="array",
        categoryarray=ordered_locations,
        autorange="reversed",
    )
    return fig


def scatter_severity(frame: pd.DataFrame, x_col: str, y_col: str) -> go.Figure:
    if frame.empty:
        return _empty_figure("Sem registros para o filtro selecionado")

    fig = px.scatter(
        frame,
        x=x_col,
        y=y_col,
        color="severity",
        hover_data=["state", "city", "accident_type", "occurred_at"],
        color_discrete_map={"light": "#0f766e", "serious": "#d18a1c", "fatal": "#c44935"},
    )
    fig.update_traces(
        marker=dict(size=8, opacity=0.68),
        hovertemplate="%{x:,} %{xaxis.title.text}<br>%{y:,} %{yaxis.title.text}<br>%{customdata[0]} - %{customdata[1]}<br>%{customdata[2]}",
    )
    return _apply_layout(
        fig,
        height=300,
        xaxis_title=x_col.replace("_", " ").title(),
        yaxis_title=y_col.replace("_", " ").title(),
    )
