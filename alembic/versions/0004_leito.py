"""Leitos por estabelecimento e competência (retrato mensal do CNES LT).

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-07
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        -- id_carga faz parte da chave: se o DATASUS republicar a competência,
        -- a nova versão entra ao lado da anterior (ver leito_vigente).
        CREATE TABLE leito (
            competencia DATE        NOT NULL CHECK (competencia = date_trunc('month', competencia)),
            cnes        CHAR(7)     NOT NULL REFERENCES estabelecimento (cnes),
            cod_leito   CHAR(2)     NOT NULL CHECK (cod_leito ~ '^[0-9]{2}$'),
            tipo_leito  CHAR(1)     NOT NULL CHECK (tipo_leito ~ '^[0-9]$'),
            qt_existente SMALLINT   NOT NULL CHECK (qt_existente >= 0),
            qt_contratado SMALLINT  NOT NULL CHECK (qt_contratado >= 0),
            qt_sus      SMALLINT    NOT NULL CHECK (qt_sus >= 0),
            qt_nao_sus  SMALLINT    NOT NULL CHECK (qt_nao_sus >= 0),
            id_carga    BIGINT      NOT NULL REFERENCES carga (id_carga) DEFERRABLE INITIALLY DEFERRED,
            dt_ingestao TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (competencia, cnes, cod_leito, id_carga)
        );
        CREATE INDEX idx_leito_cnes ON leito (cnes, competencia);
        CREATE INDEX idx_leito_carga ON leito (id_carga);

        CREATE TRIGGER leito_insert_only BEFORE UPDATE OR DELETE ON leito
            FOR EACH ROW EXECUTE FUNCTION bloquear_alteracao();
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE leito")
