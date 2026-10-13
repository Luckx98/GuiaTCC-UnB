# Histórico da origem

## Declaração

**A origem é insert-only.** Nenhuma tabela de dados aceita `UPDATE` ou `DELETE`: uma trigger rejeita as duas operações com erro. Cada carga só acrescenta linhas. A justificativa e as alternativas medidas estão no [ADR 0001](../adr/0001-origem-insert-only-versionada-por-competencia.md).

| Tabela | Como guarda histórico |
| --- | --- |
| `internacao` | cada linha guarda a competência em que a AIH chegou e a data em que foi carregada; a republicação de uma competência entra como nova carga |
| `leito` | um retrato completo por competência; os meses anteriores continuam no banco |
| `estabelecimento_versao` | nova linha só quando algum atributo do cadastro muda; a vigência de cada versão sai da visão `estabelecimento_vigencia` |
| `carga`, `carga_rejeicao` | registro permanente de cada arquivo carregado e de cada linha recusada |

As visões `carga_vigente`, `leito_vigente` e `internacao_vigente` mostram só a versão mais recente de cada competência, para que uma republicação não seja contada duas vezes.

## O que isso permite perguntar

As consultas abaixo só funcionam porque a origem não sobrescreve. Estão em `sql/historico/`, e os resultados de 07/10/2026 em `sql/historico/resultados/`.

### Hospitais que mudaram de gestão mudaram de desempenho? (pergunta 8)

`estabelecimento_versao` registra 44 mudanças de gestão entre 2021 e 2026. Quinze delas são de hospitais com internação, todos em GO e todos de gestão municipal para estadual; nove mudaram juntos em 11/2021, em Goiânia. O hospital de maior volume (CNES 7743068) passou de **1.201 para 1.845 internações por mês** nos 12 meses seguintes à mudança (+54%). Num modelo CRUD, só restaria a gestão atual, e a comparação antes/depois seria impossível.

### Quais regiões perderam leitos enquanto as internações cresceram? (pergunta 2)

Comparando os leitos SUS de 01/2021 com os de 01/2026, e as internações de 2021 com as de 2025:

| Região (GO) | Leitos SUS | Internações |
| --- | ---: | ---: |
| São Patrício I | −28,5% | +64,9% |
| Pirineus | −11,9% | +44,1% |
| São Patrício II | −10,0% | +42,9% |
| Sudoeste II | −6,1% | +47,4% |

No DF, todas as regiões ganharam leitos (de +4% a +14%). A Região Leste é a que mais pressiona, com +12,6% de leitos para +21,2% de internações. Ressalva: 2021 foi ano de pandemia, com cirurgias eletivas suspensas, o que infla o crescimento das internações.

### O que a base sabia em cada mês?

Quantas saídas de janeiro/2025 já eram conhecidas ao fim de cada competência:

| Base ao fim de | DF | GO |
| --- | ---: | ---: |
| 01/2025 | 76,5% | 70,2% |
| 02/2025 | 93,5% | 87,0% |
| 03/2025 | 96,7% | 95,7% |
| 04/2025 | 100% | 99,6% |

Isso reconstrói o que a Central de Regulação via na época, e explica por que um mês recente parece ter "queda" de internações. Se a carga sobrescrevesse pela AIH, a competência de chegada se perderia.

### Quanto o cadastro muda?

Foram 4.871 versões novas de cadastro em cinco anos e meio. Os atributos que mais mudam são:

| Atributo | Mudanças |
| --- | ---: |
| tipo de unidade | 1.856 |
| natureza jurídica | 1.809 |
| atendimento de urgência | 560 |
| vínculo SUS | 550 |

O município nunca mudou.

## Limites

- **Ruído da fonte.** Em 12/2022, o CNES reclassificou a natureza jurídica em massa: 799 versões novas numa só competência. Além disso, 38 estabelecimentos têm cadastro que "vai e volta" (A → B → A). Nem toda versão é uma mudança real; o SCD da E3 precisa filtrar esses casos.
- **Fechamento não registrado.** Quando um estabelecimento some do CNES-ST, nenhuma versão marca o fechamento. A presença mês a mês pode ser obtida do CNES-LT.
- **Custo.** O estado atual exige filtrar a versão mais recente, e consultá-lo custa de 11 a 34 vezes mais que numa tabela CRUD (até 209 ms; ver o ADR).

## Reproduzir

```bash
sql/historico/executar.sh    # ~10 s
```
