"""Estabelecimentos do CNES (chave de negócio + versões por competência).

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-07
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        -- Chave de negócio: alvo das FKs de leito e internação.
        CREATE TABLE estabelecimento (
            cnes            CHAR(7)     PRIMARY KEY CHECK (cnes ~ '^[0-9]{7}$'),
            primeira_carga  BIGINT      NOT NULL REFERENCES carga (id_carga) DEFERRABLE INITIALLY DEFERRED,
            dt_ingestao     TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        -- Uma nova versão só é gravada quando algum atributo muda em relação à
        -- versão anterior (SCD tipo 2 na origem). A competência final de uma
        -- versão é a competência inicial da seguinte (ver estabelecimento_vigencia).
        CREATE TABLE estabelecimento_versao (
            cnes               CHAR(7)     NOT NULL REFERENCES estabelecimento (cnes),
            competencia_inicio DATE        NOT NULL CHECK (competencia_inicio = date_trunc('month', competencia_inicio)),
            cod_municipio      CHAR(6)     NOT NULL REFERENCES municipio (cod_municipio),
            tipo_unidade       CHAR(2)     NOT NULL,
            tipo_gestao        CHAR(1)     NOT NULL,
            natureza_juridica  CHAR(4),
            cnpj_mantenedora   CHAR(14),
            vinculo_sus        BOOLEAN,
            atende_internacao  BOOLEAN,
            atende_urgencia    BOOLEAN,
            id_carga           BIGINT      NOT NULL REFERENCES carga (id_carga) DEFERRABLE INITIALLY DEFERRED,
            dt_ingestao        TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (cnes, competencia_inicio)
        );
        CREATE INDEX idx_estabelecimento_versao_municipio ON estabelecimento_versao (cod_municipio);

        CREATE TRIGGER estabelecimento_insert_only BEFORE UPDATE OR DELETE ON estabelecimento
            FOR EACH ROW EXECUTE FUNCTION bloquear_alteracao();
        CREATE TRIGGER estabelecimento_versao_insert_only BEFORE UPDATE OR DELETE ON estabelecimento_versao
            FOR EACH ROW EXECUTE FUNCTION bloquear_alteracao();

        CREATE VIEW estabelecimento_vigencia AS
        SELECT v.*,
               lead(v.competencia_inicio) OVER (PARTITION BY v.cnes ORDER BY v.competencia_inicio)
                   AS competencia_fim
        FROM estabelecimento_versao v;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW estabelecimento_vigencia")
    op.execute("DROP TABLE estabelecimento_versao, estabelecimento")
