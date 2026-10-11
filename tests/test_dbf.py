import struct
import tempfile
import unittest
from pathlib import Path

from loader.dbf import campos, ler_dbf


def escrever_dbf(caminho: Path, colunas: list[tuple[str, int]], registros: list[list[str]], terminador: bytes) -> None:
    """Gera um dBase III mínimo; `terminador` simula o 0x0D padrão ou o 0x00 do CNES-ST."""
    tamanho_registro = 1 + sum(tamanho for _, tamanho in colunas)
    tamanho_cabecalho = 32 + 32 * len(colunas) + 1
    cabecalho = struct.pack("<B3sIHH20x", 0x03, b"\x7e\x01\x01", len(registros), tamanho_cabecalho, tamanho_registro)
    descritores = b"".join(
        struct.pack("<11sc4xB15x", nome.encode("ascii"), b"C", tamanho) for nome, tamanho in colunas
    )
    corpo = b""
    for apagado, *valores in registros:
        corpo += apagado.encode() + b"".join(
            valor.encode("latin-1").ljust(tamanho) for valor, (_, tamanho) in zip(valores, colunas)
        )
    caminho.write_bytes(cabecalho + descritores + terminador + corpo + b"\x1a")


class TestLeitorDbf(unittest.TestCase):
    def setUp(self):
        self.diretorio = tempfile.TemporaryDirectory()
        self.addCleanup(self.diretorio.cleanup)
        self.caminho = Path(self.diretorio.name) / "teste.dbf"
        self.colunas = [("CNES", 7), ("NOME", 10)]
        self.registros = [[" ", "0010456", "HBDF"], ["*", "9999999", "APAGADO"], [" ", "0010464", "São José"]]

    def test_cabecalho_padrao(self):
        escrever_dbf(self.caminho, self.colunas, self.registros, b"\x0d")
        linhas = list(ler_dbf(self.caminho))
        self.assertEqual(linhas, [{"CNES": "0010456", "NOME": "HBDF"}, {"CNES": "0010464", "NOME": "São José"}])

    def test_cabecalho_terminado_em_zero_como_no_cnes_st(self):
        escrever_dbf(self.caminho, self.colunas, self.registros, b"\x00")
        self.assertEqual([nome for nome, _, _ in campos(self.caminho)], ["CNES", "NOME"])
        self.assertEqual(len(list(ler_dbf(self.caminho))), 2)


if __name__ == "__main__":
    unittest.main()
