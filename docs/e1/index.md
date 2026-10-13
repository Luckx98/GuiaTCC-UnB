# Entrega 1 — Fonte OLTP modelada e populada

A E1 coloca de pé o sistema de origem do Leitos SUS-DF: um PostgreSQL com esquema versionado, populado automaticamente com as internações do SIH/SUS e o cadastro de estabelecimentos e leitos do CNES, para o DF e Goiás, de janeiro de 2021 até a última competência publicada.

## Onde está cada requisito

| Requisito da E1 | Onde está | Evidência no repositório |
| --- | --- | --- |
| Domínio e pergunta de gestão em uma frase | [Domínio e pergunta](01-dominio-e-pergunta.md) | — |
| Esquema versionado com migrações executáveis do zero | [Esquema e migrações](02-esquema-e-migracoes.md) | `alembic/versions/0001`–`0006` |
| Carga reprodutível com um comando | [Carga reprodutível](03-carga-reprodutivel.md) | `docker-compose.yml`, `loader/`, `dados/amostra/` |
| Volume que torne a plataforma interessante | [Volume](04-volume.md) | tabela `carga` |
| Caracterização da carga (passo 1) | [Caracterização da carga](05-caracterizacao-da-carga.md) | `sql/caracterizacao/` |
| Como a origem trata histórico | [Histórico da origem](06-historico-da-origem.md) | `sql/historico/` |
| ADR da modelagem da origem | [ADR 0001](../adr/0001-origem-insert-only-versionada-por-competencia.md) | `sql/adr/0001_medicao.sql` |
| README para subir com Docker Compose | [README](https://github.com/Luckx98/Leitos-SUS-DF#executar-o-projeto) | — |

## Resultado em números

| Medida | Valor |
| --- | ---: |
| Arquivos públicos carregados | 406 |
| Internações (SIH/SUS) | 3.669.874 |
| Linhas de leito por competência (CNES-LT) | 240.132 |
| Estabelecimentos / versões de cadastro (CNES-ST) | 26.048 / 30.919 |
| Linhas rejeitadas na validação | 145 (0,004%) |
| Tempo da carga completa | 14 min 20 s |
| Tamanho do banco | 1,16 GB |

`docker compose up` sem configuração carrega um recorte versionado (DF, 01/2025) em menos de um minuto e sem acesso à rede. `MODO=completo` baixa o período inteiro do FTP do DATASUS.
