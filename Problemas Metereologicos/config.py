"""
Configuracoes fixas do projeto.
Centralizar aqui evita espalhar "numero magico" pelo codigo.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
PASTA_BASE = Path(__file__).parent
PASTA_DADOS = PASTA_BASE / "data"
PASTA_FOTOS = PASTA_DADOS / "fotos"
CAMINHO_BANCO = PASTA_DADOS / "ocorrencias.db"

# ---------------------------------------------------------------------------
# Mapa
# ---------------------------------------------------------------------------
# Centro padrao do mapa ao abrir o app (Pirapozinho - SP).
CENTRO_PADRAO = (-22.2747, -51.5019)
ZOOM_PADRAO = 14

# Raio (m) para considerar que dois relatos sao do MESMO evento
RAIO_DUPLICIDADE_M = 50

# Precisao de GPS acima disso e considerada ruim (gera aviso na tela)
PRECISAO_GPS_RUIM_M = 100

# ---------------------------------------------------------------------------
# Classificacao de emergencia (triagem)
# ---------------------------------------------------------------------------
# sla_acionamento_min -> prazo para acionar o orgao responsavel
# sla_resolucao_h     -> prazo para encerrar a ocorrencia
ORDEM_NIVEIS = ["P1", "P2", "P3", "P4"]

# Teto do escalonamento automatico por SLA vencido.
# P1 so e atingido por criterio real de risco a vida - nunca por atraso,
# senao a fila inteira vira "emergencia" e a triagem perde o sentido.
TETO_ESCALONAMENTO = "P2"

NIVEIS = {
    "P1": {
        "nome": "EMERGENCIA",
        "cor": "#B71C1C",
        "emoji": "🔴",
        "descricao": "Risco iminente a vida ou a integridade fisica.",
        "acao": "Acionamento imediato e deslocamento de equipe.",
        "sla_acionamento_min": 15,
        "sla_resolucao_h": 2,
    },
    "P2": {
        "nome": "URGENCIA",
        "cor": "#EF6C00",
        "emoji": "🟠",
        "descricao": "Risco alto de agravamento, sem vitima identificada.",
        "acao": "Acionar o orgao responsavel e monitorar ate a resposta.",
        "sla_acionamento_min": 60,
        "sla_resolucao_h": 12,
    },
    "P3": {
        "nome": "PRIORITARIO",
        "cor": "#F9A825",
        "emoji": "🟡",
        "descricao": "Dano material ou transtorno relevante a circulacao.",
        "acao": "Programar atendimento no proximo turno de trabalho.",
        "sla_acionamento_min": 480,     # 8 h
        "sla_resolucao_h": 72,
    },
    "P4": {
        "nome": "ROTINA",
        "cor": "#2E7D32",
        "emoji": "🟢",
        "descricao": "Sem risco imediato; entra na fila normal de servico.",
        "acao": "Incluir na programacao ordinaria da Prefeitura.",
        "sla_acionamento_min": 2880,    # 48 h
        "sla_resolucao_h": 360,         # 15 dias
    },
}

# ---------------------------------------------------------------------------
# Tipos de evento
# ---------------------------------------------------------------------------
# peso        -> risco intrinseco (entra no score de prioridade)
# risco_vital -> evento capaz de matar em minutos (dispara P1 na triagem)
# orgao       -> quem deve ser acionado primeiro
# cobrade     -> Classificacao e Codificacao Brasileira de Desastres (S2iD)
CATEGORIAS = {
    "Alagamento / enchente": {
        "cor": "blue", "icone": "water", "peso": 4, "risco_vital": False,
        "orgao": "Defesa Civil", "cobrade": "1.2.3.0.0 - Alagamentos",
    },
    "Enxurrada / inundacao": {
        "cor": "darkblue", "icone": "house-flood-water", "peso": 5,
        "risco_vital": True, "orgao": "Defesa Civil",
        "cobrade": "1.2.2.0.0 - Enxurradas",
    },
    "Deslizamento de terra": {
        "cor": "beige", "icone": "mountain", "peso": 5, "risco_vital": True,
        "orgao": "Defesa Civil",
        "cobrade": "1.1.3.2.1 - Deslizamento de solo e/ou rocha",
    },
    "Arvore caida": {
        "cor": "darkgreen", "icone": "tree", "peso": 3, "risco_vital": False,
        "orgao": "Bombeiros", "cobrade": "",
    },
    "Vendaval / destelhamento": {
        "cor": "lightgray", "icone": "wind", "peso": 4, "risco_vital": False,
        "orgao": "Defesa Civil", "cobrade": "1.3.2.1.5 - Vendaval",
    },
    "Granizo": {
        "cor": "lightblue", "icone": "icicles", "peso": 3, "risco_vital": False,
        "orgao": "Defesa Civil", "cobrade": "1.3.2.1.3 - Granizo",
    },
    "Raio / incendio": {
        "cor": "red", "icone": "bolt-lightning", "peso": 5, "risco_vital": True,
        "orgao": "Bombeiros", "cobrade": "1.3.2.1.2 - Tempestade de raios",
    },
    "Fio de energia rompido": {
        "cor": "orange", "icone": "bolt", "peso": 5, "risco_vital": True,
        "orgao": "Concessionaria de energia", "cobrade": "",
    },
    "Erosao / rachadura em encosta": {
        "cor": "darkred", "icone": "house-crack", "peso": 4, "risco_vital": True,
        "orgao": "Defesa Civil", "cobrade": "1.1.4.3.2 - Erosao continental (ravinas)",
    },
    "Bueiro entupido / boca de lobo": {
        "cor": "cadetblue", "icone": "circle-notch", "peso": 2,
        "risco_vital": False, "orgao": "Prefeitura", "cobrade": "",
    },
    "Buraco na via": {
        "cor": "orange", "icone": "road", "peso": 2, "risco_vital": False,
        "orgao": "Prefeitura", "cobrade": "",
    },
    "Via interditada / obstruida": {
        "cor": "purple", "icone": "road-barrier", "peso": 3,
        "risco_vital": False, "orgao": "Prefeitura", "cobrade": "",
    },
    "Outros": {
        "cor": "gray", "icone": "triangle-exclamation", "peso": 1,
        "risco_vital": False, "orgao": "Prefeitura", "cobrade": "",
    },
}

SEVERIDADES = {
    "Baixa":   {"peso": 1, "emoji": "🟢"},
    "Media":   {"peso": 2, "emoji": "🟡"},
    "Alta":    {"peso": 3, "emoji": "🟠"},
    "Critica": {"peso": 4, "emoji": "🔴"},
}

STATUS = ["Aberto", "Em atendimento", "Resolvido", "Improcedente"]

CORES_STATUS = {
    "Aberto": "#E53935",
    "Em atendimento": "#FB8C00",
    "Resolvido": "#43A047",
    "Improcedente": "#757575",
}

# Telefones de emergencia (padrao nacional brasileiro)
ORGAOS = {
    "Defesa Civil": "199",
    "Bombeiros": "193",
    "SAMU": "192",
    "Policia Militar": "190",
    "Concessionaria de energia": "0800 010 0196",
    "Prefeitura": "156",
}

# ---------------------------------------------------------------------------
# Score de prioridade (ordena a fila DENTRO de cada nivel)
# ---------------------------------------------------------------------------
PESO_SEVERIDADE = 2
BONUS_EMERGENCIA = 6
BONUS_PESSOAS_RISCO = 5
BONUS_POR_CONFIRMACAO = 2
MAX_CONFIRMACOES_PONTUADAS = 5

# Atualizacao automatica do painel de emergencia (segundos)
SEGUNDOS_AUTOREFRESH = 30

# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
EXTENSOES_IMAGEM = ["jpg", "jpeg", "png", "webp"]
LARGURA_MAX_FOTO = 1280
