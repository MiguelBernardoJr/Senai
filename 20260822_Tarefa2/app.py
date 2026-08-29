# app.py
# ---------------------------------------------------------
# Servidor Flask do projeto de reconhecimento de imagens.
#
# FASE 1 (pronta): criar classes e enviar imagens.
# FASE 2 (pronta): treinar um modelo de classificação usando
#                  transfer learning com MobileNetV2 (TensorFlow/Keras).
# FASE 3 (pronta): testar uma imagem nova e ver a porcentagem de
#                  confiança para cada classe.
# FASE 4 (nova): mensagens de erro mais claras para o usuário, em
#                situações como treinar sem classes, treinar com
#                poucas imagens, testar sem modelo treinado, ou
#                enviar um arquivo que não é imagem.
#
# O que este arquivo faz:
# 1. Serve a página principal (templates/index.html).
# 2. Serve a página de teste (templates/testar.html).
# 3. Recebe imagens enviadas pelo navegador e salva na pasta certa
#    (dataset/nome_da_classe/).
# 4. Lista as classes já criadas e a quantidade de imagens de cada uma.
# 5. Treina um modelo de IA usando as imagens salvas e guarda o
#    resultado em disco (modelo/modelo.h5 e modelo/classes.json).
# 6. Usa o modelo treinado para prever a classe de uma imagem nova,
#    devolvendo a porcentagem de confiança para cada classe.
# 7. Em todas as rotas acima, avisa o usuário com uma mensagem clara
#    quando algo dá errado, em vez de travar com um erro técnico.
# ---------------------------------------------------------

import os
import json
import numpy as np
from flask import Flask, render_template, request, jsonify

# Importações do TensorFlow/Keras.
import tensorflow as tf
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.layers import GlobalAveragePooling2D, Dense
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.preprocessing.image import ImageDataGenerator, load_img, img_to_array

# Cria a aplicação Flask.
app = Flask(__name__)

# Pastas usadas pelo projeto.
PASTA_DATASET = "dataset"          # imagens organizadas por classe
PASTA_MODELO = "modelo"            # onde salvamos o modelo treinado
CAMINHO_MODELO = os.path.join(PASTA_MODELO, "modelo.h5")
CAMINHO_CLASSES = os.path.join(PASTA_MODELO, "classes.json")

# Extensões de arquivo que vamos aceitar como "imagem".
EXTENSOES_PERMITIDAS = {"png", "jpg", "jpeg", "gif", "bmp", "webp"}

# Tamanho da imagem esperado pela MobileNetV2.
TAMANHO_IMAGEM = (224, 224)

# Quantidade mínima de imagens por classe para permitir o treinamento.
MINIMO_IMAGENS_POR_CLASSE = 5

# Guardamos o modelo carregado em memória aqui, para não precisar
# recarregar do disco a cada previsão (isso deixaria a Fase 3 lenta).
_modelo_carregado = None
_classes_carregadas = None


def extensao_e_valida(nome_arquivo):
    """
    Verifica se o nome do arquivo termina com uma extensão de imagem
    permitida. Ex: 'foto.jpg' -> True, 'documento.pdf' -> False
    """
    if "." not in nome_arquivo:
        return False
    extensao = nome_arquivo.rsplit(".", 1)[1].lower()
    return extensao in EXTENSOES_PERMITIDAS


def nome_de_classe_e_valido(nome_classe):
    """
    Garante que o nome da classe é seguro para virar nome de pasta.
    Não deixamos vazio, nem com caracteres estranhos como barras.
    """
    if not nome_classe:
        return False
    if "/" in nome_classe or "\\" in nome_classe or ".." in nome_classe:
        return False
    return True


@app.route("/")
def pagina_inicial():
    """
    Rota principal: apenas mostra a página index.html.
    """
    return render_template("index.html")


@app.route("/testar")
def pagina_de_teste():
    """
    Rota que mostra a página de teste (Fase 3), onde o usuário envia
    uma imagem nova e vê o resultado da previsão.
    """
    return render_template("testar.html")


