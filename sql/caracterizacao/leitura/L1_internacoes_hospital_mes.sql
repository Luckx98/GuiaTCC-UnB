-- L1 (acesso pontual): internações que saíram de um hospital num mês.
-- Uso típico: o gestor abre o detalhe de um hospital. Pergunta 1 e 6.
-- Hospital: HRT (0010499), saídas de março/2024.
SELECT i.n_aih, i.dt_internacao, i.dt_saida, i.dias_permanencia, i.cid_principal, i.valor_total
FROM internacao_vigente i
WHERE i.cnes = '0010499'
  AND i.dt_saida >= DATE '2024-03-01' AND i.dt_saida < DATE '2024-04-01'
ORDER BY i.dt_saida
