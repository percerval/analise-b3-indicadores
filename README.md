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

As etapas atualmente implementadas abrangem auditoria, limpeza, agregação,
análise exploratória e análise correlacional dos dados.

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
├── correlation_analysis.py
├── README.md
├── requirements.txt
└── .gitignore
```

### Arquivos principais

- `prepare_data.py` normaliza, valida, saneia e agrega os dados brutos.
- `exploratory_analysis.py` utiliza os dados processados para produzir tabelas
  descritivas, sumários mensais e figuras.
- `correlation_analysis.py` executa a Etapa 4 de forma sequencial, agregando as
  ações por mês e calculando Pearson e Spearman na análise agregada e por
  ticker.
- `notebooks/` contém o notebook utilizado para documentar e apresentar a
  análise exploratória e a Etapa 4, lendo os resultados já gerados.
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
python correlation_analysis.py
```

As análises exploratória e correlacional dependem das bases produzidas por
`prepare_data.py` em `data/processed/`. A ordem acima acompanha a apresentação
do estudo; o script correlacional não depende computacionalmente das saídas
do exploratório. Os scripts sobrescrevem seus resultados; o notebook somente
carrega as bases, tabelas e figuras existentes, sem recalcular correlações.

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
antes da execução de `prepare_data.py`. A origem externa exata dos dois CSVs
**não foi comprovada**: fornecedor, URL de aquisição, licença, data, método de
coleta e códigos das séries continuam desconhecidos. Nomes de arquivos e colunas
não comprovam procedência da B3, Yahoo Finance, Kaggle, Banco Central, IBGE ou
FGV. O campo `source` dos relatórios identifica apenas uma entrada local.

Há linhagem computacional interna, mas não proveniência externa documentada.
Essa lacuna deve ser resolvida antes de afirmar reprodutibilidade completa.

O bruto de ações contém 1.031.282 registros, 472 símbolos e datas de janeiro/2010
a fevereiro/2025. As bases mensais e a exploração abrangem março/2012 a
dezembro/2024; a base diária saneada não recebe esse corte mensal. A análise
conjunta da Etapa 4 usa apenas março/2012 a dezembro/2022. O corte da análise
não apaga registros dos brutos nem das bases processadas já existentes.

### Auditoria local de frequência e unidades

O bruto econômico contém 5.537 datas civis consecutivas, ordenadas e sem
duplicatas, de 01/01/2010 a 27/02/2025. A Selic está preenchida em todas as
linhas, inclusive fins de semana. Os outros indicadores não são repetidos
diariamente: têm um único valor não nulo por mês, sempre no dia 1.

IPCA, IGP-M e INPC têm 181 observações de janeiro/2010 a janeiro/2025; desemprego
tem 154, de março/2012 a dezembro/2024. A data no dia 1 é uma convenção de
armazenamento observada, não prova de data de divulgação ou disponibilidade.

**Nenhuma unidade macroeconômica foi confirmada por documentação do dataset.**
As correspondências abaixo são inferências compatíveis com os valores e as
definições oficiais, não identificação das séries nem da origem dos arquivos.

| Série | Intervalo observado no bruto | Operação no pipeline | Unidade compatível/provável, não comprovada |
|---|---|---|---|
| Taxa Selic | 2,00 a 14,25 | Média dos níveis registrados diariamente no mês e último valor não nulo do mês | Taxa em % a.a., possivelmente meta Selic |
| Diferença mensal da Selic | −1,00 a +1,50 (derivada) | Diferença entre os valores finais de meses consecutivos no arquivo auditado | Diferença mensal na unidade original da série Selic; p.p. somente se a unidade percentual for confirmada |
| IPCA | −0,68 a 1,62 | Primeiro valor não nulo do mês, único no arquivo auditado | Variação percentual mensal |
| IGP-M | −1,93 a 4,34 | Primeiro valor não nulo do mês, único no arquivo auditado | Variação percentual mensal |
| INPC | −0,60 a 1,71 | Primeiro valor não nulo do mês, único no arquivo auditado | Variação percentual mensal |
| Desemprego PNADC | 6,1 a 14,9 | Primeiro valor não nulo do mês, único no arquivo auditado | Taxa percentual de desocupação de trimestre móvel |

