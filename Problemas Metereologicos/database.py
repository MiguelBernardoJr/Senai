"""
Camada de acesso ao banco SQLite.

Toda leitura/escrita passa por aqui - a tela (app.py) nunca escreve SQL direto.

Tabelas:
    ocorrencias      -> estado ATUAL de cada evento registrado
    historico_status -> uma linha por mudanca de status (auditoria/evolucao)
    confirmacoes     -> outros cidadaos confirmando o MESMO evento
"""

from __future__ import annotations

import math
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Iterable

import pandas as pd

import classificacao as tri
from config import (
    BONUS_EMERGENCIA,
    BONUS_PESSOAS_RISCO,
    BONUS_POR_CONFIRMACAO,
    CAMINHO_BANCO,
    CATEGORIAS,
    MAX_CONFIRMACOES_PONTUADAS,
    NIVEIS,
    ORDEM_NIVEIS,
    PASTA_FOTOS,
    PESO_SEVERIDADE,
    SEVERIDADES,
)


# ---------------------------------------------------------------------------
# Conexao
# ---------------------------------------------------------------------------
@contextmanager
def conectar():
    """Abre a conexao, faz commit no sucesso e sempre fecha no final."""
    CAMINHO_BANCO.parent.mkdir(parents=True, exist_ok=True)
    PASTA_FOTOS.mkdir(parents=True, exist_ok=True)

    conexao = sqlite3.connect(CAMINHO_BANCO, check_same_thread=False)
    conexao.row_factory = sqlite3.Row  # acessar coluna pelo nome
    conexao.execute("PRAGMA foreign_keys = ON")
    try:
        yield conexao
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def criar_tabelas() -> None:
    """Cria as tabelas na primeira execucao. Seguro chamar sempre."""
    with conectar() as conexao:
        conexao.executescript(
            """
            CREATE TABLE IF NOT EXISTS ocorrencias (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                protocolo          TEXT    UNIQUE,
                categoria          TEXT    NOT NULL,
                severidade         TEXT    NOT NULL,
                descricao          TEXT,
                latitude           REAL    NOT NULL,
                longitude          REAL    NOT NULL,
                precisao_gps       REAL,
                origem_coordenada  TEXT    DEFAULT 'Mapa',
                referencia         TEXT,
                bairro             TEXT,
                autor              TEXT,
                contato            TEXT,
                foto               TEXT,
                emergencia         INTEGER NOT NULL DEFAULT 0,
                pessoas_em_risco   INTEGER NOT NULL DEFAULT 0,
                status             TEXT    NOT NULL DEFAULT 'Aberto',
                classificacao_manual  TEXT,
                motivo_classificacao  TEXT,
                orgao_acionado     TEXT,
                acionado_em        TEXT,
                criado_em          TEXT    NOT NULL,
                atualizado_em      TEXT    NOT NULL,
                resolvido_em       TEXT
            );

            CREATE TABLE IF NOT EXISTS historico_status (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                ocorrencia_id   INTEGER NOT NULL,
                status_anterior TEXT,
                status_novo     TEXT    NOT NULL,
                observacao      TEXT,
                responsavel     TEXT,
                criado_em       TEXT    NOT NULL,
                FOREIGN KEY (ocorrencia_id) REFERENCES ocorrencias(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS confirmacoes (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                ocorrencia_id INTEGER NOT NULL,
                autor         TEXT,
                comentario    TEXT,
                criado_em     TEXT NOT NULL,
                FOREIGN KEY (ocorrencia_id) REFERENCES ocorrencias(id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_ocorrencias_status
                ON ocorrencias(status);
            CREATE INDEX IF NOT EXISTS idx_ocorrencias_categoria
                ON ocorrencias(categoria);
            CREATE INDEX IF NOT EXISTS idx_ocorrencias_emergencia
                ON ocorrencias(emergencia);
            CREATE INDEX IF NOT EXISTS idx_historico_ocorrencia
                ON historico_status(ocorrencia_id);
            CREATE INDEX IF NOT EXISTS idx_confirmacoes_ocorrencia
                ON confirmacoes(ocorrencia_id);
            """
        )
    _migrar()


