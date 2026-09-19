"""Testes dos servicos: despacho, links, foto e mapa."""

from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
import pytest

import servicos
from config import CENTRO_PADRAO, LARGURA_MAX_FOTO

LAT, LON = CENTRO_PADRAO


def alerta(**campos) -> pd.Series:
    base = {
        "protocolo": "OC2026-00007",
        "categoria": "Deslizamento de terra",
        "severidade": "Critica",
        "descricao": "Barranco cedeu sobre a calcada",
        "latitude": -22.2753,
        "longitude": -51.5000,
        "precisao_gps": 12.0,
        "origem_coordenada": "GPS",
        "referencia": "Rua das Flores, 120",
        "bairro": "Centro",
        "autor": "Miguel",
        "contato": "(18) 99999-0000",
        "emergencia": 1,
        "pessoas_em_risco": 1,
        "confirmacoes": 2,
        "status": "Aberto",
        "criado_em": datetime.now().isoformat(timespec="seconds"),
        "nivel": "P1",
        "motivo_nivel": "Pessoas ilhadas, feridas ou presas no local",
    }
    base.update(campos)
    return pd.Series(base)


# ---------------------------------------------------------------------------
# Despacho
# ---------------------------------------------------------------------------


def test_despacho_traz_o_que_a_equipe_precisa():
    texto = servicos.texto_despacho(alerta())
    for trecho in ("OC2026-00007", "P1", "EMERGENCIA",
                   "1.1.3.2.1", "PESSOAS EM RISCO", "Rua das Flores",
                   "-22.2753", "google.com/maps", "Defesa Civil", "199"):
        assert trecho in texto, f"faltou {trecho!r} no despacho"


def test_despacho_mostra_o_prazo_do_nivel():
    """Quem recebe no radio precisa saber em quanto tempo tem de estar la."""
    texto = servicos.texto_despacho(alerta())
    assert "15 min" in texto      # SLA de acionamento do P1
    assert "2 h" in texto         # SLA de resolucao do P1


def test_despacho_cita_o_motivo_da_classificacao():
    """A triagem tem de viajar junto com o alerta - a decisao e auditavel."""
    assert "Pessoas ilhadas" in servicos.texto_despacho(alerta())


def test_despacho_de_rotina_nao_inventa_urgencia():
    rotina = alerta(categoria="Buraco na via", severidade="Baixa",
                    emergencia=0, pessoas_em_risco=0, confirmacoes=0,
                    nivel="P4", motivo_nivel="Sem risco imediato identificado")
    texto = servicos.texto_despacho(rotina)
    assert "ROTINA" in texto
    assert "PESSOAS EM RISCO" not in texto
    assert "Prefeitura" in texto      # orgao do tipo, nao a Defesa Civil


def test_despacho_diz_a_precisao_quando_veio_do_gps():
    assert "GPS +/- 12 m" in servicos.texto_despacho(alerta())


def test_despacho_diz_a_origem_quando_veio_do_mapa():
    texto = servicos.texto_despacho(alerta(precisao_gps=None,
                                           origem_coordenada="Mapa"))
    assert "(Mapa)" in texto
    assert "GPS +/-" not in texto


def test_despacho_aguenta_alerta_sem_campo_opcional():
    minimo = alerta(referencia=None, bairro=None, autor=None, contato=None,
                    descricao=None, confirmacoes=0, pessoas_em_risco=0)
    texto = servicos.texto_despacho(minimo)
    assert "nao informado" in texto
    assert "Anonimo" in texto
    assert "sem contato" in texto


def test_despacho_de_categoria_sem_cobrade_nao_inventa_codigo():
    texto = servicos.texto_despacho(alerta(categoria="Buraco na via"))
    assert "COBRADE" not in texto


def test_despacho_de_nivel_desconhecido_nao_quebra():
    """Registro torto nao pode impedir o despacho de uma ocorrencia."""
    assert "OC2026-00007" in servicos.texto_despacho(alerta(nivel="P9"))


