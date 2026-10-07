import unittest
from datetime import date
from pathlib import Path

from loader.__main__ import _interpretar
from loader.referencias import ler_cnv

REGIOES = """474 6
    465  53001 Distrito Federal                             530000
    465  53001 Distrito Federal                             530010
    466  53002 Região de Saúde Oeste                        530020
    474       Ignorado - DF                                 530000,539999
"""

MUNICIPIOS = """5598 6
      1   MUNICIPIO IGNORADO - RO                           110000,119999
      2  110001 ALTA FLORESTA D'OESTE                       110001
    100  530010 BRASILIA                                    530010,530000-530009
"""


class TestCnv(unittest.TestCase):
    def test_codigo_exibido_com_largura_diferente_da_declarada(self):
        # O cabeçalho declara 6, mas o código da região tem 5 dígitos.
        linhas = ler_cnv(REGIOES)
        self.assertEqual(linhas[0], ("53001", "Distrito Federal", ["530000"]))
        self.assertEqual(linhas[2], ("53002", "Região de Saúde Oeste", ["530020"]))

    def test_linha_sem_codigo_exibido(self):
        self.assertEqual(ler_cnv(REGIOES)[3], (None, "Ignorado - DF", ["530000", "539999"]))

    def test_faixas_sao_descartadas(self):
        linhas = ler_cnv(MUNICIPIOS)
        self.assertEqual(linhas[0], (None, "MUNICIPIO IGNORADO - RO", ["110000", "119999"]))
        self.assertEqual(linhas[2], ("530010", "BRASILIA", ["530010"]))


class TestNomeArquivo(unittest.TestCase):
    def test_fontes_uf_e_competencia(self):
        rd = _interpretar(Path("RDGO2607.dbc"))
        self.assertEqual((rd.fonte, rd.uf, rd.competencia), ("SIH_RD", "GO", date(2026, 7, 1)))
        self.assertEqual(_interpretar(Path("STDF2101.dbc")).fonte, "CNES_ST")
        self.assertEqual(_interpretar(Path("LTDF2501.dbc")).fonte, "CNES_LT")

    def test_ignora_outros_arquivos(self):
        self.assertIsNone(_interpretar(Path("RDDF2501.dbf")))
        self.assertIsNone(_interpretar(Path("TAB_SIH.zip")))


if __name__ == "__main__":
    unittest.main()