def _migrar() -> None:
    """
    Adiciona colunas novas em bancos criados por versoes anteriores do app.
    Evita ter que apagar o ocorrencias.db a cada evolucao do projeto.
    """
    novas_colunas = {
        "precisao_gps": "REAL",
        "origem_coordenada": "TEXT DEFAULT 'Mapa'",
        "emergencia": "INTEGER NOT NULL DEFAULT 0",
        "pessoas_em_risco": "INTEGER NOT NULL DEFAULT 0",
        "orgao_acionado": "TEXT",
        "acionado_em": "TEXT",
        "classificacao_manual": "TEXT",
        "motivo_classificacao": "TEXT",
    }
    with conectar() as conexao:
        existentes = {
            linha["name"]
            for linha in conexao.execute("PRAGMA table_info(ocorrencias)")
        }
        for coluna, tipo in novas_colunas.items():
            if coluna not in existentes:
                conexao.execute(
                    f"ALTER TABLE ocorrencias ADD COLUMN {coluna} {tipo}"
                )


def _agora() -> str:
    """Data/hora atual em texto ISO - padrao adotado no banco."""
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Escrita
# ---------------------------------------------------------------------------
def inserir_ocorrencia(
    categoria: str,
    severidade: str,
    descricao: str,
    latitude: float,
    longitude: float,
    precisao_gps: float | None = None,
    origem_coordenada: str = "Mapa",
    referencia: str = "",
    bairro: str = "",
    autor: str = "",
    contato: str = "",
    foto: str | None = None,
    emergencia: bool = False,
    pessoas_em_risco: bool = False,
) -> str:
    """Grava um novo evento e devolve o protocolo gerado."""
    agora = _agora()
    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO ocorrencias
                (categoria, severidade, descricao, latitude, longitude,
                 precisao_gps, origem_coordenada, referencia, bairro,
                 autor, contato, foto, emergencia, pessoas_em_risco,
                 status, criado_em, atualizado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Aberto', ?, ?)
            """,
            (
                categoria, severidade, descricao, latitude, longitude,
                precisao_gps, origem_coordenada, referencia, bairro,
                autor, contato, foto, int(emergencia), int(pessoas_em_risco),
                agora, agora,
            ),
        )
        novo_id = cursor.lastrowid

        protocolo = f"OC{datetime.now().year}-{novo_id:05d}"
        conexao.execute(
            "UPDATE ocorrencias SET protocolo = ? WHERE id = ?",
            (protocolo, novo_id),
        )

        conexao.execute(
            """
            INSERT INTO historico_status
                (ocorrencia_id, status_anterior, status_novo,
                 observacao, responsavel, criado_em)
            VALUES (?, NULL, 'Aberto', ?, ?, ?)
            """,
            (
                novo_id,
                "Alerta aberto pelo cidadao"
                + (" (EMERGENCIA)" if emergencia else ""),
                autor or "Cidadao",
                agora,
            ),
        )

    return protocolo


def confirmar_ocorrencia(
    ocorrencia_id: int, autor: str = "", comentario: str = ""
) -> None:
    """Outro cidadao confirma o mesmo evento - eleva a prioridade."""
    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO confirmacoes (ocorrencia_id, autor, comentario, criado_em)
            VALUES (?, ?, ?, ?)
            """,
            (ocorrencia_id, autor or "Anonimo", comentario, _agora()),
        )


