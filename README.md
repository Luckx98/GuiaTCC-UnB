# GuiaOrientador-UnB

O **GuiaOrientador-UnB** é uma plataforma de apoio à escolha de temas e orientadores de trabalhos acadêmicos na Universidade de Brasília. O projeto busca reduzir a distância entre estudantes e docentes, reunindo informações acadêmicas que normalmente ficam dispersas entre departamentos, programas e diferentes fontes institucionais.

O público principal são estudantes que estão definindo um tema de TCC ou monografia, procurando orientação acadêmica ou buscando oportunidades de iniciação científica.

## Visão geral

O estudante informa um tema ou uma área de interesse. A plataforma organiza dados públicos sobre docentes e programas acadêmicos para ajudar a identificar pessoas e áreas relacionadas à busca.

O projeto combina uma aplicação web com uma pipeline de dados responsável por coletar, tratar, validar e armazenar as informações usadas nas consultas.

## Como funciona

1. Dados acadêmicos públicos são obtidos de fontes oficiais.
2. A pipeline seleciona os campos necessários, normaliza os registros e evita duplicações.
3. As informações são armazenadas em um banco relacional versionado por migrações.
4. A API disponibiliza os dados para a interface e para os módulos de busca.
5. O estudante consulta docentes e áreas relacionadas ao seu tema de interesse.

## Componentes

| Componente | Responsabilidade |
| --- | --- |
| Frontend | Interface de consulta e interação com o estudante |
| FastAPI | API e regras da aplicação |
| PostgreSQL | Cadastro relacional de docentes, programas e demais entidades |
| pgvector | Suporte à evolução da busca por similaridade semântica |
| Pipeline de dados | Download, transformação, validação e carga das fontes públicas |
| Alembic | Versionamento e execução das mudanças do banco |
| Docker Compose | Inicialização reproduzível dos serviços |

## Equipe

| Nome                              | Papel no pipeline de dados                              |
| --------------------------------- | ------------------------------------------------------- |
| Lucas Macedo Barboza              | Integrante                                              |
| Caetano Santos Lucio              | Engenharia de dados, embeddings e runtime do assistente |
| Cairo Florenço                    | Integrante                                              |
| Leonardo Sobrinho                 | Integrante                                              |
| Carlos Eduardo Mendes de Mesquita | Integrante                                              |
| Bruna                             | Integrante                                              |
| Lais                              | Integrante                                              |


## Executar o projeto

Requisito: Docker com Docker Compose. O arquivo `.env` é opcional, porque o `docker-compose.yml` já tem valores padrão. Para mudar algum valor, copie o `.env.example`.

```bash
git clone https://github.com/CA1RO/GuiaTCC-UnB.git
cd GuiaTCC-UnB
docker compose up --build
```

O Compose sobe três serviços, nesta ordem:

1. `postgres`: PostgreSQL 16 com `wal_level=logical`;
2. `migrate`: aplica as migrações de `alembic/versions/` num banco vazio;
3. `loader`: carrega as tabelas de referência e os dados do SIH/SUS e do CNES e termina com um resumo das contagens.

### Modos de carga

| Modo | O que carrega | Rede | Tempo aproximado |
| --- | --- | --- | --- |
| `amostra` (padrão) | Recorte versionado em `dados/amostra/` (DF, 01/2025) | Não precisa | < 1 min |
| `completo` | DF e GO de 01/2021 até a última competência publicada, baixados do FTP do DATASUS | Precisa | ~15 min, ~330 MB baixados |

```bash
MODO=completo docker compose up --build -d
docker compose logs -f loader      # acompanhar o progresso
docker compose ps -a               # leitos_loader "Exited (0)" = carga concluída sem falhas
```

Para limitar o recorte, use as variáveis `UFS`, `COMPETENCIA_INICIO` e `COMPETENCIA_FIM`, no formato `AAAA-MM`:

```bash
MODO=completo UFS=DF COMPETENCIA_INICIO=2024-01 COMPETENCIA_FIM=2024-12 docker compose up --build
```

A carga é idempotente: um arquivo já carregado com o mesmo conteúdo é ignorado. Se o FTP cair no meio, basta rodar o mesmo comando de novo. Os arquivos já baixados ficam no volume `leitos_dados_brutos` e não são baixados outra vez.

### Consultar o banco

Conexão: `localhost:5432`, banco `leitos`, usuário `leitos`, senha `leitos`. Se a porta 5432 já estiver em uso, suba com `POSTGRES_PORT=55432 docker compose up --build`.

```bash
docker compose exec postgres psql -U leitos -d leitos -c \
  "SELECT fonte, count(*) arquivos, sum(linhas_inseridas) inseridas, sum(linhas_rejeitadas) rejeitadas FROM carga GROUP BY 1"
```

### Testes

```bash
docker compose run --rm loader python -m unittest
```

### Recomeçar do zero

```bash
docker compose down -v   # apaga o banco e os arquivos baixados
```

## Documentação

A documentação completa do projeto, das entregas da disciplina e das decisões de modelagem está no [GitHub Pages do GuiaOrientador-UnB](https://ca1ro.github.io/GuiaTCC-UnB/).

Para visualizar o site localmente:

```bash
python -m venv .venv-docs
source .venv-docs/bin/activate
python -m pip install -r requirements-docs.txt
mkdocs serve
```

Abra <http://127.0.0.1:8000>. O MkDocs atualiza a página automaticamente quando um arquivo em `docs/` é salvo.

## Estrutura principal

```text
alembic/      migrações do banco
docs/         documentação publicada pelo MkDocs
frontend/     interface web
scripts/      cargas e medições reproduzíveis
src/api/      rotas e serviços da API
src/db/       modelos e acesso ao banco
src/pipeline/ ingestão e transformação dos dados
tests/        testes automatizados
```
