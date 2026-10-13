-- Medição do ADR 0001: modelo da origem (espelho dos arquivos x CRUD x insert-only versionado).
--
-- Roda sobre a carga completa. Os modelos alternativos são montados em tabelas
-- temporárias a partir dos dados já carregados; nada é gravado no banco.
--
-- Uso:
--   docker compose exec -T postgres psql -U leitos -d leitos < sql/adr/0001_medicao.sql

\pset footer off

-- Tempo de execução (ms) de uma consulta: mediana de 5 execuções com
-- EXPLAIN (ANALYZE, TIMING OFF). Sem TIMING OFF, a cronometragem de cada nó
-- infla consultas com laços grandes (medido: 6 s com, 0,2 s sem).
CREATE FUNCTION pg_temp.tempo_ms(consulta text) RETURNS numeric LANGUAGE plpgsql AS $$
DECLARE
    plano json;
    tempos numeric[] := '{}';
BEGIN
    FOR i IN 1..5 LOOP
        EXECUTE 'EXPLAIN (ANALYZE, TIMING OFF, FORMAT JSON) ' || consulta INTO plano;
        tempos := tempos || (plano -> 0 ->> 'Execution Time')::numeric;
    END LOOP;
    RETURN (SELECT round(percentile_cont(0.5) WITHIN GROUP (ORDER BY t)::numeric, 2) FROM unnest(tempos) t);
END;
$$;

-- Alternativa CRUD: uma linha por chave de negócio, com o valor mais recente.
CREATE TEMP TABLE crud_estabelecimento AS
SELECT DISTINCT ON (cnes) cnes, cod_municipio, tipo_unidade, tipo_gestao, natureza_juridica,
       cnpj_mantenedora, vinculo_sus, atende_internacao, atende_urgencia
FROM estabelecimento_versao
ORDER BY cnes, competencia_inicio DESC;
ALTER TABLE crud_estabelecimento ADD PRIMARY KEY (cnes);

CREATE TEMP TABLE crud_leito AS
SELECT DISTINCT ON (cnes, cod_leito) cnes, cod_leito, tipo_leito, qt_existente, qt_contratado, qt_sus, qt_nao_sus
FROM leito_vigente
ORDER BY cnes, cod_leito, competencia DESC;
ALTER TABLE crud_leito ADD PRIMARY KEY (cnes, cod_leito);

ANALYZE crud_estabelecimento;
ANALYZE crud_leito;

\echo
\echo '== M1. Linhas guardadas por alternativa'
WITH lidos AS (
    SELECT fonte, sum(linhas_lidas) AS linhas FROM carga_vigente GROUP BY fonte
)
SELECT 'CNES-ST (estabelecimentos)' AS fonte,
       (SELECT linhas FROM lidos WHERE fonte = 'CNES_ST')                         AS espelho_dos_arquivos,
       (SELECT count(*) FROM crud_estabelecimento)                                AS crud_estado_atual,
       (SELECT count(*) FROM estabelecimento) + (SELECT count(*) FROM estabelecimento_versao) AS insert_only_versionado
UNION ALL
SELECT 'CNES-LT (leitos)',
       (SELECT linhas FROM lidos WHERE fonte = 'CNES_LT'),
       (SELECT count(*) FROM crud_leito),
       (SELECT count(*) FROM leito)
UNION ALL
SELECT 'SIH-RD (internações)',
       (SELECT linhas FROM lidos WHERE fonte = 'SIH_RD'),
       (SELECT count(DISTINCT n_aih) FROM internacao),
       (SELECT count(*) FROM internacao);

\echo
\echo '== M2. Espaço em disco (dados + índices)'
SELECT 'estabelecimento + estabelecimento_versao (insert-only)' AS tabela,
       pg_size_pretty(pg_total_relation_size('estabelecimento') + pg_total_relation_size('estabelecimento_versao')) AS tamanho