def atualizar_status(
    ocorrencia_id: int,
    novo_status: str,
    observacao: str = "",
    responsavel: str = "",
) -> bool:
    """Muda o status e registra no historico. False se nada mudou."""
    agora = _agora()
    with conectar() as conexao:
        linha = conexao.execute(
            "SELECT status FROM ocorrencias WHERE id = ?", (ocorrencia_id,)
        ).fetchone()

        if linha is None or linha["status"] == novo_status:
            return False

        status_anterior = linha["status"]
        resolvido_em = agora if novo_status == "Resolvido" else None

        conexao.execute(
            """
            UPDATE ocorrencias
               SET status = ?, atualizado_em = ?, resolvido_em = ?
             WHERE id = ?
            """,
            (novo_status, agora, resolvido_em, ocorrencia_id),
        )
        conexao.execute(
            """
            INSERT INTO historico_status
                (ocorrencia_id, status_anterior, status_novo,
                 observacao, responsavel, criado_em)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (ocorrencia_id, status_anterior, novo_status,
             observacao, responsavel or "Defesa Civil", agora),
        )
    return True


def registrar_acionamento(
    ocorrencia_id: int, orgao: str, responsavel: str = ""
) -> None:
    """Marca qual orgao foi acionado e quando - prova de resposta."""
    agora = _agora()
    with conectar() as conexao:
        conexao.execute(
            """
            UPDATE ocorrencias
               SET orgao_acionado = ?, acionado_em = ?, atualizado_em = ?
             WHERE id = ?
            """,
            (orgao, agora, agora, ocorrencia_id),
        )
        conexao.execute(
            """
            INSERT INTO historico_status
                (ocorrencia_id, status_anterior, status_novo,
                 observacao, responsavel, criado_em)
            SELECT id, status, status, ?, ?, ?
              FROM ocorrencias WHERE id = ?
            """,
            (f"Acionamento: {orgao}", responsavel or "Defesa Civil",
             agora, ocorrencia_id),
        )


def excluir_ocorrencia(ocorrencia_id: int) -> None:
    """Remove o registro e tudo ligado a ele (uso em moderacao/teste)."""
    with conectar() as conexao:
        conexao.execute("DELETE FROM ocorrencias WHERE id = ?", (ocorrencia_id,))


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------
def listar_ocorrencias(
    categorias: Iterable[str] | None = None,
    status: Iterable[str] | None = None,
    severidades: Iterable[str] | None = None,
    somente_emergencia: bool = False,
    data_inicio: str | None = None,
    data_fim: str | None = None,
    texto: str = "",
) -> pd.DataFrame:
    """
    Devolve as ocorrencias filtradas ja com as colunas calculadas
    'confirmacoes', 'horas_aberta' e 'prioridade'.
    """
    sql = """
        SELECT o.*,
               (SELECT COUNT(*) FROM confirmacoes c
                 WHERE c.ocorrencia_id = o.id) AS confirmacoes
          FROM ocorrencias o
         WHERE 1 = 1
    """
    parametros: list = []

    def _filtro_lista(coluna: str, valores: Iterable[str] | None) -> None:
        valores = list(valores or [])
        if valores:
            nonlocal sql
            marcadores = ", ".join("?" for _ in valores)
            sql += f" AND o.{coluna} IN ({marcadores})"
            parametros.extend(valores)

    _filtro_lista("categoria", categorias)
    _filtro_lista("status", status)
    _filtro_lista("severidade", severidades)

    if somente_emergencia:
        sql += " AND o.emergencia = 1"
    if data_inicio:
        sql += " AND date(o.criado_em) >= date(?)"
        parametros.append(data_inicio)
    if data_fim:
        sql += " AND date(o.criado_em) <= date(?)"
        parametros.append(data_fim)
    if texto:
        sql += (" AND (o.descricao LIKE ? OR o.referencia LIKE ?"
                " OR o.bairro LIKE ? OR o.protocolo LIKE ?)")
        curinga = f"%{texto}%"
        parametros.extend([curinga] * 4)

    sql += " ORDER BY o.criado_em DESC"

    with conectar() as conexao:
        dados = pd.read_sql_query(sql, conexao, params=parametros)

    return _enriquecer(dados)


def _enriquecer(dados: pd.DataFrame) -> pd.DataFrame:
    """
    Acrescenta as colunas calculadas: score de prioridade, horas em aberto
    e toda a triagem (nivel, motivo, SLA) vinda de classificacao.py.
    """
    if dados.empty:
        for coluna in ["prioridade", "horas_aberta"]:
            dados[coluna] = []
        return tri.aplicar(dados)

    agora = datetime.now()
    dados["horas_aberta"] = dados["criado_em"].apply(
        lambda valor: round(
            (agora - datetime.fromisoformat(valor)).total_seconds() / 3600, 1
        )
    )
    dados["prioridade"] = dados.apply(calcular_prioridade, axis=1)
    return tri.aplicar(dados)


def calcular_prioridade(linha) -> int:
    """
    Score de atendimento. Quanto maior, mais urgente.

        gravidade x 2
      + risco do tipo de evento
      + bonus de emergencia declarada
      + bonus de pessoas em risco
      + confirmacoes de outros cidadaos (ate o limite configurado)
    """
    score = SEVERIDADES.get(linha["severidade"], {}).get("peso", 1) * PESO_SEVERIDADE
    score += CATEGORIAS.get(linha["categoria"], {}).get("peso", 1)

    if int(linha.get("emergencia", 0)):
        score += BONUS_EMERGENCIA
    if int(linha.get("pessoas_em_risco", 0)):
        score += BONUS_PESSOAS_RISCO

    confirmacoes = int(linha.get("confirmacoes", 0) or 0)
    score += min(confirmacoes, MAX_CONFIRMACOES_PONTUADAS) * BONUS_POR_CONFIRMACAO

    return int(score)


def fila_emergencia(niveis: Iterable[str] | None = None) -> pd.DataFrame:
    """
    Ocorrencias nao resolvidas ordenadas por:
        1) nivel de classificacao (P1 antes de P2, e assim por diante)
        2) prazo de SLA mais apertado
        3) score de prioridade
    """
    dados = listar_ocorrencias(status=["Aberto", "Em atendimento"])
    if dados.empty:
        return dados

    niveis = list(niveis or [])
    if niveis:
        dados = dados[dados["nivel"].isin(niveis)]
        if dados.empty:
            return dados

    dados["ordem_nivel"] = dados["nivel"].apply(ORDEM_NIVEIS.index)
    return (
        dados.sort_values(
            ["ordem_nivel", "minutos_sla", "prioridade"],
            ascending=[True, True, False],
        )
        .drop(columns=["ordem_nivel"])
        .reset_index(drop=True)
    )


def reclassificar(
    ocorrencia_id: int, nivel: str, motivo: str, responsavel: str = ""
) -> None:
    """
    Triagem humana sobrepondo a automatica.
    Fica registrado no historico - a decisao precisa ser auditavel.
    """
    if nivel not in NIVEIS:
        raise ValueError(f"Nivel invalido: {nivel}")

    agora = _agora()
    with conectar() as conexao:
        linha = conexao.execute(
            "SELECT status FROM ocorrencias WHERE id = ?", (ocorrencia_id,)
        ).fetchone()
        if linha is None:
            return

        conexao.execute(
            """
            UPDATE ocorrencias
               SET classificacao_manual = ?, motivo_classificacao = ?,
                   atualizado_em = ?
             WHERE id = ?
            """,
            (nivel, motivo, agora, ocorrencia_id),
        )
        conexao.execute(
            """
            INSERT INTO historico_status
                (ocorrencia_id, status_anterior, status_novo,
                 observacao, responsavel, criado_em)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (ocorrencia_id, linha["status"], linha["status"],
             f"Reclassificado para {nivel} ({NIVEIS[nivel]['nome']}): {motivo}",
             responsavel or "Defesa Civil", agora),
        )


