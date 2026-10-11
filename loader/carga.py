"""Registro de cargas: idempotência por hash e transação única por arquivo."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

import psycopg

from loader.ftp import sha256

log = logging.getLogger(__name__)


@dataclass
class Resultado:
    """O que o processamento de um arquivo produziu antes de gravar."""

    linhas_lidas: int = 0
    rejeicoes: list[tuple[int, str, dict]] = field(default_factory=list)

    def rejeitar(self, linha: int, motivo: str, registro: dict) -> None:
        self.rejeicoes.append((linha, motivo, registro))


@dataclass(frozen=True)
class Arquivo:
    fonte: str
    caminho: Path
    uf: str | None = None
    competencia: date | None = None


def ja_carregado(conexao: psycopg.Connection, arquivo: Arquivo, hash_arquivo: str) -> bool:
    linha = conexao.execute(
        "SELECT 1 FROM carga WHERE fonte = %s AND arquivo = %s AND sha256 = %s AND status = 'concluida'",
        (arquivo.fonte, arquivo.caminho.name, hash_arquivo),
    ).fetchone()
    return linha is not None


def carregar_arquivo(
    conexao: psycopg.Connection,
    arquivo: Arquivo,
    processar: Callable[[psycopg.Connection, int], tuple[Resultado, int]],
) -> bool:
    """Executa `processar` numa transação e registra a carga.

    `processar(conexao, id_carga)` grava os dados e devolve (resultado, linhas_inseridas).
    Devolve False se o arquivo já tinha sido carregado com o mesmo conteúdo.
    """
    hash_arquivo = sha256(arquivo.caminho)
    if ja_carregado(conexao, arquivo, hash_arquivo):
        log.info("%s já carregado (mesmo sha256); ignorado", arquivo.caminho.name)
        return False

    iniciada_em = datetime.now(timezone.utc)
    valores = (
        arquivo.fonte,
        arquivo.caminho.name,
        arquivo.uf,
        arquivo.competencia,
        hash_arquivo,
        arquivo.caminho.stat().st_size,
        iniciada_em,
    )
    try:
        with conexao.transaction():
            # As contagens só são conhecidas no fim e carga não aceita UPDATE:
            # reserva o id, grava os dados e insere a carga por último. As FKs
            # para carga são verificadas no COMMIT (DEFERRABLE INITIALLY DEFERRED).
            id_carga = conexao.execute(
                "SELECT nextval(pg_get_serial_sequence('carga', 'id_carga'))"
            ).fetchone()[0]
            resultado, inseridas = processar(conexao, id_carga)
            conexao.execute(
                """
                INSERT INTO carga (id_carga, fonte, arquivo, uf, competencia, sha256, tamanho_bytes,
                                   iniciada_em, linhas_lidas, linhas_inseridas, linhas_rejeitadas, status)
                OVERRIDING SYSTEM VALUE
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'concluida')
                """,
                (id_carga, *valores, resultado.linhas_lidas, inseridas, len(resultado.rejeicoes)),
            )
            if resultado.rejeicoes:
                with conexao.cursor().copy(
                    "COPY carga_rejeicao (id_carga, linha, motivo, registro) FROM STDIN"
                ) as copia:
                    for linha, motivo, registro in resultado.rejeicoes:
                        copia.write_row((id_carga, linha, motivo, json.dumps(registro, ensure_ascii=False)))
    except Exception as erro:
        conexao.execute(
            """
            INSERT INTO carga (fonte, arquivo, uf, competencia, sha256, tamanho_bytes, iniciada_em,
                               status, mensagem)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'falhou', %s)
            """,
            (*valores, f"{type(erro).__name__}: {erro}"[:2000]),
        )
        conexao.commit()
        raise

    log.info(
        "%s: %d lidas, %d inseridas, %d rejeitadas",
        arquivo.caminho.name,
        resultado.linhas_lidas,
        inseridas,
        len(resultado.rejeicoes),
    )
    return True
