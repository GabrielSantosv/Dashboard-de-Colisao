from __future__ import annotations

import pandas as pd


SEVERITY_LABELS = {
    "light": "Leves",
    "serious": "Graves",
    "fatal": "Fatais",
}
PERIOD_ORDER = ["Madrugada", "Manh\u00e3", "Tarde", "Noite"]
INSUFFICIENT_STREET_DATA_MESSAGE = "N\u00e3o h\u00e1 registros suficientes para gerar a an\u00e1lise de ruas e avenidas no recorte atual."


def _preferred_location_label(series: pd.Series) -> str:
    if series.empty:
        return ""
    counts = series.astype(str).value_counts()
    return str(counts.index[0]) if not counts.empty else ""


def _format_number(value: float | int) -> str:
    return f"{int(value):,}".replace(",", ".")


def _format_percent(value: float) -> str:
    formatted = f"{value * 100:.1f}".replace(".", ",")
    return formatted[:-2] if formatted.endswith(",0") else formatted


def build_kpis(frame: pd.DataFrame) -> dict[str, float]:
    total = len(frame)
    fatalities = int(frame["fatalities"].fillna(0).sum())
    injured = int(frame["injured"].fillna(0).sum())
    severe = int(frame["severity"].isin(["serious", "fatal"]).sum())
    fatal_rate = (fatalities / total * 1000) if total else 0.0
    return {
        "total_accidents": total,
        "fatalities": fatalities,
        "injured": injured,
        "severe_share": severe / total if total else 0.0,
        "fatal_rate_per_thousand": fatal_rate,
        "states_in_scope": int(frame["state"].nunique()) if "state" in frame.columns else 0,
        "source_files": int(frame["source_file"].nunique()) if "source_file" in frame.columns else 0,
    }


def monthly_trend(frame: pd.DataFrame) -> pd.DataFrame:
    data = (
        frame.dropna(subset=["occurred_at"])
        .assign(month_period=lambda current: current["occurred_at"].dt.to_period("M").dt.to_timestamp())
        .groupby("month_period", as_index=False)
        .agg(accidents=("occurred_at", "size"), fatalities=("fatalities", "sum"), injured=("injured", "sum"))
    )
    return data.sort_values("month_period")


def by_state(frame: pd.DataFrame) -> pd.DataFrame:
    return (
        frame.groupby("state", as_index=False)
        .agg(accidents=("state", "size"), fatalities=("fatalities", "sum"), injured=("injured", "sum"))
        .sort_values("accidents", ascending=False)
    )


def by_city(frame: pd.DataFrame) -> pd.DataFrame:
    cleaned = frame.copy()
    cleaned["city"] = cleaned["city"].fillna("").astype(str).str.strip()
    cleaned["state"] = cleaned["state"].fillna("").astype(str).str.strip()
    cleaned = cleaned[cleaned["city"].ne("") & cleaned["city"].ne("Nan")]

    data = (
        cleaned.groupby(["city", "state"], as_index=False)
        .agg(accidents=("city", "size"), fatalities=("fatalities", "sum"), injured=("injured", "sum"))
        .sort_values("accidents", ascending=False)
    )
    data["city_label"] = data["city"] + " / " + data["state"]
    return data


def by_accident_type(frame: pd.DataFrame) -> pd.DataFrame:
    return (
        frame.groupby("accident_type", as_index=False)
        .agg(accidents=("accident_type", "size"), fatalities=("fatalities", "sum"), injured=("injured", "sum"))
        .sort_values("accidents", ascending=False)
    )


def by_period(frame: pd.DataFrame) -> pd.DataFrame:
    data = (
        frame.groupby("periodo_dia", as_index=False, observed=False)
        .agg(accidents=("periodo_dia", "size"), fatalities=("fatalities", "sum"), injured=("injured", "sum"))
    )
    data["periodo_dia"] = pd.Categorical(data["periodo_dia"], categories=PERIOD_ORDER, ordered=True)
    data["time_period"] = data["periodo_dia"]
    return data.sort_values("periodo_dia")


def by_severity(frame: pd.DataFrame) -> pd.DataFrame:
    order = ["Leves", "Graves", "Fatais"]
    data = (
        frame.assign(severity_label=lambda current: current["severity"].map(SEVERITY_LABELS).fillna("Nao classificado"))
        .groupby("severity_label", as_index=False)
        .agg(accidents=("severity_label", "size"), fatalities=("fatalities", "sum"), injured=("injured", "sum"))
    )
    data["severity_label"] = pd.Categorical(data["severity_label"], categories=order, ordered=True)
    return data.sort_values("severity_label")


