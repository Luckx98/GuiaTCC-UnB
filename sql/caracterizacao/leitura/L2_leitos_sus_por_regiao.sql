-- L2 (agregação pequena): leitos SUS por região de saúde numa competência.
-- Denominador da ocupação. Pergunta 2.
-- Região: tabela curada no DF; município do estabelecimento em GO.
WITH regiao AS (
    SELECT v.cnes,
           CASE WHEN v.cod_municipio = '530010' THEN df.cod_regiao_saude ELSE m.cod_regiao_saude END AS cod_regiao_saude
    FROM estabelecimento_vigencia v
    JOIN municipio m USING (cod_municipio)
    LEFT JOIN estabelecimento_regiao_df df USING (cnes)
    WHERE v.competencia_inicio <= DATE '2024-06-01'
      AND (v.competencia_fim IS NULL OR v.competencia_fim > DATE '2024-06-01')
)
SELECT rs.cod_uf, rs.nome AS regiao_saude, count(DISTINCT l.cnes) AS estabelecimentos, sum(l.qt_sus) AS leitos_sus
FROM leito_vigente l
JOIN regiao r USING (cnes)
JOIN regiao_saude rs USING (cod_regiao_saude)
WHERE l.competencia = DATE '2024-06-01'
GROUP BY 1, 2
ORDER BY 1, 4 DESC