@app.route("/upload", methods=["POST"])
def upload_imagens():
    """
    Rota que recebe:
    - o nome da classe (campo de formulário 'classe')
    - uma ou mais imagens (campo de formulário 'imagens')

    E salva cada imagem dentro de dataset/nome_da_classe/
    """
    nome_classe = request.form.get("classe", "").strip()

    if not nome_de_classe_e_valido(nome_classe):
        return jsonify({
            "sucesso": False,
            "mensagem": "Nome de classe inválido. Digite um nome simples, sem barras."
        }), 400

    arquivos = request.files.getlist("imagens")

    if not arquivos or arquivos[0].filename == "":
        return jsonify({
            "sucesso": False,
            "mensagem": "Nenhuma imagem foi enviada."
        }), 400

    # Cria a pasta da classe, se ainda não existir.
    pasta_da_classe = os.path.join(PASTA_DATASET, nome_classe)
    os.makedirs(pasta_da_classe, exist_ok=True)

    imagens_salvas = 0
    imagens_ignoradas = 0

    for arquivo in arquivos:
        if arquivo and extensao_e_valida(arquivo.filename):
            caminho_completo = os.path.join(pasta_da_classe, arquivo.filename)
            arquivo.save(caminho_completo)
            imagens_salvas += 1
        else:
            imagens_ignoradas += 1

    # Se NENHUM arquivo era uma imagem válida, avisamos com erro em vez
    # de dizer "sucesso" com 0 imagens salvas (isso confundiria o usuário).
    if imagens_salvas == 0:
        return jsonify({
            "sucesso": False,
            "mensagem": (
                "Nenhum dos arquivos enviados é uma imagem válida "
                f"(use {', '.join(sorted(EXTENSOES_PERMITIDAS))})."
            )
        }), 400

    mensagem = f"{imagens_salvas} imagem(ns) salva(s) na classe '{nome_classe}'."
    if imagens_ignoradas > 0:
        mensagem += f" ({imagens_ignoradas} arquivo(s) ignorado(s) por não ser(em) imagem válida)."

    return jsonify({
        "sucesso": True,
        "mensagem": mensagem,
        "imagens_salvas": imagens_salvas,
        "imagens_ignoradas": imagens_ignoradas
    })


@app.route("/classes", methods=["GET"])
def listar_classes():
    """
    Rota que devolve, em JSON, todas as classes já criadas e
    quantas imagens cada uma tem. Exemplo de retorno:

    {
      "classes": [
        {"nome": "gato", "quantidade": 12},
        {"nome": "cachorro", "quantidade": 8}
      ]
    }
    """
    os.makedirs(PASTA_DATASET, exist_ok=True)

    lista_de_classes = []

    for nome_da_pasta in sorted(os.listdir(PASTA_DATASET)):
        caminho_da_pasta = os.path.join(PASTA_DATASET, nome_da_pasta)

        if os.path.isdir(caminho_da_pasta):
            arquivos_na_pasta = os.listdir(caminho_da_pasta)
            quantidade_de_imagens = sum(
                1 for nome in arquivos_na_pasta if extensao_e_valida(nome)
            )

            lista_de_classes.append({
                "nome": nome_da_pasta,
                "quantidade": quantidade_de_imagens
            })

    return jsonify({"classes": lista_de_classes})


