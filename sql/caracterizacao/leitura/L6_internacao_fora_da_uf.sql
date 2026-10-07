-- L6 (varredura completa): internações de pacientes residentes fora da UF do
-- hospital, por ano e UF do hospital. Pergunta 4. Lê o período inteiro.
SELECT extract(year FROM i.dt_saida)::int AS ano,
       left(i.municipio_estabelecimento, 2) AS uf_hospital,
       count(*)                               AS internacoes,
       count(*) FILTER (WHERE left(i.municipio_residencia, 2) <> left(i.municipio_estabelecimento, 2)) AS residentes_outra_uf,
       round(100.0 * count(*) FILTER (WHERE left(i.municipio_residencia, 2) <> left(i.municipio_estabelecimento, 2))
             / count(*), 1)                   AS pct_outra_uf
FROM internacao_vigente i
GROUP BY 1, 2
ORDER BY 1, 2
