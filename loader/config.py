"""Parâmetros do loader, lidos de variáveis de ambiente."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DIR_AMOSTRA = RAIZ / "dados" / "amostra"
DIR_REFERENCIA = RAIZ / "dados" / "referencia"


def _competencia(texto: str) -> date:
    ano, mes = texto.strip().split("-")
    return date(int(ano), int(mes), 1)


@dataclass(frozen=True)
class Config:
    database_url: str
    modo: str
    ufs: tuple[str, ...]
    competencia_inicio: date
    competencia_fim: date | None
    dir_brutos: Path

    @classmethod
    def do_ambiente(cls) -> Config:
        modo = os.environ.get("MODO", "amostra").strip().lower()
        if modo not in {"amostra", "completo"}:
            raise ValueError(f"MODO deve ser 'amostra' ou 'completo', não {modo!r}")
        fim = os.environ.get("COMPETENCIA_FIM", "").strip()
        return cls(
            database_url=os.environ["DATABASE_URL"],
            modo=modo,
            ufs=tuple(uf.strip().upper() for uf in os.environ.get("UFS", "DF,GO").split(",") if uf.strip()),
            competencia_inicio=_competencia(os.environ.get("COMPETENCIA_INICIO", "2021-01")),
            competencia_fim=_competencia(fim) if fim else None,
            dir_brutos=Path(os.environ.get("DIR_BRUTOS", RAIZ / "dados" / "brutos")),
        )