def weekend_comparison(frame: pd.DataFrame) -> pd.DataFrame:
    return (
        frame.assign(day_type=lambda current: current["is_weekend"].map({True: "Fim de semana", False: "Dias uteis"}))
        .groupby("day_type", as_index=False)
        .agg(accidents=("day_type", "size"), fatalities=("fatalities", "sum"), injured=("injured", "sum"))
    )


def street_ranking(frame: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["location_reference", "location_display", "city", "state", "accidents", "rank_order"])

    grouped = (
        frame.groupby(["location_reference", "city", "state"], as_index=False)
        .agg(
            location_display=("location_display", _preferred_location_label),
            accidents=("location_reference", "size"),
        )
        .sort_values("accidents", ascending=False)
        .head(limit)
    )
    grouped["rank_order"] = range(len(grouped))
    return grouped


def street_period_distribution(frame: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    ranking = street_ranking(frame, limit=limit)
    if ranking.empty:
        return pd.DataFrame(
            columns=["location_reference", "location_display", "city", "state", "rank_order", "periodo_dia", "accidents"]
        )

    selected = frame.merge(
        ranking[["location_reference", "city", "state", "location_display", "rank_order"]],
        on=["location_reference", "city", "state"],
        how="inner",
        suffixes=("", "_rank"),
    )
    selected["location_display"] = selected["location_display_rank"].fillna(selected["location_display"])
    counts = (
        selected.groupby(
            ["location_reference", "location_display", "city", "state", "rank_order", "periodo_dia"],
            observed=False,
        )
        .size()
        .reset_index(name="accidents")
    )

    base = ranking[["location_reference", "location_display", "city", "state", "rank_order"]].merge(
        pd.DataFrame({"periodo_dia": PERIOD_ORDER}),
        how="cross",
    )
    distribution = base.merge(
        counts,
        on=["location_reference", "location_display", "city", "state", "rank_order", "periodo_dia"],
        how="left",
    )
    distribution["accidents"] = distribution["accidents"].fillna(0).astype(int)
    distribution["periodo_dia"] = pd.Categorical(distribution["periodo_dia"], categories=PERIOD_ORDER, ordered=True)
    distribution = distribution.sort_values(["rank_order", "periodo_dia"])
    return distribution


def street_period_summary(frame: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    distribution = street_period_distribution(frame, limit=limit)
    if distribution.empty:
        return pd.DataFrame(
            columns=[
                "location_reference",
                "location_display",
                "city",
                "state",
                "accidents",
                "rank_order",
                "dominant_period",
                "dominant_count",
                "dominant_share",
            ]
        )

    ranking = street_ranking(frame, limit=limit).rename(columns={"accidents": "total_accidents"})
    period_priority = {period: index for index, period in enumerate(PERIOD_ORDER)}
    dominant = (
        distribution.assign(period_priority=lambda current: current["periodo_dia"].map(period_priority))
        .sort_values(
            ["location_reference", "city", "state", "accidents", "period_priority"],
            ascending=[True, True, True, False, True],
        )
        .drop_duplicates(["location_reference", "city", "state"])
        .rename(columns={"periodo_dia": "dominant_period", "accidents": "dominant_count"})
    )
    summary = ranking.merge(
        dominant[["location_reference", "city", "state", "dominant_period", "dominant_count"]],
        on=["location_reference", "city", "state"],
        how="left",
    )
    summary["dominant_share"] = (summary["dominant_count"] / summary["total_accidents"]).fillna(0.0)
    summary = summary.rename(columns={"total_accidents": "accidents"})
    return summary


def street_period_insight(frame: pd.DataFrame, limit: int = 10) -> str:
    summary = street_period_summary(frame, limit=limit)
    if summary.empty:
        return INSUFFICIENT_STREET_DATA_MESSAGE

    top = summary.iloc[0]
    return (
        f"A maior concentra\u00e7\u00e3o ocorre em {top['location_display']}, com {_format_number(top['accidents'])} acidentes. "
        f"O per\u00edodo predominante \u00e9 {top['dominant_period']}, representando {_format_percent(top['dominant_share'])}% "
        f"das ocorr\u00eancias desse local."
    )
