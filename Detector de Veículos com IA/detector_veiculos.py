"""
Detector de Veiculos com IA
---------------------------
Aplicacao Streamlit que usa um modelo YOLO pre-treinado (COCO) para identificar
carros, motos, onibus e caminhoes em uma imagem enviada pelo usuario.

Execucao:
    pip install -r requirements.txt
    streamlit run detector_veiculos.py
"""

from __future__ import annotations

import io
from collections import Counter

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

# ---------------------------------------------------------------------------
# Configuracao
# ---------------------------------------------------------------------------

# IDs das classes de veiculos no dataset COCO -> (rotulo, cor RGB da caixa)
CLASSES_VEICULOS: dict[int, tuple[str, tuple[int, int, int]]] = {
    2: ("Carro", (0, 153, 255)),
    3: ("Moto", (255, 179, 0)),
    5: ("Onibus", (0, 200, 83)),
    7: ("Caminhao", (229, 57, 53)),
}

MODELOS_DISPONIVEIS = {
    "YOLOv8n (rapido)": "yolov8n.pt",
    "YOLOv8s (equilibrado)": "yolov8s.pt",
    "YOLOv8m (mais preciso)": "yolov8m.pt",
}

FORMATOS_ACEITOS = ["jpg", "jpeg", "png", "bmp", "webp"]

st.set_page_config(page_title="Detector de Veiculos com IA", page_icon="🚗", layout="wide")


# ---------------------------------------------------------------------------
# Modelo
# ---------------------------------------------------------------------------


@st.cache_resource(show_spinner="Carregando modelo YOLO...")
def carregar_modelo(caminho_modelo: str) -> YOLO:
    """Carrega o modelo uma unica vez e mantem em cache entre execucoes."""
    return YOLO(caminho_modelo)


def detectar_veiculos(
    modelo: YOLO,
    imagem: Image.Image,
    confianca: float,
    iou: float,
) -> list[dict]:
    """Executa a inferencia e devolve apenas as deteccoes de veiculos."""
    resultado = modelo.predict(
        source=imagem,
        classes=list(CLASSES_VEICULOS.keys()),
        conf=confianca,
        iou=iou,
        verbose=False,
    )[0]

    deteccoes: list[dict] = []
    for caixa in resultado.boxes:
        classe_id = int(caixa.cls[0])
        rotulo, cor = CLASSES_VEICULOS[classe_id]
        x1, y1, x2, y2 = (float(v) for v in caixa.xyxy[0].tolist())
        deteccoes.append(
            {
                "classe_id": classe_id,
                "rotulo": rotulo,
                "cor": cor,
                "confianca": float(caixa.conf[0]),
                "bbox": (x1, y1, x2, y2),
            }
        )

    deteccoes.sort(key=lambda d: d["confianca"], reverse=True)
    return deteccoes


# ---------------------------------------------------------------------------
# Desenho das deteccoes
# ---------------------------------------------------------------------------


