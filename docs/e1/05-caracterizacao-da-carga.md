# Caracterização da carga de trabalho

Passo 1 do Método de Decisão, com números medidos sobre a carga completa (DF e GO, 01/2021 a 07/2026).

## Resumo

| Aspecto | Caracterização |
| --- | --- |
| **Volume** | 3,67 milhões de internações, 240 mil linhas de leito, 26 mil estabelecimentos com 31 mil versões; banco com 1,16 GB; arquivos brutos com 332 MB |
| **Crescimento** | cerca de 55 mil internações por mês (DF 20 mil, GO 35 mil); cerca de 200 MB por ano no banco |
| **Escrita** | lote mensal, insert-only: uma competência nova do SIH e do CNES por UF por mês; cerca de 5.400 linhas/s na carga |
| **Leitura** | analítica: agregações por semana, região de saúde e CID sobre um ou mais anos; acesso pontual por hospital e mês |
| **Proporção** | a escrita acontece em poucos minutos por mês; o resto do tempo, a origem só atende leituras |
| **Padrão de acesso** | filtro por intervalo de datas (`dt_saida`) e por estabelecimento; junção com cadastro e leitos da mesma competência |
| **Latência tolerada** | horas para atualizar o painel; segundos para uma consulta analítica; o dado da fonte já chega com 1 a 3 meses de atraso |
| **Sazonalidade** | da demanda: inverno (respiratórias) e verão (dengue); da escrita: nenhuma, sempre um lote mensal |

## Escrita

| Fonte | UF | Linhas novas por mês (média) | Mín – máx | Tempo por arquivo |
| --- | --- | ---: | --- | ---: |
| SIH-RD | DF | 20.007 | 17.344 – 22.560 | 3,7 s |
| SIH-RD | GO | 34.767 | 25.933 – 41.650 | 6,5 s |
| CNES-LT | DF | 570 | 536 – 603 | 0,06 s |
| CNES-LT | GO | 2.962 | 2.889 – 3.069 | 0,16 s |
| CNES-ST | DF | 279 versões | 54 – 7.238 | 0,6 s |
| CNES-ST | GO | 559 versões | 78 – 23.056 | 1,3 s |

O máximo do CNES-ST é a primeira competência, quando todo estabelecimento entra pela primeira vez. Depois disso, só 4 a 5% dos registros lidos viram linha nova.

## Leitura

As consultas representam as perguntas da plataforma e rodam direto sobre a origem. Os tempos são de 13/10/2026, com o banco aquecido: mediana de 3 execuções de `EXPLAIN (ANALYZE, TIMING OFF)`, num PostgreSQL 16.15 com a configuração padrão (8 CPUs, 5,7 GB de RAM).

| Consulta | Pergunta | Padrão de acesso | Tempo |
| --- | --- | --- | ---: |
| L1: internações de um hospital num mês | 1, 6 | pontual, por índice `(cnes, dt_saida)` | 3,4 ms |
| L2: leitos SUS por região numa competência | 2 | agregação pequena | 59 ms |
| L5: permanência e custo por hospital e especialidade, 2024 | 6, 7 | agregação de um ano | 377 ms |
| L3: três principais causas por região, inverno de 2024 | 3 | agregação com junções | 530 ms |
| L6: internações de residentes de outra UF, período inteiro | 4 | varredura completa | 2,5 s |
| **L4: ocupação semanal por região, 2024** | **pergunta de gestão** | expande cada internação em dias de permanência | **6,4 s** |

A origem responde bem ao acesso pontual. A pergunta de gestão custa 6,4 s para um único ano, porque precisa espalhar cada internação pelos dias de permanência. Esse é o argumento medido para materializar o paciente-dia uma vez, na camada analítica da E3, em vez de recalculá-lo a cada consulta.

## Defasagem da fonte

O SIH é um sistema de faturamento: a AIH é apresentada depois da alta e processada na competência seguinte. Meses entre a saída do paciente e a chegada da AIH, para saídas de 2021 a 2024:

| Meses após a saída | Internações | % | % acumulado |
| --- | ---: | ---: | ---: |
| 0 | 1.658.440 | 65,3 | 65,3 |
| 1 | 512.035 | 20,2 | 85,5 |
| 2 | 222.515 | 8,8 | 94,3 |
| 3 | 134.161 | 5,3 | **99,5** |
| 4 – 5 | 11.827 | 0,5 | 100,0 |

A **janela de maturidade é de 3 meses**: um mês de evento só pode ser analisado como completo três competências depois. Isso aparece nos dados: as saídas de 06/2026 e 07/2026 ainda estão incompletas (em GO, 32 mil e 25 mil internações, contra cerca de 38 mil num mês normal). Sem esse cuidado, os meses recentes pareceriam uma queda de internações.

## Ressalvas

- A taxa de leitura real ainda não pode ser medida, porque não há usuários. O uso previsto é o painel e o ETL reverso consultarem a base uma vez por mês, depois de cada nova competência, mais algumas dezenas de consultas analíticas por dia.
- A ocupação calculada pela L4 é uma estimativa bruta: leito cadastrado não é necessariamente leito em operação, e internação de zero dia não conta paciente-dia.

## Reproduzir

```bash
sql/caracterizacao/executar.sh    # ~1 min; grava sql/caracterizacao/resultados/AAAA-MM-DD.txt
```

O arquivo de resultado traz as consultas, as primeiras linhas de cada resposta, os tempos e os planos de execução.
