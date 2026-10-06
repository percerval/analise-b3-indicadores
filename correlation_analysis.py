"""Etapa 4: análise correlacional mensal, agregada e por ticker.

A unidade da análise agregada é um mês. Indicadores macroeconômicos não são
replicados para cada ticker nessa análise, evitando tratar ticker-mês como
observações macroeconômicas independentes.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import pearsonr, spearmanr


PROJECT_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
TABLES_DIR = PROJECT_DIR / "outputs" / "tables"
FIGURES_DIR = PROJECT_DIR / "outputs" / "figures"

MAIN_START = pd.Period("2012-03", freq="M")
MAIN_END = pd.Period("2022-12", freq="M")
EXPECTED_MONTHS = pd.period_range(MAIN_START, MAIN_END, freq="M")
EXPECTED_MIN_ASSETS = 186
EXPECTED_MAX_ASSETS = 213
MIN_TICKER_OBSERVATIONS = 24

MACRO_COLUMNS = [
    "selic_media_mensal",
    "selic_final_mes",
    "selic_variacao_mensal_pontos",
    "ipca",
    "igpm",
    "inpc",
    "desemprego_pnadc",
]

AGGREGATE_METRICS = [
    "mean_monthly_return",
    "median_monthly_return",
    "mean_volatility",
    "median_volatility",
    "positive_return_proportion",
    "negative_return_proportion",
]

TICKER_METRICS = ["monthly_return", "volatility_daily_return"]

INDICATOR_NOTES = {
    "selic_media_mensal": "média dos níveis registrados diariamente no mês na coluna Taxa Selic, não juros acumulados no mês; unidade não comprovada; valores compatíveis com taxa em % a.a., possivelmente meta Selic, sem identificação da série",
    "selic_final_mes": "último valor não nulo do mês na ordem dos registros da coluna Taxa Selic; arquivo auditado em ordem cronológica; unidade não comprovada, compatível com % a.a.",
    "selic_variacao_mensal_pontos": "diferença mensal na unidade original da série Selic, calculada entre valores finais de meses consecutivos no arquivo auditado; pontos percentuais somente se a unidade percentual da entrada for confirmada",
    "ipca": "primeiro valor não nulo do mês na coluna IPCA, único no arquivo auditado; unidade não comprovada, compatível com variação percentual mensal",
    "igpm": "primeiro valor não nulo do mês na coluna IGP-M, único no arquivo auditado; unidade não comprovada, compatível com variação percentual mensal",
    "inpc": "primeiro valor não nulo do mês na coluna INPC, único no arquivo auditado; unidade não comprovada, compatível com variação percentual mensal",
    "desemprego_pnadc": "primeiro valor não nulo do mês na coluna Desemprego PNADC, único no arquivo auditado; unidade e referência não comprovadas, compatíveis com taxa percentual de desocupação de trimestre móvel",
}

ANALYSIS_NOTES = {
    "provenance": "origem externa exata dos dois CSVs brutos não comprovada; referências oficiais são conceituais e não identificam o fornecedor dos arquivos",
    "p_values": "p-values convencionais/nominais, não ajustados; sem ajuste para múltiplos testes ou tratamento inferencial específico para autocorrelação",
    "observations": "n_observations conta pares mensais válidos, não observações necessariamente independentes; Spearman não elimina dependência temporal",
    "scope": "associações descritivas, contemporâneas e bivariadas, sem controles ou defasagens; mês armazenado não comprova divulgação ou disponibilidade pública",
    "ticker_eligibility": "limiar operacional de 24 pares válidos por combinação; resumo por ticker exige o limiar em todas as combinações; não garante independência ou precisão",
}

INDICATOR_LABELS = {
    "selic_media_mensal": "Selic: média dos níveis diários",
    "selic_final_mes": "Selic: último valor do mês",
    "selic_variacao_mensal_pontos": "Selic: diferença mensal",
    "ipca": "IPCA",
    "igpm": "IGP-M",
    "inpc": "INPC",
    "desemprego_pnadc": "Desemprego PNADC",
}


def load_processed_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Carrega somente as bases processadas do período principal."""
    stocks = pd.read_csv(PROCESSED_DIR / "stocks_monthly.csv")
    economic = pd.read_csv(PROCESSED_DIR / "economic_indicators_monthly.csv")

    stocks["month"] = pd.PeriodIndex(stocks["month"], freq="M")
    economic["month"] = pd.PeriodIndex(economic["month"], freq="M")

    stocks = stocks[stocks["month"].between(MAIN_START, MAIN_END)].copy()
    economic = economic[economic["month"].between(MAIN_START, MAIN_END)].copy()
    return stocks, economic


