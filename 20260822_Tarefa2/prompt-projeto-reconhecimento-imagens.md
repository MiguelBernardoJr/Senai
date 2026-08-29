# Prompt Mestre — Projeto de Reconhecimento de Imagens (Localhost)

> **Como usar este documento:** este projeto foi dividido em **5 fases**. Cada fase é um prompt para ser colado em um **chat novo** (pode ser em qualquer IA generativa: ChatGPT, Claude, Gemini, etc.). Isso economiza tokens e mantém a IA focada apenas na etapa atual.
>
> Em cada chat novo, cole **primeiro o "Contexto Geral"** (abaixo) e **depois o prompt da fase** que você está executando. Se a fase depender de arquivos criados na fase anterior, cole também o conteúdo desses arquivos (a IA vai dizer quais são).

---

## 🔷 CONTEXTO GERAL (colar em TODO chat novo, antes do prompt da fase)

```
Estou desenvolvendo, como atividade de aprendizado, um sistema simples de
reconhecimento de imagens que roda no meu computador (localhost), sem
depender de serviços pagos ou nuvem.

O sistema deve ter 3 partes funcionais:
1. Uma página (index.html) onde eu crio "classes" (categorias) e faço
   upload de várias imagens de exemplo para cada classe.
2. Um treinamento do modelo (transfer learning, usando TensorFlow/Keras
   com MobileNetV2 como base) a partir dessas imagens.
3. Uma página de teste onde envio uma nova imagem e o sistema mostra,
   em um dashboard com gráfico, a porcentagem de confiança para cada classe.

Stack obrigatória (simples, sem frameworks complexos):
- Backend: Python + Flask (arquivo principal: app.py)
- IA/Treinamento: TensorFlow/Keras (MobileNetV2, transfer learning)
- Frontend: HTML + CSS + JavaScript puro (sem React/Vue), usando Chart.js
  via CDN para os gráficos
- Sem banco de dados: usar pastas no disco para organizar as imagens
  por classe (ex: dataset/nome_da_classe/imagem1.jpg)

REGRAS IMPORTANTES PARA VOCÊ (IA) SEGUIR SEMPRE:
1. Sou um estudante iniciante. NÃO me dê "trechos" de código para eu
   colar no meio de um arquivo existente. SEMPRE entregue o ARQUIVO
   COMPLETO, do início ao fim, pronto para eu substituir o antigo.
2. Sempre que eu pedir uma mudança, você deve reescrever o(s) arquivo(s)
   afetado(s) por completo novamente — nunca em formato de "diff" ou
   "adicione essa linha aqui".
3. Identifique claramente o nome de cada arquivo antes do código
   (ex: "Arquivo: app.py").
4. Comente o código em português, de forma simples, explicando o que
   cada parte faz.
5. Sempre que terminar uma etapa, me diga exatamente:
   - quais bibliotecas preciso instalar (comando pip install completo)
   - a estrutura de pastas esperada
   - o comando exato para rodar o projeto
6. Não use bibliotecas ou ferramentas fora do que foi combinado acima,
   a menos que eu peça.
7. Evite soluções complexas demais — o objetivo é eu entender o código,
   não apenas copiar e colar.

Vou te enviar prompts por fases (Fase 1, Fase 2, etc.), pois este é um
projeto grande e queremos economizar contexto. Responda apenas à fase
que eu enviar agora.
```

---

## 🔷 FASE 1 — Estrutura do projeto + tela de criação de classes e upload

```
FASE 1 do projeto (ver contexto geral já enviado acima).

Quero que você crie a estrutura inicial do projeto e a primeira tela
funcional, que serve para:
- Criar uma nova "classe" (ex: "gato", "cachorro"), informando um nome.
- Fazer upload de várias imagens de uma vez para essa classe.
- Mostrar, na mesma página, a lista de classes já criadas e a
  quantidade de imagens de cada uma.

Preciso dos seguintes arquivos, completos:
1. app.py — servidor Flask com as rotas necessárias para:
   - servir o index.html
   - receber e salvar as imagens enviadas na pasta correta
     (dataset/nome_da_classe/)
   - listar as classes existentes e a quantidade de imagens de cada uma
     (em formato JSON, para o frontend consumir)
2. templates/index.html — página com:
   - campo para digitar o nome da nova classe
   - campo de upload de múltiplas imagens
   - botão "Enviar"
   - uma lista/tabela mostrando as classes já criadas e quantas
     imagens cada uma tem (atualizada automaticamente após o upload)
3. static/style.css — estilo simples e organizado (não precisa ser
   bonito, só limpo e legível)
4. static/script.js — toda a lógica de front-end (chamadas para o
   backend via fetch, atualização da lista de classes, etc.)
5. requirements.txt — com as bibliotecas necessárias para esta fase

No final, explique passo a passo como rodar o projeto pela primeira vez.
```

---

## 🔷 FASE 2 — Treinamento do modelo

