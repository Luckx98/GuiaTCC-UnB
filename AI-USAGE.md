# AI-USAGE.md — Squad Grupo 01 (Leitos SUS-DF)

Registro de uso de assistentes e agentes de IA no Projeto Integrado.

Este arquivo cumpre a [Política de Uso de IA](https://unb-bd2.github.io/Disciplina/uso-de-ia/)
da disciplina. Ele não é confissão nem formalidade: é o mesmo tipo de registro
que um ADR faz para decisões de arquitetura.

**Duas regras de forma.** Escreva **no momento do uso**, não na véspera da
Entrega — registro reconstruído de memória sai impreciso, e imprecisão aqui é o
que a política pune. E versione junto com o código: uma entrada por commit
relevante é melhor que um resumo mensal.

**Não precisa registrar** autocompletar de editor, correção ortográfica ou
tradução. Registre o que produziu artefato ou mudou uma decisão.

---

## Entradas

### 2026-10-07 — Remoção do código do tema anterior (GuiaOrientador/CAPES)

- **Ferramenta:** Claude Code (modelo Claude Opus 5.5), extensão do VS Code.
- **Onde:** `src/` (API FastAPI, modelos ORM, pipeline CAPES e embeddings),
  `frontend/`, `scripts/`, `tests/test_capes.py`, `db/init/`, migração
  `20260930_0001`, ADR 0001 da CAPES; ajustes em `docker-compose.yml`,
  `Dockerfile`, `requirements.txt`, `.env.example`, `alembic/env.py` e `mkdocs.yml`.
- **O que foi pedido:** levantar o que do repositório servia ao novo tema e,
  depois, remover o que não servia mais.
- **O que foi aproveitado:** a remoção inteira e o diagnóstico. Ficaram o Alembic
  (que resolveu a pendência da ferramenta de migração), a ordem
  postgres → migrate → loader do Compose, o MkDocs e o workflow do Pages.
  Redis, SeaweedFS, API e dependências de IA (OpenAI, LangChain, pgvector) saíram.
  Os textos de documentação do tema antigo foram mantidos de propósito: estão
  com outra pessoa da Squad.
- **Como foi verificado:** busca por referências aos módulos apagados (nenhum
  import quebrado) e `docker compose config` sem erro. O commit da limpeza foi
  revisado e feito à mão (`ab25d3f`).
- **Quem revisou:** Cairo Florenço.

### 2026-10-07 — Região de saúde dos hospitais do DF (`estabelecimento_regiao_saude_df.csv`)

- **Ferramenta:** Claude Code (modelo Claude Opus 5.5), extensão do VS Code.
- **Onde:** `dados/referencia/estabelecimento_regiao_saude_df.csv` e tabela
  `estabelecimento_regiao_df` (migração `0002`).
- **O que foi pedido:** medir os arquivos reais antes de modelar. A medição
  mostrou que no DF todo hospital e todo paciente têm o mesmo município (530010)
  e que o campo `REGSAUDE` do CNES é texto livre e quase sempre vazio, então não
  há como derivar a região de saúde das fontes. Das alternativas levantadas
  (tabela curada, CEP, mudar a pergunta), a Squad escolheu a tabela curada.
- **O que foi aproveitado:** a tabela com 56 estabelecimentos. Nome e bairro
  vêm da API pública do CNES (`apidadosabertos.saude.gov.br`). A região
  administrativa foi atribuída pelo assistente a partir do bairro e do endereço,
  e a região de saúde segue a composição da SES-DF, com os códigos do DATASUS
  (`df_regsaud.cnv`, 53002–53008). Dois casos ficaram marcados como incertos na
  coluna `observacao` (Setor Policial Sul e Núcleo Rural Alexandre Gusmão).
  Três hospitais de campanha da COVID-19 (Gama, Autódromo e Ceilândia) só
  apareceram na carga completa e foram acrescentados depois.
- **Como foi verificado:** a quantidade de regiões administrativas por região
  bateu com a quantidade de códigos de cada região no `df_regsaud.cnv`. Na carga
  completa, o loader avisa os CNES do DF sem região; depois do acréscimo dos três
  hospitais de campanha, o aviso deixou de aparecer.
  **Pendente:** conferir a atribuição contra a lista oficial da SES-DF.
  Hospitais de referência distrital (HBDF, HMIB, HCB, HUB, ICTDF) estão
  classificados só pela localização, o que infla a Região Central; isso será
  tratado na análise.
- **Quem revisou:** Cairo Florenço.

### 2026-10-07 — Banco de origem, migrações e loader

- **Ferramenta:** Claude Code (modelo Claude Opus 5.5), extensão do VS Code.
- **Onde:** `docker-compose.yml`, `Dockerfile`, `alembic/versions/0001`–`0006`,
  `loader/`, `dados/amostra/`, `requirements.txt`.
- **O que foi pedido:** implementar o banco insert-only versionado por
  competência e a carga reprodutível de SIH/SUS (RD) e CNES (ST, LT) para DF e
  GO, conforme o plano da E1.
- **O que foi aproveitado:** tudo, com estas mudanças em relação ao plano,
  todas motivadas por medição dos arquivos reais:
  - a chave `(n_aih, competencia)` do plano não é única. AIHs de longa
    permanência (`IDENT=5`) aparecem mais de uma vez por competência; a chave
    passou a incluir `dt_saida`. Nesses registros `DT_INTER` é a data da
    internação original (há casos de 2008);
  - a chave de leito usa `CODLEITO`, não `TP_LEITO`;
  - campos identificadores (NASC, CEP, CPF_AUT, GESTOR_CPF) não são gravados;
  - CIDs ausentes do `cid10.dbf` do DATASUS (N18.2–N18.5 e U04/U09/U10) ficam
    rejeitados e contados em `carga_rejeicao`, por decisão da Squad.
  O assistente errou o parser dos arquivos `.cnv` na primeira versão (nenhuma
  região era reconhecida); o erro apareceu na primeira execução e foi corrigido.
- **Como foi verificado:** `docker compose up --build` numa cópia limpa do
  repositório, sem `.env`: as 6 migrações rodaram em ordem e a amostra carregou.
  `UPDATE` e `DELETE` foram recusados pelo trigger. Uma segunda execução ignorou
  todos os arquivos (idempotência por sha256). A carga completa (DF+GO,
  01/2021–07/2026, 406 arquivos) terminou sem falhas em 14 min 20 s, com
  3.669.874 internações, 240.132 linhas de leito, 30.919 versões de
  estabelecimento e 145 rejeições (0,004%).
- **Quem revisou:** Cairo Florenço.

### 2026-10-07 — Testes automatizados do loader

- **Ferramenta:** Claude Code (modelo Claude Opus 5.5), extensão do VS Code.
- **Onde:** `tests/test_dbf.py`, `tests/test_referencias.py`,
  `tests/test_sih.py`; a validação de internações foi extraída para a função
  `converter` em `loader/sih.py` para poder ser testada sem banco.
- **O que foi pedido:** testes para as partes mais frágeis do loader.
- **O que foi aproveitado:** os 11 testes. Eles cobrem o leitor de DBF (inclusive
  o cabeçalho com `0x00` do CNES-ST e registros apagados), o parser de `.cnv`
  (com o caso que causou o erro de região), a interpretação dos nomes de
  arquivo, um registro de internação válido, longa permanência com data antiga,
  oito motivos de rejeição e a remoção de NASC/CEP dos registros rejeitados.
- **Como foi verificado:** `python -m unittest` no `python:3.11-slim` e dentro
  da imagem do loader (`docker compose run --rm loader python -m unittest`):
  11 testes, todos passando. Os casos de teste usam valores observados nos
  arquivos reais (CID N18.5, `DT_INTER` de 2008, `DIAG_SECUN` "0000").
- **Quem revisou:** Cairo Florenço.

### 2026-10-07 — Consultas de caracterização da carga e de histórico da origem

- **Ferramenta:** Claude Code (modelo Claude Opus 5.5), extensão do VS Code.
- **Onde:** `sql/caracterizacao/` (volume, escrita, represamento, consultas de
  leitura L1–L6 e `executar.sh`) e `sql/historico/` (consultas H1–H4 e
  `executar.sh`), com os resultados de 2026-10-07 em `resultados/`.
- **O que foi pedido:** consultas que medem volume, escrita, leitura e defasagem da origem. 
  E também, consultas que só são possíveis porque a origem guarda histórico.
- **O que foi aproveitado:** todas as consultas e os dois scripts. As consultas
  de leitura foram escolhidas pelo assistente a partir das perguntas que a
  plataforma deve responder (pontual por hospital, leitos por região, causas,
  ocupação semanal, permanência e custo, internação fora da UF). Duas correções
  foram feitas depois da primeira execução: a L4 cortava a última semana de
  2024 (que entra em 2025) e misturava a região "Central" de GO com a "Central"
  do DF; a H1 tinha um erro de SQL (`ORDER BY` com apelido de coluna dentro de
  expressão).
- **Como foi verificado:** os dois scripts rodaram sobre a carga completa
  (3,67 milhões de internações) e os resultados foram conferidos contra números
  já conhecidos. As contagens por fonte batem com a tabela `carga`, e o
  represamento medido na H3 (76,5% das saídas de jan/2025 do DF conhecidas na
  primeira competência) é coerente com o da `03_represamento` (65% no mesmo
  mês, 99,5% em até 3 meses). Os tempos vêm de `EXPLAIN (ANALYZE, BUFFERS)`,
  3 execuções por consulta, com máquina e configuração do PostgreSQL gravadas
  no cabeçalho do resultado.
  **Ressalvas que o texto da E1 precisa carregar:** a ocupação semanal da L4 é
  uma estimativa bruta (leito cadastrado não é leito operando, internação de
  zero dia não conta paciente-dia, hospitais de referência distrital caem na
  Região Central); na H2, 2021 é ano de pandemia e infla o crescimento das
  internações; na H4, parte das versões de cadastro é ruído da própria fonte
  (799 versões numa só competência, 12/2022, e 38 estabelecimentos com
  cadastro que vai e volta).
- **Quem revisou:** Cairo Florenço.
