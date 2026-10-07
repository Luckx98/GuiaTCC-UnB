#!/usr/bin/env bash
# Roda as consultas que dependem do histórico da origem e grava em
# sql/historico/resultados/AAAA-MM-DD.txt
#
# Uso (com o compose no ar e a carga concluída):
#   sql/historico/executar.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
SAIDA="$DIR/resultados/$(date +%F).txt"
mkdir -p "$DIR/resultados"

{
    echo "# Consultas sobre o histórico da origem — $(date '+%F %T %Z')"
    for arquivo in "$DIR"/H*.sql; do
        echo
        echo "================================================================"
        echo "== $(basename "$arquivo" .sql)"
        grep '^--' "$arquivo" | head -8
        echo "================================================================"
        docker compose -f "$DIR/../../docker-compose.yml" exec -T postgres \
            psql -U "${POSTGRES_USER:-leitos}" -d "${POSTGRES_DB:-leitos}" -X -q -v ON_ERROR_STOP=1 < "$arquivo"
    done
} | tee "$SAIDA"

echo "Resultado gravado em $SAIDA" >&2
