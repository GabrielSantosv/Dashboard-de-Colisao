from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


RAW_DIR = Path("data/raw")
REFERENCE_DIR = Path("data/reference")
PERIOD_LABELS = ["Madrugada", "Manh\u00e3", "Tarde", "Noite"]
LOCATION_PRIORITY = ["logradouro", "rua", "avenida", "local", "endereco", "trecho", "km", "br"]
EMPTY_LOCATION_LABEL = "Local n\u00e3o informado"


def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [re.sub(r"[^a-z0-9]+", "_", str(column).strip().lower()).strip("_") for column in frame.columns]
    return frame


def _coerce_datetime_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    for column in ["data_inversa", "crash_date", "date", "data", "datetime", "timestamp", "dh_ocorrencia"]:
        if column in frame.columns:
            frame["occurred_at"] = pd.to_datetime(frame[column], errors="coerce")
            break
    if "occurred_at" in frame.columns and "horario" in frame.columns:
        time_delta = pd.to_timedelta(frame["horario"].astype(str), errors="coerce")
        frame["occurred_at"] = frame["occurred_at"].dt.normalize() + time_delta.fillna(pd.Timedelta(0))
    if "occurred_at" not in frame.columns and {"year", "month", "day"}.issubset(frame.columns):
        frame["occurred_at"] = pd.to_datetime(
            dict(year=frame["year"], month=frame["month"], day=frame["day"]),
            errors="coerce",
        )
    return frame


