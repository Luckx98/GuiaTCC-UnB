import unittest

from loader.qualidade import VERIFICACOES


class TestVerificacoes(unittest.TestCase):
    def test_codigos_unicos(self):
        codigos = [v.codigo for v in VERIFICACOES]
        self.assertEqual(len(codigos), len(set(codigos)))

    def test_severidade_valida(self):
        for v in VERIFICACOES:
            with self.subTest(codigo=v.codigo):
                self.assertIn(v.severidade, {"erro", "alerta"})

    def test_consultas_usam_visoes_vigentes(self):
        # Ler internacao ou leito direto contaria duas vezes uma competência republicada.
        for v in VERIFICACOES:
            with self.subTest(codigo=v.codigo):
                self.assertNotRegex(v.consulta, r"\bFROM internacao\b(?!_vigente)")


if __name__ == "__main__":
    unittest.main()
