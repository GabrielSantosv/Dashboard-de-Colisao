from __future__ import annotations

from pathlib import Path

import pandas as pd
from dash import Dash, Input, Output, State, dash_table, dcc, html

from .analysis import (
    build_kpis,
    by_accident_type,
    by_city,
    by_period,
    by_severity,
    by_state,
    monthly_trend,
    street_period_distribution,
    street_period_insight,
    street_period_summary,
    street_ranking,
    weekend_comparison,
)
from .data import generate_demo_data, load_raw_accidents
from .figures import (
    accident_type_bar,
    city_bar,
    hourly_heatmap,
    monthly_line,
    period_donut,
    severity_donut,
    state_bar,
    street_period_stacked_bar,
    street_ranking_bar,
    weekend_bars,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

try:
    data = load_raw_accidents()
except Exception as exc:
    print("Warning: load_raw_accidents failed, falling back to demo data:", exc)
    data = generate_demo_data(rows=20000)

app = Dash(__name__, title="Central Analítica de Acidentes", assets_folder=str(PROJECT_ROOT / "assets"))

DISPLAY_COLUMNS = [
    "occurred_at",
    "state",
    "city",
    "br",
    "km",
    "accident_type",
    "classificacao_acidente",
    "fatalities",
    "injured",
    "vehicles",
    "severity",
    "source_file",
]

COLUMN_LABELS = {
    "occurred_at": "Data e hora",
    "state": "UF",
    "city": "Cidade",
    "br": "BR",
    "km": "Km",
    "accident_type": "Causa",
    "classificacao_acidente": "Classificação",
    "fatalities": "Mortos",
    "injured": "Feridos",
    "vehicles": "Veículos",
    "severity": "Gravidade",
    "source_file": "Arquivo",
}

SEVERITY_OPTIONS = [
    {"label": "Leves", "value": "light"},
    {"label": "Graves", "value": "serious"},
    {"label": "Fatais", "value": "fatal"},
]


def _graph_panel(title: str, component_id: str, subtitle: str, class_name: str = "panel") -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.H3(title, className="panel-title"),
                    html.P(subtitle, className="panel-subtitle"),
                ],
                className="panel-header",
            ),
            dcc.Graph(id=component_id, config={"displayModeBar": False}),
        ],
        className=class_name,
    )


def _toolbar_dropdown(label: str, component_id: str, options: list[dict[str, str]]) -> html.Div:
    return html.Div(
        [
            html.Label(label, className="toolbar-label"),
            dcc.Dropdown(
                id=component_id,
                options=options,
                value=None,
                placeholder="Todas",
                clearable=True,
                multi=False,
                className="toolbar-dropdown",
            ),
        ],
        className="toolbar-field",
    )


def _format_number(value: float | int) -> str:
    return f"{int(value):,}".replace(",", ".")


def _format_percent(value: float) -> str:
    return f"{value:.0f}%"


def _format_share_label(value: float) -> str:
    formatted = f"{value * 100:.1f}".replace(".", ",")
    return f"{formatted[:-2] if formatted.endswith(',0') else formatted}%"


def _format_date_label(value) -> str:
    if value is None or pd.isna(value):
        return "--"
    return pd.Timestamp(value).strftime("%d/%m/%Y")


def _metric_card(title: str, value: str, detail: str, tone: str = "default") -> html.Div:
    return html.Div(
        [
            html.Div(title, className="metric-card-label"),
            html.Div(value, className="metric-card-value"),
            html.Div(detail, className="metric-card-detail"),
        ],
        className=f"metric-card metric-card--{tone}",
    )


def _metric_cards(frame: pd.DataFrame) -> list[html.Div]:
    kpis = build_kpis(frame)
    return [
        _metric_card("Registros filtrados", _format_number(kpis["total_accidents"]), "Ocorrências ativas no recorte", "primary"),
        _metric_card("Mortos", _format_number(kpis["fatalities"]), "Óbitos consolidados", "danger"),
        _metric_card("Feridos", _format_number(kpis["injured"]), "Pessoas lesionadas", "warning"),
        _metric_card("Estados / UFs no filtro", _format_number(kpis["states_in_scope"]), "Cobertura territorial ativa", "neutral"),
        _metric_card("Percentual de casos graves", _format_percent(kpis["severe_share"] * 100), "Graves + fatais", "accent"),
        _metric_card("Arquivos integrados", _format_number(kpis["source_files"]), "Bases consolidadas", "neutral"),
    ]