def construir_modelo(quantidade_de_classes):
    """
    Monta a arquitetura do modelo usando TRANSFER LEARNING:

    - Pegamos a MobileNetV2 já treinada com milhões de imagens
      (pesos 'imagenet') e "congelamos" ela (não deixamos treinar de novo).
    - Por cima dela, adicionamos só uma camada final pequena, que é a
      parte que realmente vai aprender a diferenciar AS SUAS classes.

    Isso é muito mais rápido do que treinar uma rede do zero, e funciona
    bem mesmo com poucas imagens e sem GPU.
    """
    # Base pré-treinada, sem a "cabeça" de classificação original.
    base = MobileNetV2(
        input_shape=(TAMANHO_IMAGEM[0], TAMANHO_IMAGEM[1], 3),
        include_top=False,
        weights="imagenet"
    )

    # Congela a base: os pesos dela não mudam durante o treinamento.
    base.trainable = False

    # Camada que resume o "mapa de características" da base em um
    # único vetor por imagem.
    saida = GlobalAveragePooling2D()(base.output)

    # Camada final: um "neurônio" para cada classe, com softmax para
    # que a soma das porcentagens dê 100%.
    saida = Dense(quantidade_de_classes, activation="softmax")(saida)

    modelo = Model(inputs=base.input, outputs=saida)

    modelo.compile(
        optimizer="adam",
        loss="categorical_crossentropy",
        metrics=["accuracy"]
    )

    return modelo


@app.route("/treinar", methods=["POST"])
def treinar_modelo():
    """
    Rota que treina o modelo usando as imagens salvas em dataset/.

    Passos:
    1. Verifica se existem classes suficientes com imagens suficientes.
    2. Carrega as imagens em lotes (usando ImageDataGenerator).
    3. Monta o modelo (MobileNetV2 + camada final) e treina por
       poucas épocas.
    4. Salva o modelo treinado e a lista de classes em disco.
    5. Devolve o resultado (acurácia, quantidade de imagens) em JSON.
    """
    os.makedirs(PASTA_DATASET, exist_ok=True)

    # Primeiro, olhamos TODAS as pastas de classe que existem (mesmo as
    # que ainda têm poucas imagens), para poder dar uma mensagem de erro
    # bem específica caso o treinamento não possa começar.
    todas_as_classes = [
        nome for nome in sorted(os.listdir(PASTA_DATASET))
        if os.path.isdir(os.path.join(PASTA_DATASET, nome))
    ]

    if len(todas_as_classes) == 0:
        return jsonify({
            "sucesso": False,
            "mensagem": (
                "Você ainda não criou nenhuma classe. Vá até a seção "
                "'Enviar imagens para uma classe' e cadastre pelo menos "
                "2 classes antes de treinar."
            )
        }), 400

    # Separa as classes com imagens suficientes das que ainda têm poucas.
    nomes_das_classes = []
    classes_com_poucas_imagens = []

    for nome_da_pasta in todas_as_classes:
        caminho_da_pasta = os.path.join(PASTA_DATASET, nome_da_pasta)
        quantidade = sum(
            1 for nome in os.listdir(caminho_da_pasta)
            if extensao_e_valida(nome)
        )
        if quantidade >= MINIMO_IMAGENS_POR_CLASSE:
            nomes_das_classes.append(nome_da_pasta)
        else:
            classes_com_poucas_imagens.append((nome_da_pasta, quantidade))

    if len(nomes_das_classes) < 2:
        mensagem = (
            "Você precisa de pelo menos 2 classes, cada uma com "
            f"{MINIMO_IMAGENS_POR_CLASSE} ou mais imagens, para treinar."
        )
        if classes_com_poucas_imagens:
            detalhes = ", ".join(
                f"'{nome}' ({quantidade} imagem(ns))"
                for nome, quantidade in classes_com_poucas_imagens
            )
            mensagem += f" Classe(s) com poucas imagens: {detalhes}."
        return jsonify({
            "sucesso": False,
            "mensagem": mensagem
        }), 400

    # A partir daqui envolvemos tudo em um try/except: treinar um modelo
    # de IA pode falhar por vários motivos (imagem corrompida, pouca
    # memória, etc.), e é melhor avisar o usuário com uma mensagem clara
    # do que travar o servidor com um erro técnico.
    try:
        # O ImageDataGenerator lê as imagens direto das pastas, já
        # aplicando o pré-processamento que a MobileNetV2 espera, e
        # separa automaticamente uma parte para validação (20%).
        gerador_de_dados = ImageDataGenerator(
            preprocessing_function=preprocess_input,
            validation_split=0.2
        )

        dados_treino = gerador_de_dados.flow_from_directory(
            PASTA_DATASET,
            target_size=TAMANHO_IMAGEM,
            batch_size=8,
            class_mode="categorical",
            subset="training",
            classes=nomes_das_classes,
            shuffle=True
        )

        dados_validacao = gerador_de_dados.flow_from_directory(
            PASTA_DATASET,
            target_size=TAMANHO_IMAGEM,
            batch_size=8,
            class_mode="categorical",
            subset="validation",
            classes=nomes_das_classes,
            shuffle=False
        )

        total_de_imagens = dados_treino.samples + dados_validacao.samples

        # Monta o modelo com base na quantidade de classes encontradas.
        modelo = construir_modelo(quantidade_de_classes=len(nomes_das_classes))

        # Treina por poucas épocas — suficiente para um exemplo de
        # aprendizado, rodando bem em notebook comum (sem GPU).
        QUANTIDADE_DE_EPOCAS = 5

        historico = modelo.fit(
            dados_treino,
            validation_data=dados_validacao if dados_validacao.samples > 0 else None,
            epochs=QUANTIDADE_DE_EPOCAS,
            verbose=1
        )

        # Pega a acurácia da última época (validação, se existir; senão treino).
        if "val_accuracy" in historico.history:
            acuracia_final = historico.history["val_accuracy"][-1]
        else:
            acuracia_final = historico.history["accuracy"][-1]

        # Salva o modelo treinado e a lista de classes em disco.
        os.makedirs(PASTA_MODELO, exist_ok=True)
        modelo.save(CAMINHO_MODELO)

        # A ordem das classes precisa ser salva exatamente como o Keras
        # usou internamente (dados_treino.class_indices), para que a
        # Fase 3 saiba qual posição do resultado corresponde a qual classe.
        indices_das_classes = dados_treino.class_indices  # ex: {"gato": 0, "cachorro": 1}
        classes_ordenadas = sorted(indices_das_classes, key=indices_das_classes.get)

        with open(CAMINHO_CLASSES, "w", encoding="utf-8") as arquivo_json:
            json.dump(classes_ordenadas, arquivo_json, ensure_ascii=False, indent=2)

    except Exception as erro:
        return jsonify({
            "sucesso": False,
            "mensagem": f"Ocorreu um erro durante o treinamento: {erro}"
        }), 500

    # Como o modelo mudou, limpamos o cache em memória: da próxima vez
    # que alguém for prever, o modelo NOVO será recarregado do disco.
    global _modelo_carregado, _classes_carregadas
    _modelo_carregado = None
    _classes_carregadas = None

    return jsonify({
        "sucesso": True,
        "mensagem": "Modelo treinado com sucesso!",
        "acuracia": round(float(acuracia_final) * 100, 2),
        "quantidade_de_imagens": total_de_imagens,
        "classes": classes_ordenadas,
        "epocas": QUANTIDADE_DE_EPOCAS
    })


