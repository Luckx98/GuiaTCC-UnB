-- H4: o que muda no cadastro dos estabelecimentos entre competências.
-- Mede quanto histórico o CNES-ST gera e expõe ruído da própria fonte.

-- Mudanças por atributo (uma versão pode mudar mais de um atributo).
WITH v AS (
    SELECT *,
           lag(competencia_inicio) OVER w AS versao_anterior,
           lag(cod_municipio) OVER w AS municipio0, lag(tipo_unidade) OVER w AS unidade0,
           lag(tipo_gestao) OVER w AS gestao0, lag(natureza_juridica) OVER w AS natjur0,
           lag(cnpj_mantenedora) OVER w AS mantenedora0, lag(vinculo_sus) OVER w AS sus0,
           lag(atende_internacao) OVER w AS internacao0, lag(atende_urgencia) OVER w AS urgencia0
    FROM estabelecimento_versao
    WINDOW w AS (PARTITION BY cnes ORDER BY competencia_inicio)
)
SELECT count(*)                                                          AS versoes_novas,
       count(*) FILTER (WHERE unidade0 IS DISTINCT FROM tipo_unidade)        AS tipo_unidade,
       count(*) FILTER (WHERE natjur0 IS DISTINCT FROM natureza_juridica)    AS natureza_juridica,
       count(*) FILTER (WHERE urgencia0 IS DISTINCT FROM atende_urgencia)    AS atende_urgencia,
       count(*) FILTER (WHERE sus0 IS DISTINCT FROM vinculo_sus)             AS vinculo_sus,
       count(*) FILTER (WHERE internacao0 IS DISTINCT FROM atende_internacao) AS atende_internacao,
       count(*) FILTER (WHERE mantenedora0 IS DISTINCT FROM cnpj_mantenedora) AS mantenedora,
       count(*) FILTER (WHERE gestao0 IS DISTINCT FROM tipo_gestao)          AS tipo_gestao,
       count(*) FILTER (WHERE municipio0 IS DISTINCT FROM cod_municipio)     AS municipio
FROM v
WHERE versao_anterior IS NOT NULL;

-- Competências com mais versões novas: picos indicam reclassificação em massa na fonte.
SELECT competencia_inicio, count(*) AS versoes_novas
FROM estabelecimento_versao v
WHERE EXISTS (SELECT 1 FROM estabelecimento_versao a WHERE a.cnes = v.cnes AND a.competencia_inicio < v.competencia_inicio)
GROUP BY 1
ORDER BY 2 DESC
LIMIT 5;

-- Estabelecimentos cujo cadastro "vai e volta" (A -> B -> A na natureza jurídica).
SELECT count(DISTINCT cnes) AS estabelecimentos_com_ida_e_volta
FROM (
    SELECT cnes, natureza_juridica,
           lag(natureza_juridica, 1) OVER w AS anterior,
           lag(natureza_juridica, 2) OVER w AS antes_da_anterior
    FROM estabelecimento_versao
    WINDOW w AS (PARTITION BY cnes ORDER BY competencia_inicio)
) x
WHERE natureza_juridica = antes_da_anterior AND natureza_juridica <> anterior;
