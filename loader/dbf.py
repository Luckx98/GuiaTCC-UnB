"""Leitura de arquivos DBF (dBase III) e descompactação de .dbc do DATASUS.

O dbfread não aceita os DBF do CNES-ST, cujo cabeçalho termina com 0x00 em vez
de 0x0D. Este leitor usa apenas os tamanhos declarados no cabeçalho.
"""

from __future__ import annotations

import struct
import tempfile
from collections.abc import Iterator
from pathlib import Path

from datasus_dbc import decompress


def campos(caminho: Path) -> list[tuple[str, str, int]]:
    """Lista (nome, tipo, tamanho) das colunas do DBF."""
    with caminho.open("rb") as arquivo:
        cabecalho = arquivo.read(32)
        tamanho_cabecalho = struct.unpack("<H", cabecalho[8:10])[0]
        descritores = arquivo.read(tamanho_cabecalho - 32)

    resultado = []
    for inicio in range(0, len(descritores) - 31, 32):
        bloco = descritores[inicio : inicio + 32]
        if bloco[0] in (0x0D, 0x00):
            break
        nome = bloco[:11].split(b"\0")[0].decode("ascii")
        resultado.append((nome, chr(bloco[11]), bloco[16]))
    return resultado


def ler_dbf(caminho: Path, encoding: str = "latin-1") -> Iterator[dict[str, str]]:
    """Entrega cada registro como dicionário de textos sem espaços nas pontas."""
    colunas = campos(caminho)
    with caminho.open("rb") as arquivo:
        cabecalho = arquivo.read(32)
        total, tamanho_cabecalho, tamanho_registro = struct.unpack("<IHH", cabecalho[4:12])
        arquivo.seek(tamanho_cabecalho)
        for _ in range(total):
            registro = arquivo.read(tamanho_registro)
            if len(registro) < tamanho_registro or registro[:1] == b"\x1a":
                break
            if registro[:1] == b"*":  # registro marcado como apagado
                continue
            posicao, linha = 1, {}
            for nome, _tipo, tamanho in colunas:
                linha[nome] = registro[posicao : posicao + tamanho].decode(encoding).strip()
                posicao += tamanho
            yield linha


def ler_dbc(caminho: Path) -> Iterator[dict[str, str]]:
    """Descompacta o .dbc num arquivo temporário e lê o DBF resultante."""
    with tempfile.TemporaryDirectory() as diretorio:
        dbf = Path(diretorio) / (caminho.stem + ".dbf")
        decompress(str(caminho), str(dbf))
        yield from ler_dbf(dbf)
