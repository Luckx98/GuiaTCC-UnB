import unittest
from datetime import date
from decimal import Decimal

from loader.sih import Contexto, Rejeitado, _sem_identificadores, converter

CTX = Contexto(
    competencia=date(2025, 1, 1),
    id_carga=7,
    estabelecimentos={"0010456"},
    municipios={"530010", "520870"},
    cids={"O800", "J189"},
)


def registro(**alteracoes) -> dict:
    base = {
        "ANO_CMPT": "2025", "MES_CMPT": "01", "N_AIH": "5325100156541", "IDENT": "1", "CNES": "0010456",
        "DT_INTER": "20241228", "DT_SAIDA": "20250104", "DIAS_PERM": "7", "QT_DIARIAS": "7", "ESPEC": "03",
        "CAR_INT": "02", "COMPLEX": "02", "DIAG_PRINC": "J189", "DIAG_SECUN": "0000", "PROC_REA": "0303140151",
        "UTI_MES_TO": "0", "MARCA_UTI": "00", "VAL_TOT": "526.72", "VAL_UTI": "0.00", "IDADE": "53",
        "COD_IDADE": "4", "SEXO": "3", "RACA_COR": "03", "MUNIC_RES": "520870", "MUNIC_MOV": "530010",
        "MORTE": "0", "GESTAO": "2", "NASC": "19710625", "CEP": "72236800",
    }
    base.update(alteracoes)
    return base


class TestConverter(unittest.TestCase):
    def test_registro_valido(self):
        linha = converter(registro(), CTX)
        self.assertEqual(linha[:4], (date(2025, 1, 1), "5325100156541", date(2025, 1, 4), 7))
        self.assertEqual(linha[6], date(2024, 12, 28))  # internação de mês anterior (represamento)
        self.assertEqual(linha[17], Decimal("526.72"))
        self.assertIsNone(linha[13])  # DIAG_SECUN "0000" vira nulo
        self.assertFalse(linha[25])

    def test_longa_permanencia_com_internacao_antiga(self):
        linha = converter(registro(IDENT="5", DT_INTER="20080101"), CTX)
        self.assertEqual(linha[6], date(2008, 1, 1))

    def test_rejeicoes(self):
        casos = {
            "competência": registro(MES_CMPT="02"),
            "IDENT": registro(IDENT="9"),
            "CNES sem cadastro": registro(CNES="1234567"),
            "CID principal": registro(DIAG_PRINC="N185"),
            "município": registro(MUNIC_RES="999999"),
            "DT_SAIDA anterior": registro(DT_SAIDA="20241201"),
            "DT_INTER inválida": registro(DT_INTER="20241399"),
            "VAL_TOT negativo": registro(VAL_TOT="-1"),
        }
        for motivo, dado in casos.items():
            with self.subTest(motivo=motivo):
                with self.assertRaisesRegex(Rejeitado, motivo):
                    converter(dado, CTX)

    def test_rejeitado_guardado_sem_identificadores(self):
        guardado = _sem_identificadores(registro())
        self.assertNotIn("NASC", guardado)
        self.assertNotIn("CEP", guardado)
        self.assertIn("N_AIH", guardado)


if __name__ == "__main__":
    unittest.main()
