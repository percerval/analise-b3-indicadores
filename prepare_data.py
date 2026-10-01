"""Saneamento e agregação dos dados do projeto.

Este script não altera os arquivos em data/raw/. Todas as saídas são gravadas
em data/processed/ ou outputs/tables/.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
TABLES_DIR = PROJECT_DIR / "outputs" / "tables"

STOCK_NUMERIC = ["Adj Close", "Close", "High", "Low", "Open", "Volume"]
OHLC = ["Open", "High", "Low", "Close"]
MAIN_START = pd.Period("2012-03", freq="M")
MAIN_END = pd.Period("2024-12", freq="M")


def parse_dates(series: pd.Series) -> tuple[pd.Series, int]:
    """Preserva a data civil e remove o horário/timezone dos textos ISO."""
    raw = series.astype("string")
    # Os timestamps com timezone encontrados na base representam meia-noite
    # local. Usar os dez primeiros caracteres evita deslocamento de dia.
    parsed = pd.to_datetime(raw.str.slice(0, 10), errors="coerce")
    return parsed, int(parsed.isna().sum())


def numeric_conversion(df: pd.DataFrame, columns: list[str]) -> dict[str, int]:
    invalid = {}
    for column in columns:
        original = df[column].astype("string")
        converted = pd.to_numeric(original, errors="coerce")
        invalid[column] = int(((original.str.strip() != "") & converted.isna()).sum())
        df[column] = converted
    return invalid


def values_equal(left: pd.Series, right: pd.Series) -> bool:
    left = left.to_numpy(dtype=float)
    right = right.to_numpy(dtype=float)
    return bool(np.all((left == right) | (np.isnan(left) & np.isnan(right))))


def values_close(frame: pd.DataFrame) -> bool:
    reference = frame.iloc[0].to_numpy(dtype=float)
    for row in frame.iloc[1:].to_numpy(dtype=float):
        for a, b in zip(reference, row):
            if np.isnan(a) and np.isnan(b):
                continue
            if np.isnan(a) or np.isnan(b) or not np.isclose(a, b, rtol=1e-9, atol=1e-12):
                return False
    return True


def classify_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Classifica e resolve duplicatas sem escolher linha conflitante."""
    numeric = df[STOCK_NUMERIC]
    keep_indices = []
    conflict_indices = []
    conflict_rows = []
    group_counts = {"economically_identical": 0, "trivial_representation": 0, "conflicting": 0}
    excess_counts = {key: 0 for key in group_counts}

    for (date, symbol), group in df.groupby(["Date", "Symbol"], sort=False, dropna=False):
        indices = list(group.index)
        if len(indices) == 1:
            keep_indices.append(indices[0])
            continue
        numeric_group = numeric.loc[indices]
        if values_equal(numeric_group.iloc[0], numeric_group.iloc[1:].iloc[0]) if len(indices) == 2 else all(
            values_equal(numeric_group.iloc[0], row) for _, row in numeric_group.iloc[1:].iterrows()
        ):
            category = "economically_identical"
        elif values_close(numeric_group):
            category = "trivial_representation"
        else:
            category = "conflicting"

        group_counts[category] += 1
        excess_counts[category] += len(indices) - 1
        if category == "conflicting":
            conflict_indices.extend(indices)
            for index in indices:
                row = df.loc[index].copy()
                row["duplicate_group_date"] = date
                row["duplicate_group_symbol"] = symbol
                row["duplicate_group_size"] = len(indices)
                conflict_rows.append(row)
        else:
            keep_indices.append(indices[0])

    cleaned = df.loc[sorted(keep_indices)].copy()
    conflicts = pd.DataFrame(conflict_rows)
    duplicate_report = {
        "duplicate_groups": group_counts,
        "duplicate_excess_rows": excess_counts,
        "conflicting_rows_removed": len(conflict_indices),
        "rows_after_duplicate_resolution": len(cleaned),
    }
    return cleaned, conflicts, duplicate_report