def validate_inputs(stocks: pd.DataFrame, economic: pd.DataFrame) -> None:
    """Valida período, unicidade, cobertura e valores macroeconômicos."""
    if stocks.duplicated(subset=["Symbol", "month"]).any():
        raise ValueError("A base de ações contém pares Symbol + month duplicados.")
    if economic["month"].duplicated().any():
        raise ValueError("A base macroeconômica contém meses duplicados.")

    stock_months = pd.Index(stocks["month"].unique()).sort_values()
    economic_months = pd.Index(economic["month"].unique()).sort_values()
    expected = pd.Index(EXPECTED_MONTHS)
    if not stock_months.equals(expected):
        raise ValueError("A base de ações não contém exatamente os 130 meses esperados.")
    if not economic_months.equals(expected):
        raise ValueError("A base macroeconômica não contém exatamente os 130 meses esperados.")

    missing_macro = economic[MACRO_COLUMNS].isna().sum()
    if missing_macro.any():
        raise ValueError(f"Há valores macroeconômicos ausentes: {missing_macro[missing_macro > 0].to_dict()}")

    assets_per_month = stocks.groupby("month")["Symbol"].nunique()
    if assets_per_month.min() < EXPECTED_MIN_ASSETS or assets_per_month.max() > EXPECTED_MAX_ASSETS:
        raise ValueError(
            "A cobertura mensal saiu do intervalo auditado "
            f"({EXPECTED_MIN_ASSETS}, {EXPECTED_MAX_ASSETS})."
        )


def aggregate_stocks(stocks: pd.DataFrame) -> pd.DataFrame:
    """Produz exatamente uma observação agregada por mês."""
    grouped = stocks.groupby("month", sort=True)
    aggregate = grouped.agg(
        mean_monthly_return=("monthly_return", "mean"),
        median_monthly_return=("monthly_return", "median"),
        mean_volatility=("volatility_daily_return", "mean"),
        median_volatility=("volatility_daily_return", "median"),
        positive_return_assets=("monthly_return", lambda values: int((values.dropna() > 0).sum())),
        negative_return_assets=("monthly_return", lambda values: int((values.dropna() < 0).sum())),
        assets_with_month_data=("Symbol", "nunique"),
        valid_return_assets=("monthly_return", "count"),
        valid_volatility_assets=("volatility_daily_return", "count"),
    ).reset_index()
    aggregate["positive_return_proportion"] = (
        aggregate["positive_return_assets"] / aggregate["valid_return_assets"]
    )
    aggregate["negative_return_proportion"] = (
        aggregate["negative_return_assets"] / aggregate["valid_return_assets"]
    )
    return aggregate


def join_monthly_data(stocks: pd.DataFrame, economic: pd.DataFrame) -> pd.DataFrame:
    aggregate = aggregate_stocks(stocks)
    joined = aggregate.merge(economic, on="month", how="inner", validate="one_to_one")
    joined = joined.sort_values("month").reset_index(drop=True)
    if len(joined) != len(EXPECTED_MONTHS):
        raise ValueError("O join mensal não produziu as 130 observações esperadas.")
    return joined


def correlation_pair(x: pd.Series, y: pd.Series, method: str) -> tuple[float, float, int]:
    """Retorna coeficiente, p-value nominal não ajustado e pares válidos."""
    pair = pd.concat([x, y], axis=1).dropna()
    n = len(pair)
    if n < 3 or pair.iloc[:, 0].nunique() < 2 or pair.iloc[:, 1].nunique() < 2:
        return np.nan, np.nan, n
    if method == "pearson":
        result = pearsonr(pair.iloc[:, 0], pair.iloc[:, 1])
    elif method == "spearman":
        result = spearmanr(pair.iloc[:, 0], pair.iloc[:, 1])
    else:
        raise ValueError(f"Método desconhecido: {method}")
    return float(result.statistic), float(result.pvalue), n


def aggregate_correlations(monthly: pd.DataFrame, method: str) -> pd.DataFrame:
    rows = []
    for macro in MACRO_COLUMNS:
        for metric in AGGREGATE_METRICS:
            coefficient, p_value, n = correlation_pair(monthly[macro], monthly[metric], method)
            rows.append(
                {
                    "method": method,
                    "macro_indicator": macro,
                    "stock_metric": metric,
                    "coefficient": coefficient,
                    "p_value": p_value,
                    "n_observations": n,
                }
            )
    return pd.DataFrame(rows)


