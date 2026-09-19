"""
Servicos de apoio:
  - captura de GPS do navegador
  - tratamento de imagem
  - montagem do mapa Folium
  - geracao do texto de despacho para as autoridades

Separado de app.py para a tela ficar enxuta.
"""

from __future__ import annotations

import base64
import uuid
from html import escape
from pathlib import Path

import folium
import pandas as pd
from folium.plugins import Fullscreen, HeatMap, LocateControl, MarkerCluster, MiniMap
from PIL import Image

from config import (
    CATEGORIAS,
    CORES_STATUS,
    LARGURA_MAX_FOTO,
    NIVEIS,
    ORGAOS,
    PASTA_FOTOS,
    SEVERIDADES,
    texto_campo,
)


# ---------------------------------------------------------------------------
# GPS
# ---------------------------------------------------------------------------
def capturar_gps() -> dict | None:
    """
    Desenha o botao de GPS e devolve a posicao do navegador.

    Retorno:
        {"latitude": float, "longitude": float, "precisao": float|None}
        None  -> usuario ainda nao clicou / negou permissao
        {"erro": "..."} -> componente ausente ou falha

    Importante: o navegador so libera a geolocalizacao em https:// ou
    em http://localhost. Acessando pelo IP da rede local, o celular bloqueia.
    """
    try:
        from streamlit_geolocation import streamlit_geolocation
    except ImportError:
        return {"erro": "Componente de GPS nao instalado "
                        "(pip install streamlit-geolocation)."}

    posicao = streamlit_geolocation()

    if not posicao or posicao.get("latitude") is None:
        return None

    return {
        "latitude": round(float(posicao["latitude"]), 6),
        "longitude": round(float(posicao["longitude"]), 6),
        "precisao": (
            round(float(posicao["accuracy"]), 1)
            if posicao.get("accuracy") is not None
            else None
        ),
    }


# ---------------------------------------------------------------------------
# Imagem
# ---------------------------------------------------------------------------
def salvar_foto(arquivo_enviado) -> str | None:
    """
    Recebe o arquivo do st.file_uploader, reduz o tamanho e salva em data/fotos.
    Devolve o caminho relativo gravado no banco (ou None se nao houver arquivo).
    """
    if arquivo_enviado is None:
        return None

    PASTA_FOTOS.mkdir(parents=True, exist_ok=True)

    imagem = Image.open(arquivo_enviado)
    if imagem.mode in ("RGBA", "P", "LA"):
        imagem = imagem.convert("RGB")

    if imagem.width > LARGURA_MAX_FOTO:
        nova_altura = int(imagem.height * LARGURA_MAX_FOTO / imagem.width)
        imagem = imagem.resize((LARGURA_MAX_FOTO, nova_altura), Image.LANCZOS)

    nome_arquivo = f"{uuid.uuid4().hex}.jpg"
    imagem.save(PASTA_FOTOS / nome_arquivo, format="JPEG", quality=82, optimize=True)

    # Caminho relativo: o banco nao fica preso a um computador especifico
    return f"data/fotos/{nome_arquivo}"


def texto_html(valor, padrao: str = "") -> str:
    """Campo pronto para ser interpolado em HTML: limpo e com escape.

    O relato, a referencia e o bairro sao digitados pelo cidadao e vao direto
    para dentro do popup do mapa. Sem escape, um `<img src=x onerror=...>` no
    campo de referencia executa no navegador de quem esta atendendo o chamado.
    Quem monta HTML com dado de terceiro passa por aqui, sempre.
    """
    return escape(texto_campo(valor, padrao), quote=True)


def _foto_em_base64(caminho_relativo: str | None, largura: int = 220) -> str:
    """Converte a foto em <img> embutido, para aparecer dentro do popup."""
    caminho_relativo = texto_campo(caminho_relativo)
    if not caminho_relativo:
        return ""
    caminho = Path(__file__).parent / caminho_relativo
    if not caminho.exists():
        return ""
    dados = base64.b64encode(caminho.read_bytes()).decode()
    return (
        f'<img src="data:image/jpeg;base64,{dados}" '
        f'width="{largura}" style="border-radius:6px;margin-top:6px">'
    )


# ---------------------------------------------------------------------------
# Despacho para as autoridades
# ---------------------------------------------------------------------------
def link_google_maps(latitude: float, longitude: float) -> str:
    """Link que abre o ponto exato no aplicativo de mapas do celular."""
    return f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"


