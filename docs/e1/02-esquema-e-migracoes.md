# Esquema físico e migrações

O esquema é criado por seis migrações Alembic em `alembic/versions/`, escritas em SQL explícito. O serviço `migrate` do Docker Compose espera o PostgreSQL ficar saudável e roda `alembic upgrade head` num banco vazio. O loader só começa depois que a migração termina com sucesso.

| Migração | Cria |
| --- | --- |
| `0001_controle_de_carga` | `carga`, `carga_rejeicao` e a função `bloquear_alteracao()` |
| `0002_referencias` | `regiao_saude`, `municipio`, `cid`, `estabelecimento_regiao_df` |
| `0003_estabelecimento` | `estabelecimento`, `estabelecimento_versao`, visão `estabelecimento_vigencia` |
| `0004_leito` | `leito` |
| `0005_internacao` | `internacao` |
| `0006_visoes_vigentes` | visões `carga_vigente`, `leito_vigente`, `internacao_vigente` |

## Modelo

```text
regiao_saude 1 ──< municipio                          carga 1 ──< carga_rejeicao
     │ 1                                                 │ 1
     └──< estabelecimento_regiao_df (DF, curada)         │ (toda linha de dados aponta para a carga que a trouxe)
                                                         │
estabelecimento 1 ──< estabelecimento_versao >── 1 municipio
       │ 1
       ├──< leito                 (competência × cod_leito)
       └──< internacao >── cid    (competência × n_aih × dt_saida)
                     └──── municipio (residência e estabelecimento)
```

| Tabela | Chave primária | Papel |
| --- | --- | --- |
| `estabelecimento` | `cnes` | chave de negócio; alvo das FKs de leito e internação |
| `estabelecimento_versao` | `(cnes, competencia_inicio)` | uma linha por versão do cadastro (tipo de unidade, gestão, natureza jurídica, mantenedora, vínculo SUS, atendimento de internação e urgência) |
| `leito` | `(competencia, cnes, cod_leito, id_carga)` | retrato mensal: leitos existentes, contratados, SUS e não SUS |
| `internacao` | `(competencia, n_aih, dt_saida, id_carga)` | uma linha por AIH paga (ou por período cobrado, na longa permanência) |
| `carga` | `id_carga` | um registro por arquivo carregado: hash, contagens, tempo, status |
| `carga_rejeicao` | `(id_carga, linha)` | linhas recusadas na validação, com o motivo |

**Por que `dt_saida` está na chave da internação.** A AIH de longa permanência (`IDENT = 5`) é cobrada em períodos mensais, e o mesmo `N_AIH` aparece mais de uma vez na mesma competência. `(n_aih, competencia)` não é único nos arquivos reais; `(n_aih, dt_saida)` é. Nesses registros, `dt_internacao` é a data da internação original, que pode estar anos atrás.

**Por que `cod_leito` e não `tipo_leito`.** No CNES-LT, `TP_LEITO` é o grupo (cirúrgico, clínico, complementar…) e `CODLEITO` é a especialidade. Só `(CNES, CODLEITO)` é único por competência.

**Por que `id_carga` na chave.** Se o DATASUS republicar uma competência, ela entra como nova carga ao lado da anterior. As visões `*_vigente` mostram apenas a carga mais recente de cada fonte, UF e competência.

## Três datas por registro

| Data | Coluna | Significado |
| --- | --- | --- |
| Evento | `dt_internacao`, `dt_saida` | quando o paciente entrou e saiu |
| Processamento | `competencia` | mês em que a AIH foi apresentada e processada pelo DATASUS |
| Ingestão | `dt_ingestao` (e `carga.concluida_em`) | quando o loader gravou a linha |

## Integridade

- Chaves primárias e estrangeiras em todas as tabelas de dados: internação → estabelecimento, CID e município; leito e versão → estabelecimento; tudo → carga.
- `NOT NULL` em todos os campos obrigatórios da fonte.
- `CHECK`s de domínio:
  - formato do CNES, da AIH e do procedimento;
  - `IDENT ∈ {1, 3, 5}`;
  - quantidades e valores não negativos;
  - `dt_saida >= dt_internacao`;
  - competência sempre no primeiro dia do mês.
- **Insert-only garantido pelo banco:** uma trigger em cada tabela de dados (e em `carga`) rejeita `UPDATE` e `DELETE` com erro.
- As FKs para `carga` são `DEFERRABLE INITIALLY DEFERRED`. A linha de `carga` é gravada no fim da transação, quando as contagens já são conhecidas, sem precisar de `UPDATE`.
- Índices nas chaves de junção e de filtro: `(cnes, dt_saida)`, `dt_internacao`, `cid_principal`, `n_aih`, `id_carga`.

## Dados que a origem não guarda

O arquivo RD traz data de nascimento, CEP e CPFs (do autorizador e do gestor). Nenhum deles é necessário à pergunta de gestão, e eles não são gravados nem nos registros rejeitados (minimização, LGPD). A idade fica em `idade` e `cod_idade`.

## Preparação para a E2

O PostgreSQL sobe com `wal_level=logical`, `max_replication_slots=4` e `max_wal_senders=4`, prontos para a captura de mudanças com Debezium.
