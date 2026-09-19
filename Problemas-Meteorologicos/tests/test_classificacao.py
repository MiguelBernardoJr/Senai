"""Testes da triagem: discriminadores, escalonamento, SLA e formatacao.

A ordem dos discriminadores e a regra de negocio central do projeto. Estes
testes fixam essa ordem: mexer na lista sem intencao quebra algum deles.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import pytest

import classificacao as tri
from config import ORDEM_NIVEIS, TETO_ESCALONAMENTO


def linha(**campos) -> dict:
    """Alerta minimo, aberto agora, com os campos pedidos por cima."""
    base = {
        "categoria": "Buraco na via",
        "severidade": "Baixa",
        "emergencia": 0,
        "pessoas_em_risco": 0,
        "confirmacoes": 0,
        "status": "Aberto",
        "criado_em": datetime.now().isoformat(timespec="seconds"),
    }
    base.update(campos)
    return base


# ---------------------------------------------------------------------------
# Discriminadores, na ordem em que a tabela de triagem os avalia
# ---------------------------------------------------------------------------

CASOS = [
    # (campos, nivel esperado, trecho do motivo)
    (dict(pessoas_em_risco=1), "P1", "ilhadas"),
    (dict(categoria="Deslizamento de terra", severidade="Alta"), "P1", "risco vital"),
    (dict(categoria="Alagamento / enchente", severidade="Critica", emergencia=1),
     "P1", "Emergencia declarada"),
    (dict(categoria="Alagamento / enchente", severidade="Critica", confirmacoes=3),
     "P1", "evento de massa"),
    (dict(severidade="Media", emergencia=1), "P2", "Emergencia declarada"),
    (dict(categoria="Alagamento / enchente", severidade="Critica"),
     "P2", "sem vitima identificada"),
    (dict(categoria="Fio de energia rompido", severidade="Media"),
     "P2", "risco vital direto"),
    (dict(categoria="Alagamento / enchente", severidade="Alta", confirmacoes=2),
     "P2", "confirmada por outros"),
    (dict(categoria="Granizo", severidade="Alta"), "P3", "Gravidade alta"),
    (dict(categoria="Buraco na via", severidade="Baixa", confirmacoes=2),
     "P3", "confirmado por outros"),
    (dict(categoria="Alagamento / enchente", severidade="Baixa"),
     "P3", "risco relevante de agravamento"),
    (dict(categoria="Buraco na via", severidade="Baixa"), "P4", "Sem risco imediato"),
]


@pytest.mark.parametrize("campos,nivel,trecho", CASOS)
def test_discriminador_que_decide_o_nivel(campos, nivel, trecho):
    triagem = tri.classificar(linha(**campos))
    assert triagem["nivel"] == nivel
    assert trecho.lower() in triagem["motivo"].lower()
    assert triagem["origem"] == "Automatica"


def test_pessoas_em_risco_vence_qualquer_outro_criterio():
    """E o primeiro da lista: nada abaixo dele pode rebaixar o alerta."""
    triagem = tri.classificar(
        linha(categoria="Buraco na via", severidade="Baixa", pessoas_em_risco=1))
    assert triagem["nivel"] == "P1"


def test_emergencia_declarada_sozinha_nao_chega_a_p1():
    """Sem gravidade critica, o botao de emergencia para em P2.

    E a trava que impede o botao de virar a fila do avesso.
    """
    assert tri.classificar(linha(severidade="Media", emergencia=1))["nivel"] == "P2"


def test_evento_de_massa_precisa_de_gravidade_critica():
    """Tres confirmacoes so viram P1 se a gravidade ja for critica."""
    assert tri.classificar(linha(categoria="Alagamento / enchente",
                                 severidade="Media", confirmacoes=3))["nivel"] == "P3"
    assert tri.classificar(linha(categoria="Alagamento / enchente",
                                 severidade="Critica", confirmacoes=3))["nivel"] == "P1"


def test_uma_confirmacao_isolada_nao_muda_o_nivel():
    """O discriminador exige DUAS: um relato so nao e confirmacao cruzada."""
    assert tri.classificar(linha(confirmacoes=1))["nivel"] == "P4"
    assert tri.classificar(linha(confirmacoes=2))["nivel"] == "P3"


def test_todo_alerta_recebe_um_nivel():
    """A lista termina em um padrao: nunca existe alerta sem classificacao."""
    from config import CATEGORIAS, SEVERIDADES
    for categoria in CATEGORIAS:
        for severidade in SEVERIDADES:
            nivel = tri.classificar(linha(categoria=categoria,
                                          severidade=severidade))["nivel"]
            assert nivel in ORDEM_NIVEIS


def test_categoria_desconhecida_nao_quebra_a_triagem():
    assert tri.classificar(linha(categoria="Meteoro"))["nivel"] == "P4"


def test_campo_faltando_nao_derruba_a_triagem():
    """A fila da Defesa Civil nao pode quebrar por causa de um registro torto."""
    assert tri.classificar({"criado_em": "2026-01-01T00:00:00"})["nivel"] == "P4"


# ---------------------------------------------------------------------------
# Reclassificacao manual
# ---------------------------------------------------------------------------


def test_triagem_humana_prevalece_sobre_a_regra():
    triagem = tri.classificar(linha(
        categoria="Deslizamento de terra", severidade="Critica",
        classificacao_manual="P3",
        motivo_classificacao="Equipe confirmou que o talude esta contido"))
    assert triagem["nivel"] == "P3"
    assert triagem["origem"] == "Manual"
    assert "talude" in triagem["motivo"]


def test_reclassificacao_sem_motivo_ainda_se_explica():
    triagem = tri.classificar(linha(classificacao_manual="P1"))
    assert triagem["nivel"] == "P1"
    assert triagem["motivo"]


def test_nivel_manual_invalido_volta_para_a_regra():
    triagem = tri.classificar(linha(categoria="Deslizamento de terra",
                                    severidade="Alta", classificacao_manual="P9"))
    assert triagem["origem"] == "Automatica"
    assert triagem["nivel"] == "P1"


# ---------------------------------------------------------------------------
# Escalonamento
# ---------------------------------------------------------------------------


def test_subir_nivel_respeita_o_teto():
    assert tri.subir_nivel("P4") == "P3"
    assert tri.subir_nivel("P3") == TETO_ESCALONAMENTO
    assert tri.subir_nivel("P2") == "P2"


def test_subir_nivel_nunca_rebaixa_uma_emergencia():
    """P1 e o topo: escalonar um P1 nao pode devolver P2."""
    assert tri.subir_nivel("P1") == "P1"


def test_alerta_aberto_que_estoura_o_prazo_sobe_um_nivel():
    antigo = (datetime.now() - timedelta(hours=49)).isoformat(timespec="seconds")
    resultado = tri.aplicar(pd.DataFrame([linha(criado_em=antigo)]))
    assert resultado.loc[0, "nivel"] == "P3"      # era P4
    assert bool(resultado.loc[0, "escalado"]) is True


def test_escalonamento_nunca_passa_do_teto():
    """Atraso nao transforma evento sem risco de vida em emergencia."""
    antigo = (datetime.now() - timedelta(days=30)).isoformat(timespec="seconds")
    registro = linha(categoria="Granizo", severidade="Alta", criado_em=antigo)
    resultado = tri.aplicar(pd.DataFrame([registro]))
    assert resultado.loc[0, "nivel"] == TETO_ESCALONAMENTO
    assert resultado.loc[0, "nivel"] != "P1"


def test_alerta_ja_acionado_nao_escalona():
    """O relogio de acionamento para quando o orgao e acionado."""
    criado = datetime.now() - timedelta(hours=49)
    registro = linha(criado_em=criado.isoformat(timespec="seconds"),
                     acionado_em=(criado + timedelta(minutes=30)).isoformat(
                         timespec="seconds"),
                     status="Em atendimento")
    resultado = tri.aplicar(pd.DataFrame([registro]))
    assert bool(resultado.loc[0, "escalado"]) is False
    assert resultado.loc[0, "nivel"] == "P4"


def test_alerta_dentro_do_prazo_nao_escalona():
    recente = (datetime.now() - timedelta(hours=10)).isoformat(timespec="seconds")
    resultado = tri.aplicar(pd.DataFrame([linha(criado_em=recente)]))
    assert bool(resultado.loc[0, "escalado"]) is False


def test_alerta_em_atendimento_nao_escalona():
    """Escalonamento e para quem foi esquecido, nao para quem ja esta sendo visto."""
    antigo = (datetime.now() - timedelta(hours=49)).isoformat(timespec="seconds")
    resultado = tri.aplicar(pd.DataFrame(
        [linha(criado_em=antigo, status="Em atendimento")]))
    assert bool(resultado.loc[0, "escalado"]) is False


# ---------------------------------------------------------------------------
# SLA
# ---------------------------------------------------------------------------


def test_prazo_de_acionamento_sai_da_tabela_do_nivel():
    criado = datetime.now()
    sla = tri.avaliar_sla(linha(criado_em=criado.isoformat(timespec="seconds")), "P1")
    prazo = datetime.fromisoformat(sla["prazo_acionamento"])
    assert round((prazo - criado).total_seconds() / 60) == 15
    assert sla["situacao"] == "No prazo"
    assert sla["dentro_do_sla"] is True


def test_prazo_estourado_e_marcado_como_vencido():
    antigo = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
    sla = tri.avaliar_sla(linha(criado_em=antigo), "P1")
    assert sla["situacao"] == "VENCIDO"
    assert sla["minutos_restantes"] < 0
    assert sla["dentro_do_sla"] is False


def test_faixa_de_atencao_antes_de_vencer():
    """Nos ultimos 30% do prazo o alerta muda de cor na central."""
    criado = (datetime.now() - timedelta(minutes=55)).isoformat(timespec="seconds")
    assert tri.avaliar_sla(linha(criado_em=criado), "P2")["situacao"] == "Atencao"


def test_acionamento_dentro_e_fora_do_prazo():
    criado = datetime.now() - timedelta(hours=2)
    registro = linha(criado_em=criado.isoformat(timespec="seconds"))

    no_prazo = dict(registro, acionado_em=(
        criado + timedelta(minutes=10)).isoformat(timespec="seconds"))
    assert tri.avaliar_sla(no_prazo, "P1")["situacao"] == "Acionado"

    atrasado = dict(registro, acionado_em=(
        criado + timedelta(minutes=40)).isoformat(timespec="seconds"))
    assert tri.avaliar_sla(atrasado, "P1")["situacao"] == "Acionado fora do prazo"


@pytest.mark.parametrize("minutos,esperado", [
    (45, "45min restantes"),
    (80, "1h 20min restantes"),
    (2880, "2d 0h restantes"),
    (-45, "atrasado 45min"),
    (0, "0min restantes"),
])
def test_formatar_prazo(minutos, esperado):
    assert tri.formatar_prazo(minutos) == esperado


# ---------------------------------------------------------------------------
# Aplicacao em lote
# ---------------------------------------------------------------------------


def test_aplicar_em_tabela_vazia_devolve_as_colunas():
    """A central abre sem nenhum alerta cadastrado e nao pode quebrar."""
    resultado = tri.aplicar(pd.DataFrame())
    for coluna in ("nivel", "nivel_nome", "motivo_nivel", "escalado", "situacao_sla"):
        assert coluna in resultado.columns
    assert resultado.empty


def test_aplicar_preserva_as_colunas_originais():
    resultado = tri.aplicar(pd.DataFrame([linha(protocolo="OC2026-00001")]))
    assert resultado.loc[0, "protocolo"] == "OC2026-00001"
    assert resultado.loc[0, "nivel_nome"] == "ROTINA"
