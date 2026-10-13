# Carga reprodutível

Um comando cria o banco, aplica as migrações e carrega os dados, sem passo manual nem arquivo baixado à mão:

```bash
git clone https://github.com/Luckx98/GuiaTCC-UnB.git
cd GuiaTCC-UnB
docker compose up --build
```

O `.env` é opcional; o `docker-compose.yml` tem valores padrão.

## Dois modos

| Modo | O que carrega | Rede | Tempo medido |
| --- | --- | --- | --- |
| `amostra` (padrão) | recorte versionado em `dados/amostra/` (2,3 MB): SIH, CNES-ST e CNES-LT do DF de 01/2025, mais as tabelas de referência | não precisa | < 1 min |
| `completo` | DF e GO de 01/2021 até a última competência publicada, baixados do FTP do DATASUS | precisa | 14 min 20 s (406 arquivos, 332 MB) |

```bash
MODO=completo docker compose up --build -d
docker compose logs -f loader
```

O recorte também pode ser limitado por `UFS`, `COMPETENCIA_INICIO` e `COMPETENCIA_FIM`.

## O que o loader faz

O loader roda em Python 3.11 (`loader/`) e executa estes passos:

1. **Seleciona os arquivos.** No modo completo, lista o FTP do DATASUS e filtra por UF e período. No modo amostra, usa `dados/amostra/`.
2. **Baixa** com até 5 tentativas e retomada do ponto em que parou (arquivo `.part`). Os arquivos ficam no volume `leitos_dados_brutos`.
3. **Calcula o sha256.** Um arquivo já carregado com o mesmo conteúdo é ignorado.
4. **Descompacta o `.dbc`** com `datasus-dbc` e lê o DBF com um leitor próprio. O `dbfread` não lê o cabeçalho do CNES-ST, que termina com `0x00`, e o PySUS não instala em Python recente.
5. **Valida linha a linha:** chaves, datas, códigos de CID e município, quantidades e coerência da competência. Uma linha inválida vai para `carga_rejeicao` com o motivo, e o resto do arquivo segue.
6. **Grava com `COPY`, numa transação por arquivo:** ou o arquivo entra inteiro, ou não entra. A ordem é imposta pelas FKs: referências, depois CNES-ST, CNES-LT e SIH-RD.
7. **Registra a carga** em `carga`: linhas lidas, inseridas e rejeitadas, tempo e status. Uma falha também fica registrada (`status = 'falhou'`), com a mensagem.

## Idempotência e retomada

- Rodar o loader de novo sobre a base completa levou 9,5 s e ignorou os 406 arquivos já carregados.
- Se o FTP cair no meio, basta repetir o comando. Os arquivos já baixados não são baixados de novo, e os já gravados são ignorados pelo hash.

## Rejeições

Na carga completa, 145 das 3.670.019 internações lidas foram rejeitadas (0,004%), todas por CID principal ausente da tabela CID-10 do DATASUS. São estágios da doença renal crônica (N18.2 a N18.5) e códigos de COVID-19 e pós-COVID (U04, U09, U10). As rejeições ficam em `carga_rejeicao` e podem ser contadas por competência:

```sql
SELECT c.competencia, c.uf, r.registro->>'DIAG_PRINC' AS cid, count(*)
FROM carga_rejeicao r JOIN carga c USING (id_carga)
GROUP BY 1, 2, 3 ORDER BY 1, 2;
```

## Verificação

```bash
docker compose exec postgres psql -U leitos -d leitos -c \
  "SELECT fonte, count(*) arquivos, sum(linhas_inseridas) inseridas, sum(linhas_rejeitadas) rejeitadas FROM carga GROUP BY 1"
docker compose run --rm loader python -m unittest   # 11 testes do loader
```

A reprodutibilidade foi testada com `git clone` do repositório numa pasta nova, sem `.env`. As migrações rodaram, a amostra carregou e o loader terminou com código 0.
