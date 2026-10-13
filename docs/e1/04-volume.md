# Volume

O modo completo carrega anos inteiros, não uma amostra: DF e GO, de 01/2021 até a última competência publicada (07/2026 no SIH, 08/2026 no CNES). Os números abaixo são da carga de 07/10/2026 e podem ser refeitos com `sql/caracterizacao/executar.sh` (seção `01_volume`).

## Por fonte

| Fonte | UF | Arquivos | Linhas lidas | Linhas gravadas | Rejeitadas | Arquivos brutos |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| SIH-RD | DF | 67 | 1.340.532 | 1.340.458 | 74 | 100 MB |
| SIH-RD | GO | 67 | 2.329.487 | 2.329.416 | 71 | 164 MB |
| CNES-ST | DF | 68 | 353.650 | 18.954 | 0 | 19 MB |
| CNES-ST | GO | 68 | 925.087 | 38.013 | 0 | 39 MB |
| CNES-LT | DF | 68 | 38.741 | 38.741 | 0 | 0,5 MB |
| CNES-LT | GO | 68 | 201.391 | 201.391 | 0 | 2,2 MB |

No CNES-ST, "linhas gravadas" soma estabelecimentos novos e versões novas de cadastro: só o que mudou em relação à competência anterior é gravado (ver [Histórico da origem](06-historico-da-origem.md)).

## No banco

| Tabela | Linhas | Dados | Índices | Total |
| --- | ---: | ---: | ---: | ---: |
| `internacao` | 3.669.874 | 586 MB | 522 MB | 1.108 MB |
| `leito` | 240.132 | 18 MB | 18 MB | 36 MB |
| `estabelecimento_versao` | 30.919 | 2,6 MB | 1,5 MB | 4,2 MB |
| `estabelecimento` | 26.048 | 1,4 MB | 0,8 MB | 2,2 MB |
| `cid` | 14.253 | — | — | 1,3 MB |
| `municipio` | 5.645 | — | — | 0,6 MB |
| **Banco inteiro** | | | | **1,16 GB** |

Cada internação ocupa cerca de 317 bytes, contando os índices.

## Internações por ano (competência de processamento)

| Ano | DF | GO | Média mensal DF | Média mensal GO |
| --- | ---: | ---: | ---: | ---: |
| 2021 | 230.888 | 343.684 | 19.241 | 28.640 |
| 2022 | 232.062 | 369.940 | 19.339 | 30.828 |
| 2023 | 237.372 | 423.919 | 19.781 | 35.327 |
| 2024 | 248.066 | 451.993 | 20.672 | 37.666 |
| 2025 | 248.722 | 467.925 | 20.727 | 38.994 |
| 2026 (até 07) | 143.348 | 271.955 | 20.478 | 38.851 |

Em cinco anos, a média mensal cresceu 8% no DF e 36% em GO.