def ticker_quality(raw_df: pd.DataFrame, clean_df: pd.DataFrame) -> pd.DataFrame:
    raw = raw_df.groupby("Symbol").agg(
        first_date=("Date", "min"), last_date=("Date", "max"), raw_observations=("Date", "size")
    )
    clean = clean_df.groupby("Symbol").agg(
        valid_observations=("Date", "size"),
        first_valid_date=("Date", "min"),
        last_valid_date=("Date", "max"),
        valid_months=("month", "nunique"),
    )
    quality = raw.join(clean, how="left")
    quality["valid_observations"] = quality["valid_observations"].fillna(0).astype(int)
    quality["valid_months"] = quality["valid_months"].fillna(0).astype(int)
    quality["invalid_observations"] = quality["raw_observations"] - quality["valid_observations"]
    quality["invalid_proportion"] = quality["invalid_observations"] / quality["raw_observations"]
    first_period = pd.PeriodIndex(quality["first_date"], freq="M")
    last_period = pd.PeriodIndex(quality["last_date"], freq="M")
    first_ord = pd.Series(first_period, index=quality.index).map(lambda value: value.ordinal)
    last_ord = pd.Series(last_period, index=quality.index).map(lambda value: value.ordinal)
    quality["calendar_months_span"] = last_ord - first_ord + 1
    quality["coverage_pct"] = 100 * quality["valid_months"] / quality["calendar_months_span"]
    quality["passes_quality_filter"] = (
        (quality["valid_months"] >= 24)
        & (quality["coverage_pct"] >= 70)
        & (quality["invalid_proportion"] <= 0.05)
    )
    return quality.reset_index()


def prepare_stocks() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    path = RAW_DIR / "bovespa_stocks.csv"
    original = pd.read_csv(path, dtype={"Symbol": "string"}, low_memory=False)
    original_rows = len(original)
    original["Date"], invalid_dates = parse_dates(original["Date"])
    invalid_numeric = numeric_conversion(original, STOCK_NUMERIC)
    original["Symbol"] = original["Symbol"].astype("string").str.strip()

    # Valores ajustados não positivos não são usados como preço; não são
    # substituídos por estimativas. Os tickers aprovados posteriormente têm
    # Adj Close positivo em todas as suas observações válidas.
    nonpositive_adj_close = int((original["Adj Close"] <= 0).sum())
    original.loc[original["Adj Close"] <= 0, "Adj Close"] = np.nan

    deduped, conflicts, duplicate_report = classify_duplicates(original)

    zero_block = (
        deduped[["High", "Low", "Open", "Volume"]].eq(0).all(axis=1)
    )
    zero_report = {
        "zero_block_after_duplicate_resolution": int(zero_block.sum()),
        "zero_block_with_close_positive": int((zero_block & (deduped["Close"] > 0)).sum()),
        "zero_block_with_adj_close_positive": int((zero_block & (deduped["Adj Close"] > 0)).sum()),
        "zero_block_with_close_zero_or_missing": int((zero_block & (deduped["Close"] <= 0)).sum()),
    }

    numeric_complete = deduped[STOCK_NUMERIC].notna().all(axis=1)
    positive_close = deduped["Close"] > 0
    valid_ohlc_range = (
        (deduped["High"] > 0)
        & (deduped["Low"] > 0)
        & (deduped["Low"] <= deduped["Close"])
        & (deduped["Close"] <= deduped["High"])
    )
    ohlc_inconsistent = numeric_complete & ~valid_ohlc_range
    ohlc_inconsistent_nonzero = ohlc_inconsistent & ~zero_block

    valid_mask = numeric_complete & positive_close & ~zero_block & valid_ohlc_range & (deduped["Volume"] >= 0)
    clean = deduped.loc[valid_mask].copy()
    clean = clean.sort_values(["Symbol", "Date"]).reset_index(drop=True)
    clean["month"] = clean["Date"].dt.to_period("M")
    clean["daily_return"] = clean.groupby("Symbol", sort=False)["Adj Close"].pct_change()

    # Métricas mensais: retorno de fechamento mensal contra o mês civil anterior.
    month_end = clean.groupby(["Symbol", "month"], as_index=False).agg(
        month_end_close=("Close", "last"),
        month_end_adj_close=("Adj Close", "last"),
        volume_mean=("Volume", "mean"),
        volume_total=("Volume", "sum"),
        valid_sessions=("Date", "size"),
        volatility_daily_return=("daily_return", "std"),
    )
    month_end = month_end.sort_values(["Symbol", "month"])
    month_end["previous_month_end_adj_close"] = month_end.groupby("Symbol")["month_end_adj_close"].shift(1)
    month_end["previous_month"] = month_end.groupby("Symbol")["month"].shift(1)
    month_ord = month_end["month"].map(lambda value: value.ordinal)
    previous_month_ord = month_end["previous_month"].map(
        lambda value: value.ordinal if not pd.isna(value) else np.nan
    )
    consecutive = (month_ord - previous_month_ord) == 1
    month_end["monthly_return"] = np.where(
        consecutive
        & month_end["month_end_adj_close"].gt(0)
        & month_end["previous_month_end_adj_close"].gt(0),
        month_end["month_end_adj_close"] / month_end["previous_month_end_adj_close"] - 1,
        np.nan,
    )
    month_end["month"] = month_end["month"].astype(str)

    quality = ticker_quality(original.assign(month=original["Date"].dt.to_period("M")), clean)
    selected = set(quality.loc[quality["passes_quality_filter"], "Symbol"])
    monthly = month_end[month_end["Symbol"].isin(selected)].copy()
    monthly = monthly[(monthly["month"] >= str(MAIN_START)) & (monthly["month"] <= str(MAIN_END))]
    selected_clean = clean[clean["Symbol"].isin(selected)]

    # A base diária saneada contém somente sessões utilizáveis; dados brutos,
    # inválidos e conflitos permanecem documentados no relatório.
    clean = clean.drop(columns=["daily_return", "month"])
    clean.to_csv(PROCESSED_DIR / "stocks_clean_daily.csv", index=False, date_format="%Y-%m-%d")
    monthly.to_csv(PROCESSED_DIR / "stocks_monthly.csv", index=False)
    quality.to_csv(TABLES_DIR / "ticker_quality.csv", index=False)
    if not conflicts.empty:
        conflicts.to_csv(TABLES_DIR / "duplicate_conflicts.csv", index=False)

    report = {
        "source": str(path),
        "original_rows": original_rows,
        "original_tickers": int(original["Symbol"].nunique()),
        "invalid_dates": invalid_dates,
        "invalid_numeric_values": invalid_numeric,
        "nonpositive_adj_close_set_to_nan": nonpositive_adj_close,
        **duplicate_report,
        "ohlc_inconsistent_after_deduplication": int(ohlc_inconsistent.sum()),
        "ohlc_inconsistent_nonzero_after_deduplication": int(ohlc_inconsistent_nonzero.sum()),
        "zero_report": zero_report,
        "clean_daily_rows": len(clean),
        "tickers_before_filter": int(len(quality)),
        "tickers_after_filter": int(len(selected)),
        "quality_filter": "valid_months >= 24; coverage_pct >= 70; invalid_proportion <= 5%",
        "monthly_rows_main_period": len(monthly),
        "main_period": {"start": str(MAIN_START), "end": str(MAIN_END)},
        "selected_clean_daily_rows": len(selected_clean),
        "selected_adj_close_positive_rows": int(selected_clean["Adj Close"].gt(0).sum()),
        "selected_adj_close_positive_pct": float(100 * selected_clean["Adj Close"].gt(0).mean()),
        "return_price_used": "Adj Close (todos os registros diários válidos dos 215 tickers selecionados são positivos)",
    }
    return clean, monthly, report


