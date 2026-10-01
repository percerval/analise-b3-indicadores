"""Etapa 3: análise exploratória exclusivamente dos dados processados."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


ROOT = Path(__file__).resolve().parent
PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"
START = pd.Period("2012-03", freq="M")
END = pd.Period("2024-12", freq="M")

STOCK_METRICS = [
    "monthly_return",
    "volatility_daily_return",
    "volume_mean",
    "volume_total",
    "valid_sessions",
]
ECONOMIC_METRICS = [
    "selic_media_mensal",
    "selic_final_mes",
    "selic_variacao_mensal_pontos",
    "ipca",
    "igpm",
    "inpc",
    "desemprego_pnadc",
]


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    stocks = pd.read_csv(PROCESSED / "stocks_monthly.csv")
    economic = pd.read_csv(PROCESSED / "economic_indicators_monthly.csv")
    stocks["month"] = pd.PeriodIndex(stocks["month"], freq="M")
    economic["month"] = pd.PeriodIndex(economic["month"], freq="M")
    stocks = stocks[stocks["month"].between(START, END)].copy()
    economic = economic[economic["month"].between(START, END)].copy()
    return stocks, economic


def descriptive_table(df: pd.DataFrame, metrics: list[str], include_period: bool = False) -> pd.DataFrame:
    rows = []
    for metric in metrics:
        values = pd.to_numeric(df[metric], errors="coerce")
        valid = values.dropna()
        row = {
            "metric": metric,
            "count": int(valid.size),
            "missing": int(values.isna().sum()),
            "mean": valid.mean(),
            "median": valid.median(),
            "std": valid.std(),
            "min": valid.min(),
            "q25": valid.quantile(0.25),
            "q75": valid.quantile(0.75),
            "max": valid.max(),
        }
        if include_period:
            dates = df.loc[values.notna(), "month"]
            row["period_start"] = str(dates.min()) if len(dates) else None
            row["period_end"] = str(dates.max()) if len(dates) else None
        rows.append(row)
    return pd.DataFrame(rows)


def aggregate_stocks(stocks: pd.DataFrame) -> pd.DataFrame:
    grouped = stocks.groupby("month")
    result = grouped.agg(
        median_monthly_return=("monthly_return", "median"),
        mean_monthly_return=("monthly_return", "mean"),
        median_volatility=("volatility_daily_return", "median"),
        mean_volatility=("volatility_daily_return", "mean"),
        assets_with_month_data=("Symbol", "nunique"),
        valid_return_assets=("monthly_return", "count"),
        positive_return_assets=("monthly_return", lambda s: int((s.dropna() > 0).sum())),
        negative_return_assets=("monthly_return", lambda s: int((s.dropna() < 0).sum())),
    ).reset_index()
    result["positive_return_proportion"] = (
        result["positive_return_assets"] / result["valid_return_assets"]
    )
    result["negative_return_proportion"] = (
        result["negative_return_assets"] / result["valid_return_assets"]
    )
    return result


def extreme_months(aggregate: pd.DataFrame) -> pd.DataFrame:
    definitions = {
        "median_monthly_return": ["lowest", "highest"],
        "median_volatility": ["highest"],
        "negative_return_proportion": ["highest"],
    }
    rows = []
    for metric, directions in definitions.items():
        for direction in directions:
            ascending = direction == "lowest"
            ordered = aggregate.sort_values(metric, ascending=ascending).head(10)
            for rank, (_, row) in enumerate(ordered.iterrows(), start=1):
                rows.append(
                    {
                        "metric": metric,
                        "direction": direction,
                        "rank": rank,
                        "month": str(row["month"]),
                        "value": row[metric],
                        "valid_return_assets": row["valid_return_assets"],
                    }
                )
    return pd.DataFrame(rows)


def stock_return_extremes(stocks: pd.DataFrame) -> pd.DataFrame:
    values = stocks.dropna(subset=["monthly_return"]).copy()
    high = values.nlargest(20, "monthly_return").assign(extreme_type="highest_return")
    low = values.nsmallest(20, "monthly_return").assign(extreme_type="lowest_return")
    result = pd.concat([high, low], ignore_index=True)
    return result[
        ["extreme_type", "Symbol", "month", "monthly_return", "volatility_daily_return", "valid_sessions"]
    ].sort_values(["extreme_type", "monthly_return"])


def save_tables(stocks: pd.DataFrame, economic: pd.DataFrame) -> dict[str, object]:
    stock_stats = descriptive_table(stocks, STOCK_METRICS)
    economic_stats = descriptive_table(economic, ECONOMIC_METRICS, include_period=True)
    aggregate = aggregate_stocks(stocks)
    extremes = extreme_months(aggregate)
    return_extremes = stock_return_extremes(stocks)

    stock_stats.to_csv(TABLES / "stock_descriptive_statistics.csv", index=False)
    economic_stats.to_csv(TABLES / "economic_descriptive_statistics.csv", index=False)
    aggregate.to_csv(TABLES / "monthly_market_summary.csv", index=False)
    extremes.to_csv(TABLES / "extreme_months.csv", index=False)
    return_extremes.to_csv(TABLES / "stock_return_extremes.csv", index=False)

    quality = aggregate["valid_return_assets"]
    report = {
        "period": {"start": str(START), "end": str(END)},
        "stock_rows": len(stocks),
        "stock_tickers": int(stocks["Symbol"].nunique()),
        "economic_rows": len(economic),
        "economic_missing_by_column": economic[ECONOMIC_METRICS].isna().sum().to_dict(),
        "valid_assets_per_month": {
            "minimum": int(quality.min()),
            "maximum": int(quality.max()),
            "median": float(quality.median()),
        },
        "return_extreme_counts": {
            "monthly_return_abs_at_least_100pct": int(stocks["monthly_return"].abs().ge(1).sum()),
            "monthly_return_abs_at_least_500pct": int(stocks["monthly_return"].abs().ge(5).sum()),
        },
    }
    (TABLES / "exploratory_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    return report


def configure_plot() -> None:
    sns.set_theme(style="whitegrid", context="notebook")
    plt.rcParams["figure.dpi"] = 120
    plt.rcParams["savefig.dpi"] = 160


def savefig(name: str) -> None:
    plt.tight_layout()
    plt.savefig(FIGURES / name, bbox_inches="tight")
    plt.close()


def make_plots(stocks: pd.DataFrame, economic: pd.DataFrame, aggregate: pd.DataFrame) -> None:
    months = aggregate["month"].dt.to_timestamp()

    plt.figure(figsize=(11, 5))
    plt.plot(economic["month"].dt.to_timestamp(), economic["selic_media_mensal"], label="Selic média mensal")
    plt.plot(economic["month"].dt.to_timestamp(), economic["selic_final_mes"], label="Selic ao final do mês", alpha=0.75)
    plt.title("Taxa Selic mensal — março/2012 a dezembro/2024")
    plt.xlabel("Mês")
    plt.ylabel("Taxa (%)")
    plt.legend()
    savefig("selic_historica.png")

    plt.figure(figsize=(11, 5))
    for column, label in [("ipca", "IPCA"), ("igpm", "IGP-M"), ("inpc", "INPC")]:
        plt.plot(economic["month"].dt.to_timestamp(), economic[column], label=label)
    plt.axhline(0, color="black", linewidth=0.7)
    plt.title("Índices de inflação mensais")
    plt.xlabel("Mês")
    plt.ylabel("Variação mensal (%)")
    plt.legend()
    savefig("inflacao_historica.png")

    plt.figure(figsize=(11, 5))
    plt.plot(economic["month"].dt.to_timestamp(), economic["desemprego_pnadc"], color="darkorange")
    plt.title("Desemprego PNADC mensal")
    plt.xlabel("Mês")
    plt.ylabel("Taxa (%)")
    savefig("desemprego_historico.png")

    plt.figure(figsize=(11, 5))
    plt.plot(months, aggregate["median_monthly_return"] * 100, label="Mediana", linewidth=2)
    plt.plot(months, aggregate["mean_monthly_return"] * 100, label="Média", alpha=0.65)
    plt.axhline(0, color="black", linewidth=0.7)
    plt.title("Retorno mensal da amostra agregada de ações da B3")
    plt.xlabel("Mês")
    plt.ylabel("Retorno (%)")
    plt.legend()
    savefig("retorno_mediano_b3.png")

    plt.figure(figsize=(11, 5))
    plt.plot(months, aggregate["median_volatility"] * 100, label="Mediana", linewidth=2)
    plt.plot(months, aggregate["mean_volatility"] * 100, label="Média", alpha=0.65)
    plt.title("Volatilidade diária mensal da amostra agregada")
    plt.xlabel("Mês")
    plt.ylabel("Desvio-padrão dos retornos diários (%)")
    plt.legend()
    savefig("volatilidade_mediana_b3.png")

    returns = stocks["monthly_return"].dropna()
    plt.figure(figsize=(10, 5))
    sns.histplot(returns * 100, bins=100, kde=False)
    plt.title("Distribuição completa dos retornos mensais")
    plt.xlabel("Retorno mensal (%)")
    plt.ylabel("Quantidade de observações")
    savefig("distribuicao_retornos_completa.png")

    low, high = returns.quantile([0.01, 0.99])
    visible = returns[(returns >= low) & (returns <= high)]
    plt.figure(figsize=(10, 5))
    sns.histplot(visible * 100, bins=60, kde=False)
    plt.title("Distribuição dos retornos mensais — faixa entre os percentis 1 e 99")
    plt.xlabel("Retorno mensal (%)")
    plt.ylabel("Quantidade de observações")
    savefig("distribuicao_retornos.png")

    plt.figure(figsize=(11, 5))
    plt.stackplot(
        months,
        aggregate["positive_return_proportion"],
        aggregate["negative_return_proportion"],
        labels=["Retorno positivo", "Retorno negativo"],
        colors=["seagreen", "indianred"],
        alpha=0.85,
    )
    plt.ylim(0, 1)
    plt.title("Proporção mensal de retornos positivos e negativos")
    plt.xlabel("Mês")
    plt.ylabel("Proporção dos ativos com retorno válido")
    plt.legend(loc="upper right")
    savefig("proporcao_retornos_positivos_negativos.png")

    plt.figure(figsize=(11, 5))
    plt.plot(months, aggregate["valid_return_assets"], label="Ativos com retorno válido")
    plt.plot(months, aggregate["assets_with_month_data"], label="Ativos com dados no mês", alpha=0.7)
    plt.title("Quantidade de ativos disponíveis por mês")
    plt.xlabel("Mês")
    plt.ylabel("Quantidade de ativos")
    plt.legend()
    savefig("ativos_validos_por_mes.png")


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    configure_plot()
    stocks, economic = load_data()
    report = save_tables(stocks, economic)
    aggregate = pd.read_csv(TABLES / "monthly_market_summary.csv")
    aggregate["month"] = pd.PeriodIndex(aggregate["month"], freq="M")
    make_plots(stocks, economic, aggregate)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
