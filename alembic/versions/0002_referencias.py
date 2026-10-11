"""Tabelas de referência: regiões de saúde, municípios, CID-10 e leitos.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-07
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        -- Códigos do DATASUS (TAB_SIH: xx_regsaud.cnv), ex.: 52001, 53006.
        CREATE TABLE regiao_saude (
            cod_regiao_saude CHAR(5) PRIMARY KEY CHECK (cod_regiao_saude ~ '^[0-9]{5}$'),
            nome             TEXT    NOT NULL,
            cod_uf           CHAR(2) NOT NULL
        );

        -- Código de município com 6 dígitos, como nos arquivos do DATASUS.
        CREATE TABLE municipio (
            cod_municipio    CHAR(6) PRIMARY KEY CHECK (cod_municipio ~ '^[0-9]{6}$'),
            nome             TEXT    NOT NULL,
            cod_uf           CHAR(2) NOT NULL,
            cod_regiao_saude CHAR(5) REFERENCES regiao_saude (cod_regiao_saude)
        );
        CREATE INDEX idx_municipio_regiao ON municipio (cod_regiao_saude);

        CREATE TABLE cid (
            cod_cid   VARCHAR(4) PRIMARY KEY CHECK (cod_cid ~ '^[A-Z][0-9]{2}[0-9X]?$'),
            descricao TEXT       NOT NULL
        );

        -- No DF todo estabelecimento tem o mesmo município (530010), por isso a
        -- região de saúde vem de uma tabela curada (dados/referencia).
        CREATE TABLE estabelecimento_regiao_df (
            cnes                  CHAR(7) PRIMARY KEY CHECK (cnes ~ '^[0-9]{7}$'),
            nome_fantasia         TEXT    NOT NULL,
            regiao_administrativa TEXT    NOT NULL,
            cod_regiao_saude      CHAR(5) NOT NULL REFERENCES regiao_saude (cod_regiao_saude),
            observacao            TEXT
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE estabelecimento_regiao_df, cid, municipio, regiao_saude")