def _filter_data(
    *,
    severity: str | None = None,
    state: str | None = None,
    city: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    km_start: float | None = None,
    km_end: float | None = None,
) -> pd.DataFrame:
    filtered = data.copy()
    if severity:
        filtered = filtered[filtered["severity"] == severity]
    if state:
        filtered = filtered[filtered["state"] == state]
    if city:
        filtered = filtered[filtered["city"] == city]
    if start_date:
        filtered = filtered[filtered["occurred_at"] >= pd.to_datetime(start_date)]
    if end_date:
        end_timestamp = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        filtered = filtered[filtered["occurred_at"] <= end_timestamp]
    if km_start is not None or km_end is not None:
        km_min_value = float(km_start) if km_start is not None else None
        km_max_value = float(km_end) if km_end is not None else None
        if km_min_value is not None and km_max_value is not None and km_min_value > km_max_value:
            km_min_value, km_max_value = km_max_value, km_min_value
        if km_min_value is not None:
            filtered = filtered[filtered["km"] >= km_min_value]
        if km_max_value is not None:
            filtered = filtered[filtered["km"] <= km_max_value]
    return filtered


def _search_table(frame: pd.DataFrame, search_value: str | None) -> pd.DataFrame:
    if not search_value:
        return frame

    search = str(search_value).strip()
    if not search:
        return frame

    searchable_columns = [column for column in DISPLAY_COLUMNS if column in frame.columns]
    mask = pd.Series(False, index=frame.index)
    for column in searchable_columns:
        mask = mask | frame[column].astype(str).str.contains(search, case=False, na=False)
    return frame[mask]


