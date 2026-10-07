"""Controle de carga e bloqueio de UPDATE/DELETE (origem insert-only).

Revision ID: 0001
Revises:
Create Date: 2026-10-07
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Toda tabela de dados da origem é insert-only. A função é ligada às
    # tabelas nas migrações seguintes.
    op.execute(
        """
        CREATE FUNCTION bloquear_alteracao() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'tabela % é insert-only: % não é permitido', TG_TABLE_NAME, TG_OP;
        END;
        $$;
        """
    )

    # Uma linha por arquivo carregado. A linha 'concluida' é gravada na mesma
    # transação dos dados; a linha 'falhou' é gravada depois do rollback.
    op.execute(
        """
        CREATE TABLE carga (
            id_carga          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            fonte             TEXT        NOT NULL CHECK (fonte IN ('SIH_RD', 'CNES_ST', 'CNES_LT', 'REFERENCIA')),
            arquivo           TEXT        NOT NULL,
            uf                CHAR(2),
            competencia       DATE        CHECK (competencia = date_trunc('month', competencia)),
            sha256            CHAR(64)    NOT NULL,
            tamanho_bytes     BIGINT      NOT NULL CHECK (tamanho_bytes >= 0),
            linhas_lidas      INTEGER     NOT NULL DEFAULT 0 CHECK (linhas_lidas >= 0),
            linhas_inseridas  INTEGER     NOT NULL DEFAULT 0 CHECK (linhas_inseridas >= 0),
            linhas_rejeitadas INTEGER     NOT NULL DEFAULT 0 CHECK (linhas_rejeitadas >= 0),
            iniciada_em       TIMESTAMPTZ NOT NULL,
            concluida_em      TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
            status            TEXT        NOT NULL CHECK (status IN ('concluida', 'falhou')),
            mensagem          TEXT,
            CHECK (concluida_em >= iniciada_em)
        );

        -- Idempotência: o mesmo arquivo com o mesmo conteúdo só é carregado uma vez.
        CREATE UNIQUE INDEX uq_carga_arquivo_concluida
            ON carga (fonte, arquivo, sha256) WHERE status = 'concluida';
        CREATE INDEX idx_carga_fonte_competencia ON carga (fonte, uf, competencia);

        CREATE TABLE carga_rejeicao (
            id_carga  BIGINT  NOT NULL REFERENCES carga (id_carga) DEFERRABLE INITIALLY DEFERRED,
            linha     INTEGER NOT NULL CHECK (linha > 0),
            motivo    TEXT    NOT NULL,
            registro  JSONB   NOT NULL,
            PRIMARY KEY (id_carga, linha)
        );

        CREATE TRIGGER carga_insert_only BEFORE UPDATE OR DELETE ON carga
            FOR EACH ROW EXECUTE FUNCTION bloquear_alteracao();
        CREATE TRIGGER carga_rejeicao_insert_only BEFORE UPDATE OR DELETE ON carga_rejeicao
            FOR EACH ROW EXECUTE FUNCTION bloquear_alteracao();
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE carga_rejeicao")
    op.execute("DROP TABLE carga")
    op.execute("DROP FUNCTION bloquear_alteracao()")
