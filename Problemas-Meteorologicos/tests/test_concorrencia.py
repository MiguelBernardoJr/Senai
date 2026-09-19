"""Varios cidadaos enviando ao mesmo tempo, e a Central lendo no meio disso.

O protocolo e derivado do `lastrowid` do INSERT. Estes testes fixam que isso
continua valendo sob concorrencia: se alguem trocar a geracao do protocolo por
um `SELECT MAX(...) + 1`, alguma coisa aqui quebra.
"""

from __future__ import annotations

import threading
from collections import Counter

import pytest

import database as db
from config import CENTRO_PADRAO

LAT, LON = CENTRO_PADRAO


def _em_paralelo(alvo, n_threads: int, *args):
    """Dispara n threads que so comecam quando todas estao prontas."""
    largada = threading.Event()
    trava = threading.Lock()
    resultados: list = []
    erros: list[str] = []

    def envolver(indice):
        largada.wait()
        try:
            for valor in alvo(indice, *args) or []:
                with trava:
                    resultados.append(valor)
        except Exception as erro:                       # noqa: BLE001
            with trava:
                erros.append(f"{type(erro).__name__}: {erro}")

    threads = [threading.Thread(target=envolver, args=(i,)) for i in range(n_threads)]
    for thread in threads:
        thread.start()
    largada.set()
    for thread in threads:
        thread.join(timeout=60)
    return resultados, erros


def test_envios_simultaneos_nao_repetem_protocolo(banco):
    """O caso da apresentacao: a turma inteira registrando junto."""
    def enviar(indice):
        return [db.inserir_ocorrencia(
            categoria="Alagamento / enchente", severidade="Media",
            descricao=f"envio {indice}-{i}", latitude=LAT, longitude=LON)
            for i in range(8)]

    protocolos, erros = _em_paralelo(enviar, 10)

    assert erros == []
    assert len(protocolos) == 80
    repetidos = [p for p, vezes in Counter(protocolos).items() if vezes > 1]
    assert repetidos == [], f"protocolos repetidos: {repetidos}"


def test_nenhum_alerta_fica_sem_protocolo(banco):
    """O protocolo e gravado num UPDATE logo apos o INSERT, na mesma transacao.

    Se a transacao fosse fechada entre os dois, existiria alerta com protocolo
    NULL -- e o cidadao ficaria sem numero para acompanhar.
    """
    def enviar(indice):
        return [db.inserir_ocorrencia(
            categoria="Granizo", severidade="Alta", descricao=f"{indice}-{i}",
            latitude=LAT, longitude=LON) for i in range(6)]

    _, erros = _em_paralelo(enviar, 8)
    assert erros == []

    dados = db.listar_ocorrencias()
    assert len(dados) == 48
    assert dados["protocolo"].isna().sum() == 0
    assert dados["protocolo"].nunique() == 48


def test_central_lendo_enquanto_os_alertas_chegam(banco):
    """Leitura concorrente com escrita nao pode dar 'database is locked'.

    E exatamente o que acontece na demo: a Central recarrega sozinha a cada
    30 s enquanto o cidadao registra.
    """
    for i in range(30):
        db.inserir_ocorrencia(categoria="Buraco na via", severidade="Baixa",
                              descricao=f"base {i}", latitude=LAT + i * 0.0001,
                              longitude=LON)

    parar = threading.Event()
    leituras = []
    erros_leitura = []

    def ler():
        while not parar.is_set():
            try:
                db.fila_emergencia()
                db.estatisticas()
                leituras.append(1)
            except Exception as erro:                   # noqa: BLE001
                erros_leitura.append(f"{type(erro).__name__}: {erro}")

    leitores = [threading.Thread(target=ler, daemon=True) for _ in range(3)]
    for leitor in leitores:
        leitor.start()

    def escrever(indice):
        return [db.inserir_ocorrencia(
            categoria="Vendaval / destelhamento", severidade="Media",
            descricao=f"w{indice}-{i}", latitude=LAT, longitude=LON)
            for i in range(10)]

    _, erros_escrita = _em_paralelo(escrever, 6)
    parar.set()
    for leitor in leitores:
        leitor.join(timeout=10)

    assert erros_escrita == []
    assert erros_leitura == []
    assert leituras, "nenhuma leitura concluiu durante as escritas"


def test_confirmacoes_simultaneas_no_mesmo_alerta(banco):
    """Um evento de massa: muita gente confirmando o mesmo alerta de uma vez."""
    protocolo = db.inserir_ocorrencia(
        categoria="Deslizamento de terra", severidade="Alta",
        descricao="talude", latitude=LAT, longitude=LON)
    identificador = int(db.listar_ocorrencias(texto=protocolo).iloc[0]["id"])

    def confirmar(indice):
        for i in range(5):
            db.confirmar_ocorrencia(identificador, autor=f"cidadao {indice}-{i}")
        return []

    _, erros = _em_paralelo(confirmar, 8)
    assert erros == []
    assert len(db.listar_confirmacoes(identificador)) == 40
    assert int(db.listar_ocorrencias(texto=protocolo).iloc[0]["confirmacoes"]) == 40
