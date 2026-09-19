"""Ponta a ponta: o caminho que um alerta real percorre.

Cobre a costura entre config, classificacao, database e servicos -- que os
testes de unidade, isolados, nao pegam.
"""

from __future__ import annotations

from datetime import datetime

import pytest

import database as db
import servicos
from config import CENTRO_PADRAO, RAIO_DUPLICIDADE_M, TETO_ESCALONAMENTO

LAT, LON = CENTRO_PADRAO


def _alerta(protocolo: str):
    return db.listar_ocorrencias(texto=protocolo).iloc[0]


def test_ciclo_de_vida_de_uma_emergencia(banco):
    # 1. O cidadao marca pelo GPS um deslizamento grave com gente presa.
    protocolo = db.inserir_ocorrencia(
        categoria="Deslizamento de terra", severidade="Critica",
        descricao="Barranco cedeu sobre a calcada", latitude=LAT, longitude=LON,
        precisao_gps=9.0, origem_coordenada="GPS",
        referencia="Rua das Flores, 120", bairro="Centro",
        autor="Miguel", contato="(18) 99999-0000",
        emergencia=True, pessoas_em_risco=True)
    assert protocolo == f"OC{datetime.now().year}-00001"

    alerta = _alerta(protocolo)
    identificador = int(alerta["id"])
    assert alerta["nivel"] == "P1"
    assert "ilhadas" in alerta["motivo_nivel"]
    assert alerta["situacao_sla"] in ("No prazo", "Atencao")

    # 2. Outro cidadao chega ao mesmo ponto: o app oferece confirmar.
    vizinhas = db.buscar_proximas(LAT + 0.0001, LON, RAIO_DUPLICIDADE_M)
    assert list(vizinhas["protocolo"]) == [protocolo]
    assert vizinhas.iloc[0]["distancia_m"] < RAIO_DUPLICIDADE_M

    db.confirmar_ocorrencia(identificador, autor="Ana", comentario="Vi tambem")
    assert _alerta(protocolo)["confirmacoes"] == 1

    # 3. Sobe ao topo da fila, na frente de um buraco aberto antes.
    db.inserir_ocorrencia(categoria="Buraco na via", severidade="Baixa",
                          descricao="Buraco fundo", latitude=LAT + 0.01,
                          longitude=LON)
    fila = db.fila_emergencia()
    assert fila.iloc[0]["protocolo"] == protocolo
    assert fila.iloc[-1]["nivel"] == "P4"

    # 4. O despacho leva tudo o que a equipe precisa.
    despacho = servicos.texto_despacho(fila.iloc[0])
    assert protocolo in despacho
    assert "PESSOAS EM RISCO" in despacho
    assert "1.1.3.2.1" in despacho          # COBRADE do deslizamento
    assert "Rua das Flores" in despacho
    assert "199" in despacho                # telefone da Defesa Civil

    # 5. A Defesa Civil aciona e assume o atendimento.
    db.registrar_acionamento(identificador, "Defesa Civil", responsavel="Plantao")
    db.atualizar_status(identificador, "Em atendimento", responsavel="Plantao")
    alerta = _alerta(protocolo)
    assert alerta["orgao_acionado"] == "Defesa Civil"
    assert alerta["situacao_sla"] == "Acionado"

    # 6. Resolvida: sai da fila e entra nos tempos medios do painel.
    db.atualizar_status(identificador, "Resolvido", observacao="Talude contido",
                        responsavel="Equipe 2")
    assert protocolo not in list(db.fila_emergencia()["protocolo"])

    numeros = db.estatisticas()
    assert numeros["resolvidas"] == 1
    assert numeros["emergencias_ativas"] == 0
    assert numeros["tempo_medio_horas"] is not None
    assert db.aderencia_sla()["percentual"] == 100.0

    # 7. O historico conta a operacao inteira, do mais novo para o mais antigo.
    eventos = db.listar_historico(identificador)
    assert len(eventos) == 4    # abertura, acionamento, em atendimento, resolvido
    assert eventos.iloc[0]["status_novo"] == "Resolvido"
    assert eventos.iloc[-1]["status_novo"] == "Aberto"


def test_alerta_esquecido_escalona_e_para_quando_atendido(banco, recuar):
    """Um P4 largado 49 h vira P3; acionar congela o relogio."""
    protocolo = db.inserir_ocorrencia(
        categoria="Buraco na via", severidade="Baixa", descricao="Buraco",
        latitude=LAT, longitude=LON)
    recuar(protocolo, hours=49)

    alerta = _alerta(protocolo)
    assert alerta["nivel"] == "P3"
    assert bool(alerta["escalado"]) is True
    assert alerta["situacao_sla"] == "VENCIDO"

    db.registrar_acionamento(int(alerta["id"]), "Prefeitura")
    depois = _alerta(protocolo)
    assert bool(depois["escalado"]) is False
    assert depois["nivel"] == "P4"


def test_escalonamento_para_no_teto_mesmo_apos_semanas(banco, recuar):
    protocolo = db.inserir_ocorrencia(
        categoria="Granizo", severidade="Alta", descricao="Granizo",
        latitude=LAT, longitude=LON)
    recuar(protocolo, days=30)
    assert _alerta(protocolo)["nivel"] == TETO_ESCALONAMENTO


def test_reclassificacao_manual_prevalece_na_fila(banco):
    """Decisao humana muda a posicao do alerta na fila de verdade."""
    grave = db.inserir_ocorrencia(
        categoria="Deslizamento de terra", severidade="Critica",
        descricao="Talude", latitude=LAT, longitude=LON)
    db.inserir_ocorrencia(categoria="Buraco na via", severidade="Baixa",
                          descricao="Buraco", latitude=LAT + 0.01, longitude=LON)
    assert db.fila_emergencia().iloc[0]["protocolo"] == grave

    db.reclassificar(int(_alerta(grave)["id"]), "P4",
                     "Equipe foi ao local: o talude ja estava contido",
                     responsavel="Engenharia")
    alerta = _alerta(grave)
    assert alerta["nivel"] == "P4"
    assert alerta["origem_nivel"] == "Manual"
    assert "talude" in alerta["motivo_nivel"]


def test_confirmacoes_sobem_o_alerta_na_fila(banco):
    """Confirmacao cruzada tem de mudar a ordem de atendimento, nao so o numero."""
    comum = db.inserir_ocorrencia(categoria="Buraco na via", severidade="Baixa",
                                  descricao="Buraco", latitude=LAT, longitude=LON)
    confirmado = db.inserir_ocorrencia(
        categoria="Buraco na via", severidade="Baixa", descricao="Outro buraco",
        latitude=LAT + 0.01, longitude=LON)

    identificador = int(_alerta(confirmado)["id"])
    for nome in ("Ana", "Bruno"):
        db.confirmar_ocorrencia(identificador, autor=nome)

    fila = db.fila_emergencia()
    assert fila.iloc[0]["protocolo"] == confirmado
    assert fila.iloc[0]["nivel"] == "P3"
    assert _alerta(comum)["nivel"] == "P4"


def test_banco_recem_criado_responde_a_todas_as_telas(banco):
    """A primeira execucao abre com o banco vazio: nada pode quebrar."""
    assert db.listar_ocorrencias().empty
    assert db.fila_emergencia().empty
    assert db.buscar_proximas(LAT, LON, RAIO_DUPLICIDADE_M).empty
    assert db.listar_historico().empty
    assert len(db.resumo_por_nivel()) == 4
    assert db.estatisticas()["total"] == 0
    assert db.aderencia_sla()["percentual"] is None
