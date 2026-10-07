-- H2: leitos SUS em 01/2021 x 01/2026 e internações em 2021 x 2025, por região de saúde.
-- Quais regiões perderam leitos enquanto as internações cresceram? Pergunta 2.
--
-- Só é possível porque cada competência do CNES-LT é guardada (retrato mensal),
-- em vez de ser substituída pela mais recente.
WITH regiao AS (
    SELECT DISTINCT ON (v.cnes) v.cnes,
           CASE WHEN v.cod_municipio = '530010' THEN df.cod_regiao_saude ELSE m.cod_regiao_saude END AS cod_regiao_saude
    FROM estabelecimento_versao v
    JOIN municipio m USING (cod_municipio)
    LEFT JOIN estabelecimento_regiao_df df USING (cnes)
    ORDER BY v.cnes, v.competencia_inicio DESC
),
leitos AS (
    SELECT r.cod_regiao_saude,
           sum(l.qt_sus) FILTER (WHERE l.competencia = DATE '2021-01-01') AS leitos_2021,
           sum(l.qt_sus) FILTER (WHERE l.competencia = DATE '2026-01-01') AS leitos_2026
    FROM leito_vigente l
    JOIN regiao r USING (cnes)
    WHERE l.competencia IN (DATE '2021-01-01', DATE '2026-01-01')
    GROUP BY 1
),
internacoes AS (
    SELECT r.cod_regiao_saude,
           count(*) FILTER (WHERE i.dt_saida >= DATE '2021-01-01' AND i.dt_saida < DATE '2022-01-01') AS internacoes_2021,
           count(*) FILTER (WHERE i.dt_saida >= DATE '2025-01-01' AND i.dt_saida < DATE '2026-01-01') AS internacoes_2025
    FROM internacao_vigente i
    JOIN regiao r USING (cnes)
    GROUP BY 1
)
SELECT rs.cod_uf, rs.nome AS regiao_saude,
       l.leitos_2021, l.leitos_2026,
       round(100.0 * (l.leitos_2026 - l.leitos_2021) / nullif(l.leitos_2021, 0), 1) AS var_leitos_pct,
       n.internacoes_2021, n.internacoes_2025,
       round(100.0 * (n.internacoes_2025 - n.internacoes_2021) / nullif(n.internacoes_2021, 0), 1) AS var_internacoes_pct
FROM leitos l
JOIN internacoes n USING (cod_regiao_saude)
JOIN regiao_saude rs USING (cod_regiao_saude)
ORDER BY rs.cod_uf DESC, var_leitos_pct;
