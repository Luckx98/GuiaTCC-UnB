-- Taxa de escrita: quanto cada competência acrescenta e quanto tempo a carga leva.

-- Por fonte e UF: linhas novas por mês e vazão da carga.
SELECT fonte,
       uf,
       round(avg(linhas_inseridas))                     AS linhas_mes_media,
       min(linhas_inseridas)                            AS linhas_mes_min,
       max(linhas_inseridas)                            AS linhas_mes_max,
       round(avg(extract(epoch FROM concluida_em - iniciada_em))::numeric, 2) AS segundos_por_arquivo,
       round(sum(linhas_lidas) / sum(extract(epoch FROM concluida_em - iniciada_em))::numeric) AS linhas_lidas_por_segundo
FROM carga_vigente
GROUP BY fonte, uf
ORDER BY fonte, uf;

-- Crescimento anual das internações (pela competência de processamento).
SELECT extract(year FROM competencia)::int AS ano,
       uf,
       count(*)                            AS competencias,
       sum(linhas_inseridas)               AS internacoes,
       round(avg(linhas_inseridas))        AS media_mes
FROM carga_vigente
WHERE fonte = 'SIH_RD'
GROUP BY 1, 2
ORDER BY 1, 2;

-- Escrita do CNES-ST: linhas lidas x versões novas (efeito do insert-only com versão por mudança).
SELECT uf,
       sum(linhas_lidas)       AS registros_lidos,
       sum(linhas_inseridas)   AS linhas_gravadas,
       round(100.0 * sum(linhas_inseridas) / sum(linhas_lidas), 1) AS pct_gravado
FROM carga_vigente
WHERE fonte = 'CNES_ST'
GROUP BY uf;

-- Rejeições por motivo.
SELECT c.fonte, r.motivo, count(*) AS linhas
FROM carga_rejeicao r
JOIN carga c USING (id_carga)
GROUP BY 1, 2
ORDER BY 3 DESC;
