-- Volume armazenado: linhas, tamanho dos dados e dos índices, bytes por linha.

SELECT relname                                          AS tabela,
       n_live_tup                                       AS linhas,
       pg_size_pretty(pg_table_size(relid))             AS dados,
       pg_size_pretty(pg_indexes_size(relid))           AS indices,
       pg_size_pretty(pg_total_relation_size(relid))    AS total,
       round(pg_total_relation_size(relid)::numeric / nullif(n_live_tup, 0)) AS bytes_por_linha
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

SELECT pg_size_pretty(pg_database_size(current_database())) AS banco_total;

-- Volume por fonte e UF (dados efetivamente gravados).
SELECT fonte,
       uf,
       count(*)                AS arquivos,
       min(competencia)        AS de,
       max(competencia)        AS ate,
       sum(linhas_lidas)       AS lidas,
       sum(linhas_inseridas)   AS inseridas,
       sum(linhas_rejeitadas)  AS rejeitadas,
       pg_size_pretty(sum(tamanho_bytes)) AS arquivos_brutos
FROM carga_vigente
GROUP BY fonte, uf
ORDER BY fonte, uf;
