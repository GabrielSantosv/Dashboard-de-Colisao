from __future__ import annotations

import pandas as pd


SEVERITY_LABELS = {
    "light": "Leves",
    "serious": "Graves",
    "fatal": "Fatais",
}


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
    order = ["Madrugada", "Manha", "Tarde", "Noite", "Fim de noite"]
    data = (
        frame.groupby("time_period", as_index=False, observed=False)
        .agg(accidents=("time_period", "size"), fatalities=("fatalities", "sum"), injured=("injured", "sum"))
    )
    data["time_period"] = pd.Categorical(data["time_period"], categories=order, ordered=True)
    return data.sort_values("time_period")


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
