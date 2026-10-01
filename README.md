# Análise da relação entre indicadores econômicos brasileiros e o comportamento histórico das ações da B3

## Identificação

**Integrantes:**

- Ian Lucas Lobato Barra da Silva
- Leonardo Jacomini Barcos
- Ilard Moisés da Silva Lamarão
- Cauã Cavalcante

**Instituição:** Instituto Federal do Pará — Campus Ananindeua  
**Curso:** Ciência da Computação  
**Disciplina:** Inteligência Artificial 2  
**Professor:** Guilherme Damasceno

## Apresentação

Este projeto acadêmico investiga associações históricas entre indicadores
macroeconômicos brasileiros e uma amostra de ações negociadas na B3.

A investigação é histórica, descritiva e correlacional. O projeto não utiliza
algoritmos de previsão, não pretende prever preços futuros e não realiza
forecasting ou regressão preditiva. Correlação não será interpretada como
causalidade, e os resultados não constituem recomendação de investimento.

As etapas atualmente implementadas abrangem auditoria, limpeza, agregação e
análise exploratória dos dados. A etapa atual ainda não calcula correlações.

## Indicadores e medidas

Os indicadores econômicos utilizados são:

- Selic;
- IPCA;
- IGP-M;
- INPC;
- desemprego da PNAD Contínua.

Para a amostra de ações, são produzidas as seguintes medidas:

- retorno mensal;
- volatilidade dos retornos diários;
- volume negociado;
- número de sessões válidas.

As ações selecionadas são descritas como uma amostra de ativos, não como o
Ibovespa ou como um índice de mercado.

## Estrutura do projeto

```text
analise-b3-indicadores/
├── data/
│   ├── raw/          # datasets brutos usados como entrada
│   └── processed/    # dados derivados pelo pipeline
├── notebooks/        # exploração e apresentação da análise
├── outputs/
│   ├── figures/      # figuras geradas
│   └── tables/       # tabelas e relatórios gerados
├── prepare_data.py   # limpeza, validação e agregação
├── exploratory_analysis.py
├── README.md
├── requirements.txt
└── .gitignore
```

### Arquivos principais

- `prepare_data.py` normaliza, valida, saneia e agrega os dados brutos.
- `exploratory_analysis.py` utiliza os dados processados para produzir tabelas
  descritivas, sumários mensais e figuras.
- `notebooks/` contém o notebook utilizado para documentar e apresentar a
  análise exploratória.
- `data/raw/` contém as entradas brutas locais. Esses arquivos não são
  versionados atualmente.
- `data/processed/` contém bases derivadas pelo pipeline. Esses arquivos não
  são versionados atualmente.
- `outputs/` contém tabelas, relatórios e figuras reproduzíveis. Esses arquivos
  não são versionados atualmente.

## Instalação

A instalação convencional em Debian/Linux utiliza um ambiente virtual Python:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

As dependências declaradas atualmente em `requirements.txt` são pandas, numpy,
jupyter, matplotlib, seaborn e scipy.

## Execução

Execute os scripts a partir da raiz do projeto e na ordem indicada:

```bash
python prepare_data.py
python exploratory_analysis.py
```

O primeiro script deve ser executado antes do segundo porque a análise
exploratória depende dos arquivos produzidos em `data/processed/`.

### Notebook

Com o ambiente virtual ativado, inicie o Jupyter usando a instalação do próprio
ambiente:

```bash
python -m jupyter lab
```

Depois, abra `notebooks/analise_b3_indicadores.ipynb` pela interface do Jupyter.
Não é necessário instalar Jupyter globalmente quando ele estiver disponível no
ambiente virtual criado a partir de `requirements.txt`.

## Dados

Os datasets brutos não estão incluídos no repositório público neste momento.
Os nomes esperados pelo pipeline são:

```text
data/raw/bovespa_stocks.csv
data/raw/economic_indicators.csv
```

Os arquivos brutos devem ser obtidos separadamente e colocados nesses caminhos
antes da execução de `prepare_data.py`. A origem pública, a data de aquisição,
a licença e as instruções oficiais de obtenção dos datasets ainda não estão
documentadas no projeto. Essa documentação está pendente e deve ser concluída
antes de afirmar a reprodutibilidade completa da análise.

O arquivo bruto de ações contém registros posteriores a dezembro de 2024. O
período principal atualmente definido para o estudo termina em dezembro de
2024; registros posteriores não fazem parte desse período principal.

## Limitação de cobertura em 2023

A base original de ações apresenta uma quebra severa de cobertura durante 2023.
Essa ausência já está presente no arquivo bruto `bovespa_stocks.csv` e não foi
causada pelo pipeline de limpeza.

Como evidência da diferença de cobertura:

- 2022: 113.614 registros;
- 2023: 5.889 registros;
- 2024: 100.248 registros.

O tratamento metodológico dessa limitação ainda será definido antes das
análises finais. Este README não assume uma causa para a ausência e não define
como o ano de 2023 será tratado.

## Decisões atuais de preparação

- Datas são normalizadas para a data civil, sem horário ou timezone.
- Valores numéricos que não podem ser convertidos com segurança tornam-se
  ausentes (`NaN`) e são contabilizados.
- Duplicatas são agrupadas por `Date + Symbol` após a normalização.
- Grupos duplicados economicamente idênticos ou apenas trivialmente diferentes
  mantêm uma linha.
- Grupos conflitantes são excluídos da base diária saneada, sem escolher uma
  observação arbitrariamente.
- Registros com `High = Low = Open = Volume = 0` são tratados como sessões
  inválidas e excluídos das métricas. Nenhum preço é estimado.
- Inconsistências OHLC não são corrigidas; registros afetados não entram nas
  métricas válidas.
- O filtro objetivo de ativos exige pelo menos 24 meses válidos, cobertura
  mensal mínima de 70% e no máximo 5% de observações inválidas.
- A base mensal utiliza `Adj Close` para retorno e volatilidade. `Close` é
  mantido como referência não ajustada, sem imputação de preços.
- O retorno mensal compara o fechamento ajustado com o mês civil anterior.
- A Selic é agregada por média mensal, valor no fim do mês e variação mensal em
  pontos.
- O período principal é março de 2012 a dezembro de 2024.
- A amostra agregada representa os ativos selecionados, não o Ibovespa nem um
  índice de mercado. Medianas são priorizadas para descrever o comportamento
  típico.

## Reprodutibilidade

As entradas do pipeline são:

- `data/raw/bovespa_stocks.csv`;
- `data/raw/economic_indicators.csv`.

`prepare_data.py` produz:

- `data/processed/stocks_clean_daily.csv`;
- `data/processed/stocks_monthly.csv`;
- `data/processed/economic_indicators_monthly.csv`;
- `outputs/tables/ticker_quality.csv`;
- `outputs/tables/duplicate_conflicts.csv`, quando houver conflitos;
- `outputs/tables/cleaning_report.json`.

`exploratory_analysis.py` produz tabelas descritivas, relatórios, sumários
mensais e figuras em `outputs/tables/` e `outputs/figures/`.

Os arquivos de dados e resultados são ignorados pelo Git atualmente porque são
grandes ou reproduzíveis. A origem pública dos datasets ainda precisa ser
documentada; portanto, este projeto ainda não deve ser descrito como
completamente reproduzível apenas a partir do repositório.
