-- H1: hospitais que mudaram de gestão (municipal <-> estadual) e o que aconteceu
-- com as internações nos 12 meses antes e depois. Pergunta 8.
--
-- Só é possível porque estabelecimento_versao guarda cada versão do cadastro.
-- Num modelo CRUD que sobrescreve, só restaria a gestão atual.
WITH versoes AS (
    SELECT cnes, competencia_inicio, tipo_gestao,
           lag(tipo_gestao) OVER (PARTITION BY cnes ORDER BY competencia_inicio) AS gestao_anterior
    FROM estabelecimento_versao
),
mudancas AS (
    SELECT cnes, competencia_inicio AS mudou_em, gestao_anterior, tipo_gestao AS gestao_nova
    FROM versoes
    WHERE gestao_anterior IS NOT NULL AND gestao_anterior <> tipo_gestao
)
SELECT m.cnes,
       left(v.cod_municipio, 2)  AS uf,
       mu.nome                   AS municipio,
       m.mudou_em,
       m.gestao_anterior || ' -> ' || m.gestao_nova AS gestao,
       round(count(*) FILTER (WHERE i.competencia >= m.mudou_em - interval '12 months' AND i.competencia < m.mudou_em) / 12.0, 1)
           AS internacoes_mes_antes,
       round(count(*) FILTER (WHERE i.competencia >= m.mudou_em AND i.competencia < m.mudou_em + interval '12 months') / 12.0, 1)
           AS internacoes_mes_depois
FROM mudancas m
JOIN estabelecimento_versao v ON v.cnes = m.cnes AND v.competencia_inicio = m.mudou_em
JOIN municipio mu ON mu.cod_municipio = v.cod_municipio
JOIN internacao_vigente i ON i.cnes = m.cnes
GROUP BY 1, 2, 3, 4, 5
ORDER BY count(*) DESC;
