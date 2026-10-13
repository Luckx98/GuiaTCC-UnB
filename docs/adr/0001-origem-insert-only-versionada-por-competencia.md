# ADR 0001 — A origem OLTP é insert-only e versionada por competência

- **Status:** Aceito
- **Data:** 2026-10-13
- **Decisores:** Squad Grupo 01 (Leitos SUS-DF)

## Contexto

A pergunta de gestão compara cinco anos de ocupação de leitos SUS por semana e região de saúde do DF. As fontes chegam como **retratos periódicos** publicados pelo DATASUS:

- **SIH/SUS (RD):** uma linha por AIH paga, publicada por UF e competência (mês de processamento). Uma competência traz internações de meses anteriores: em 65% dos casos a AIH chega no mesmo mês da saída do paciente, e em 99,5% dos casos em até 3 meses. AIHs de longa permanência aparecem uma vez por mês cobrado.
- **CNES ST e LT:** retrato mensal completo do cadastro de estabelecimentos e dos leitos.

As entregas seguintes dependem do histórico: a E2 captura mudanças (CDC) e a E3 constrói dimensões de variação lenta (SCD).

**Carga de trabalho** (medida na carga completa, DF e GO, 01/2021 a 07/2026; detalhes em [Caracterização da carga](../e1/05-caracterizacao-da-carga.md)):

| Aspecto | Medida |
| --- | --- |
| Volume | 3,67 milhões de internações, 240 mil linhas de leito, 26 mil estabelecimentos; banco com 1,16 GB |
| Escrita | lote mensal: cerca de 55 mil internações, 3,5 mil linhas de leito e 840 versões de cadastro por mês |
| Leitura | analítica: agregações por semana, região e CID sobre anos completos; acesso pontual por hospital |
| Latência tolerada | horas (o dado chega com 1 a 3 meses de atraso) |

**Restrições não funcionais:**

- Tudo sobe com `docker compose up` numa máquina de estudante (8 CPUs, 6 GB de RAM).
- Somente software livre.
- A equipe domina SQL e Python.
- A licença dos dados é CC BY-ND 3.0, que não permite republicar a base modificada.
- AIH é dado sensível de saúde (LGPD, art. 5º, II).
- O PostgreSQL deve estar pronto para CDC (`wal_level=logical`).

## Alternativas consideradas

| | Alternativa | Prós | Custos |
| --- | --- | --- | --- |
| 0 | **Opção nula: espelhar os arquivos.** Cada arquivo publicado é acrescentado como veio, sem chave de versão nem restrições além do formato | trivial de carregar; guarda tudo | repete o cadastro inteiro a cada mês; sem chave natural (a AIH se repete); cada análise precisa recalcular diferenças |
| 1 | **CRUD com upsert.** Uma linha por chave de negócio, sobrescrita a cada carga | menor volume; estado atual direto | apaga o passado: leitos de meses anteriores, mudanças de gestão, competência de chegada da AIH |
| 2 | **Híbrido.** Cadastro (estabelecimento) em CRUD; fatos (leito, internação) insert-only | volume pequeno no cadastro; mantém a série de fatos | perde a história do cadastro, justamente a usada para comparar hospitais antes e depois de mudar de gestão |
| 3 | **Insert-only versionado por competência.** Cada carga só acrescenta linhas; o cadastro ganha nova versão quando algum atributo muda; toda linha guarda competência e data de ingestão | preserva o histórico; CDC e SCD diretos; republicações viram nova carga | mais volume que o CRUD; o estado atual exige filtrar a versão mais recente |

## Medição

A medição usa os dados reais carregados. As alternativas 1 e 2 foram montadas em tabelas temporárias a partir da carga completa. Para reproduzir: `docker compose exec -T postgres psql -U leitos -d leitos < sql/adr/0001_medicao.sql`. Resultado em `sql/adr/resultados/0001_2026-10-13.txt`.

**Linhas guardadas**