def listar_historico(ocorrencia_id: int | None = None) -> pd.DataFrame:
    """Historico de mudancas. Sem parametro, traz o historico completo."""
    sql = """
        SELECT h.*, o.protocolo, o.categoria
          FROM historico_status h
          JOIN ocorrencias o ON o.id = h.ocorrencia_id
    """
    parametros: list = []
    if ocorrencia_id is not None:
        sql += " WHERE h.ocorrencia_id = ?"
        parametros.append(ocorrencia_id)
    sql += " ORDER BY h.criado_em DESC"

    with conectar() as conexao:
        return pd.read_sql_query(sql, conexao, params=parametros)


def listar_confirmacoes(ocorrencia_id: int) -> pd.DataFrame:
    with conectar() as conexao:
        return pd.read_sql_query(
            "SELECT * FROM confirmacoes WHERE ocorrencia_id = ? ORDER BY criado_em",
            conexao,
            params=[ocorrencia_id],
        )


def estatisticas() -> dict:
    """Numeros do topo dos paineis."""
    with conectar() as conexao:
        def _contar(condicao: str = "1 = 1") -> int:
            return conexao.execute(
                f"SELECT COUNT(*) FROM ocorrencias WHERE {condicao}"
            ).fetchone()[0]

        media = conexao.execute(
            """
            SELECT AVG((julianday(resolvido_em) - julianday(criado_em)) * 24)
              FROM ocorrencias WHERE resolvido_em IS NOT NULL
            """
        ).fetchone()[0]

        media_emergencia = conexao.execute(
            """
            SELECT AVG((julianday(acionado_em) - julianday(criado_em)) * 1440)
              FROM ocorrencias
             WHERE acionado_em IS NOT NULL AND emergencia = 1
            """
        ).fetchone()[0]

        # Aderencia ao SLA de acionamento (somente alertas ja acionados)
        sla = conexao.execute(
            """
            SELECT COUNT(*) FROM ocorrencias WHERE acionado_em IS NOT NULL
            """
        ).fetchone()[0]

        resultado = {
            "total": _contar(),
            "acionados": sla,
            "abertas": _contar("status = 'Aberto'"),
            "em_atendimento": _contar("status = 'Em atendimento'"),
            "resolvidas": _contar("status = 'Resolvido'"),
            "emergencias_ativas": _contar(
                "emergencia = 1 AND status IN ('Aberto', 'Em atendimento')"
            ),
            "pessoas_em_risco": _contar(
                "pessoas_em_risco = 1 AND status IN ('Aberto', 'Em atendimento')"
            ),
            "tempo_medio_horas": round(media, 1) if media is not None else None,
            "tempo_medio_acionamento_min": (
                round(media_emergencia, 1) if media_emergencia is not None else None
            ),
        }
    return resultado