def _format_table_frame(frame: pd.DataFrame) -> pd.DataFrame:
    table_frame = frame.copy()
    if "occurred_at" in table_frame.columns:
        table_frame["occurred_at"] = pd.to_datetime(table_frame["occurred_at"], errors="coerce").dt.strftime("%d/%m/%Y %H:%M")
    if "km" in table_frame.columns:
        table_frame["km"] = pd.to_numeric(table_frame["km"], errors="coerce").map(
            lambda value: "" if pd.isna(value) else f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
    for numeric_column in ("fatalities", "injured", "vehicles", "br"):
        if numeric_column in table_frame.columns:
            table_frame[numeric_column] = (
                pd.to_numeric(table_frame[numeric_column], errors="coerce")
                .fillna(0)
                .astype(int)
                .map(lambda value: f"{value:,}".replace(",", "."))
            )
    return table_frame


data_min = data["occurred_at"].min() if "occurred_at" in data.columns and not data.empty else None
data_max = data["occurred_at"].max() if "occurred_at" in data.columns and not data.empty else None
km_values = pd.to_numeric(data.get("km", pd.Series(dtype=float)), errors="coerce").dropna()
km_min = float(km_values.min()) if not km_values.empty else None
km_max = float(km_values.max()) if not km_values.empty else None
data_window = f"{_format_date_label(data_min)} → {_format_date_label(data_max)}"
base_source_count = int(data["source_file"].nunique()) if "source_file" in data.columns else 0
base_state_count = int(data["state"].nunique()) if "state" in data.columns else 0
state_options = [{"label": state, "value": state} for state in sorted(data["state"].dropna().unique())]
city_options = [{"label": city, "value": city} for city in sorted(data.get("city", pd.Series(dtype=str)).dropna().unique())]


app.layout = html.Div(
    [
        html.Header(
            [
                html.Div(
                    [
                        html.Img(
                            src=app.get_asset_url("logo-detran.png"),
                            className="masthead-logo",
                            alt="Logo DETRAN",
                        ),
                        html.Div(
                            [
                                html.Div("Central Analítica de Acidentes", className="masthead-title"),
                                html.Div("DETRAN | Dados consolidados de ocorrências de trânsito", className="masthead-subtitle"),
                                html.P(
                                    "Painel operacional para análise de gravidade, localização e evolução temporal dos acidentes.",
                                    className="masthead-copy",
                                ),
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.Div("Período da base", className="masthead-meta-label"),
                                                html.Div(data_window, className="masthead-meta-value"),
                                            ],
                                            className="masthead-meta",
                                        ),
                                        html.Div(
                                            [
                                                html.Div("Arquivos integrados", className="masthead-meta-label"),
                                                html.Div(_format_number(base_source_count), className="masthead-meta-value"),
                                            ],
                                            className="masthead-meta",
                                        ),
                                        html.Div(
                                            [
                                                html.Div("UFs monitoradas", className="masthead-meta-label"),
                                                html.Div(_format_number(base_state_count), className="masthead-meta-value"),
                                            ],
                                            className="masthead-meta",
                                        ),
                                    ],
                                    className="masthead-meta-row",
                                ),
                            ],
                            className="masthead-title-block",
                        ),
                    ],
                    className="masthead-brand",
                ),
                html.Div(
                    [
                        _toolbar_dropdown("Gravidade", "filter-severity", SEVERITY_OPTIONS),
                        _toolbar_dropdown("Estado", "filter-state", state_options),
                        _toolbar_dropdown("Cidade", "filter-city", city_options),
                    ],
                    className="toolbar toolbar--header",
                ),
            ],
            className="masthead",
        ),
        dcc.Tabs(
            id="tabs",
            value="overview",
            className="tabs",
            children=[
                dcc.Tab(
                    label="Visão Geral",
                    value="overview",
                    className="tab",
                    selected_className="tab--selected",
                    children=[
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.H2("Visão Geral", className="section-title"),
                                        html.P("Panorama executivo das ocorrências de trânsito.", className="section-copy"),
                                    ],
                                    className="section-header",
                                ),
                                html.Div(id="overview-metrics", className="metric-grid"),
                                html.Div(
                                    [
                                        _graph_panel(
                                            "Evolução mensal",
                                            "overview-monthly",
                                            "Série histórica das ocorrências consolidadas.",
                                            class_name="panel panel--span-2",
                                        ),
                                        _graph_panel(
                                            "Comparação por causa",
                                            "overview-causes",
                                            "Top causas com maior recorrência no recorte.",
                                        ),
                                        _graph_panel(
                                            "Distribuição por dia e período",
                                            "overview-heatmap",
                                            "Matriz de intensidade temporal das ocorrências.",
                                            class_name="panel panel--span-2",
                                        ),
                                        _graph_panel(
                                            "Severidade das ocorrências",
                                            "overview-severity",
                                            "Distribuição por nível de gravidade.",
                                        ),
                                        _graph_panel(
                                            "Estados com mais ocorrências",
                                            "overview-states",
                                            "Ranking técnico por unidade federativa.",
                                        ),
                                        _graph_panel(
                                            "Top cidades",
                                            "overview-cities",
                                            "Municípios com maior concentração de registros.",
                                        ),
                                        _graph_panel(
                                            "Distribuição por período",
                                            "overview-period",
                                            "Concentração dos casos ao longo do dia.",
                                        ),
                                    ],
                                    className="overview-analytics-grid",
                                ),
                            ],
                            className="page page--overview",
                        )
                    ],
                ),
                dcc.Tab(
                    label="Exploração",
                    value="explore",
                    className="tab",
                    selected_className="tab--selected",
                    children=[
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.H2("Exploração de Registros", className="section-title"),
                                        html.P(
                                            "Consulta detalhada com recorte temporal e exportação dos registros filtrados.",
                                            className="section-copy",
                                        ),
                                    ],
                                    className="section-header",
                                ),
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.Label("Data", className="toolbar-label"),
                                                dcc.DatePickerRange(
                                                    id="explore-period",
                                                    start_date=data_min.date() if data_min is not None else None,
                                                    end_date=data_max.date() if data_max is not None else None,
                                                    display_format="DD/MM/YYYY",
                                                    clearable=True,
                                                    minimum_nights=0,
                                                ),
                                            ],
                                            className="toolbar-field toolbar-field--period",
                                        ),
                                        _toolbar_dropdown("UF", "explore-state", state_options),
                                        _toolbar_dropdown("Município", "explore-city", city_options),
                                        _toolbar_dropdown("Severidade", "explore-severity", SEVERITY_OPTIONS),
                                        html.Div(
                                            [
                                                html.Label("Quilometragem (km)", className="toolbar-label"),
                                                html.Div(
                                                    [
                                                        dcc.Input(
                                                            id="explore-km-start",
                                                            type="number",
                                                            placeholder=f"De {km_min:.1f}".replace(".", ",") if km_min is not None else "Km inicial",
                                                            debounce=True,
                                                            className="range-input",
                                                        ),
                                                        dcc.Input(
                                                            id="explore-km-end",
                                                            type="number",
                                                            placeholder=f"Até {km_max:.1f}".replace(".", ",") if km_max is not None else "Km final",
                                                            debounce=True,
                                                            className="range-input",
                                                        ),
                                                    ],
                                                    className="range-inputs",
                                                ),
                                            ],
                                            className="toolbar-field toolbar-field--km",
                                        ),
                                        html.Div(
                                            [
                                                html.Label("Ação", className="toolbar-label"),
                                                html.Button("Exportar CSV", id="btn-download", className="primary-button"),
                                                dcc.Download(id="download-data"),
                                            ],
                                            className="toolbar-field toolbar-field--action",
                                        ),
                                    ],
                                    className="toolbar toolbar--explore",
                                ),
                                html.Div(id="explore-metrics", className="metric-grid metric-grid--compact"),
                                html.Div(
                                    [
                                        _graph_panel(
                                            "Evolução do recorte",
                                            "explore-monthly",
                                            "Série temporal aplicada à consulta atual.",
                                            class_name="panel panel--span-2",
                                        ),
                                        _graph_panel(
                                            "Comparação por causa",
                                            "explore-causes",
                                            "Causas com maior presença dentro do recorte filtrado.",
                                        ),
                                        _graph_panel(
                                            "Dias úteis x fim de semana",
                                            "explore-weekend",
                                            "Comportamento do volume entre tipos de dia.",
                                        ),
                                    ],
                                    className="explore-analytics-grid",
                                ),
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.H2(
                                                    "Ruas e avenidas com maior concentração de acidentes",
                                                    className="section-title",
                                                ),
                                                html.P(
                                                    "Concentração por via/local e comportamento ao longo dos períodos do dia.",
                                                    className="section-copy",
                                                ),
                                            ],
                                            className="section-header",
                                        ),
                                        html.Div(id="street-insight", className="insight-banner"),
                                        html.Div(
                                            [
                                                _graph_panel(
                                                    "Ranking de ruas e avenidas",
                                                    "explore-street-ranking",
                                                    "Top 10 vias ou referências com maior número de acidentes.",
                                                    class_name="panel",
                                                ),
                                                _graph_panel(
                                                    "Distribuição por período do dia",
                                                    "explore-street-period",
                                                    "Barras empilhadas por período do dia para as vias do ranking.",
                                                    class_name="panel",
                                                ),
                                            ],
                                            className="street-analytics-grid",
                                        ),
                                        html.Div(
                                            [
                                                html.Div(
                                                    [
                                                        html.H3("Tabela complementar", className="panel-title"),
                                                        html.P(
                                                            "Período dominante e participação relativa para cada via do ranking.",
                                                            className="panel-subtitle",
                                                        ),
                                                    ],
                                                    className="panel-header panel-header--table",
                                                ),
                                                dash_table.DataTable(
                                                    id="table-street-summary",
                                                    columns=[],
                                                    data=[],
                                                    page_action="none",
                                                    sort_action="native",
                                                    style_table={"overflowX": "auto"},
                                                    style_cell={
                                                        "textAlign": "left",
                                                        "padding": "10px 12px",
                                                        "fontSize": "13px",
                                                        "whiteSpace": "normal",
                                                        "backgroundColor": "#0f1b28",
                                                        "color": "#e4edf4",
                                                        "border": "0",
                                                        "fontFamily": "Bahnschrift, Aptos, Trebuchet MS, sans-serif",
                                                    },
                                                    style_header={
                                                        "fontWeight": "700",
                                                        "backgroundColor": "#132738",
                                                        "color": "#f4f8fb",
                                                        "borderBottom": "1px solid #28445a",
                                                        "fontFamily": "Cascadia Code, IBM Plex Mono, Consolas, monospace",
                                                        "textTransform": "uppercase",
                                                        "fontSize": "11px",
                                                        "letterSpacing": "0.08em",
                                                    },
                                                    style_data_conditional=[
                                                        {"if": {"row_index": "odd"}, "backgroundColor": "#132233"},
                                                        {"if": {"state": "active"}, "backgroundColor": "#17354b", "border": "1px solid #2f6f96"},
                                                        {"if": {"state": "selected"}, "backgroundColor": "#17415c", "border": "1px solid #39a7c9"},
                                                    ],
                                                ),
                                            ],
                                            className="panel panel--table",
                                        ),
                                    ],
                                    className="street-section",
                                ),
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.H3("Registros filtrados", className="panel-title"),
                                                html.P(
                                                    "Busca textual, paginação e ordenação sobre os dados selecionados.",
                                                    className="panel-subtitle",
                                                ),
                                            ],
                                            className="panel-header panel-header--table",
                                        ),
                                        dcc.Input(
                                            id="table-search",
                                            type="text",
                                            placeholder="Buscar por cidade, causa, BR, arquivo ou classificação...",
                                            className="table-search",
                                        ),
                                        dash_table.DataTable(
                                            id="table-explore",
                                            columns=[],
                                            data=[],
                                            page_size=15,
                                            page_current=0,
                                            page_action="custom",
                                            sort_action="custom",
                                            sort_mode="single",
                                            sort_by=[],
                                            style_table={"overflowX": "auto"},
                                            style_cell={
                                                "textAlign": "left",
                                                "padding": "10px 12px",
                                                "fontSize": "13px",
                                                "whiteSpace": "normal",
                                                "backgroundColor": "#0f1b28",
                                                "color": "#e4edf4",
                                                "border": "0",
                                                "fontFamily": "Bahnschrift, Aptos, Trebuchet MS, sans-serif",
                                            },
                                            style_header={
                                                "fontWeight": "700",
                                                "backgroundColor": "#132738",
                                                "color": "#f4f8fb",
                                                "borderBottom": "1px solid #28445a",
                                                "fontFamily": "Cascadia Code, IBM Plex Mono, Consolas, monospace",
                                                "textTransform": "uppercase",
                                                "fontSize": "11px",
                                                "letterSpacing": "0.08em",
                                            },
                                            style_data_conditional=[
                                                {"if": {"row_index": "odd"}, "backgroundColor": "#132233"},
                                                {"if": {"state": "active"}, "backgroundColor": "#17354b", "border": "1px solid #2f6f96"},
                                                {"if": {"state": "selected"}, "backgroundColor": "#17415c", "border": "1px solid #39a7c9"},
                                            ],
                                        ),
                                    ],
                                    className="panel panel--table",
                                ),
                            ],
                            className="page",
                        )
                    ],
                ),
            ],
        ),
    ],
    className="app-shell",
)


