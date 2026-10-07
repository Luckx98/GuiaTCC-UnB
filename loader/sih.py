"""SIH/SUS: AIH reduzida (RD), um arquivo por UF e competência."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import psycopg

from loader.carga import Arquivo, Resultado
from loader.dbf import ler_dbc

COLUNAS = (
    "competencia, n_aih, dt_saida, id_carga, ident, cnes, dt_internacao, dias_permanencia, qt_diarias, "
    "especialidade, carater_internacao, complexidade, cid_principal, cid_secundario, procedimento, "
    "dias_uti, marca_uti, valor_total, valor_uti, idade, cod_idade, sexo, raca_cor, "
    "municipio_residencia, municipio_estabelecimento, obito, tipo_gestao"
)


class Rejeitado(Exception):
    pass


def _data(valor: str, campo: str) -> date:
    try:
        return datetime.strptime(valor, "%Y%m%d").date()
    except ValueError:
        raise Rejeitado(f"{campo} inválida") from None


def _inteiro(valor: str, campo: str) -> int:
    try:
        numero = int(valor or 0)
    except ValueError:
        raise Rejeitado(f"{campo} não numérico") from None
    if numero < 0:
        raise Rejeitado(f"{campo} negativo")
    return numero


def _decimal(valor: str, campo: str) -> Decimal:
    try:
        numero = Decimal(valor or "0")
    except InvalidOperation:
        raise Rejeitado(f"{campo} não numérico") from None
    if numero < 0:
        raise Rejeitado(f"{campo} negativo")
    return numero


def _opcional(valor: str) -> str | None:
    return valor or None


@dataclass(frozen=True)
class Contexto:
    competencia: date
    id_carga: int
    estabelecimentos: set[str]
    municipios: set[str]
    cids: set[str]


def converter(r: dict, ctx: Contexto) -> tuple:
    """Valida um registro do RD e devolve a linha de internacao; levanta Rejeitado."""
    if f"{r['ANO_CMPT']}{r['MES_CMPT']}" != f"{ctx.competencia:%Y%m}":
        raise Rejeitado("competência do registro diferente da do arquivo")
    if not re.fullmatch(r"[0-9]{13}", r["N_AIH"]):
        raise Rejeitado("N_AIH inválido")
    if r["IDENT"] not in {"1", "3", "5"}:
        raise Rejeitado("IDENT inválido")
    if r["CNES"] not in ctx.estabelecimentos:
        raise Rejeitado("CNES sem cadastro")
    if r["DIAG_PRINC"] not in ctx.cids:
        raise Rejeitado("CID principal desconhecido")
    if not re.fullmatch(r"[0-9]{10}", r["PROC_REA"]):
        raise Rejeitado("procedimento inválido")
    if r["MUNIC_RES"] not in ctx.municipios or r["MUNIC_MOV"] not in ctx.municipios:
        raise Rejeitado("município desconhecido")
    if r["MORTE"] not in {"0", "1"}:
        raise Rejeitado("MORTE inválido")
    dt_inter, dt_saida = _data(r["DT_INTER"], "DT_INTER"), _data(r["DT_SAIDA"], "DT_SAIDA")
    if dt_saida < dt_inter:
        raise Rejeitado("DT_SAIDA anterior a DT_INTER")
    cid_secundario = r["DIAG_SECUN"] if r["DIAG_SECUN"] not in {"", "0000"} else None
    return (
        ctx.competencia,
        r["N_AIH"],
        dt_saida,
        ctx.id_carga,
        r["IDENT"],
        r["CNES"],
        dt_inter,
        _inteiro(r["DIAS_PERM"], "DIAS_PERM"),
        _inteiro(r["QT_DIARIAS"], "QT_DIARIAS"),
        r["ESPEC"],
        _opcional(r["CAR_INT"]),
        _opcional(r["COMPLEX"]),
        r["DIAG_PRINC"],
        cid_secundario,
        r["PROC_REA"],
        _inteiro(r["UTI_MES_TO"], "UTI_MES_TO"),
        _opcional(r["MARCA_UTI"]),
        _decimal(r["VAL_TOT"], "VAL_TOT"),
        _decimal(r["VAL_UTI"], "VAL_UTI"),
        _inteiro(r["IDADE"], "IDADE"),
        r["COD_IDADE"],
        r["SEXO"],
        _opcional(r["RACA_COR"]),
        r["MUNIC_RES"],
        r["MUNIC_MOV"],
        r["MORTE"] == "1",
        _opcional(r["GESTAO"]),
    )


def processar_rd(conexao: psycopg.Connection, id_carga: int, arquivo: Arquivo) -> tuple[Resultado, int]:
    resultado = Resultado()
    ctx = Contexto(
        competencia=arquivo.competencia,  # type: ignore[arg-type]
        id_carga=id_carga,
        estabelecimentos={linha[0] for linha in conexao.execute("SELECT cnes FROM estabelecimento")},
        municipios={linha[0] for linha in conexao.execute("SELECT cod_municipio FROM municipio")},
        cids={linha[0] for linha in conexao.execute("SELECT cod_cid FROM cid")},
    )

    linhas, vistos = [], set()
    for numero, registro in enumerate(ler_dbc(arquivo.caminho), start=1):
        resultado.linhas_lidas += 1
        try:
            linha = converter(registro, ctx)
        except Rejeitado as motivo:
            resultado.rejeitar(numero, str(motivo), _sem_identificadores(registro))
            continue
        chave = (linha[1], linha[2])
        if chave in vistos:
            resultado.rejeitar(numero, "N_AIH + DT_SAIDA repetido no arquivo", _sem_identificadores(registro))
            continue
        vistos.add(chave)
        linhas.append(linha)

    with conexao.cursor().copy(f"COPY internacao ({COLUNAS}) FROM STDIN") as copia:
        for linha in linhas:
            copia.write_row(linha)
    return resultado, len(linhas)


_IDENTIFICADORES = ("NASC", "CEP", "CPF_AUT", "GESTOR_CPF", "INSC_PN")


def _sem_identificadores(registro: dict) -> dict:
    """Registros rejeitados são guardados sem os campos que a origem não grava (LGPD)."""
    return {k: v for k, v in registro.items() if k not in _IDENTIFICADORES}
