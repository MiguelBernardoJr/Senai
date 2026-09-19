"""Testes de gerar_cobertura(): 2 alertas de teste por categoria cadastrada."""

from __future__ import annotations

import database as db
import gerar_dados_exemplo as gerador
from classificacao import classificar
from config import CATEGORIAS, RAIO_DUPLICIDADE_M


def _gerar(banco, semente: int = 42):
    gerador.gerar_cobertura(semente=semente)
    return db.listar_ocorrencias()


def test_duas_ocorrencias_por_categoria_e_todas_presentes(banco):
    dados = _gerar(banco)

    contagem = dados["categoria"].value_counts().to_dict()

    assert set(contagem.keys()) == set(CATEGORIAS.keys())
    assert all(quantidade == 2 for quantidade in contagem.values())


def test_total_igual_a_duas_vezes_o_numero_de_categorias(banco):
    dados = _gerar(banco)

    assert len(dados) == 2 * len(CATEGORIAS)


def test_nenhum_par_de_pontos_fica_a_menos_de_50_metros(banco):
    dados = _gerar(banco)

    pontos = list(zip(dados["latitude"], dados["longitude"]))
    for i in range(len(pontos)):
        for j in range(i + 1, len(pontos)):
            lat1, lon1 = pontos[i]
            lat2, lon2 = pontos[j]
            distancia = db.distancia_metros(lat1, lon1, lat2, lon2)
            assert distancia >= RAIO_DUPLICIDADE_M


def test_determinismo_mesma_semente_mesmas_coordenadas(banco, tmp_path, monkeypatch):
    dados_1 = _gerar(banco)
    coordenadas_1 = sorted(zip(dados_1["latitude"], dados_1["longitude"]))

    # Novo banco isolado para a segunda rodada, mesma semente.
    monkeypatch.setattr(db, "CAMINHO_BANCO", tmp_path / "teste2.db")
    monkeypatch.setattr(db, "PASTA_FOTOS", tmp_path / "fotos2")
    dados_2 = _gerar(banco)
    coordenadas_2 = sorted(zip(dados_2["latitude"], dados_2["longitude"]))

    assert coordenadas_1 == coordenadas_2


def test_todos_abertos_e_sem_acionamento(banco):
    dados = _gerar(banco)

    assert (dados["status"] == "Aberto").all()
    assert dados["acionado_em"].isna().all()


def test_as_duas_origens_aparecem_uma_de_cada_por_categoria(banco):
    dados = _gerar(banco)

    for categoria in CATEGORIAS:
        origens = set(dados.loc[dados["categoria"] == categoria, "origem_coordenada"])
        assert origens == {"GPS", "Mapa"}


def test_ponto_grave_e_leve_recebem_niveis_de_triagem_diferentes(banco):
    dados = _gerar(banco)

    for categoria in CATEGORIAS:
        linhas = dados.loc[dados["categoria"] == categoria]
        niveis = {
            classificar(linha)["nivel"]
            for _, linha in linhas.iterrows()
        }
        assert len(niveis) == 2, (
            f"{categoria}: os dois pontos cairam no mesmo nivel de triagem"
        )


def test_limpar_banco_funciona_em_clone_novo(tmp_path, monkeypatch):
    """`--limpar` e o primeiro comando que alguem roda ao baixar o projeto.

    Antes desta correcao, limpar_banco() rodava DELETE antes de criar_tabelas()
    e quebrava com "no such table: confirmacoes" num banco que ainda nao existe.
    """
    monkeypatch.setattr(db, "CAMINHO_BANCO", tmp_path / "novo.db")
    monkeypatch.setattr(db, "PASTA_FOTOS", tmp_path / "fotos")
    assert not (tmp_path / "novo.db").exists()

    gerador.limpar_banco()          # nao pode levantar excecao

    assert db.listar_ocorrencias().empty
    gerador.gerar_cobertura(semente=1)
    assert len(db.listar_ocorrencias()) == 2 * len(CATEGORIAS)


def test_limpar_banco_apaga_tudo(banco):
    gerador.gerar_cobertura(semente=1)
    assert not db.listar_ocorrencias().empty

    gerador.limpar_banco()
    assert db.listar_ocorrencias().empty
    assert db.listar_historico().empty