# ---------------------------------------------------------------------------
# Geometria
# ---------------------------------------------------------------------------
def distancia_metros(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia entre dois pontos do globo (formula de Haversine)."""
    raio_terra = 6_371_000  # metros
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return 2 * raio_terra * math.asin(math.sqrt(a))


def buscar_proximas(
    latitude: float, longitude: float, raio_m: float, categoria: str | None = None
) -> pd.DataFrame:
    """
    Eventos ainda nao resolvidos perto do ponto informado.
    Usado para sugerir CONFIRMAR em vez de abrir um protocolo duplicado.
    """
    sql = """
        SELECT o.*,
               (SELECT COUNT(*) FROM confirmacoes c
                 WHERE c.ocorrencia_id = o.id) AS confirmacoes
          FROM ocorrencias o
         WHERE o.status <> 'Resolvido'
    """
    parametros: list = []
    if categoria:
        sql += " AND o.categoria = ?"
        parametros.append(categoria)

    with conectar() as conexao:
        dados = pd.read_sql_query(sql, conexao, params=parametros)

    if dados.empty:
        return dados

    dados["distancia_m"] = dados.apply(
        lambda linha: distancia_metros(
            latitude, longitude, linha["latitude"], linha["longitude"]
        ),
        axis=1,
    )
    proximas = dados[dados["distancia_m"] <= raio_m].copy()
    return proximas.sort_values("distancia_m")


def resumo_por_nivel() -> pd.DataFrame:
    """
    Quadro de classificacao: quantos alertas pendentes em cada nivel,
    quantos estao com o SLA de acionamento vencido e quantos escalaram.
    """
    fila = fila_emergencia()
    linhas = []
    for nivel in ORDEM_NIVEIS:
        regra = NIVEIS[nivel]
        do_nivel = fila[fila["nivel"] == nivel] if not fila.empty else fila
        linhas.append({
            "Nivel": f"{regra['emoji']} {nivel} {regra['nome']}",
            "Criterio": regra["descricao"],
            "SLA acionamento": _minutos_legivel(regra["sla_acionamento_min"]),
            "SLA resolucao": f"{regra['sla_resolucao_h']} h",
            "Pendentes": 0 if fila.empty else len(do_nivel),
            "SLA vencido": 0 if fila.empty else int(
                (do_nivel["situacao_sla"] == "VENCIDO").sum()
            ),
            "Escalados": 0 if fila.empty else int(do_nivel["escalado"].sum()),
        })
    return pd.DataFrame(linhas)


def _minutos_legivel(minutos: int) -> str:
    if minutos < 60:
        return f"{minutos} min"
    if minutos < 1440:
        return f"{minutos // 60} h"
    return f"{minutos // 1440} dias"


def aderencia_sla() -> dict:
    """Percentual de alertas acionados dentro do prazo do seu nivel."""
    dados = listar_ocorrencias()
    if dados.empty:
        return {"acionados": 0, "no_prazo": 0, "percentual": None}

    acionados = dados[dados["acionado_em"].notna()]
    if acionados.empty:
        return {"acionados": 0, "no_prazo": 0, "percentual": None}

    no_prazo = int((acionados["situacao_sla"] == "Acionado").sum())
    return {
        "acionados": len(acionados),
        "no_prazo": no_prazo,
        "percentual": round(100 * no_prazo / len(acionados), 1),
    }
