"""Visões com a versão mais recente de cada arquivo carregado.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-07
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        -- Se o DATASUS republicar uma competência, ela vira uma nova carga e as
        -- linhas antigas continuam no banco. Estas visões mostram só a última.
        CREATE VIEW carga_vigente AS
        SELECT DISTINCT ON (fonte, uf, competencia) *
        FROM carga
        WHERE status = 'concluida' AND competencia IS NOT NULL
        ORDER BY fonte, uf, competencia, id_carga DESC;

        CREATE VIEW leito_vigente AS
        SELECT l.*
        FROM leito l
        JOIN carga_vigente c USING (id_carga);

        CREATE VIEW internacao_vigente AS
        SELECT i.*
        FROM internacao i
        JOIN carga_vigente c USING (id_carga);
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW internacao_vigente, leito_vigente, carga_vigente")