def prepare_economic_indicators() -> tuple[pd.DataFrame, dict]:
    path = RAW_DIR / "economic_indicators.csv"
    df = pd.read_csv(path)
    original_rows = len(df)
    df["Date"], invalid_dates = parse_dates(df["Date"])
    indicator_columns = ["Taxa Selic", "IPCA", "IGP-M", "INPC", "Desemprego PNADC"]
    invalid_numeric = numeric_conversion(df, indicator_columns)
    df["month"] = df["Date"].dt.to_period("M")

    def first_value(series: pd.Series):
        non_null = series.dropna()
        return non_null.iloc[0] if len(non_null) else np.nan

    monthly = df.groupby("month", as_index=False).agg(
        selic_media_mensal=("Taxa Selic", "mean"),
        selic_final_mes=("Taxa Selic", "last"),
        ipca=("IPCA", first_value),
        igpm=("IGP-M", first_value),
        inpc=("INPC", first_value),
        desemprego_pnadc=("Desemprego PNADC", first_value),
    )
    monthly = monthly.sort_values("month")
    monthly["selic_variacao_mensal_pontos"] = monthly["selic_final_mes"].diff()
    monthly = monthly[(monthly["month"] >= MAIN_START) & (monthly["month"] <= MAIN_END)].copy()
    monthly["month"] = monthly["month"].astype(str)
    monthly.to_csv(PROCESSED_DIR / "economic_indicators_monthly.csv", index=False)

    report = {
        "source": str(path),
        "original_rows": original_rows,
        "invalid_dates": invalid_dates,
        "invalid_numeric_values": invalid_numeric,
        "monthly_rows_main_period": len(monthly),
        "main_period": {"start": str(MAIN_START), "end": str(MAIN_END)},
        "frequency_decision": "IPCA, IGP-M, INPC e desemprego mantidos mensais; Selic agregada por média, fim e variação mensal; sem forward-fill",
    }
    return monthly, report


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    _, _, stock_report = prepare_stocks()
    _, economic_report = prepare_economic_indicators()
    report = {"stocks": stock_report, "economic_indicators": economic_report}
    (TABLES_DIR / "cleaning_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
