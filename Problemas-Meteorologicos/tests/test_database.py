"""Testes da camada de dados: protocolo, fluxo, fila, proximidade e painel."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

import database as db
from config import CENTRO_PADRAO, RAIO_DUPLICIDADE_M

LAT, LON = CENTRO_PADRAO


def criar(**campos) -> str:
    base = dict(categoria="Alagamento / enchente", severidade="Media",
                descricao="Agua na pista", latitude=LAT, longitude=LON)
    base.update(campos)
    return db.inserir_ocorrencia(**base)


def por_protocolo(protocolo: str):
    dados = db.listar_ocorrencias(texto=protocolo)
    assert not dados.empty, f"protocolo {protocolo} nao encontrado"
    return dados.iloc[0]


# ---------------------------------------------------------------------------
# Protocolo e criacao
# ---------------------------------------------------------------------------


def test_protocolo_segue_o_formato_e_a_sequencia(banco):
    ano = datetime.now().year
    assert criar() == f"OC{ano}-00001"
    assert criar() == f"OC{ano}-00002"


def test_alerta_nasce_aberto_com_historico(banco):
    protocolo = criar(origem_coordenada="GPS", precisao_gps=8.5, autor="Miguel")
    alerta = por_protocolo(protocolo)
    assert alerta["status"] == "Aberto"
    assert alerta["origem_coordenada"] == "GPS"
    assert alerta["precisao_gps"] == 8.5
    assert alerta["confirmacoes"] == 0

    historico = db.listar_historico(int(alerta["id"]))
    assert len(historico) == 1
    assert historico.iloc[0]["status_novo"] == "Aberto"
    assert historico.iloc[0]["responsavel"] == "Miguel"


def test_emergencia_fica_marcada_no_historico(banco):
    protocolo = criar(emergencia=True)
    historico = db.listar_historico(int(por_protocolo(protocolo)["id"]))
    assert "EMERGENCIA" in historico.iloc[0]["observacao"]


def test_autor_anonimo_vira_cidadao_no_historico(banco):
    protocolo = criar()
    historico = db.listar_historico(int(por_protocolo(protocolo)["id"]))
    assert historico.iloc[0]["responsavel"] == "Cidadao"


# ---------------------------------------------------------------------------
# Fluxo de atendimento
# ---------------------------------------------------------------------------


def test_mudanca_de_status_registra_o_antes_e_o_depois(banco):
    identificador = int(por_protocolo(criar())["id"])
    assert db.atualizar_status(identificador, "Em atendimento",
                               observacao="Equipe a caminho") is True

    historico = db.listar_historico(identificador)
    assert len(historico) == 2
    recente = historico.iloc[0]
    assert (recente["status_anterior"], recente["status_novo"]) == (
        "Aberto", "Em atendimento")
    assert recente["responsavel"] == "Defesa Civil"


def test_status_repetido_nao_polui_o_historico(banco):
    identificador = int(por_protocolo(criar())["id"])
    assert db.atualizar_status(identificador, "Aberto") is False
    assert len(db.listar_historico(identificador)) == 1


def test_status_de_id_inexistente_devolve_false(banco):
    assert db.atualizar_status(999, "Resolvido") is False


def test_resolver_carimba_a_hora(banco):
    identificador = int(por_protocolo(criar())["id"])
    db.atualizar_status(identificador, "Resolvido")
    assert por_protocolo(f"OC{datetime.now().year}-00001")["resolvido_em"] is not None


def test_acionamento_grava_orgao_e_hora(banco):
    protocolo = criar()
    identificador = int(por_protocolo(protocolo)["id"])
    db.registrar_acionamento(identificador, "Bombeiros", responsavel="Plantao")

    alerta = por_protocolo(protocolo)
    assert alerta["orgao_acionado"] == "Bombeiros"
    assert alerta["acionado_em"] is not None

    historico = db.listar_historico(identificador)
    assert "Acionamento: Bombeiros" in historico.iloc[0]["observacao"]
    assert historico.iloc[0]["responsavel"] == "Plantao"


def test_acionamento_nao_inventa_mudanca_de_status(banco):
    """A linha de acionamento guarda o status atual dos dois lados."""
    identificador = int(por_protocolo(criar())["id"])
    db.registrar_acionamento(identificador, "Defesa Civil")
    linha = db.listar_historico(identificador).iloc[0]
    assert linha["status_anterior"] == linha["status_novo"] == "Aberto"


def test_excluir_leva_junto_historico_e_confirmacoes(banco):
    identificador = int(por_protocolo(criar())["id"])
    db.confirmar_ocorrencia(identificador, autor="Ana")
    db.excluir_ocorrencia(identificador)
    assert db.listar_ocorrencias().empty
    assert db.listar_historico(identificador).empty
    assert db.listar_confirmacoes(identificador).empty


# ---------------------------------------------------------------------------
# Confirmacao cruzada
# ---------------------------------------------------------------------------


def test_confirmacao_conta_e_eleva_a_prioridade(banco):
    protocolo = criar(categoria="Buraco na via", severidade="Baixa")
    identificador = int(por_protocolo(protocolo)["id"])
    assert por_protocolo(protocolo)["nivel"] == "P4"

    db.confirmar_ocorrencia(identificador, autor="Ana", comentario="Vi tambem")
    db.confirmar_ocorrencia(identificador, autor="Bruno")

    alerta = por_protocolo(protocolo)
    assert alerta["confirmacoes"] == 2
    assert alerta["nivel"] == "P3"
    assert len(db.listar_confirmacoes(identificador)) == 2


# ---------------------------------------------------------------------------
# Reclassificacao
# ---------------------------------------------------------------------------


def test_reclassificacao_persiste_e_aparece_na_triagem(banco):
    protocolo = criar(categoria="Buraco na via", severidade="Baixa")
    identificador = int(por_protocolo(protocolo)["id"])

    db.reclassificar(identificador, "P1", "Buraco tomou a pista inteira na curva",
                     responsavel="Engenharia")
    alerta = por_protocolo(protocolo)
    assert alerta["nivel"] == "P1"
    assert alerta["origem_nivel"] == "Manual"
    assert "pista inteira" in alerta["motivo_nivel"]

    observacao = db.listar_historico(identificador).iloc[0]["observacao"]
    assert "Reclassificado para P1" in observacao


def test_nivel_invalido_e_recusado(banco):
    identificador = int(por_protocolo(criar())["id"])
    with pytest.raises(ValueError):
        db.reclassificar(identificador, "P9", "motivo qualquer")


def test_reclassificar_id_inexistente_nao_quebra(banco):
    db.reclassificar(999, "P1", "nao existe")


# ---------------------------------------------------------------------------
# Score de prioridade
# ---------------------------------------------------------------------------


def test_score_soma_os_pesos_configurados():
    # Critica 4 x2 = 8, deslizamento peso 5, emergencia 6, pessoas 5,
    # 2 confirmacoes x2 = 4  ->  28
    assert db.calcular_prioridade({
        "severidade": "Critica", "categoria": "Deslizamento de terra",
        "emergencia": 1, "pessoas_em_risco": 1, "confirmacoes": 2}) == 28


def test_confirmacoes_param_de_pontuar_no_teto():
    base = {"severidade": "Baixa", "categoria": "Buraco na via",
            "emergencia": 0, "pessoas_em_risco": 0}
    assert (db.calcular_prioridade(dict(base, confirmacoes=5))
            == db.calcular_prioridade(dict(base, confirmacoes=50)))


def test_score_nao_muda_o_nivel(banco):
    """O score ordena dentro do nivel; quem decide o nivel e o discriminador."""
    protocolo = criar(categoria="Buraco na via", severidade="Baixa")
    identificador = int(por_protocolo(protocolo)["id"])
    for nome in ("Ana", "Bruno", "Carla", "Diego", "Eliane"):
        db.confirmar_ocorrencia(identificador, autor=nome)
    alerta = por_protocolo(protocolo)
    assert alerta["prioridade"] > 10
    assert alerta["nivel"] == "P3"      # nao P1, apesar do score alto


# ---------------------------------------------------------------------------
# Filtros e fila
# ---------------------------------------------------------------------------


def test_filtros_de_listagem(banco):
    criar(categoria="Buraco na via", severidade="Baixa", bairro="Centro")
    criar(categoria="Deslizamento de terra", severidade="Critica",
          emergencia=True, bairro="Vila Rica")

    assert len(db.listar_ocorrencias(categorias=["Buraco na via"])) == 1
    assert len(db.listar_ocorrencias(severidades=["Critica"])) == 1
    assert len(db.listar_ocorrencias(somente_emergencia=True)) == 1
    assert len(db.listar_ocorrencias(texto="Vila")) == 1
    assert len(db.listar_ocorrencias(status=["Resolvido"])) == 0


def test_listagem_em_banco_vazio_traz_as_colunas(banco):
    dados = db.listar_ocorrencias()
    assert dados.empty
    for coluna in ("nivel", "prioridade", "horas_aberta", "situacao_sla"):
        assert coluna in dados.columns


def test_fila_traz_a_emergencia_primeiro(banco):
    criar(categoria="Buraco na via", severidade="Baixa")
    grave = criar(categoria="Deslizamento de terra", severidade="Critica",
                  pessoas_em_risco=True)
    fila = db.fila_emergencia()
    assert fila.iloc[0]["protocolo"] == grave
    assert fila.iloc[0]["nivel"] == "P1"


def test_fila_ignora_encerradas(banco):
    identificador = int(por_protocolo(criar())["id"])
    db.atualizar_status(identificador, "Resolvido")
    assert db.fila_emergencia().empty


def test_fila_filtra_por_nivel(banco):
    criar(categoria="Buraco na via", severidade="Baixa")          # P4
    criar(categoria="Deslizamento de terra", severidade="Critica")  # P1
    assert len(db.fila_emergencia(niveis=["P1"])) == 1
    assert db.fila_emergencia(niveis=["P2"]).empty


def test_entre_dois_do_mesmo_nivel_vence_o_prazo_mais_apertado(banco, recuar):
    antigo = criar(categoria="Deslizamento de terra", severidade="Critica")
    recuar(antigo, minutes=10)
    criar(categoria="Deslizamento de terra", severidade="Critica")
    fila = db.fila_emergencia()
    assert fila.iloc[0]["protocolo"] == antigo   # o que esta ha mais tempo esperando


def test_horas_aberta_acompanha_o_relogio(banco, recuar):
    protocolo = criar()
    recuar(protocolo, hours=5)
    assert por_protocolo(protocolo)["horas_aberta"] == pytest.approx(5.0, abs=0.1)


# ---------------------------------------------------------------------------
# Proximidade / duplicidade
# ---------------------------------------------------------------------------


def test_proximas_encontra_dentro_do_raio_e_ignora_fora(banco):
    perto = criar(latitude=LAT + 0.0002)    # ~22 m
    criar(latitude=LAT + 0.0050)            # ~556 m

    achadas = db.buscar_proximas(LAT, LON, RAIO_DUPLICIDADE_M)
    assert list(achadas["protocolo"]) == [perto]
    assert achadas.iloc[0]["distancia_m"] < RAIO_DUPLICIDADE_M


def test_proximas_ordena_do_mais_perto_para_o_mais_longe(banco):
    longe = criar(latitude=LAT + 0.0004)
    perto = criar(latitude=LAT + 0.0001)
    achadas = db.buscar_proximas(LAT, LON, RAIO_DUPLICIDADE_M)
    assert list(achadas["protocolo"]) == [perto, longe]


def test_proximas_filtra_por_categoria(banco):
    criar(categoria="Alagamento / enchente")
    buraco = criar(categoria="Buraco na via")
    achadas = db.buscar_proximas(LAT, LON, RAIO_DUPLICIDADE_M,
                                 categoria="Buraco na via")
    assert list(achadas["protocolo"]) == [buraco]


def test_proximas_ignora_alertas_ja_resolvidos(banco):
    identificador = int(por_protocolo(criar())["id"])
    db.atualizar_status(identificador, "Resolvido")
    assert db.buscar_proximas(LAT, LON, RAIO_DUPLICIDADE_M).empty


def test_proximas_em_banco_vazio(banco):
    assert db.buscar_proximas(LAT, LON, RAIO_DUPLICIDADE_M).empty


def test_distancia_entre_pontos_conhecidos():
    assert db.distancia_metros(LAT, LON, LAT, LON) == 0
    # 0,001 grau de latitude ~ 111 m em qualquer lugar do planeta
    assert db.distancia_metros(LAT, LON, LAT + 0.001, LON) == pytest.approx(111, abs=2)


# ---------------------------------------------------------------------------
# Painel
# ---------------------------------------------------------------------------


def test_estatisticas_contam_o_que_o_painel_mostra(banco):
    criar(categoria="Deslizamento de terra", severidade="Critica",
          emergencia=True, pessoas_em_risco=True)
    resolvida = criar()
    db.atualizar_status(int(por_protocolo(resolvida)["id"]), "Resolvido")

    numeros = db.estatisticas()
    assert numeros["total"] == 2
    assert numeros["abertas"] == 1
    assert numeros["resolvidas"] == 1
    assert numeros["emergencias_ativas"] == 1
    assert numeros["pessoas_em_risco"] == 1
    assert numeros["tempo_medio_horas"] is not None


def test_estatisticas_em_banco_vazio(banco):
    numeros = db.estatisticas()
    assert numeros["total"] == 0
    assert numeros["tempo_medio_horas"] is None
    assert numeros["tempo_medio_acionamento_min"] is None


def test_resumo_por_nivel_sempre_lista_os_quatro(banco):
    criar(categoria="Deslizamento de terra", severidade="Critica")
    resumo = db.resumo_por_nivel()
    assert len(resumo) == 4
    assert int(resumo[resumo["Nivel"].str.contains("P1")]["Pendentes"].iloc[0]) == 1


def test_resumo_por_nivel_em_banco_vazio(banco):
    resumo = db.resumo_por_nivel()
    assert len(resumo) == 4
    assert resumo["Pendentes"].sum() == 0


def test_aderencia_sla_conta_so_os_acionados(banco):
    no_prazo = criar(categoria="Buraco na via", severidade="Baixa")
    db.registrar_acionamento(int(por_protocolo(no_prazo)["id"]), "Prefeitura")
    criar()  # nunca acionado, fica de fora da conta

    aderencia = db.aderencia_sla()
    assert aderencia["acionados"] == 1
    assert aderencia["no_prazo"] == 1
    assert aderencia["percentual"] == 100.0


def test_aderencia_sla_sem_acionamento(banco):
    criar()
    assert db.aderencia_sla()["percentual"] is None


# ---------------------------------------------------------------------------
# Migracao
# ---------------------------------------------------------------------------


def test_migracao_adiciona_colunas_em_banco_antigo(banco):
    """Banco de uma versao anterior nao pode exigir apagar o .db."""
    with db.conectar() as conexao:
        conexao.execute("DROP TABLE ocorrencias")
        conexao.execute(
            "CREATE TABLE ocorrencias ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT, protocolo TEXT UNIQUE,"
            " categoria TEXT NOT NULL, severidade TEXT NOT NULL, descricao TEXT,"
            " latitude REAL NOT NULL, longitude REAL NOT NULL,"
            " referencia TEXT, bairro TEXT, autor TEXT, contato TEXT, foto TEXT,"
            " status TEXT NOT NULL DEFAULT 'Aberto', resolvido_em TEXT,"
            " criado_em TEXT NOT NULL, atualizado_em TEXT NOT NULL)")
        agora = datetime.now().isoformat(timespec="seconds")
        conexao.execute(
            "INSERT INTO ocorrencias (protocolo, categoria, severidade, latitude,"
            " longitude, criado_em, atualizado_em)"
            " VALUES ('OC2025-00001','Buraco na via','Baixa',?,?,?,?)",
            (LAT, LON, agora, agora))

    db.criar_tabelas()   # roda a migracao

    antigo = por_protocolo("OC2025-00001")
    assert antigo["emergencia"] == 0
    assert antigo["origem_coordenada"] == "Mapa"
    assert antigo["nivel"] == "P4"
    criar()   # o banco migrado continua aceitando alertas novos


def test_criar_tabelas_e_idempotente(banco):
    criar()
    db.criar_tabelas()
    db.criar_tabelas()
    assert len(db.listar_ocorrencias()) == 1