def _coerce_number(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    normalized = series.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    normalized = normalized.str.replace(r"^\s*(nan|none|na|)\s*$", "", flags=re.IGNORECASE, regex=True)
    return pd.to_numeric(normalized, errors="coerce")


def _collapse_spaces(series: pd.Series) -> pd.Series:
    return series.astype(str).str.replace(r"\s+", " ", regex=True).str.strip()


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _clean_text_series(series: pd.Series) -> pd.Series:
    cleaned = _collapse_spaces(series.fillna("").astype(str))
    return cleaned.replace({"Nan": "", "None": "", "Na": "", "N/A": ""})


def _format_location_display(series: pd.Series) -> pd.Series:
    display = _clean_text_series(series)
    display = display.str.replace(r"\s*-\s*", "-", regex=True)
    display = display.str.replace(r"\s*,\s*", ", ", regex=True)
    display = display.str.replace(r"\s*/\s*", " / ", regex=True)
    display = display.str.replace(r"\bav[.]?\b", "Avenida", flags=re.IGNORECASE, regex=True)
    display = display.str.replace(r"\br[.]?\b", "Rua", flags=re.IGNORECASE, regex=True)
    display = display.str.replace(r"\brod[.]?\b", "Rodovia", flags=re.IGNORECASE, regex=True)
    display = display.str.replace(r"\bbr[\s-]*(\d+)\b", r"BR-\1", flags=re.IGNORECASE, regex=True)
    display = display.str.replace(r"\bkm[\s-]*(\d+(?:[.,]\d+)?)\b", r"Km \1", flags=re.IGNORECASE, regex=True)
    display = display.str.title()
    display = display.str.replace(r"\bBr-(\d+)\b", r"BR-\1", regex=True)
    display = display.str.replace(r"\bBr\b", "BR", regex=True)
    display = display.str.replace(r"\bKm\b", "Km", regex=True)
    return _collapse_spaces(display)


def _canonicalize_location(series: pd.Series) -> pd.Series:
    canonical = _clean_text_series(series).map(_strip_accents)
    canonical = canonical.str.lower()
    canonical = canonical.str.replace(r"\bav[.]?\b", "avenida", flags=re.IGNORECASE, regex=True)
    canonical = canonical.str.replace(r"\br[.]?\b", "rua", flags=re.IGNORECASE, regex=True)
    canonical = canonical.str.replace(r"\brod[.]?\b", "rodovia", flags=re.IGNORECASE, regex=True)
    canonical = canonical.str.replace(r"\bbr[\s-]*(\d+)\b", r"br \1", flags=re.IGNORECASE, regex=True)
    canonical = canonical.str.replace(r"\bkm[\s-]*(\d+(?:[.,]\d+)?)\b", r"km \1", flags=re.IGNORECASE, regex=True)
    canonical = canonical.str.replace(r"[^a-z0-9]+", " ", regex=True)
    return _collapse_spaces(canonical)


def _build_periodo_dia(hour_series: pd.Series) -> pd.Categorical:
    return pd.cut(
        hour_series,
        bins=[-1, 5, 11, 17, 23],
        labels=PERIOD_LABELS,
        include_lowest=True,
    )


def _find_location_column(columns: Iterable[str]) -> str | None:
    available = list(columns)

    for candidate in LOCATION_PRIORITY:
        if candidate in available:
            return candidate

    for candidate in LOCATION_PRIORITY:
        for column in available:
            if candidate in column:
                return column
    return None


def _compose_br_km_reference(frame: pd.DataFrame) -> pd.Series:
    br_series = pd.to_numeric(frame.get("br", pd.Series(dtype=float)), errors="coerce")
    km_series = pd.to_numeric(frame.get("km", pd.Series(dtype=float)), errors="coerce")
    br_text = br_series.map(lambda value: "" if pd.isna(value) else f"BR-{int(value)}")
    km_text = km_series.map(
        lambda value: ""
        if pd.isna(value)
        else "Km " + f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    composed = _collapse_spaces(br_text + " " + km_text)
    return composed


def _build_location_reference(frame: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    location_column = _find_location_column(frame.columns)
    city = _clean_text_series(frame.get("city", pd.Series(dtype=str))).str.title()
    state = _clean_text_series(frame.get("state", pd.Series(dtype=str))).str.upper()

    if location_column and location_column not in {"km", "br"}:
        location_display = _format_location_display(frame[location_column])
    else:
        location_display = _compose_br_km_reference(frame)

    location_display = _clean_text_series(location_display)
    location_display = location_display.mask(location_display.eq(""), EMPTY_LOCATION_LABEL)

    location_reference = _canonicalize_location(location_display)
    location_reference = location_reference.mask(location_reference.eq(""), _strip_accents(EMPTY_LOCATION_LABEL).lower())

    display = location_display.copy()
    has_city = city.ne("")
    has_state = state.ne("")
    display = display.mask(has_city & has_state, display + " | " + city + " / " + state)
    display = display.mask(has_city & ~has_state, display + " | " + city)
    display = display.mask(~has_city & has_state, display + " / " + state)
    display = display.mask(display.eq(""), EMPTY_LOCATION_LABEL)
    return location_reference, display


def _prepare_accidents(frame: pd.DataFrame) -> pd.DataFrame:
    frame = _normalize_columns(frame)
    frame = _coerce_datetime_columns(frame)

    if "feridos" not in frame.columns:
        injury_columns = [column for column in ["feridos_leves", "feridos_graves"] if column in frame.columns]
        if injury_columns:
            frame["feridos"] = sum(_coerce_number(frame[column]).fillna(0) for column in injury_columns)

    rename_map = {
        "borough": "state",
        "borough_name": "state",
        "uf": "state",
        "estado": "state",
        "regional": "region",
        "municipio": "city",
        "cidade": "city",
        "severity": "severity",
        "gravidade": "severity",
        "number_of_persons_killed": "fatalities",
        "fatalities": "fatalities",
        "killed": "fatalities",
        "mortos": "fatalities",
        "mortos_posteriores": "fatalities",
        "number_of_persons_injured": "injured",
        "feridos": "injured",
        "feridos_leves": "injured",
        "feridos_graves": "injured",
        "injured": "injured",
        "vehicles": "vehicles",
        "number_of_vehicles_involved": "vehicles",
        "veiculos": "vehicles",
        "contributing_factor_vehicle_1": "accident_type",
        "contributing_factor_vehicle_2": "accident_type",
        "tipo_acidente": "accident_type",
        "causa_acidente": "accident_type",
        "accident_type": "accident_type",
        "collision_id": "incident_id",
        "id": "incident_id",
    }
    frame = frame.rename(columns=rename_map)

    if frame.columns.duplicated().any():
        for column in pd.Index(frame.columns[frame.columns.duplicated()]).unique():
            duplicate_block = frame.loc[:, frame.columns == column]
            frame = frame.loc[:, ~frame.columns.duplicated()]
            frame[column] = duplicate_block.bfill(axis=1).iloc[:, 0]

    if "severity" not in frame.columns:
        fatal = frame.get("fatalities", pd.Series(dtype=float)).fillna(0)
        injured = frame.get("injured", pd.Series(dtype=float)).fillna(0)
        frame["severity"] = np.select(
            [fatal > 0, injured > 0],
            ["fatal", "serious"],
            default="light",
        )

    frame["state"] = frame.get("state", pd.Series(dtype=str)).astype(str).str.upper().str.strip()
    frame.loc[frame["state"].str.lower().isin(["nan", "none", "", "unknown"]), "state"] = "Unknown"
    frame["city"] = frame.get("city", pd.Series(dtype=str)).astype(str).str.title().str.strip()
    frame["accident_type"] = frame.get("accident_type", pd.Series(dtype=str)).astype(str).str.title().str.strip()
    frame.loc[frame["accident_type"].str.lower().isin(["nan", "none", "", "unknown", "na"]), "accident_type"] = "Não informado"
    frame["year"] = pd.to_datetime(frame["occurred_at"], errors="coerce").dt.year
    frame["month"] = pd.to_datetime(frame["occurred_at"], errors="coerce").dt.month
    frame["day_name"] = pd.to_datetime(frame["occurred_at"], errors="coerce").dt.day_name()

    if "hour" not in frame.columns:
        frame["hour"] = np.where(frame["occurred_at"].notna(), frame["occurred_at"].dt.hour, np.nan)

    frame["periodo_dia"] = _build_periodo_dia(frame["hour"])
    frame["time_period"] = frame["periodo_dia"]
    frame["is_weekend"] = pd.to_datetime(frame["occurred_at"], errors="coerce").dt.dayofweek >= 5

    for column in ["fatalities", "injured", "vehicles", "km", "br", "latitude", "longitude", "pessoas"]:
        if column not in frame.columns:
            frame[column] = np.nan
        frame[column] = _coerce_number(frame[column])

    if "region" in frame.columns:
        frame["region"] = frame["region"].astype(str).str.title().str.strip()

    if "incident_id" not in frame.columns:
        frame["incident_id"] = np.arange(1, len(frame) + 1)

    frame["location_reference"], frame["location_display"] = _build_location_reference(frame)

    return frame


def _load_csv_files(paths: Iterable[Path]) -> list[pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    paths = list(paths)
    has_occurrence_2026 = any("ocorrencias" in path.name.lower() and "2026" in path.name for path in paths)
    for path in paths:
        if has_occurrence_2026 and path.name.lower().startswith("acidentes2026"):
            continue
        frame = None
        read_attempts = [
            {"sep": ",", "encoding": "utf-8"},
            {"sep": ";", "encoding": "utf-8"},
            {"sep": ";", "encoding": "latin-1"},
        ]
        for options in read_attempts:
            try:
                candidate = pd.read_csv(path, **options)
            except Exception:
                continue
            if candidate.shape[1] > 1:
                frame = candidate
                break
            if frame is None:
                frame = candidate
        if frame is None:
            continue
        if not frame.empty:
            frame["source_file"] = path.name
            frames.append(frame)
    return frames


def _load_borough_reference(reference_dir: Path = REFERENCE_DIR) -> pd.DataFrame:
    reference_path = reference_dir / "borough_groups.csv"
    if not reference_path.exists():
        return pd.DataFrame(columns=["state", "borough_group"])
    reference = pd.read_csv(reference_path)
    reference.columns = [str(column).strip().lower() for column in reference.columns]
    reference["state"] = reference["state"].astype(str).str.title().str.strip()
    reference["borough_group"] = reference["borough_group"].astype(str).str.strip()
    return reference


def load_raw_accidents(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    csv_files = sorted(raw_dir.glob("*.csv"))
    frames = _load_csv_files(csv_files)
    if not frames:
        cleaned = generate_demo_data()
    else:
        accidents = pd.concat(frames, ignore_index=True)
        cleaned = _prepare_accidents(accidents)

    reference = _load_borough_reference()
    if not reference.empty:
        cleaned = cleaned.merge(reference, on="state", how="left")
    else:
        cleaned["borough_group"] = "Desconhecida"

    cleaned["borough_group"] = cleaned["borough_group"].fillna("Desconhecida")
    return cleaned


def generate_demo_data(rows: int = 20000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    boroughs = np.array(["Manhattan", "Bronx", "Brooklyn", "Queens", "Staten Island"])
    factors = np.array([
        "Driver Inattention/Distraction",
        "Failure to Yield Right-of-Way",
        "Following Too Closely",
        "Backing Unsafely",
        "Unsafe Speed",
        "Alcohol Involvement",
        "Passing or Lane Usage Improper",
    ])
    vehicle_types = np.array(["Sedan", "Station Wagon/Sport Utility Vehicle", "Taxi", "Bus", "Box Truck", "Pick-up Truck"])
    severities = np.array(["light", "serious", "fatal"])
    dates = pd.date_range("2023-01-01", "2025-05-01", freq="h")

    occurred_at = rng.choice(dates, size=rows, replace=True)
    frame = pd.DataFrame(
        {
            "collision_id": np.arange(1, rows + 1),
            "crash_date": occurred_at,
            "borough": rng.choice(boroughs, size=rows, p=[0.23, 0.12, 0.31, 0.22, 0.12]),
            "contributing_factor_vehicle_1": rng.choice(factors, size=rows, p=[0.24, 0.18, 0.14, 0.11, 0.15, 0.08, 0.10]),
            "vehicle_type_code_1": rng.choice(vehicle_types, size=rows),
            "severity": rng.choice(severities, size=rows, p=[0.72, 0.22, 0.06]),
            "number_of_persons_killed": rng.poisson(0.03, size=rows),
            "number_of_persons_injured": rng.poisson(1.6, size=rows),
            "number_of_vehicles_involved": rng.integers(1, 6, size=rows),
        }
    )
    frame["number_of_persons_killed"] = np.where(
        frame["severity"] == "fatal",
        np.maximum(frame["number_of_persons_killed"], 1),
        frame["number_of_persons_killed"],
    )
    frame["source_file"] = "demo"
    return _prepare_accidents(frame)
