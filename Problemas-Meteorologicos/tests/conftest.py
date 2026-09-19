"""Configuracao comum dos testes.

O banco de cada teste e um arquivo temporario proprio: nenhum teste toca no
data/ocorrencias.db de verdade.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import database  # noqa: E402


@pytest.fixture()
def banco(tmp_path, monkeypatch):
    """Banco vazio e isolado. database.conectar() passa a apontar para ele.

    CAMINHO_BANCO e PASTA_FOTOS sao importados para dentro do namespace de
    database (`from config import ...`), entao e la que precisam ser trocados.
    """
    monkeypatch.setattr(database, "CAMINHO_BANCO", tmp_path / "teste.db")
    monkeypatch.setattr(database, "PASTA_FOTOS", tmp_path / "fotos")
    database.criar_tabelas()
    return tmp_path / "teste.db"


@pytest.fixture()
def recuar():
    """Move o criado_em de um alerta para o passado.

    inserir_ocorrencia() carimba a hora internamente; para testar SLA,
    escalonamento e "horas em aberto" o jeito honesto e envelhecer o registro
    depois de grava-lo, em vez de desmontar a funcao.
    """
    def _recuar(protocolo: str, **delta) -> str:
        momento = (datetime.now() - timedelta(**delta)).isoformat(timespec="seconds")
        with database.conectar() as conexao:
            conexao.execute(
                "UPDATE ocorrencias SET criado_em = ? WHERE protocolo = ?",
                (momento, protocolo),
            )
        return momento
    return _recuar
