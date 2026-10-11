"""Download do FTP público do DATASUS, com novas tentativas e retomada."""

from __future__ import annotations

import ftplib
import hashlib
import logging
import time
from pathlib import Path

log = logging.getLogger(__name__)

HOST = "ftp.datasus.gov.br"
TENTATIVAS = 5

# Diretórios remotos por fonte.
DIRETORIOS = {
    "SIH_RD": "/dissemin/publicos/SIHSUS/200801_/Dados",
    "CNES_ST": "/dissemin/publicos/CNES/200508_/Dados/ST",
    "CNES_LT": "/dissemin/publicos/CNES/200508_/Dados/LT",
    "TAB_SIH": "/dissemin/publicos/SIHSUS/200801_/Auxiliar",
}


def sha256(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


class ClienteFTP:
    """Mantém uma conexão e reconecta quando o servidor a derruba."""

    def __init__(self) -> None:
        self._ftp: ftplib.FTP | None = None

    def _conexao(self) -> ftplib.FTP:
        if self._ftp is None:
            self._ftp = ftplib.FTP(HOST, timeout=120)
            self._ftp.login()
        return self._ftp

    def _descartar(self) -> None:
        if self._ftp is not None:
            try:
                self._ftp.close()
            finally:
                self._ftp = None

    def _com_tentativas(self, descricao: str, acao):
        for tentativa in range(1, TENTATIVAS + 1):
            try:
                return acao(self._conexao())
            except (ftplib.Error, OSError, EOFError) as erro:
                self._descartar()
                if tentativa == TENTATIVAS:
                    raise
                espera = 2**tentativa
                log.warning("%s falhou (%s); nova tentativa em %ss", descricao, erro, espera)
                time.sleep(espera)

    def listar(self, fonte: str) -> set[str]:
        diretorio = DIRETORIOS[fonte]
        return set(self._com_tentativas(f"listar {diretorio}", lambda ftp: ftp.nlst(diretorio)))

    def baixar(self, fonte: str, nome: str, destino_dir: Path) -> Path:
        """Baixa para <destino>.part e renomeia ao final; retoma do ponto em que parou."""
        destino_dir.mkdir(parents=True, exist_ok=True)
        destino = destino_dir / nome
        if destino.exists():
            return destino
        parcial = destino.with_suffix(destino.suffix + ".part")
        remoto = f"{DIRETORIOS[fonte]}/{nome}"

        def transferir(ftp: ftplib.FTP) -> None:
            ftp.voidcmd("TYPE I")
            inicio = parcial.stat().st_size if parcial.exists() else 0
            with parcial.open("ab") as arquivo:
                ftp.retrbinary(f"RETR {remoto}", arquivo.write, rest=inicio or None)
            if parcial.stat().st_size != ftp.size(remoto):
                raise EOFError(f"tamanho divergente em {nome}")

        self._com_tentativas(f"baixar {nome}", transferir)
        parcial.rename(destino)
        log.info("baixado %s (%.1f MB)", nome, destino.stat().st_size / 1e6)
        return destino

    def fechar(self) -> None:
        if self._ftp is not None:
            try:
                self._ftp.quit()
            except ftplib.Error:
                pass
            self._descartar()