def texto_despacho(linha: pd.Series) -> str:
    """
    Monta a mensagem pronta para enviar a Defesa Civil / Bombeiros
    (WhatsApp, radio ou e-mail). Objetiva, com coordenada e link de mapa.
    """
    categoria = linha["categoria"]
    orgao = CATEGORIAS.get(categoria, {}).get("orgao", "Defesa Civil")
    telefone = ORGAOS.get(orgao, "199")
    data = str(linha["criado_em"])[:16].replace("T", " ")
    precisao = (
        f" (GPS +/- {int(linha['precisao_gps'])} m)"
        if pd.notna(linha.get("precisao_gps"))
        else f" ({linha.get('origem_coordenada', 'Mapa')})"
    )

    nivel = linha.get("nivel", "P3")
    regra = NIVEIS.get(nivel, NIVEIS["P3"])
    cobrade = CATEGORIAS.get(categoria, {}).get("cobrade", "")

    partes = [
        f"{regra['emoji']} {nivel} - {regra['nome']} | {linha['protocolo']}",
        f"Prazo p/ acionamento: {regra['sla_acionamento_min']} min "
        f"| Resolucao: {regra['sla_resolucao_h']} h",
        f"Motivo da classificacao: {linha.get('motivo_nivel', '-')}",
        f"Evento......: {categoria}"
        + (f" (COBRADE {cobrade})" if cobrade else ""),
        f"Gravidade...: {linha['severidade']}",
        f"Registrado..: {data}",
        f"Local.......: {texto_campo(linha.get('referencia'), 'nao informado')}"
        f" - Bairro {texto_campo(linha.get('bairro'), 'nao informado')}",
        f"Coordenadas.: {linha['latitude']}, {linha['longitude']}{precisao}",
        f"Mapa........: {link_google_maps(linha['latitude'], linha['longitude'])}",
    ]

    if int(linha.get("pessoas_em_risco", 0)):
        partes.append("⚠️ PESSOAS EM RISCO NO LOCAL")

    confirmacoes = int(linha.get("confirmacoes", 0) or 0)
    if confirmacoes:
        partes.append(f"Confirmado por mais {confirmacoes} cidadao(s).")

    partes += [
        f"Relato......: {texto_campo(linha.get('descricao'), '-')}",
        f"Solicitante.: {texto_campo(linha.get('autor'), 'Anonimo')}"
        f" / {texto_campo(linha.get('contato'), 'sem contato')}",
        f"Acionar.....: {orgao} - {telefone}",
    ]
    return "\n".join(partes)


# ---------------------------------------------------------------------------
# Mapa
# ---------------------------------------------------------------------------
def _html_popup(linha: pd.Series, com_foto: bool = True) -> str:
    """Conteudo HTML exibido ao clicar em um marcador."""
    emoji = SEVERIDADES.get(linha["severidade"], {}).get("emoji", "")
    cor_status = CORES_STATUS.get(linha["status"], "#555")
    # Tudo que veio do registro passa por texto_html: e texto de terceiro
    # entrando em HTML. Nomes de config (emoji, cores) sao nossos e ficam.
    descricao = texto_html(linha.get("descricao"), "Sem descricao.")
    referencia = texto_html(linha.get("referencia"))
    categoria = texto_html(linha.get("categoria"))
    protocolo = texto_html(linha.get("protocolo"))
    status = texto_html(linha.get("status"))
    severidade = texto_html(linha.get("severidade"))
    data = texto_html(str(linha.get("criado_em", ""))[:16].replace("T", " "))
    emergencia = int(linha.get("emergencia", 0))
    confirmacoes = int(linha.get("confirmacoes", 0) or 0)

    nivel = linha.get("nivel")
    if nivel in NIVEIS:
        regra = NIVEIS[nivel]
        faixa = (
            f"<div style='background:{regra['cor']};color:#fff;padding:3px 8px;"
            "border-radius:4px;font-weight:700;font-size:11px;margin-bottom:6px'>"
            f"{nivel} - {regra['nome']}</div>"
        )
    else:
        faixa = (
            "<div style='background:#B71C1C;color:#fff;padding:3px 8px;"
            "border-radius:4px;font-weight:700;font-size:11px;margin-bottom:6px'>"
            "EMERGENCIA</div>"
            if emergencia else ""
        )
    aviso_risco = (
        "<div style='color:#B71C1C;font-weight:700;margin-top:4px'>"
        "⚠️ Pessoas em risco</div>"
        if int(linha.get("pessoas_em_risco", 0)) else ""
    )

    return f"""
    <div style="font-family:system-ui,sans-serif;font-size:13px;width:250px">
      {faixa}
      <div style="font-weight:700;font-size:14px">{categoria}</div>
      <div style="color:#666;font-size:11px;margin-bottom:6px">
        {protocolo} &middot; {data}
      </div>
      <span style="background:{cor_status};color:#fff;padding:2px 8px;
                   border-radius:10px;font-size:11px">{status}</span>
      <span style="margin-left:6px">{emoji} {severidade}</span>
      {aviso_risco}
      <p style="margin:8px 0 0">{descricao}</p>
      {f'<p style="margin:4px 0 0;color:#555"><b>Referencia:</b> {referencia}</p>' if referencia else ''}
      {f'<p style="margin:4px 0 0;color:#00695C">✔ {confirmacoes} confirmacao(oes)</p>' if confirmacoes else ''}
      {_foto_em_base64(linha.get('foto')) if com_foto else ''}
    </div>
    """


