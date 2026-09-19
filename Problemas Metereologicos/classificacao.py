"""
Classificacao de emergencia (triagem) e controle de SLA.

O modelo segue a logica dos protocolos de triagem usados em emergencia:
uma lista ordenada de DISCRIMINADORES - o primeiro que se aplica define o
nivel. Isso torna a decisao auditavel: todo alerta guarda o motivo pelo qual
recebeu aquela prioridade.

Niveis:
    P1 EMERGENCIA  (vermelho) - risco iminente a vida
    P2 URGENCIA    (laranja)  - risco alto, sem vitima no momento
    P3 PRIORITARIO (amarelo)  - dano material ou transtorno relevante
    P4 ROTINA      (verde)    - sem risco imediato

Regras complementares:
    - a Defesa Civil pode RECLASSIFICAR manualmente (triagem humana vence);
    - o alerta ESCALA um nivel automaticamente se estourar o SLA de
      acionamento sem ter sido acionado.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from config import (
    CATEGORIAS,
    NIVEIS,
    ORDEM_NIVEIS,
    SEVERIDADES,
    TETO_ESCALONAMENTO,
)

# ---------------------------------------------------------------------------
# Auxiliares de leitura da linha
# ---------------------------------------------------------------------------
def _peso_severidade(linha) -> int:
    return SEVERIDADES.get(linha["severidade"], {}).get("peso", 1)


def _risco_vital(linha) -> bool:
    """Tipos de evento que, por natureza, podem matar em minutos."""
    return bool(CATEGORIAS.get(linha["categoria"], {}).get("risco_vital", False))


def _confirmacoes(linha) -> int:
    return int(linha.get("confirmacoes", 0) or 0)


def _sim(linha, campo: str) -> bool:
    return bool(int(linha.get(campo, 0) or 0))


# ---------------------------------------------------------------------------
# Discriminadores - a ORDEM importa: o primeiro que bate define o nivel
# ---------------------------------------------------------------------------
DISCRIMINADORES: list[tuple[str, str, callable]] = [
    # --------------------------- P1 - EMERGENCIA ---------------------------
    ("P1", "Pessoas ilhadas, feridas ou presas no local",
     lambda l: _sim(l, "pessoas_em_risco")),

    ("P1", "Evento com risco vital direto e gravidade alta ou critica",
     lambda l: _risco_vital(l) and _peso_severidade(l) >= 3),

    ("P1", "Emergencia declarada pelo cidadao com gravidade critica",
     lambda l: _sim(l, "emergencia") and _peso_severidade(l) >= 4),

    ("P1", "Multiplas confirmacoes em evento critico (evento de massa)",
     lambda l: _peso_severidade(l) >= 4 and _confirmacoes(l) >= 3),

    # ---------------------------- P2 - URGENCIA ----------------------------
    ("P2", "Emergencia declarada pelo cidadao",
     lambda l: _sim(l, "emergencia")),

    ("P2", "Gravidade critica sem vitima identificada",
     lambda l: _peso_severidade(l) >= 4),

    ("P2", "Evento com risco vital direto",
     lambda l: _risco_vital(l)),

    ("P2", "Gravidade alta confirmada por outros cidadaos",
     lambda l: _peso_severidade(l) >= 3 and _confirmacoes(l) >= 2),

    # -------------------------- P3 - PRIORITARIO ---------------------------
    ("P3", "Gravidade alta",
     lambda l: _peso_severidade(l) >= 3),

    ("P3", "Evento confirmado por outros cidadaos",
     lambda l: _confirmacoes(l) >= 2),

    ("P3", "Tipo de evento com risco relevante de agravamento",
     lambda l: CATEGORIAS.get(l["categoria"], {}).get("peso", 1) >= 4),
]

NIVEL_PADRAO = ("P4", "Sem risco imediato identificado")


# ---------------------------------------------------------------------------
# Classificacao
# ---------------------------------------------------------------------------
def classificar(linha) -> dict:
    """
    Devolve a triagem do alerta:
        {"nivel", "motivo", "origem"}  origem = 'Manual' ou 'Automatica'
    """
    manual = linha.get("classificacao_manual")
    if isinstance(manual, str) and manual in NIVEIS:
        return {
            "nivel": manual,
            "motivo": linha.get("motivo_classificacao")
                      or "Reclassificado pela equipe",
            "origem": "Manual",
        }

    for nivel, motivo, condicao in DISCRIMINADORES:
        try:
            if condicao(linha):
                return {"nivel": nivel, "motivo": motivo, "origem": "Automatica"}
        except (KeyError, TypeError):
            continue

    return {"nivel": NIVEL_PADRAO[0], "motivo": NIVEL_PADRAO[1],
            "origem": "Automatica"}


def subir_nivel(nivel: str) -> str:
    """
    Escalonamento automatico: P4 -> P3 -> P2.

    O teto e TETO_ESCALONAMENTO (P2). Atraso no atendimento nao transforma
    um evento sem risco de vida em emergencia - P1 depende sempre de um
    discriminador clinico/operacional real.
    """
    teto = ORDEM_NIVEIS.index(TETO_ESCALONAMENTO)
    indice = ORDEM_NIVEIS.index(nivel)
    if indice <= teto:
        # P1 e o proprio teto ja estao no topo do que o escalonamento alcanca.
        # Sem esta guarda, subir_nivel("P1") devolvia "P2" - rebaixava a
        # emergencia. Hoje aplicar() nao chega aqui com P1, mas a funcao e
        # publica e nao pode depender de quem chama para se comportar.
        return nivel
    return ORDEM_NIVEIS[max(indice - 1, teto)]


# ---------------------------------------------------------------------------
# SLA
# ---------------------------------------------------------------------------
def avaliar_sla(linha, nivel: str) -> dict:
    """
    Calcula o prazo de acionamento e a situacao atual.

        situacao: 'Acionado' | 'No prazo' | 'Atencao' | 'VENCIDO'
        minutos_restantes: negativo quando estourou
    """
    regra = NIVEIS[nivel]
    criado = datetime.fromisoformat(linha["criado_em"])
    prazo = criado + timedelta(minutes=regra["sla_acionamento_min"])

    acionado = linha.get("acionado_em")
    if isinstance(acionado, str) and acionado:
        momento = datetime.fromisoformat(acionado)
        minutos = round((prazo - momento).total_seconds() / 60)
        return {
            "prazo_acionamento": prazo.isoformat(timespec="seconds"),
            "minutos_restantes": minutos,
            "situacao": "Acionado" if minutos >= 0 else "Acionado fora do prazo",
            "dentro_do_sla": minutos >= 0,
        }

    minutos = round((prazo - datetime.now()).total_seconds() / 60)
    if minutos < 0:
        situacao = "VENCIDO"
    elif minutos <= regra["sla_acionamento_min"] * 0.3:
        situacao = "Atencao"
    else:
        situacao = "No prazo"

    return {
        "prazo_acionamento": prazo.isoformat(timespec="seconds"),
        "minutos_restantes": minutos,
        "situacao": situacao,
        "dentro_do_sla": minutos >= 0,
    }


def formatar_prazo(minutos: int) -> str:
    """Converte minutos em texto curto: '1h 20min restantes' / 'atrasado 45min'."""
    atrasado = minutos < 0
    minutos = abs(int(minutos))
    horas, resto = divmod(minutos, 60)
    if horas >= 24:
        dias, horas = divmod(horas, 24)
        texto = f"{dias}d {horas}h"
    elif horas:
        texto = f"{horas}h {resto}min"
    else:
        texto = f"{resto}min"
    return f"atrasado {texto}" if atrasado else f"{texto} restantes"


# ---------------------------------------------------------------------------
# Aplicacao em lote (usado pelo database)
# ---------------------------------------------------------------------------
def aplicar(dados: pd.DataFrame) -> pd.DataFrame:
    """
    Acrescenta ao DataFrame as colunas de triagem:
        nivel, nivel_nome, nivel_cor, motivo_nivel, origem_nivel,
        escalado, prazo_acionamento, minutos_sla, situacao_sla
    """
    colunas = ["nivel", "nivel_nome", "nivel_cor", "motivo_nivel", "origem_nivel",
               "escalado", "prazo_acionamento", "minutos_sla", "situacao_sla"]
    if dados.empty:
        for coluna in colunas:
            dados[coluna] = []
        return dados

    registros = []
    for _, linha in dados.iterrows():
        triagem = classificar(linha)
        nivel = triagem["nivel"]
        sla = avaliar_sla(linha, nivel)

        # Escalonamento automatico: estourou o prazo e ninguem acionou
        escalado = False
        if (
            sla["situacao"] == "VENCIDO"
            and linha["status"] == "Aberto"
            and nivel not in ("P1", TETO_ESCALONAMENTO)
        ):
            nivel = subir_nivel(nivel)
            escalado = True
            sla = avaliar_sla(linha, nivel)

        registros.append({
            "nivel": nivel,
            "nivel_nome": NIVEIS[nivel]["nome"],
            "nivel_cor": NIVEIS[nivel]["cor"],
            "motivo_nivel": triagem["motivo"],
            "origem_nivel": triagem["origem"],
            "escalado": escalado,
            "prazo_acionamento": sla["prazo_acionamento"],
            "minutos_sla": sla["minutos_restantes"],
            "situacao_sla": sla["situacao"],
        })

    triagens = pd.DataFrame(registros, index=dados.index)
    return pd.concat([dados, triagens], axis=1)