@app.callback(
    Output("filter-city", "options"),
    Output("filter-city", "value"),
    Input("filter-state", "value"),
    State("filter-city", "value"),
)
def update_city_options(state, current_city):
    if state:
        city_frame = data[data["state"] == state]
    else:
        city_frame = data

    options = [
        {"label": city, "value": city}
        for city in sorted(city_frame.get("city", pd.Series(dtype=str)).dropna().unique())
    ]
    valid_values = {option["value"] for option in options}
    return options, current_city if current_city in valid_values else None


@app.callback(
    Output("explore-city", "options"),
    Output("explore-city", "value"),
    Input("explore-state", "value"),
    State("explore-city", "value"),
)
def update_explore_city_options(state, current_city):
    if state:
        city_frame = data[data["state"] == state]
    else:
        city_frame = data

    options = [
        {"label": city, "value": city}
        for city in sorted(city_frame.get("city", pd.Series(dtype=str)).dropna().unique())
    ]
    valid_values = {option["value"] for option in options}
    return options, current_city if current_city in valid_values else None


@app.callback(
    Output("overview-metrics", "children"),
    Output("overview-monthly", "figure"),
    Output("overview-causes", "figure"),
    Output("overview-heatmap", "figure"),
    Output("overview-severity", "figure"),
    Output("overview-states", "figure"),
    Output("overview-cities", "figure"),
    Output("overview-period", "figure"),
    Input("filter-severity", "value"),
    Input("filter-state", "value"),
    Input("filter-city", "value"),
)
def update_overview(severity, state, city):
    filtered = _filter_data(severity=severity, state=state, city=city)
    return (
        _metric_cards(filtered),
        monthly_line(monthly_trend(filtered)),
        accident_type_bar(by_accident_type(filtered)),
        hourly_heatmap(filtered),
        severity_donut(by_severity(filtered)),
        state_bar(by_state(filtered)),
        city_bar(by_city(filtered)),
        period_donut(by_period(filtered)),
    )