UNION ALL
SELECT 'crud_estabelecimento (CRUD)', pg_size_pretty(pg_total_relation_size('crud_estabelecimento'))
UNION ALL
SELECT 'leito (insert-only)', pg_size_pretty(pg_total_relation_size('leito'))
UNION ALL
SELECT 'crud_leito (CRUD)', pg_size_pretty(pg_total_relation_size('crud_leito'));

\echo
\echo '== M3. O que o CRUD não consegue responder (informação perdida ao sobrescrever)'
WITH v AS (
    SELECT cnes, tipo_gestao, lag(tipo_gestao) OVER (PARTITION BY cnes ORDER BY competencia_inicio) AS anterior,
           lag(competencia_inicio) OVER (PARTITION BY cnes ORDER BY competencia_inicio) AS versao_anterior
    FROM estabelecimento_versao
)
SELECT 'mudanças de cadastro de estabelecimento sobrescritas' AS informacao,
       count(*) FILTER (WHERE versao_anterior IS NOT NULL) AS quantidade FROM v
UNION ALL
SELECT 'mudanças de gestão municipal/estadual sobrescritas',
       count(*) FILTER (WHERE anterior IS NOT NULL AND anterior <> tipo_gestao) FROM v
UNION ALL
SELECT 'retratos mensais de leitos descartados (competências anteriores)',
       (SELECT count(*) FROM leito) - (SELECT count(*) FROM crud_leito)
UNION ALL
SELECT 'registros de longa permanência colapsados numa só AIH',
       (SELECT count(*) - count(DISTINCT n_aih) FROM internacao)
UNION ALL
SELECT 'internações que chegaram depois do mês de saída (competência de chegada perdida)',
       (SELECT count(*) FROM internacao WHERE competencia > date_trunc('month', dt_saida));

\echo
\echo '== M4. Latência de consultas de estado atual (mediana de 5 execuções, ms)'
SELECT 'cadastro atual de um hospital (HRT)' AS consulta,
       pg_temp.tempo_ms($q$SELECT * FROM estabelecimento_vigencia WHERE cnes = '0010499' AND competencia_fim IS NULL$q$) AS insert_only,
       pg_temp.tempo_ms($q$SELECT * FROM crud_estabelecimento WHERE cnes = '0010499'$q$) AS crud
UNION ALL
SELECT 'estabelecimentos por tipo de gestão hoje',
       pg_temp.tempo_ms($q$SELECT tipo_gestao, count(*) FROM (SELECT DISTINCT ON (cnes) cnes, tipo_gestao FROM estabelecimento_versao ORDER BY cnes, competencia_inicio DESC) x GROUP BY 1$q$),
       pg_temp.tempo_ms($q$SELECT tipo_gestao, count(*) FROM crud_estabelecimento GROUP BY 1$q$)
UNION ALL
SELECT 'leitos SUS atuais de um hospital (HRT)',
       pg_temp.tempo_ms($q$SELECT sum(qt_sus) FROM leito_vigente WHERE cnes = '0010499' AND competencia = (SELECT max(competencia) FROM leito_vigente WHERE cnes = '0010499')$q$),
       pg_temp.tempo_ms($q$SELECT sum(qt_sus) FROM crud_leito WHERE cnes = '0010499'$q$)
UNION ALL
SELECT 'leitos SUS atuais por UF',
       pg_temp.tempo_ms($q$SELECT left(e.cod_municipio, 2), sum(l.qt_sus) FROM leito_vigente l JOIN estabelecimento_vigencia e ON e.cnes = l.cnes AND e.competencia_fim IS NULL WHERE l.competencia = (SELECT max(competencia) FROM leito) GROUP BY 1$q$),
       pg_temp.tempo_ms($q$SELECT left(e.cod_municipio, 2), sum(l.qt_sus) FROM crud_leito l JOIN crud_estabelecimento e USING (cnes) GROUP BY 1$q$);
