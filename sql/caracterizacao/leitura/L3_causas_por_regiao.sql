-- L3 (agregação média): principais causas de internação por região de saúde
-- no inverno de 2024 (junho a agosto). Pergunta 3 e segunda metade da pergunta de gestão.
WITH regiao AS (
    SELECT DISTINCT ON (v.cnes) v.cnes,
           CASE WHEN v.cod_municipio = '530010' THEN df.cod_regiao_saude ELSE m.cod_regiao_saude END AS cod_regiao_saude
    FROM estabelecimento_versao v
    JOIN municipio m USING (cod_municipio)
    LEFT JOIN estabelecimento_regiao_df df USING (cnes)
    ORDER BY v.cnes, v.competencia_inicio DESC
),
contagem AS (
    SELECT r.cod_regiao_saude, i.cid_principal, count(*) AS internacoes,
           row_number() OVER (PARTITION BY r.cod_regiao_saude ORDER BY count(*) DESC) AS posicao
    FROM internacao_vigente i
    JOIN regiao r USING (cnes)
    WHERE i.dt_saida >= DATE '2024-06-01' AND i.dt_saida < DATE '2024-09-01'
    GROUP BY 1, 2
)
SELECT rs.nome AS regiao_saude, c.posicao, c.cid_principal, cid.descricao, c.internacoes
FROM contagem c
JOIN regiao_saude rs USING (cod_regiao_saude)
JOIN cid ON cid.cod_cid = c.cid_principal
WHERE c.posicao <= 3
ORDER BY rs.cod_regiao_saude, c.posicao