`selic_media_mensal` é a média dos níveis diários disponíveis, **não juros
acumulados no mês**. No arquivo auditado, os meses completos dão peso igual a
cada dia corrido. Uma média mensal de taxas anuais continuaria sendo expressa
em taxa anual. `selic_variacao_mensal_pontos` conserva seu nome técnico por
compatibilidade, mas não confirma uma unidade em pontos percentuais.

Percentual, pontos percentuais, variação mensal, taxa anual e número-índice não
são equivalentes. A agregação por mês não determina a unidade. Os gráficos
macroeconômicos usam rótulos neutros de unidade original não comprovada.
Para retornos, a conversão em percentual é sustentada pela fórmula adimensional
`(preço_atual / preço_anterior - 1) * 100`, não por uma unidade macroeconômica.
A moeda dos preços, a unidade de `Volume` e a metodologia de ajuste de
`Adj Close` também não foram comprovadas pela documentação dos arquivos.

### Referências conceituais oficiais — não são fontes comprovadas dos CSVs

- BCB: [Selic em % a.d. (SGS 11)](https://dadosabertos.bcb.gov.br/dataset/11-taxa-de-juros---selic),
  [Selic anualizada em % a.a. (SGS 1178)](https://dadosabertos.bcb.gov.br/dataset/1178-taxa-de-juros---selic-anualizada-base-252)
  e [meta Selic em % a.a. (SGS 432)](https://dadosabertos.bcb.gov.br/dataset/432-taxa-de-juros---meta-selic-definida-pelo-copom).
  Observações diárias não implicam uma taxa expressa ao dia.
- IBGE: metadados do [IPCA (1737)](https://servicodados.ibge.gov.br/api/v3/agregados/1737/metadados)
  e [INPC (1736)](https://servicodados.ibge.gov.br/api/v3/agregados/1736/metadados)
  distinguem número-índice, variação mensal e acumulados em diferentes janelas.
- FGV IBRE: [IGP](https://portalibre.fgv.br/igp), com periodicidade mensal e
  coleta do IGP-M entre o dia 21 do mês anterior e o dia 20 do mês de referência.
- IBGE: [PNAD Contínua mensal (6381)](https://servicodados.ibge.gov.br/api/v3/agregados/6381/metadados)
  documenta taxa de desocupação em % com referência trimestral móvel. Essa
  correspondência continua provável, não comprovada para a coluna local.

## Limitação de cobertura em 2023

A base original de ações apresenta uma quebra severa de cobertura durante 2023.
Essa ausência já está presente no arquivo bruto `bovespa_stocks.csv` e não foi
causada pelo pipeline de limpeza.

Como evidência da diferença de cobertura:

- 2022: 113.614 registros;
- 2023: 5.889 registros;
- 2024: 100.248 registros.

Para manter uma janela contínua anterior à quebra, a decisão adotada na Etapa 4
é encerrar o período principal em dezembro/2022. Assim, **2023 e 2024 ficam fora
das correlações principais**, embora participem da exploração até dezembro/2024,
que deve ser lida com atenção à cobertura. Não se presume a causa da ausência
nem se afirma que o histórico Git comprova pré-especificação desse recorte.

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
- A verificação de intervalo exige `Low <= Close <= High`, com `Low` e `High`
  positivos; ela não verifica se `Open` está dentro desse intervalo. Não há
  correção de preços inconsistentes.
- O filtro exige pelo menos 24 meses com registros válidos, correspondentes a
  pelo menos 70% dos meses entre a primeira e a última data observadas no bruto,
  e no máximo 5% de observações inválidas. Isso não exige 70% dos pregões em cada mês.
- A base mensal utiliza `Adj Close` para retorno e volatilidade. `Close` é
  mantido como referência não ajustada, sem imputação de preços.
- O retorno mensal compara os últimos registros ajustados válidos de meses
  civis consecutivos, sem comprovar que sejam os últimos pregões de cada mês.
- A Selic é agregada por média dos níveis diários, último valor mensal e
  diferença mensal na unidade original da série, sem conversão de unidade.
- O período principal da análise conjunta da Etapa 4 é março de 2012 a dezembro
  de 2022, totalizando 130 meses consecutivos.
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

`correlation_analysis.py` utiliza exclusivamente março de 2012 a dezembro de
2022 e produz:

- `outputs/tables/correlation_monthly_aggregate.csv`;
- `outputs/tables/correlation_pearson.csv`;
- `outputs/tables/correlation_spearman.csv`;
- `outputs/tables/correlation_by_ticker.csv`;
- `outputs/tables/correlation_ticker_summary.csv`;
- `outputs/tables/correlation_indicator_metadata.json`;
- `outputs/tables/correlation_report.json`;
- heatmaps, scatterplots selecionados e distribuição das correlações por ticker
  em `outputs/figures/`.

A unidade da análise agregada é um mês. O mesmo indicador macroeconômico não é
replicado para cada ticker como se cada ticker-mês fosse uma observação
independente. A análise por ticker é calculada separadamente para cada ativo.

### Leitura e limitações da Etapa 4

- Pearson mede associação linear; Spearman utiliza postos e mede associação
  monotônica. Diferenças podem refletir não linearidade monotônica, outliers,
  empates e características da distribuição. Reordenar conjuntamente os pares
  de observações não altera nenhum dos coeficientes.
- Os p-values são **convencionais/nominais, não ajustados**. Não há tratamento
  inferencial específico para autocorrelação nem ajuste para múltiplos testes.
  Os 130 pares mensais válidos não são necessariamente 130 observações
  independentes; Spearman não elimina dependência temporal. Se a PNADC local
  corresponder a trimestres móveis, há ainda sobreposição das janelas.
- São examinadas 42 relações agregadas por método (84 resultados) e 28
  combinações por ticker (6.020 para 215 ativos, antes da elegibilidade). Essas
  comparações não são independentes. `p < 0,05` não é usado como prova de relação
  econômica; o foco é direção, magnitude e comparação entre métodos.
- A seleção dos 215 ativos é retrospectiva, baseada no histórico disponível,
  inclusive posterior a 2022. O corte das correlações não remove essa influência
  sobre a composição da amostra.
- Os agregados têm composição variável, sem ponderação por capitalização.
  Ativos presentes, retornos válidos e volatilidades válidas têm contagens
  distintas. Retornos exatamente zero entram no denominador das proporções,
  mas não são positivos nem negativos; as proporções não precisam somar 100%.
- A volatilidade é o desvio-padrão amostral dos retornos entre registros válidos,
  agrupados por mês, sem anualização. Lacunas podem produzir intervalos maiores
  que uma sessão. Não há limiar explícito de sessões por ativo-mês.
- O limiar de 24 pares válidos é operacional, não garantia de independência ou
  precisão. O resumo por ticker exige o limiar em todas as combinações:
  **212 de 215 ativos** atendem; **F11, G11 e SRNA3** ficam abaixo. As figuras por
  ticker aplicam a elegibilidade por combinação e separam indicador e métrica.
- As correlações são contemporâneas e bivariadas, sem controles ou defasagens.
  O mês armazenado não comprova data de divulgação ou disponibilidade pública.
  Origem, unidades e referência temporal das séries não estão integralmente
  documentadas. Não há interpretação causal, previsão ou recomendação financeira.

O notebook compara os mesmos pares em Pearson e Spearman e mantém p-values e
contagens. Os quatro scatterplots destacam os maiores valores absolutos de
Pearson, uma seleção exploratória, sem linha preditiva. Na distribuição por
ticker, cada painel corresponde a um indicador e uma métrica; não se misturam
relações macroeconômicas distintas dentro de uma caixa.

Os arquivos de dados e resultados são ignorados pelo Git atualmente porque são
grandes ou regeneráveis a partir das entradas locais. A origem externa dos
datasets ainda precisa ser comprovada; portanto, este projeto não deve ser descrito como
completamente reproduzível apenas a partir do repositório.
