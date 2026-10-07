"""Internações pagas pelo SUS (SIH/SUS, AIH reduzida - RD).

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-07
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        -- Três datas por registro:
        --   evento         -> dt_internacao / dt_saida
        --   processamento  -> competencia (mês em que a AIH foi apresentada)
        --   ingestão       -> dt_ingestao (e carga.concluida_em)
        --
        -- A mesma AIH de longa permanência (ident = '5') aparece mais de uma vez
        -- na mesma competência, um registro por período cobrado; por isso
        -- dt_saida faz parte da chave. Nesses registros dt_internacao é a data
        -- da internação original, não o início do período cobrado.
        --
        -- Campos identificadores da fonte (NASC, CEP, CPF_AUT, GESTOR_CPF) não
        -- são gravados (minimização, LGPD).
        CREATE TABLE internacao (
            competencia        DATE          NOT NULL CHECK (competencia = date_trunc('month', competencia)),
            n_aih              CHAR(13)      NOT NULL CHECK (n_aih ~ '^[0-9]{13}$'),
            dt_saida           DATE          NOT NULL,
            id_carga           BIGINT        NOT NULL REFERENCES carga (id_carga) DEFERRABLE INITIALLY DEFERRED,
            ident              CHAR(1)       NOT NULL CHECK (ident IN ('1', '3', '5')),
            cnes               CHAR(7)       NOT NULL REFERENCES estabelecimento (cnes),
            dt_internacao      DATE          NOT NULL,
            dias_permanencia   SMALLINT      NOT NULL CHECK (dias_permanencia >= 0),
            qt_diarias         SMALLINT      NOT NULL CHECK (qt_diarias >= 0),
            especialidade      CHAR(2)       NOT NULL,
            carater_internacao CHAR(2),
            complexidade       CHAR(2),
            cid_principal      VARCHAR(4)    NOT NULL REFERENCES cid (cod_cid),
            cid_secundario     VARCHAR(4),
            procedimento       CHAR(10)      NOT NULL CHECK (procedimento ~ '^[0-9]{10}$'),
            dias_uti           SMALLINT      NOT NULL CHECK (dias_uti >= 0),
            marca_uti          CHAR(2),
            valor_total        NUMERIC(12,2) NOT NULL CHECK (valor_total >= 0),
            valor_uti          NUMERIC(12,2) NOT NULL CHECK (valor_uti >= 0),
            idade              SMALLINT      NOT NULL CHECK (idade >= 0),
            cod_idade          CHAR(1)       NOT NULL,
            sexo               CHAR(1)       NOT NULL,
            raca_cor           CHAR(2),
            municipio_residencia     CHAR(6) NOT NULL REFERENCES municipio (cod_municipio),
            municipio_estabelecimento CHAR(6) NOT NULL REFERENCES municipio (cod_municipio),
            obito              BOOLEAN       NOT NULL,
            tipo_gestao        CHAR(1),
            dt_ingestao        TIMESTAMPTZ   NOT NULL DEFAULT now(),
            PRIMARY KEY (competencia, n_aih, dt_saida, id_carga),
            CHECK (dt_saida >= dt_internacao)
        );
        CREATE INDEX idx_internacao_carga ON internacao (id_carga);
        CREATE INDEX idx_internacao_cnes_saida ON internacao (cnes, dt_saida);
        CREATE INDEX idx_internacao_dt_internacao ON internacao (dt_internacao);
        CREATE INDEX idx_internacao_cid ON internacao (cid_principal);
        CREATE INDEX idx_internacao_n_aih ON internacao (n_aih);

        CREATE TRIGGER internacao_insert_only BEFORE UPDATE OR DELETE ON internacao
            FOR EACH ROW EXECUTE FUNCTION bloquear_alteracao();
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE internacao")