@app.callback(
    Output("explore-metrics", "children"),
    Output("explore-monthly", "figure"),
    Output("explore-causes", "figure"),
    Output("explore-weekend", "figure"),
    Output("explore-street-ranking", "figure"),
    Output("explore-street-period", "figure"),
    Output("street-insight", "children"),
    Output("table-street-summary", "data"),
    Output("table-street-summary", "columns"),
    Output("table-explore", "data"),
    Output("table-explore", "columns"),
    Output("table-explore", "page_count"),
    Input("explore-severity", "value"),
    Input("explore-state", "value"),
    Input("explore-city", "value"),
    Input("explore-period", "start_date"),
    Input("explore-period", "end_date"),
    Input("explore-km-start", "value"),
    Input("explore-km-end", "value"),
    Input("table-search", "value"),
    Input("table-explore", "page_current"),
    Input("table-explore", "page_size"),
    Input("table-explore", "sort_by"),
)
def update_exploration(severity, state, city, start_date, end_date, km_start, km_end, search_value, page_current, page_size, sort_by):
    filtered = _filter_data(
        severity=severity,
        state=state,
        city=city,
        start_date=start_date,
        end_date=end_date,
        km_start=km_start,
        km_end=km_end,
    )

    table_source = _search_table(filtered, search_value)
    if sort_by:
        column_id = sort_by[0]["column_id"]
        ascending = sort_by[0]["direction"] == "asc"
        if column_id in table_source.columns:
            table_source = table_source.sort_values(column_id, ascending=ascending)

    available = [column for column in DISPLAY_COLUMNS if column in table_source.columns]
    table_frame = _format_table_frame(table_source[available].copy())
    page_current = page_current or 0
    page_size = page_size or 15
    start = page_current * page_size
    end = start + page_size
    page_frame = table_frame.iloc[start:end]
    street_summary = street_period_summary(filtered)
    if street_summary.empty:
        street_summary_records = []
        street_summary_columns = [
            {"name": "Rua/Avenida/Local", "id": "location_display"},
            {"name": "Município", "id": "city"},
            {"name": "UF", "id": "state"},
            {"name": "Total de acidentes", "id": "accidents"},
            {"name": "Período dominante", "id": "dominant_period"},
            {"name": "Acidentes no período dominante", "id": "dominant_count"},
            {"name": "Percentual do período dominante", "id": "dominant_share"},
        ]
    else:
        street_table = street_summary[
            ["location_display", "city", "state", "accidents", "dominant_period", "dominant_count", "dominant_share"]
        ].copy()
        street_table["accidents"] = street_table["accidents"].map(_format_number)
        street_table["dominant_count"] = street_table["dominant_count"].fillna(0).astype(int).map(_format_number)
        street_table["dominant_share"] = street_table["dominant_share"].fillna(0).map(_format_share_label)
        street_summary_records = street_table.to_dict("records")
        street_summary_columns = [
            {"name": "Rua/Avenida/Local", "id": "location_display"},
            {"name": "Município", "id": "city"},
            {"name": "UF", "id": "state"},
            {"name": "Total de acidentes", "id": "accidents"},
            {"name": "Período dominante", "id": "dominant_period"},
            {"name": "Acidentes no período dominante", "id": "dominant_count"},
            {"name": "Percentual do período dominante", "id": "dominant_share"},
        ]

    return (
        _metric_cards(filtered),
        monthly_line(monthly_trend(filtered)),
        accident_type_bar(by_accident_type(filtered)),
        weekend_bars(weekend_comparison(filtered)),
        street_ranking_bar(street_ranking(filtered)),
        street_period_stacked_bar(street_period_distribution(filtered)),
        street_period_insight(filtered),
        street_summary_records,
        street_summary_columns,
        page_frame.to_dict("records"),
        [{"name": COLUMN_LABELS.get(column, column.replace("_", " ").title()), "id": column} for column in available],
        max(1, (len(table_frame) + page_size - 1) // page_size),
    )


@app.callback(
    Output("download-data", "data"),
    Input("btn-download", "n_clicks"),
    State("explore-severity", "value"),
    State("explore-state", "value"),
    State("explore-city", "value"),
    State("explore-period", "start_date"),
    State("explore-period", "end_date"),
    State("explore-km-start", "value"),
    State("explore-km-end", "value"),
    prevent_initial_call=True,
)
def download_filtered(_, severity, state, city, start_date, end_date, km_start, km_end):
    filtered = _filter_data(
        severity=severity,
        state=state,
        city=city,
        start_date=start_date,
        end_date=end_date,
        km_start=km_start,
        km_end=km_end,
    )
    available = [column for column in DISPLAY_COLUMNS if column in filtered.columns]
    export = _format_table_frame(filtered[available].copy())
    return dcc.send_data_frame(export.to_csv, "acidentes_filtrados.csv", index=False)
