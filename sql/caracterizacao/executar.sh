#!/usr/bin/env bash
# Mede a carga de trabalho da origem e grava em sql/caracterizacao/resultados/AAAA-MM-DD.txt
#
# Uso (com o compose no ar e a carga concluída):
#   sql/caracterizacao/executar.sh
#
# Para cada consulta de leitura: mostra as primeiras linhas do resultado e roda
# EXPLAIN (ANALYZE, BUFFERS) REPETICOES vezes. A primeira execução tende a ler
# do disco; as seguintes, do cache.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
REPETICOES="${REPETICOES:-3}"
SAIDA="$DIR/resultados/$(date +%F).txt"
mkdir -p "$DIR/resultados"

psql_() {
    docker compose -f "$DIR/../../docker-compose.yml" exec -T postgres \
        psql -U "${POSTGRES_USER:-leitos}" -d "${POSTGRES_DB:-leitos}" -X -q -v ON_ERROR_STOP=1 "$@"
}

{
    echo "# Caracterização da carga — $(date '+%F %T %Z')"
    echo "# Máquina: $(nproc) CPUs, $(free -h | awk '/^Mem:/ {print $2}') de RAM"
    psql_ -At -c "SELECT '# ' || version()"
    psql_ -At -c "SELECT '# ' || name || ' = ' || setting || coalesce(unit, '') FROM pg_settings
                  WHERE name IN ('shared_buffers', 'work_mem', 'effective_cache_size', 'max_parallel_workers_per_gather')"
    echo

    # Estatísticas do planejador atualizadas depois da carga.
    psql_ -c "ANALYZE"

    for arquivo in "$DIR"/0*.sql; do
        echo "================================================================"
        echo "== $(basename "$arquivo")"
        echo "================================================================"
        psql_ < "$arquivo"
        echo
    done

    for arquivo in "$DIR"/leitura/*.sql; do
        nome="$(basename "$arquivo" .sql)"
        consulta="$(grep -v '^--' "$arquivo")"
        echo "================================================================"
        echo "== $nome"
        grep '^--' "$arquivo"
        echo "================================================================"
        echo "-- primeiras linhas do resultado:"
        psql_ -c "SELECT * FROM ($consulta) AS resultado LIMIT 12"
        psql_ -At -c "SELECT '-- linhas no resultado: ' || count(*) FROM ($consulta) AS resultado"
        for i in $(seq 1 "$REPETICOES"); do
            plano="$(psql_ -At -c "EXPLAIN (ANALYZE, BUFFERS) $consulta")"
            echo "-- execução $i: $(grep 'Execution Time' <<< "$plano" | sed 's/^ *//')"
        done
        echo "-- plano da última execução:"
        echo "$plano"
        echo
    done
} | tee "$SAIDA"

echo "Resultado gravado em $SAIDA" >&2
