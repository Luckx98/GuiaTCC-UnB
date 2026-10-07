-- Represamento: quantos meses depois da saída do paciente a AIH chega ao SIH.
-- Mede a defasagem da fonte e define a janela de maturidade (a partir de
-- quantos meses um mês de evento pode ser considerado completo).
--
-- Considera só saídas de 2021 a 2024, que já tiveram tempo de chegar.

WITH atraso AS (
    SELECT (extract(year FROM age(competencia, date_trunc('month', dt_saida))) * 12
          + extract(month FROM age(competencia, date_trunc('month', dt_saida))))::int AS meses
    FROM internacao_vigente
    WHERE dt_saida >= DATE '2021-01-01' AND dt_saida < DATE '2025-01-01'
)
SELECT CASE WHEN meses >= 7 THEN '7+' ELSE meses::text END AS meses_apos_saida,
       count(*)                                          AS internacoes,
       round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS pct,
       round(100.0 * sum(count(*)) OVER (ORDER BY min(meses)) / sum(count(*)) OVER (), 2) AS pct_acumulado
FROM atraso
GROUP BY 1
ORDER BY min(meses);

-- Meses recentes ainda incompletos: internações por mês de saída, por UF.
SELECT date_trunc('month', i.dt_saida)::date AS mes_saida,
       c.uf,
       count(*) AS internacoes
FROM internacao_vigente i
JOIN carga c USING (id_carga)
WHERE i.dt_saida >= DATE '2025-07-01'
GROUP BY 1, 2
ORDER BY 1, 2;
