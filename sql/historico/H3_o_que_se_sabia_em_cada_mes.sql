-- H3: quantas saídas de janeiro/2025 a base conhecia ao final de cada competência.
-- Responde "o que a Central de Regulação via naquela época" e mostra o represamento
-- de um mês concreto.
--
-- Só é possível porque cada internação guarda a competência em que chegou
-- (data de processamento) além da data do evento. Se a carga sobrescrevesse
-- pela AIH, não haveria como reconstruir a base de uma data passada.
SELECT c.uf,
       i.competencia                  AS base_ao_final_de,
       count(*)                       AS chegaram_nesta_competencia,
       sum(count(*)) OVER (PARTITION BY c.uf ORDER BY i.competencia) AS conhecidas_ate_entao,
       round(100.0 * sum(count(*)) OVER (PARTITION BY c.uf ORDER BY i.competencia)
             / sum(count(*)) OVER (PARTITION BY c.uf), 1) AS pct_do_total_atual
FROM internacao_vigente i
JOIN carga c USING (id_carga)
WHERE i.dt_saida >= DATE '2025-01-01' AND i.dt_saida < DATE '2025-02-01'
GROUP BY c.uf, i.competencia
ORDER BY c.uf, i.competencia;
