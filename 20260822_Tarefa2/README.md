# Reconhecimento de Imagens (Localhost)

Sistema simples de reconhecimento de imagens que roda no seu computador
(localhost), sem depender de serviços pagos ou de nuvem. Foi desenvolvido
como atividade de aprendizado.

## O que o projeto faz

1. **Cadastro de classes**: você cria "classes" (categorias, ex: "gato",
   "cachorro") e envia várias imagens de exemplo para cada uma.
2. **Treinamento**: o sistema treina um modelo de IA (transfer learning
   com MobileNetV2, usando TensorFlow/Keras) a partir dessas imagens.
3. **Teste**: você envia uma imagem nova e o sistema mostra, em um
   dashboard com gráfico de barras, a porcentagem de confiança do
   modelo para cada classe cadastrada.

## Estrutura de pastas

```
20260822_Tarefa2/
├── app.py                  # Servidor Flask (backend + rotas da IA)
├── requirements.txt        # Bibliotecas Python necessárias
├── dataset/                # Imagens de exemplo, organizadas por classe
│   ├── gato/
│   └── cachorro/
├── modelo/                 # Modelo treinado (gerado ao clicar em "Treinar")
│   ├── modelo.h5
│   └── classes.json
├── temp/                   # Arquivos temporários usados durante o teste
├── templates/
│   ├── index.html          # Página inicial: criar classes e treinar
│   └── testar.html         # Página de teste: analisar uma imagem nova
└── static/
    ├── style.css            # Estilo visual das páginas
    ├── script.js             # Lógica da página inicial
    └── testar.js             # Lógica da página de teste
```

## Como instalar as dependências

Com o Python já instalado, dentro da pasta do projeto rode:

```
pip install -r requirements.txt
```

Isso instala Flask, TensorFlow, NumPy e Pillow.

## Como rodar o projeto

```
python app.py
```

O terminal vai mostrar um endereço como `http://127.0.0.1:5000`. Abra
esse endereço no navegador.

## Passo a passo de uso

1. **Criar classe > enviar imagens**: na página inicial, digite o nome
   da classe (ex: "gato"), selecione várias imagens dessa classe e
   clique em "Enviar". Repita para cada classe que você quiser
   reconhecer (no mínimo 2 classes).
2. **Treinar**: depois de ter pelo menos 2 classes com 5 ou mais
   imagens cada, clique em "Treinar Modelo". O treinamento pode levar
   alguns minutos, dependendo do seu computador. Ao final, a acurácia
   do modelo é exibida na tela.
3. **Testar**: clique em "Ir para a página de teste", escolha uma
   imagem nova (que não foi usada no treinamento) e clique em
   "Analisar Imagem". O dashboard mostra um gráfico com a porcentagem
   de confiança para cada classe e destaca qual foi o resultado final.

## Mensagens de erro tratadas

O sistema avisa com uma mensagem clara, em vez de travar, nas seguintes
situações:

- Tentar treinar sem nenhuma classe criada.
- Tentar treinar com menos de 2 classes válidas, ou com classes que têm
  menos de 5 imagens (o aviso indica exatamente quais classes precisam
  de mais imagens).
- Tentar testar uma imagem sem ainda existir um modelo treinado.
- Enviar um arquivo que não é uma imagem válida (upload ou teste).
- Enviar uma imagem corrompida ou que não pode ser processada.
- Erros de conexão entre o navegador e o servidor Flask.

## Dicas de boas práticas

- Use **pelo menos 10 a 20 imagens por classe** para um resultado mais
  confiável (o mínimo aceito pelo sistema é 5, mas poucas imagens
  deixam o modelo menos preciso).
- Use imagens variadas: ângulos, fundos e iluminações diferentes,
  para o modelo aprender a reconhecer a classe em situações diversas.
- Evite imagens muito parecidas entre si dentro da mesma classe.
- Sempre teste com imagens que **não** foram usadas no treinamento,
  para ter uma ideia real de como o modelo se comporta com fotos novas.
- Se treinar novamente (com mais imagens ou mais classes), o modelo
  antigo é substituído — não é necessário apagar nada manualmente.