def _obter_fonte(tamanho: int) -> ImageFont.ImageFont:
    for nome in ("DejaVuSans-Bold.ttf", "Arial.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(nome, tamanho)
        except OSError:
            continue
    return ImageFont.load_default()


def desenhar_deteccoes(imagem: Image.Image, deteccoes: list[dict]) -> Image.Image:
    """Desenha caixas e rotulos sobre uma copia da imagem original."""
    anotada = imagem.convert("RGB").copy()
    desenho = ImageDraw.Draw(anotada)

    escala = max(anotada.width, anotada.height)
    espessura = max(2, round(escala * 0.003))
    fonte = _obter_fonte(max(14, round(escala * 0.018)))

    for deteccao in deteccoes:
        x1, y1, x2, y2 = deteccao["bbox"]
        cor = deteccao["cor"]
        texto = f"{deteccao['rotulo']} {deteccao['confianca']:.0%}"

        desenho.rectangle([x1, y1, x2, y2], outline=cor, width=espessura)

        tx1, ty1, tx2, ty2 = desenho.textbbox((0, 0), texto, font=fonte)
        largura_txt, altura_txt = tx2 - tx1, ty2 - ty1
        margem = max(2, espessura)

        topo = y1 - altura_txt - 2 * margem
        if topo < 0:  # rotulo nao cabe acima da caixa
            topo = y1 + margem

        desenho.rectangle(
            [x1, topo, x1 + largura_txt + 2 * margem, topo + altura_txt + 2 * margem],
            fill=cor,
        )
        desenho.text((x1 + margem, topo + margem), texto, fill=(255, 255, 255), font=fonte)

    return anotada


def imagem_para_bytes(imagem: Image.Image) -> bytes:
    buffer = io.BytesIO()
    imagem.save(buffer, format="PNG")
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------


def main() -> None:
    st.title("🚗 Detector de Veiculos com IA")
    st.caption(
        "Envie uma imagem e o modelo YOLO identifica carros, motos, onibus e caminhoes."
    )

    with st.sidebar:
        st.header("Configuracoes")
        nome_modelo = st.selectbox("Modelo YOLO", list(MODELOS_DISPONIVEIS.keys()))
        confianca = st.slider("Confianca minima", 0.05, 0.95, 0.35, 0.05)
        iou = st.slider("Limiar de IoU (NMS)", 0.10, 0.90, 0.45, 0.05)
        st.divider()
        st.markdown(
            "**Classes detectadas**\n\n"
            + "\n".join(f"- {rotulo}" for rotulo, _ in CLASSES_VEICULOS.values())
        )

    arquivo = st.file_uploader(
        "Selecione uma imagem", type=FORMATOS_ACEITOS, accept_multiple_files=False
    )

    if arquivo is None:
        st.info("Envie uma imagem nos formatos: " + ", ".join(FORMATOS_ACEITOS).upper())
        return

    try:
        imagem = Image.open(arquivo).convert("RGB")
    except Exception:
        st.error("Nao foi possivel abrir o arquivo enviado. Verifique se e uma imagem valida.")
        return

    modelo = carregar_modelo(MODELOS_DISPONIVEIS[nome_modelo])

    with st.spinner("Analisando a imagem..."):
        deteccoes = detectar_veiculos(modelo, imagem, confianca, iou)

    anotada = desenhar_deteccoes(imagem, deteccoes)
    contagem = Counter(d["rotulo"] for d in deteccoes)

    st.subheader("Resultado")
    st.metric("Total de veiculos encontrados", len(deteccoes))

    colunas = st.columns(len(CLASSES_VEICULOS))
    for coluna, (rotulo, _) in zip(colunas, CLASSES_VEICULOS.values()):
        coluna.metric(rotulo, contagem.get(rotulo, 0))

    if not deteccoes:
        st.warning(
            "Nenhum veiculo detectado. Reduza a confianca minima ou tente outra imagem."
        )

    col_original, col_detectada = st.columns(2)
    with col_original:
        st.markdown("**Imagem original**")
        st.image(imagem, use_container_width=True)
    with col_detectada:
        st.markdown("**Imagem com deteccoes**")
        st.image(anotada, use_container_width=True)

    if deteccoes:
        with st.expander("Detalhes das deteccoes"):
            tabela = pd.DataFrame(
                [
                    {
                        "#": i,
                        "Veiculo": d["rotulo"],
                        "Confianca": f"{d['confianca']:.1%}",
                        "X1": round(d["bbox"][0]),
                        "Y1": round(d["bbox"][1]),
                        "X2": round(d["bbox"][2]),
                        "Y2": round(d["bbox"][3]),
                    }
                    for i, d in enumerate(deteccoes, start=1)
                ]
            )
            st.dataframe(tabela, use_container_width=True, hide_index=True)

        st.download_button(
            "Baixar imagem com deteccoes",
            data=imagem_para_bytes(anotada),
            file_name="veiculos_detectados.png",
            mime="image/png",
        )


if __name__ == "__main__":
    main()