# ---------------------------------------------------------------------------
# Links
# ---------------------------------------------------------------------------


def test_link_aponta_para_a_coordenada():
    link = servicos.link_google_maps(-22.2753, -51.5)
    assert "-22.2753,-51.5" in link
    assert link.startswith("https://")


# ---------------------------------------------------------------------------
# Foto
# ---------------------------------------------------------------------------


def _imagem(largura=2400, altura=1800, modo="RGB") -> io.BytesIO:
    from PIL import Image
    buffer = io.BytesIO()
    Image.new(modo, (largura, altura), (120, 140, 160) if modo == "RGB" else 128)\
        .save(buffer, "PNG")
    buffer.seek(0)
    return buffer


def test_foto_e_reduzida_antes_de_gravar(tmp_path, monkeypatch):
    from PIL import Image
    monkeypatch.setattr(servicos, "PASTA_FOTOS", tmp_path)

    caminho = servicos.salvar_foto(_imagem())
    assert caminho.startswith("data/fotos/")
    gravada = tmp_path / caminho.split("/")[-1]
    assert gravada.exists()
    assert Image.open(gravada).width == LARGURA_MAX_FOTO


def test_foto_pequena_nao_e_esticada(tmp_path, monkeypatch):
    from PIL import Image
    monkeypatch.setattr(servicos, "PASTA_FOTOS", tmp_path)
    caminho = servicos.salvar_foto(_imagem(640, 480))
    assert Image.open(tmp_path / caminho.split("/")[-1]).width == 640


def test_foto_com_transparencia_vira_jpeg(tmp_path, monkeypatch):
    from PIL import Image
    monkeypatch.setattr(servicos, "PASTA_FOTOS", tmp_path)
    caminho = servicos.salvar_foto(_imagem(800, 600, modo="RGBA"))
    assert Image.open(tmp_path / caminho.split("/")[-1]).format == "JPEG"


def test_cada_foto_recebe_um_nome_proprio(tmp_path, monkeypatch):
    """Nome por uuid: dois cidadaos enviando junto nao sobrescrevem um ao outro."""
    monkeypatch.setattr(servicos, "PASTA_FOTOS", tmp_path)
    assert servicos.salvar_foto(_imagem(200, 200)) != \
           servicos.salvar_foto(_imagem(200, 200))


def test_sem_foto_devolve_none():
    assert servicos.salvar_foto(None) is None


def test_foto_ausente_no_disco_nao_quebra_o_popup():
    assert servicos._foto_em_base64(None) == ""
    assert servicos._foto_em_base64("data/fotos/nao-existe.jpg") == ""


# ---------------------------------------------------------------------------
# Mapa
# ---------------------------------------------------------------------------


def test_mapa_vazio_abre_no_centro_pedido():
    mapa = servicos.criar_mapa(CENTRO_PADRAO, 14)
    assert mapa.location == list(CENTRO_PADRAO)
    assert "openstreetmap" in mapa._repr_html_().lower()


def test_mapa_desenha_um_marcador_por_alerta():
    dados = pd.DataFrame([alerta(), alerta(protocolo="OC2026-00008",
                                           latitude=-22.28)])
    html = servicos.criar_mapa(CENTRO_PADRAO, 14, dados=dados)._repr_html_()
    assert "OC2026-00007" in html
    assert "OC2026-00008" in html


@pytest.mark.parametrize("criterio", ["categoria", "status", "prioridade"])
def test_mapa_aceita_os_tres_criterios_de_cor(criterio):
    dados = pd.DataFrame([alerta(prioridade=20)])
    mapa = servicos.criar_mapa(CENTRO_PADRAO, 14, dados=dados,
                               colorir_por=criterio)
    assert mapa._repr_html_()


def test_mapa_marca_o_ponto_escolhido_e_o_raio():
    mapa = servicos.criar_mapa(CENTRO_PADRAO, 14,
                               ponto_selecionado=(LAT, LON), raio_precisao=50)
    assert mapa._repr_html_()
