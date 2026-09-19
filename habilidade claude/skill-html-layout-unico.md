---
name: html-layout-unico
description: Gera uma página HTML estruturada em um único arquivo (Single-File), contendo CSS e JavaScript embutidos, para facilitar a prototipagem rápida e o desenvolvimento de layouts por programadores.
---

## Descrição

Gere um boilerplate ou protótipo funcional de uma página web completa em um único arquivo `.html`.

Esta skill transforma os requisitos do desenvolvedor (como seções desejadas, paleta de cores e comportamento) em um código prático e imediato, contendo:
- Estrutura semântica de HTML5
- Estilização responsiva embutida (via tag `<style>` ou frameworks via CDN, como Tailwind/Bootstrap)
- Interatividade básica encapsulada (via tag `<script>`)

---

## Princípios Centrais

- Todo o código gerado deve ser **pronto para uso imediato** (copiar, colar e rodar no navegador).
- O foco é a **prototipagem rápida** e a eficiência operacional do programador.
- Nunca dependa de arquivos locais externos (sem chamadas para `style.css` ou `app.js`).
- O código deve ser limpo, bem indentado e extensamente comentado para facilitar futuras refatorações.

---

## Processo

### 1. Analise o Input
Leia os requisitos do layout solicitados pelo programador e extraia:
- O propósito da página (ex: landing page, dashboard, formulário de login).
- As seções principais (navbar, hero, cards, footer).
- O framework CSS preferido (se houver) ou a preferência por CSS puro (Vanilla).

### 2. Estruture o HTML Semântico
Crie a base do documento (`<!DOCTYPE html>`), configurando as meta tags para responsividade (`viewport`) e importando as CDNs necessárias (fontes, ícones, frameworks).

### 3. Construa o Layout e Estilo (CSS)
- Projete o layout utilizando abordagens modernas (Flexbox ou CSS Grid).
- Garanta que o design seja *mobile-first* e adaptável a diferentes tamanhos de tela.
- Se usar CSS puro, agrupe as classes e variáveis no topo da tag `<style>`.

### 4. Adicione Interatividade (JS)
- Inclua funções essenciais para o funcionamento do layout (ex: abrir/fechar menu mobile, modais, validação simples de formulários).
- Isole a lógica dentro da tag `<script>` no final do `<body>`.

---

## Regras

1. O resultado final deve ser estritamente contido em **um único arquivo**.
2. Deixe marcadores visuais ou comentários claros onde o programador deve inserir dados dinâmicos ou conectar sua própria API (ex: `<!-- INSERIR LÓGICA DE BACKEND AQUI -->`).
3. Use nomes de classes descritivos e padronizados (como BEM) se estiver escrevendo CSS customizado.
4. O design base deve ser esteticamente agradável, com uso de espaços em branco (padding/margin) e hierarquia visual clara, mesmo que simples.

---

## Formato de Output

Sempre retorne:
- Uma breve explicação das bibliotecas/CDNs utilizadas (se houver).
- Um único bloco de código estruturado contendo o HTML completo (iniciando em `<!DOCTYPE html>` e terminando em `</html>`).

---

## Objetivo

Eliminar o atrito inicial da criação de interfaces, entregando ao desenvolvedor um **layout sólido, responsivo e sem dependências locais**, permitindo que ele foque imediatamente na integração da lógica e no desenvolvimento do sistema.