def criar_mapa(
    centro: tuple[float, float],
    zoom: int,
    dados: pd.DataFrame | None = None,
    ponto_selecionado: tuple[float, float] | None = None,
    raio_precisao: float | None = None,
    agrupar: bool = True,
    mapa_calor: bool = False,
    colorir_por: str = "categoria",
    botao_localizar: bool = True,
) -> folium.Map:
    """
    Monta o mapa Folium sobre tiles do OpenStreetMap.

    colorir_por: "categoria", "status" ou "prioridade".
    """
    mapa = folium.Map(
        location=centro, zoom_start=zoom, tiles="OpenStreetMap", control_scale=True
    )

    # Camada de satelite - ajuda a confirmar alagamento / area de encosta
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/"
              "World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery", name="Satelite", overlay=False, control=True,
    ).add_to(mapa)

    Fullscreen(title="Tela cheia", title_cancel="Sair").add_to(mapa)
    MiniMap(toggle_display=True, position="bottomright").add_to(mapa)
    if botao_localizar:
        # Botao nativo do Leaflet que centraliza o mapa na posicao do usuario
        LocateControl(
            auto_start=False,
            strings={"title": "Ir para minha localizacao"},
        ).add_to(mapa)

    if dados is not None and not dados.empty:
        destino = (
            MarkerCluster(name="Ocorrencias").add_to(mapa)
            if agrupar
            else folium.FeatureGroup(name="Ocorrencias").add_to(mapa)
        )

        for _, linha in dados.iterrows():
            if colorir_por == "status":
                cor = {
                    "Aberto": "red", "Em atendimento": "orange",
                    "Resolvido": "green", "Improcedente": "lightgray",
                }.get(linha["status"], "gray")
                icone = "circle-exclamation"
            elif colorir_por in ("prioridade", "nivel"):
                cor = {"P1": "darkred", "P2": "red",
                       "P3": "orange", "P4": "green"}.get(
                    linha.get("nivel", "P3"), "gray"
                )
                icone = "triangle-exclamation"
            else:
                config = CATEGORIAS.get(linha["categoria"], {})
                cor = config.get("cor", "gray")
                icone = config.get("icone", "triangle-exclamation")

            # Halo vermelho destacando emergencias ativas
            eh_p1 = linha.get("nivel") == "P1"
            if (eh_p1 or int(linha.get("emergencia", 0))) \
                    and linha["status"] != "Resolvido":
                folium.Circle(
                    location=[linha["latitude"], linha["longitude"]],
                    radius=90, color="#B71C1C", weight=2,
                    fill=True, fill_opacity=0.15,
                ).add_to(mapa)

            folium.Marker(
                location=[linha["latitude"], linha["longitude"]],
                popup=folium.Popup(_html_popup(linha), max_width=280),
                tooltip=f"{linha['categoria']} - {linha['status']}",
                icon=folium.Icon(color=cor, icon=icone, prefix="fa"),
            ).add_to(destino)

        if mapa_calor:
            pesos = [
                [linha["latitude"], linha["longitude"],
                 SEVERIDADES.get(linha["severidade"], {}).get("peso", 1)]
                for _, linha in dados.iterrows()
            ]
            HeatMap(pesos, name="Mapa de calor", radius=22, blur=16).add_to(mapa)

    # Ponto que o usuario acabou de marcar (clique ou GPS)
    if ponto_selecionado:
        folium.Marker(
            location=list(ponto_selecionado),
            tooltip="Local selecionado",
            icon=folium.Icon(color="black", icon="location-crosshairs", prefix="fa"),
        ).add_to(mapa)
        # Circulo mostrando a margem de erro real do GPS
        folium.Circle(
            location=list(ponto_selecionado),
            radius=max(raio_precisao or 30, 15),
            color="#111", weight=1, fill=True, fill_opacity=0.10,
        ).add_to(mapa)

    folium.LayerControl(collapsed=True).add_to(mapa)
    return mapa