def carregar_modelo_e_classes():
    """
    Carrega o modelo treinado e a lista de classes do disco, apenas
    UMA VEZ (guarda em memória para as próximas previsões serem rápidas).

    Devolve (modelo, lista_de_classes) ou (None, None) se ainda não
    existir um modelo treinado.
    """
    global _modelo_carregado, _classes_carregadas

    if _modelo_carregado is not None and _classes_carregadas is not None:
        return _modelo_carregado, _classes_carregadas

    if not os.path.exists(CAMINHO_MODELO) or not os.path.exists(CAMINHO_CLASSES):
        return None, None

    _modelo_carregado = load_model(CAMINHO_MODELO)

    with open(CAMINHO_CLASSES, "r", encoding="utf-8") as arquivo_json:
        _classes_carregadas = json.load(arquivo_json)

    return _modelo_carregado, _classes_carregadas


@app.route("/prever", methods=["POST"])
def prever_imagem():
    """
    Rota da FASE 3: recebe uma imagem nova enviada pelo usuário e
    devolve a porcentagem de confiança para CADA classe conhecida.

    Passos:
    1. Verifica se já existe um modelo treinado.
    2. Verifica se a imagem enviada é válida.
    3. Prepara a imagem do mesmo jeito que a MobileNetV2 espera
       (mesmo tamanho e mesmo pré-processamento usado no treino).
    4. Roda a previsão e monta o JSON de resposta.

    Exemplo de retorno:
    {
      "sucesso": true,
      "resultado_final": "gato",
      "porcentagens": {"gato": 87.5, "cachorro": 12.5}
    }
    """
    modelo, lista_de_classes = carregar_modelo_e_classes()

    if modelo is None:
        return jsonify({
            "sucesso": False,
            "mensagem": "Ainda não existe um modelo treinado. Vá até a página inicial e clique em 'Treinar Modelo' primeiro."
        }), 400

    if "imagem" not in request.files:
        return jsonify({
            "sucesso": False,
            "mensagem": "Nenhuma imagem foi enviada."
        }), 400

    arquivo_de_imagem = request.files["imagem"]

    if arquivo_de_imagem.filename == "":
        return jsonify({
            "sucesso": False,
            "mensagem": "Nenhuma imagem foi enviada."
        }), 400

    if not extensao_e_valida(arquivo_de_imagem.filename):
        return jsonify({
            "sucesso": False,
            "mensagem": "Arquivo enviado não é uma imagem válida (use png, jpg, jpeg, gif, bmp ou webp)."
        }), 400

    # Salva a imagem temporariamente em disco, para poder abri-la com
    # a função load_img do Keras (mais simples do que ler direto da memória).
    os.makedirs("temp", exist_ok=True)
    caminho_temporario = os.path.join("temp", arquivo_de_imagem.filename)
    arquivo_de_imagem.save(caminho_temporario)

    try:
        # Carrega a imagem já no tamanho esperado pela MobileNetV2.
        # Se o arquivo tiver extensão de imagem mas estiver corrompido
        # ou não for realmente uma imagem, isso aqui vai falhar.
        imagem = load_img(caminho_temporario, target_size=TAMANHO_IMAGEM)

        # Converte a imagem para um array numérico (formato que o
        # modelo entende) e aplica o mesmo pré-processamento do treino.
        array_da_imagem = img_to_array(imagem)
        array_da_imagem = np.expand_dims(array_da_imagem, axis=0)
        array_da_imagem = preprocess_input(array_da_imagem)

        # Roda a previsão. O resultado é uma lista de porcentagens,
        # uma para cada classe, na mesma ordem de 'lista_de_classes'.
        previsoes = modelo.predict(array_da_imagem)[0]
    except Exception:
        return jsonify({
            "sucesso": False,
            "mensagem": "Não foi possível analisar essa imagem. Verifique se o arquivo não está corrompido e tente novamente."
        }), 400
    finally:
        # Remove o arquivo temporário, exista erro ou não.
        if os.path.exists(caminho_temporario):
            os.remove(caminho_temporario)

    # Monta um dicionário {"gato": 87.5, "cachorro": 12.5, ...}
    porcentagens = {
        lista_de_classes[i]: round(float(previsoes[i]) * 100, 2)
        for i in range(len(lista_de_classes))
    }

    # Descobre qual foi a classe com maior porcentagem (o "resultado final").
    resultado_final = max(porcentagens, key=porcentagens.get)

    return jsonify({
        "sucesso": True,
        "resultado_final": resultado_final,
        "porcentagens": porcentagens
    })


# Ponto de entrada: só roda o servidor se este arquivo for executado
# diretamente (python app.py), e não quando for importado por outro arquivo.
if __name__ == "__main__":
    # debug=True facilita o desenvolvimento: reinicia sozinho quando o
    # código muda e mostra erros detalhados no navegador.
    app.run(debug=True, port=5000)