| Fonte | Espelho (0) | CRUD (1) | Insert-only (3) |
| --- | ---: | ---: | ---: |
| CNES-ST (estabelecimentos) | 1.278.737 | 26.048 | 56.967 |
| CNES-LT (leitos) | 240.132 | 4.471 | 240.132 |
| SIH-RD (internações) | 3.670.019 | 3.612.699 | 3.669.874 |

No híbrido (2), o cadastro fica com o número do CRUD e os fatos com o número do insert-only.

**O que o CRUD (e, no cadastro, o híbrido) apaga**

| Informação perdida ao sobrescrever | Quantidade |
| --- | ---: |
| mudanças de cadastro de estabelecimento | 4.871 |
| mudanças de gestão municipal ↔ estadual | 44 |
| retratos mensais de leitos de competências anteriores | 235.661 |
| registros de longa permanência colapsados numa só AIH | 57.175 |
| internações cuja competência de chegada é posterior ao mês de saída | 1.194.613 |

**Custo de consultar o estado atual** (mediana de 5 execuções, ms)

| Consulta | Insert-only | CRUD |
| --- | ---: | ---: |
| cadastro atual de um hospital | 0,04 | 0,02 |
| estabelecimentos por tipo de gestão hoje | 67 | 6 |
| leitos SUS atuais de um hospital | 1,8 | 0,02 |
| leitos SUS atuais por UF | 209 | 6 |

Espaço ocupado: cadastro com 6,4 MB no insert-only e 2,6 MB no CRUD; leitos com 36 MB e 0,4 MB.

## Decisão

A origem OLTP é **insert-only e versionada por competência**:

- toda tabela de dados só recebe `INSERT`, garantido por trigger que rejeita `UPDATE` e `DELETE`;
- o cadastro do CNES ganha nova versão só quando algum atributo muda;
- cada linha guarda a data do evento, a competência de processamento e a data de ingestão;
- a republicação de uma competência entra como nova carga, e as visões `*_vigente` mostram a mais recente.

Quanto à normalização, a origem fica normalizada: a região de saúde, o CID e o município são tabelas de referência. Desnormalizar não compensa aqui; a camada analítica da E3 é o lugar para isso.

## Consequências

**Ganhos**

- As perguntas 2, 3 e 8 e a reconstrução do "o que se sabia em cada mês" só são possíveis com este modelo (ver [Histórico da origem](../e1/06-historico-da-origem.md)).
- O represamento fica mensurável, o que fixou a janela de maturidade em 3 meses.
- O CDC da E2 lê apenas inserções. O SCD da E3 parte de `estabelecimento_versao`.
- No cadastro, o insert-only guarda 4,5% das linhas do espelho.

**Perdas**

- O cadastro ocupa 2,2 vezes as linhas do CRUD, e os leitos 54 vezes.
- Consultar o estado atual custa de 11 a 34 vezes mais (até 209 ms contra 6 ms).
- Toda consulta precisa usar as visões `*_vigente` para não contar duas vezes uma competência republicada.
- O fechamento de um estabelecimento não é registrado: quando um CNES some do ST, a última versão continua aparecendo como vigente.
- Parte das versões é ruído da própria fonte (799 versões numa só competência, 12/2022) e precisa ser filtrada na E3.

**Irreversibilidade**

A decisão é barata de desfazer num sentido e impossível no outro. Do insert-only se obtém o CRUD a qualquer momento: as tabelas da medição saíram de um `DISTINCT ON`. Do CRUD não se recupera o que foi sobrescrito. Reverter para CRUD custaria uma migração que derruba as triggers e compacta as tabelas.

## Gatilho de revisão

Revisar se ocorrer qualquer uma destas condições:

- o banco passar de **10 GB** no recorte DF+GO (hoje 1,16 GB, crescendo cerca de 200 MB por ano);
- alguma consulta de estado atual passar de **1 s** de mediana mesmo com índice (hoje no máximo 209 ms);
- a E3 mostrar que o histórico guardado no Iceberg (com *time travel*) cobre as perguntas de histórico, tornando redundante guardá-lo também na origem.
