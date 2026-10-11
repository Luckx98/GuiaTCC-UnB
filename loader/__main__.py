"""Ponto de entrada: python -m loader

MODO=amostra  carrega o recorte versionado em dados/amostra (sem rede).
MODO=completo baixa do FTP do DATASUS as UFS entre COMPETENCIA_INICIO e
              COMPETENCIA_FIM (padrão: última disponível) e carrega em ordem.
"""

from __future__ import annotations

import logging
import re
import sys
from datetime import date
from functools import partial
from pathlib import Path

import psycopg

from loader import cnes, sih
from loader.carga import Arquivo, carregar_arquivo
from loader.config import DIR_AMOSTRA, DIR_REFERENCIA, Config
from loader.ftp import ClienteFTP
from loader.referencias import carregar_referencias

log = logging.getLogger("loader")

# Ordem imposta pelas FKs: estabelecimentos antes de leitos e internações.
ORDEM_FONTES = ("CNES_ST", "CNES_LT", "SIH_RD")
PREFIXOS = {"ST": "CNES_ST", "LT": "CNES_LT", "RD": "SIH_RD"}
PROCESSADORES = {"CNES_ST": cnes.processar_st, "CNES_LT": cnes.processar_lt, "SIH_RD": sih.processar_rd}
_NOME_ARQUIVO = re.compile(r"^(ST|LT|RD)([A-Z]{2})(\d{2})(\d{2})\.dbc$", re.IGNORECASE)


def _interpretar(caminho: Path) -> Arquivo | None:
    encontrado = _NOME_ARQUIVO.match(caminho.name)
    if not encontrado:
        return None
    prefixo, uf, ano, mes = encontrado.groups()
    return Arquivo(PREFIXOS[prefixo.upper()], caminho, uf.upper(), date(2000 + int(ano), int(mes), 1))


def _ordenar(arquivos: list[Arquivo]) -> list[Arquivo]:
    return sorted(arquivos, key=lambda a: (ORDEM_FONTES.index(a.fonte), a.competencia, a.uf))


def arquivos_amostra() -> tuple[Path, list[Arquivo]]:
    dados = [a for a in map(_interpretar, sorted(DIR_AMOSTRA.glob("*.dbc"))) if a]
    return DIR_AMOSTRA / "TAB_SIH_recorte.zip", _ordenar(dados)


def arquivos_completo(config: Config, ftp: ClienteFTP) -> tuple[Path, list[Arquivo]]:
    tab_sih = ftp.baixar("TAB_SIH", "TAB_SIH.zip", config.dir_brutos / "TAB_SIH")
    selecionados = []
    for fonte in ORDEM_FONTES:
        for nome in sorted(ftp.listar(fonte)):
            arquivo = _interpretar(Path(nome))
            if (
                arquivo is None
                or arquivo.fonte != fonte
                or arquivo.uf not in config.ufs
                or arquivo.competencia < config.competencia_inicio
                or (config.competencia_fim and arquivo.competencia > config.competencia_fim)
            ):
                continue
            selecionados.append(arquivo)
    log.info("%d arquivos selecionados no FTP", len(selecionados))

    baixados = []
    for arquivo in _ordenar(selecionados):
        caminho = ftp.baixar(arquivo.fonte, arquivo.caminho.name, config.dir_brutos / arquivo.fonte)
        baixados.append(Arquivo(arquivo.fonte, caminho, arquivo.uf, arquivo.competencia))
    return tab_sih, baixados


def resumo(conexao: psycopg.Connection) -> None:
    for tabela in ("estabelecimento", "estabelecimento_versao", "leito", "internacao", "carga_rejeicao"):
        total = conexao.execute(f"SELECT count(*) FROM {tabela}").fetchone()[0]
        log.info("%-24s %10d linhas", tabela, total)
    sem_regiao = conexao.execute(
        """
        SELECT DISTINCT i.cnes FROM internacao i
        WHERE i.municipio_estabelecimento = '530010'
          AND NOT EXISTS (SELECT 1 FROM estabelecimento_regiao_df r WHERE r.cnes = i.cnes)
        ORDER BY 1
        """
    ).fetchall()
    if sem_regiao:
        log.warning(
            "CNES do DF sem região de saúde em dados/referencia/estabelecimento_regiao_saude_df.csv: %s",
            ", ".join(c for (c,) in sem_regiao),
        )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = Config.do_ambiente()
    log.info("modo=%s ufs=%s", config.modo, ",".join(config.ufs))

    ftp = ClienteFTP()
    try:
        if config.modo == "amostra":
            tab_sih, arquivos = arquivos_amostra()
        else:
            tab_sih, arquivos = arquivos_completo(config, ftp)
    finally:
        ftp.fechar()

    falhas = 0
    with psycopg.connect(config.database_url, autocommit=True) as conexao:
        carregar_referencias(conexao, tab_sih, DIR_REFERENCIA / "estabelecimento_regiao_saude_df.csv")
        for arquivo in arquivos:
            try:
                carregar_arquivo(conexao, arquivo, partial(_processar, arquivo=arquivo))
            except Exception:
                falhas += 1
                log.exception("falha ao carregar %s", arquivo.caminho.name)
        resumo(conexao)

    if falhas:
        log.error("%d arquivo(s) falharam; ver tabela carga (status = 'falhou')", falhas)
        return 1
    return 0


def _processar(conexao: psycopg.Connection, id_carga: int, arquivo: Arquivo):
    return PROCESSADORES[arquivo.fonte](conexao, id_carga, arquivo)


if __name__ == "__main__":
    sys.exit(main())
