-- L5 (agregação grande): tempo médio de permanência e custo médio por hospital e
-- especialidade, 2024 inteiro. Perguntas 6 e 7.
SELECT i.cnes, i.especialidade,
       count(*)                                AS internacoes,
       round(avg(i.dias_permanencia), 1)       AS permanencia_media,
       round(avg(i.valor_total), 2)            AS custo_medio
FROM internacao_vigente i
WHERE i.dt_saida >= DATE '2024-01-01' AND i.dt_saida < DATE '2025-01-01'
GROUP BY 1, 2
HAVING count(*) >= 30
ORDER BY permanencia_media DESC
LIMIT 20
