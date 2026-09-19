# Detector de Veículos com IA

Atividade de Visão Computacional — SENAI.
Aplicação em **Python + Streamlit + YOLO** que detecta veículos em imagens.

## Funcionalidades

- Upload de imagem (JPG, JPEG, PNG, BMP, WEBP)
- Detecção com modelo YOLO pré-treinado (COCO)
- Identifica **carros, motos, ônibus e caminhões**
- Exibe a quantidade total e a contagem por tipo de veículo
- Mostra a imagem original e a imagem com as caixas de detecção
- Tabela com confiança e coordenadas de cada detecção
- Download da imagem anotada

## Como executar

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run detector_veiculos.py
```

O arquivo de pesos (`yolov8n.pt`) é baixado automaticamente na primeira execução.

## Como funciona

1. A imagem enviada é aberta com Pillow e convertida para RGB.
2. O modelo YOLO faz a inferência filtrando apenas as classes COCO de veículos:
   `2 = carro`, `3 = moto`, `5 = ônibus`, `7 = caminhão`.
3. Os parâmetros de **confiança mínima** e **IoU (NMS)** são ajustáveis na barra lateral.
4. As caixas são desenhadas com cor própria por classe e rótulo com o percentual de confiança.
5. A contagem é agregada por classe e exibida em métricas.