def ticker_correlations(stocks: pd.DataFrame, economic: pd.DataFrame) -> pd.DataFrame:
    """Calcula correlações separadas, sem empilhar ticker-mês."""
    rows = []
    macro = economic.set_index("month")[MACRO_COLUMNS]
    for symbol, ticker_data in stocks.groupby("Symbol", sort=True):
        ticker = ticker_data.set_index("month")[TICKER_METRICS].join(macro, how="inner")
        for stock_metric in TICKER_METRICS:
            for macro_indicator in MACRO_COLUMNS:
                x = ticker[macro_indicator]
                y = ticker[stock_metric]
                for method in ("pearson", "spearman"):
                    coefficient, p_value, n = correlation_pair(x, y, method)
                    rows.append(
                        {
                            "Symbol": symbol,
                            "stock_metric": stock_metric,
                            "macro_indicator": macro_indicator,
                            "method": method,
                            "coefficient": coefficient,
                            "p_value": p_value,
                            "n_observations": n,
                            "eligible_primary_analysis": n >= MIN_TICKER_OBSERVATIONS,
                        }
                    )
    return pd.DataFrame(rows)


def ticker_summary(results: pd.DataFrame, stocks: pd.DataFrame) -> pd.DataFrame:
    coverage = (
        results.groupby("Symbol")
        .agg(
            min_observations=("n_observations", "min"),
            max_observations=("n_observations", "max"),
            eligible_primary_analysis=("eligible_primary_analysis", "all"),
        )
        .reset_index()
    )
    monthly_coverage = (
        stocks.groupby("Symbol")
        .agg(
            months_with_data=("month", "nunique"),
            valid_return_months=("monthly_return", "count"),
            valid_volatility_months=("volatility_daily_return", "count"),
        )
        .reset_index()
    )
    coverage = monthly_coverage.merge(coverage, on="Symbol", validate="one_to_one")
    return coverage


