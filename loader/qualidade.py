"""Verificações de qualidade sobre os dados já carregados.

Roda no fim de toda carga e também sozinho:
    docker compose run --rm loader python -m loader.qualidade

Cada verificação é uma consulta que devolve as linhas que violam a regra.
- erro:   a carga está incompleta ou incoerente; o loader termina com código 1.
- alerta: característica da fonte que a análise precisa conhecer; só informa.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass

import psycopg

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Verificacao:
    codigo: str
    descricao: str
    severidade: str  # "erro" ou "alerta"
    consulta: str


VERIFICACOES = (
    Verificacao(
        "Q01", "carga de arquivo que falhou e nunca foi concluída", "erro",
        """
        SELECT c.fonte, c.arquivo, c.mensagem FROM carga c
        WHERE c.status = 'falhou'
          AND NOT EXISTS (SELECT 1 FROM carga d WHERE d.status = 'concluida' AND d.arquivo = c.arquivo)
        """,
    ),
    Verificacao(
        "Q02", "competência faltando na série de uma fonte e UF", "erro",
        """
        WITH limites AS (
            SELECT fonte, uf, min(competencia) AS de, max(competencia) AS ate
            FROM carga_vigente WHERE fonte <> 'REFERENCIA' GROUP BY 1, 2
        )
        SELECT l.fonte, l.uf, m::date AS competencia_faltando
        FROM limites l, generate_series(l.de, l.ate, interval '1 month') AS m
        WHERE NOT EXISTS (
            SELECT 1 FROM carga_vigente c WHERE c.fonte = l.fonte AND c.uf = l.uf AND c.competencia = m
        )
        """,
    ),
    Verificacao(
        "Q03", "arquivo com mais de 1% das linhas rejeitadas", "erro",
        """
        SELECT fonte, arquivo, linhas_lidas, linhas_rejeitadas FROM carga_vigente
        WHERE linhas_lidas > 0 AND linhas_rejeitadas > 0.01 * linhas_lidas
        """,
    ),
    Verificacao(
        "Q04", "internação contada duas vezes nas visões vigentes", "erro",
        """
        SELECT competencia, n_aih, dt_saida, count(*) FROM internacao_vigente
        GROUP BY 1, 2, 3 HAVING count(*) > 1
        """,
    ),
    Verificacao(
        "Q05", "internação com saída depois do mês da competência", "erro",
        """
        SELECT competencia, n_aih, dt_saida FROM internacao_vigente
        WHERE dt_saida >= competencia + interval '1 month'
        """,
    ),
    Verificacao(
        "Q06", "hospital do DF com internação e sem região de saúde "
        "(completar dados/referencia/estabelecimento_regiao_saude_df.csv)", "erro",
        """
        SELECT DISTINCT i.cnes FROM internacao_vigente i
        WHERE i.municipio_estabelecimento = '530010'
          AND NOT EXISTS (SELECT 1 FROM estabelecimento_regiao_df r WHERE r.cnes = i.cnes)
        """,
    ),
    Verificacao(
        "Q07", "leitos SUS acima dos leitos existentes", "alerta",
        "SELECT competencia, cnes, cod_leito, qt_sus, qt_existente FROM leito_vigente WHERE qt_sus > qt_existente",
    ),
    Verificacao(
        "Q08", "leitos SUS + não SUS diferente dos leitos existentes", "alerta",
        """
        SELECT competencia, cnes, cod_leito, qt_sus, qt_nao_sus, qt_existente FROM leito_vigente
        WHERE qt_sus + qt_nao_sus <> qt_existente
        """,
    ),
    Verificacao(
        "Q09", "dias de permanência incoerentes com as datas (internação normal)", "alerta",
        """
        SELECT competencia, n_aih, dt_internacao, dt_saida, dias_permanencia FROM internacao_vigente
        WHERE ident = '1' AND abs(dias_permanencia - (dt_saida - dt_internacao)) > 1
        """,
    ),
    Verificacao(
        "Q10", "internação em hospital sem leito SUS no mês da saída (sem denominador de ocupação)", "alerta",
        """
        WITH meses AS MATERIALIZED (
                 SELECT cnes, date_trunc('month', dt_saida)::date AS mes, count(*) AS internacoes
                 FROM internacao_vigente GROUP BY 1, 2
             ),
             com_leito_sus AS MATERIALIZED (
                 SELECT DISTINCT cnes, competencia FROM leito_vigente WHERE qt_sus > 0
             ),
             periodo AS (SELECT min(competencia) AS de, max(competencia) AS ate FROM leito)
        SELECT m.cnes, m.mes, m.internacoes FROM meses m, periodo p
        WHERE m.mes BETWEEN p.de AND p.ate
          AND NOT EXISTS (SELECT 1 FROM com_leito_sus c WHERE c.cnes = m.cnes AND c.competencia = m.mes)
        """,
    ),
    Verificacao(
        "Q11", "competência do SIH com menos de 60% da mediana de internações da UF (arquivo truncado?)", "alerta",
        """
        WITH s AS (SELECT uf, competencia, linhas_inseridas FROM carga_vigente WHERE fonte = 'SIH_RD'),
             mediana AS (SELECT uf, percentile_cont(0.5) WITHIN GROUP (ORDER BY linhas_inseridas) AS m FROM s GROUP BY uf)
        SELECT s.uf, s.competencia, s.linhas_inseridas, mediana.m FROM s JOIN mediana USING (uf)
        WHERE s.linhas_inseridas < 0.6 * mediana.m
        """,
    ),
    Verificacao(
        "Q12", "idade acima de 110 anos", "alerta",
        "SELECT competencia, n_aih, idade FROM internacao_vigente WHERE cod_idade = '4' AND idade > 110",
    ),
    Verificacao(
        "Q13", "internação com valor total zero", "alerta",
        "SELECT competencia, n_aih, cnes, procedimento FROM internacao_vigente WHERE valor_total = 0",
    ),
)


def verificar(conexao: psycopg.Connection) -> int:
    """Roda todas as verificações, registra o resultado e devolve o número de erros."""
    erros = 0
    for v in VERIFICACOES:
        total = conexao.execute(f"SELECT count(*) FROM ({v.consulta}) AS violacoes").fetchone()[0]
        if total == 0:
            log.info("[ok]     %s %s", v.codigo, v.descricao)
            continue
        exemplos = conexao.execute(f"SELECT * FROM ({v.consulta}) AS violacoes LIMIT 3").fetchall()
        nivel = logging.ERROR if v.severidade == "erro" else logging.WARNING
        log.log(nivel, "[%s] %s %s: %d (ex.: %s)", v.severidade, v.codigo, v.descricao, total, exemplos)
        if v.severidade == "erro":
            erros += 1
    return erros


def main() -> int:
    import os

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conexao:
        erros = verificar(conexao)
    if erros:
        log.error("%d verificação(ões) de qualidade com erro", erros)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
