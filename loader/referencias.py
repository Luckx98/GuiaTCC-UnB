"""Tabelas de referência: TAB_SIH.zip do DATASUS e tabela curada do DF."""

from __future__ import annotations

import csv
import re
import tempfile
import zipfile
from pathlib import Path

import psycopg

from loader.carga import Arquivo, Resultado, carregar_arquivo
from loader.dbf import ler_dbf

ARQ_MUNICIPIOS = "CNV/br_municip.cnv"
ARQ_REGIOES = "CNV/br_regsaud.cnv"
ARQ_CID = "DBF/cid10.dbf"

_LINHA_CNV = re.compile(r"^\s*\d+\s+(?P<rotulo>.*?)\s{2,}(?P<valores>[0-9A-Z,\-]+)\s*$")


def _membro(pacote: zipfile.ZipFile, nome: str) -> str:
    """Os nomes no zip variam de caixa entre versões (br_regsaud / BR_regsaud)."""
    for membro in pacote.namelist():
        if membro.lower() == nome.lower():
            return membro
    raise KeyError(f"{nome} não encontrado em {pacote.filename}")


def ler_cnv(texto: str) -> list[tuple[str | None, str, list[str]]]:
    """Lê um arquivo .cnv do TabWin: (código exibido, rótulo, códigos de origem).

    Faixas ("530000-530009") são descartadas; ficam só os códigos individuais.
    """
    resultado = []
    for linha in texto.splitlines()[1:]:
        encontrado = _LINHA_CNV.match(linha)
        if not encontrado:
            continue
        rotulo = encontrado["rotulo"].strip()
        codigo = None
        primeiro, _, resto = rotulo.partition(" ")
        if primeiro.isdigit() and resto.strip():
            codigo, rotulo = primeiro, resto.strip()
        valores = [v for v in encontrado["valores"].split(",") if v and "-" not in v]
        resultado.append((codigo, rotulo, valores))
    return resultado


def _carregar_tab_sih(conexao: psycopg.Connection, caminho: Path) -> tuple[Resultado, int]:
    resultado = Resultado()
    with zipfile.ZipFile(caminho) as pacote:
        regioes_cnv = ler_cnv(pacote.read(_membro(pacote, ARQ_REGIOES)).decode("latin-1"))
        municipios_cnv = ler_cnv(pacote.read(_membro(pacote, ARQ_MUNICIPIOS)).decode("latin-1"))
        with tempfile.TemporaryDirectory() as diretorio:
            cid_dbf = Path(pacote.extract(_membro(pacote, ARQ_CID), diretorio))
            cids = list(ler_dbf(cid_dbf))

    regioes: dict[str, str] = {}
    regiao_do_municipio: dict[str, str] = {}
    for codigo, nome, municipios in regioes_cnv:
        if codigo is None:
            continue
        regioes.setdefault(codigo, nome)
        for municipio in municipios:
            regiao_do_municipio.setdefault(municipio, codigo)

    municipios: dict[str, str] = {}
    for _codigo, nome, codigos in municipios_cnv:
        for codigo in codigos:
            if re.fullmatch(r"[0-9]{6}", codigo):
                municipios.setdefault(codigo, nome)

    resultado.linhas_lidas = len(regioes) + len(municipios) + len(cids)
    inseridas = 0
    with conexao.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO regiao_saude (cod_regiao_saude, nome, cod_uf) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            [(codigo, nome, codigo[:2]) for codigo, nome in regioes.items()],
        )
        inseridas += cursor.rowcount
        cursor.executemany(
            """
            INSERT INTO municipio (cod_municipio, nome, cod_uf, cod_regiao_saude)
            VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING
            """,
            [(codigo, nome, codigo[:2], regiao_do_municipio.get(codigo)) for codigo, nome in municipios.items()],
        )
        inseridas += cursor.rowcount

        linhas_cid = []
        for numero, registro in enumerate(cids, start=1):
            codigo = registro.get("CD_COD", "").replace(".", "").upper()
            # A descrição vem com o código na frente: "A00.0 Colera dev ...".
            descricao = re.sub(r"^\S+\s+", "", registro.get("CD_DESCR", ""))
            if not re.fullmatch(r"[A-Z][0-9]{2}[0-9X]?", codigo) or not descricao:
                resultado.rejeitar(numero, "código CID inválido ou sem descrição", registro)
                continue
            linhas_cid.append((codigo, descricao))
        cursor.executemany(
            "INSERT INTO cid (cod_cid, descricao) VALUES (%s, %s) ON CONFLICT DO NOTHING", linhas_cid
        )
        inseridas += cursor.rowcount
    return resultado, inseridas


def _carregar_regioes_df(conexao: psycopg.Connection, caminho: Path) -> tuple[Resultado, int]:
    resultado = Resultado()
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    resultado.linhas_lidas = len(linhas)
    with conexao.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO estabelecimento_regiao_df
                (cnes, nome_fantasia, regiao_administrativa, cod_regiao_saude, observacao)
            VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING
            """,
            [
                (l["cnes"], l["nome_fantasia"], l["regiao_administrativa"], l["cod_regiao_saude"], l["observacao"] or None)
                for l in linhas
            ],
        )
        inseridas = cursor.rowcount
    return resultado, inseridas


def carregar_referencias(conexao: psycopg.Connection, tab_sih: Path, regioes_df: Path) -> None:
    carregar_arquivo(conexao, Arquivo("REFERENCIA", tab_sih), lambda c, _id: _carregar_tab_sih(c, tab_sih))
    carregar_arquivo(conexao, Arquivo("REFERENCIA", regioes_df), lambda c, _id: _carregar_regioes_df(c, regioes_df))