def save_tables(monthly: pd.DataFrame, stocks: pd.DataFrame, economic: pd.DataFrame) -> dict[str, object]:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    pearson = aggregate_correlations(monthly, "pearson")
    spearman = aggregate_correlations(monthly, "spearman")
    by_ticker = ticker_correlations(stocks, economic)
    summary = ticker_summary(by_ticker, stocks)

    monthly_out = monthly.copy()
    monthly_out["month"] = monthly_out["month"].astype(str)
    monthly_out.to_csv(TABLES_DIR / "correlation_monthly_aggregate.csv", index=False)
    pearson.to_csv(TABLES_DIR / "correlation_pearson.csv", index=False)
    spearman.to_csv(TABLES_DIR / "correlation_spearman.csv", index=False)
    by_ticker.to_csv(TABLES_DIR / "correlation_by_ticker.csv", index=False)
    summary.to_csv(TABLES_DIR / "correlation_ticker_summary.csv", index=False)
    (TABLES_DIR / "correlation_indicator_metadata.json").write_text(
        json.dumps(INDICATOR_NOTES, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    report = {
        "period": {"start": str(MAIN_START), "end": str(MAIN_END)},
        "months": len(monthly),
        "tickers": int(stocks["Symbol"].nunique()),
        "monthly_asset_coverage": {
            "minimum": int(monthly["assets_with_month_data"].min()),
            "median": float(monthly["assets_with_month_data"].median()),
            "maximum": int(monthly["assets_with_month_data"].max()),
        },
        "correlation_observations": {
            "aggregate_pearson": int(pearson["n_observations"].min()),
            "aggregate_spearman": int(spearman["n_observations"].min()),
        },
        "ticker_observation_limit": MIN_TICKER_OBSERVATIONS,
        "ticker_eligible_count": int(summary["eligible_primary_analysis"].sum()),
        "ticker_total_count": int(len(summary)),
        "indicator_notes": INDICATOR_NOTES,
        "analysis_notes": ANALYSIS_NOTES,
        "outputs": [
            "correlation_monthly_aggregate.csv",
            "correlation_pearson.csv",
            "correlation_spearman.csv",
            "correlation_by_ticker.csv",
            "correlation_ticker_summary.csv",
            "correlation_indicator_metadata.json",
        ],
    }
    (TABLES_DIR / "correlation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def save_heatmap(results: pd.DataFrame, filename: str, title: str) -> None:
    matrix = results.pivot(index="macro_indicator", columns="stock_metric", values="coefficient")
    plt.figure(figsize=(12, 6))
    sns.heatmap(matrix, annot=True, fmt=".2f", cmap="PuOr", center=0, vmin=-1, vmax=1)
    plt.title(title)
    plt.xlabel("Métrica agregada das ações")
    plt.ylabel("Indicador macroeconômico")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / filename, dpi=180, bbox_inches="tight")
    plt.close()


def save_selected_scatterplots(monthly: pd.DataFrame, pearson: pd.DataFrame, spearman: pd.DataFrame) -> None:
    combined = pearson.copy()
    combined["abs_coefficient"] = combined["coefficient"].abs()
    selected = combined.sort_values("abs_coefficient", ascending=False).drop_duplicates(
        subset=["macro_indicator", "stock_metric"]
    ).head(4)

    figure, axes = plt.subplots(2, 2, figsize=(13, 9))
    for axis, (_, relation) in zip(axes.flat, selected.iterrows()):
        axis.scatter(monthly[relation["macro_indicator"]], monthly[relation["stock_metric"]], alpha=0.75, color="#0072B2")
        rank_coefficient = spearman.loc[
            spearman["macro_indicator"].eq(relation["macro_indicator"])
            & spearman["stock_metric"].eq(relation["stock_metric"]),
            "coefficient",
        ].iloc[0]
        axis.set_title(
            f"{relation['macro_indicator']} × {relation['stock_metric']}\n"
            f"Pearson={relation['coefficient']:.2f}; Spearman={rank_coefficient:.2f}"
        )
        axis.set_xlabel(f"{INDICATOR_LABELS[relation['macro_indicator']]}\nUnidade original não comprovada")
        axis.set_ylabel(relation["stock_metric"])
    for axis in axes.flat[len(selected) :]:
        axis.set_visible(False)
    figure.suptitle("Quatro maiores |Pearson| — seleção exploratória, mar/2012–dez/2022", y=1.02)
    figure.tight_layout()
    figure.savefig(FIGURES_DIR / "correlation_selected_scatterplots.png", dpi=180, bbox_inches="tight")
    plt.close(figure)


def save_ticker_distributions(by_ticker: pd.DataFrame) -> None:
    """Separa indicador e métrica; cada caixa reúne tickers da mesma relação."""
    eligible = by_ticker[by_ticker["eligible_primary_analysis"]].copy()
    if eligible.empty:
        return
    figure, axes = plt.subplots(len(MACRO_COLUMNS), len(TICKER_METRICS), figsize=(15, 23), sharey=True)
    for row, macro in enumerate(MACRO_COLUMNS):
        for column, metric in enumerate(TICKER_METRICS):
            axis = axes[row, column]
            subset = eligible[
                eligible["macro_indicator"].eq(macro) & eligible["stock_metric"].eq(metric)
            ]
            if not subset.empty:
                sns.boxplot(
                    data=subset,
                    x="method",
                    y="coefficient",
                    order=["pearson", "spearman"],
                    color="#90B4C8",
                    ax=axis,
                )
            axis.axhline(0, color="#444444", linewidth=0.8)
            axis.set_ylim(-1, 1)
            metric_label = "Retorno mensal" if metric == "monthly_return" else "Volatilidade não anualizada"
            axis.set_title(f"{INDICATOR_LABELS[macro]} × {metric_label}")
            axis.set_xlabel("Método")
            axis.set_ylabel("Coeficiente (adimensional)")
    figure.suptitle(
        "Correlações por ticker — mar/2012–dez/2022\n"
        "Uma relação indicador × métrica por painel; elegibilidade: ≥24 pares válidos por combinação",
        y=0.995,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.975))
    figure.savefig(FIGURES_DIR / "correlation_ticker_distributions.png", dpi=180, bbox_inches="tight")
    plt.close(figure)


def save_figures(monthly: pd.DataFrame, pearson: pd.DataFrame, spearman: pd.DataFrame, by_ticker: pd.DataFrame) -> None:
    save_heatmap(pearson, "correlation_pearson_heatmap.png", "Correlação de Pearson — análise agregada")
    save_heatmap(spearman, "correlation_spearman_heatmap.png", "Correlação de Spearman — análise agregada")
    save_selected_scatterplots(monthly, pearson, spearman)
    save_ticker_distributions(by_ticker)


def main() -> None:
    stocks, economic = load_processed_data()
    validate_inputs(stocks, economic)
    monthly = join_monthly_data(stocks, economic)
    report = save_tables(monthly, stocks, economic)
    pearson = pd.read_csv(TABLES_DIR / "correlation_pearson.csv")
    spearman = pd.read_csv(TABLES_DIR / "correlation_spearman.csv")
    by_ticker = pd.read_csv(TABLES_DIR / "correlation_by_ticker.csv")
    save_figures(monthly, pearson, spearman, by_ticker)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