```
FASE 2 do projeto (ver contexto geral já enviado acima).

Já tenho a Fase 1 pronta: um projeto Flask onde consigo criar classes e
fazer upload de imagens, que ficam salvas em pastas assim:
dataset/nome_da_classe/imagem1.jpg (etc).

[Cole aqui o conteúdo atual do seu app.py da Fase 1]

Agora quero adicionar o TREINAMENTO do modelo. Preciso que você:

1. Reescreva o app.py por completo, adicionando:
   - uma rota /treinar que, quando chamada, treina um modelo de
     classificação de imagens usando transfer learning com MobileNetV2
     (TensorFlow/Keras), usando as imagens da pasta dataset/
   - o modelo treinado deve ser salvo em disco (ex: modelo/modelo.h5)
     junto com a lista de classes (ex: modelo/classes.json), para ser
     usado depois na Fase 3
   - a rota deve retornar o progresso/resultado do treinamento em JSON
     (ex: acurácia final, quantidade de imagens usadas)

2. Adicione um botão "Treinar Modelo" na página index.html (reescreva
   o arquivo completo), que chama essa rota e mostra uma mensagem de
   "Treinando..." e depois o resultado (ex: "Modelo treinado com
   sucesso! Acurácia: 92%").

3. Atualize o script.js (arquivo completo) com a lógica desse botão.

4. Atualize o requirements.txt (arquivo completo) se novas bibliotecas
   forem necessárias.

Lembre-se: o código de treinamento precisa ser simples de entender
(comentado em português), pois serei eu, aluno iniciante, quem vai
explicar isso depois. Use poucas épocas e configurações que rodem bem
em um notebook comum, sem GPU.

No final, explique como rodar o treinamento e quanto tempo aproximado
ele deve levar.
```

---

## 🔷 FASE 3 — Tela de teste + dashboard de porcentagens

```
FASE 3 do projeto (ver contexto geral já enviado acima).

Já tenho as Fases 1 e 2 prontas: consigo criar classes, fazer upload de
imagens e treinar um modelo, que fica salvo em modelo/modelo.h5 e
modelo/classes.json.

[Cole aqui o conteúdo atual do seu app.py]

Agora quero criar a tela de TESTE do modelo treinado. Preciso que você:

1. Reescreva o app.py por completo, adicionando uma rota /prever que:
   - recebe uma imagem enviada pelo usuário
   - carrega o modelo salvo (modelo/modelo.h5) e a lista de classes
   - retorna em JSON a porcentagem de confiança para CADA classe
     (ex: {"gato": 87.5, "cachorro": 12.5})

2. Crie uma nova página, templates/testar.html (arquivo completo), com:
   - um campo para upload de uma única imagem
   - um botão "Analisar Imagem"
   - um DASHBOARD com um gráfico de barras (usando Chart.js via CDN)
     mostrando a porcentagem de cada classe após a análise
   - abaixo do gráfico, destaque em texto qual foi a classe com maior
     porcentagem (o "resultado final")

3. Adicione um link no index.html (arquivo completo) para acessar essa
   nova página testar.html.

4. Crie/atualize static/testar.js (arquivo completo) com a lógica de
   upload, chamada à rota /prever e montagem do gráfico.

5. Atualize static/style.css (arquivo completo) se precisar de estilos
   novos para o dashboard.

No final, explique como usar essa tela pela primeira vez.
```

---

## 🔷 FASE 4 — Ajustes finais, tratamento de erros e README

```
FASE 4 do projeto (fase final — ver contexto geral já enviado acima).

Já tenho as Fases 1, 2 e 3 prontas e funcionando: criação de classes,
upload de imagens, treinamento do modelo e tela de teste com dashboard.

[Cole aqui o conteúdo atual do seu app.py]

Agora quero deixar o projeto mais robusto e fácil de entender/executar.
Preciso que você:

1. Reescreva o app.py por completo adicionando tratamento de erros
   simples e mensagens claras para situações como:
   - tentar treinar sem nenhuma classe criada
   - tentar treinar com uma classe que tem poucas imagens (ex: menos
     de 5)
   - tentar testar uma imagem sem ter um modelo treinado ainda
   - upload de arquivo que não é imagem

2. Reescreva o script.js e o testar.js (arquivos completos) para
   exibir essas mensagens de erro na tela, de forma amigável.

3. Crie um arquivo README.md completo, explicando em português simples:
   - o que o projeto faz
   - a estrutura de pastas do projeto
   - como instalar as dependências (pip install ...)
   - como rodar o projeto (comando exato)
   - o passo a passo de uso: criar classe > enviar imagens > treinar >
     testar
   - dicas de boas práticas (ex: quantidade mínima recomendada de
     imagens por classe)

Não adicione nenhuma funcionalidade nova além do que já existe — o
foco desta fase é deixar tudo estável, claro e bem documentado.
```

---

## 📌 Dicas de uso para o aluno

- Sempre que a IA responder, **salve os arquivos exatamente com os nomes indicados** (app.py, templates/index.html, static/script.js, etc.).
- Antes de colar o prompt da próxima fase, **teste se a fase atual está funcionando** no seu navegador.
- Se der erro ao rodar, cole a mensagem de erro completa na própria conversa da fase em que você está, pedindo para a IA reescrever o(s) arquivo(s) por completo já corrigido(s).
- Nunca misture pedaços de código de fases diferentes gerados por IAs diferentes — sempre use os arquivos completos mais recentes de uma mesma "linha" de conversa.
