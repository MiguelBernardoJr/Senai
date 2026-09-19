# MEMÓRIA DO PROJETO — Alerta Cidadão

> Estado atual, decisões vigentes e pendências. **Sempre anexado.**
> Última atualização: 19/09/2026 · Fase: **v1 no ar, 146 testes, 5 correcoes**

## Situação

Projeto na pasta `Problemas Metereologicos/`, publicado em
`MiguelBernardoJr/Senai`, branch `main` (commit `d8e21d5`).

**Entregue e funcionando:**

- `config.py` — 13 tipos de evento (peso, `risco_vital`, órgão, COBRADE), 4 níveis
  com SLA, severidades, status, telefones dos órgãos e pesos do score.
- `classificacao.py` — 11 discriminadores ordenados + padrão P4, escalonamento
  com teto, `avaliar_sla()` com as 5 situações e `aplicar()` enriquecendo o
  DataFrame inteiro de uma vez.
- `database.py` — 3 tabelas, migração por `PRAGMA table_info`, filtros, fila
  priorizada, busca por proximidade (haversine), estatísticas, aderência ao SLA
  e resumo por nível.
- `servicos.py` — GPS, foto (Pillow), mapa Folium com cluster / mapa de calor /
  satélite e texto de despacho com telefone do órgão.
- `app.py` — interface Streamlit.
- `tests/` — **146 testes, todos passando** (`python -m pytest`).

## Como a suíte de testes está organizada

| Arquivo | Cobre | Testes |
|---|---|---|
| `test_classificacao.py` | Os 12 discriminadores um a um, teto do escalonamento, SLA e formatação de prazo | 40 |
| `test_database.py` | Protocolo, fluxo de status, confirmação, reclassificação, score, filtros, fila, proximidade, painel e migração | 39 |
| `test_servicos.py` | Despacho, links, foto, mapa, o NaN do pandas e o escape de HTML | 54 |
| `test_fluxo_completo.py` | Ciclo de vida ponta a ponta, escalonamento, banco vazio e contaminacao por NaN | 13 |

`tests/conftest.py` dá a cada teste um `.db` temporário próprio (trocando
`database.CAMINHO_BANCO`) — nenhum teste encosta no `data/ocorrencias.db` real.
A fixture `recuar` envelhece o `criado_em` de um alerta para testar SLA e
escalonamento sem desmontar `inserir_ocorrencia()`.

## Bugs encontrados pelos testes e corrigidos

| # | Onde | O que acontecia | Correção |
|---|---|---|---|
| B-01 | `criar_tabelas()` | Os índices eram criados **antes** de `_migrar()`. Num banco de versão anterior, `CREATE INDEX ... ON ocorrencias(emergencia)` falhava com *"no such column"* e a migração nunca rodava — o app não subia, exatamente no caso que a migração existe para resolver. | Tabelas → migração → índices, nessa ordem. |
| B-02 | `listar_historico()` | `ORDER BY criado_em DESC` sem desempate. Como `_agora()` tem precisão de segundos, abrir e acionar no mesmo segundo fazia o histórico aparecer fora de ordem na tela. | `ORDER BY h.criado_em DESC, h.id DESC`. |
| B-03 | `subir_nivel()` | `subir_nivel("P1")` devolvia `"P2"` — **rebaixava** a emergência. Hoje `aplicar()` não chega a chamar com P1 (há guarda no chamador), mas a função é pública e não pode depender de quem a chama. | Guarda `if indice <= teto: return nivel`. |
| B-05 | `servicos._html_popup()` e `app.py` | **Injeção de HTML.** O popup do mapa é montado por f-string e o relato, a referência e a categoria entravam **sem escape**. Um cidadão registrando `<img src=x onerror=...>` no campo de referência teria o código executado no navegador de quem está atendendo o chamado — `<script>` inserido por `innerHTML` não roda, mas um atributo `onerror` sim. Atingia também o `motivo_nivel` na Central, que carrega a justificativa digitada na reclassificação. | `servicos.texto_html()` (escape + `texto_campo`) em tudo que vem do registro. O despacho **não** é escapado: é texto puro para WhatsApp/rádio. |
| B-04 | `servicos._foto_em_base64()` e `app._cartao()` | **Derrubava o app em uso real.** Enquanto nenhum alerta tinha foto, a coluna era toda NULL e o pandas devolvia `None` — as guardas `if linha["foto"]` funcionavam. Bastou a **primeira foto** para a coluna virar texto e os NULL dos outros alertas virarem `NaN` (float, e **truthy**): a guarda passava e `PASTA_BASE / NaN` estourava `TypeError`, quebrando o mapa e o cartão da Central **para todos os alertas**. Os mesmos `or` de fallback em referência, bairro, autor, contato, descrição e órgão acionado imprimiriam `nan` na tela. | `config.texto_campo()`, usado em `classificacao`, `servicos` e `app`. |

B-05 é o único achado de segurança: o app é alimentado por qualquer cidadão e lido pela Defesa Civil, então texto de terceiro que vira HTML precisa de escape por princípio, não por sintoma observado.

B-01, B-02 e B-03 não mudavam comportamento visível: B-03 era inalcançável e
B-01 só atinge quem já tinha um `.db` antigo. Foram corrigidos porque são
armadilhas para a próxima alteração. **B-04 era diferente — quebrava o app de
verdade**, e só aparecia depois que alguém enviasse a primeira foto.

## Pendências

- [ ] Testar o GPS em celular real. Exige HTTPS — só dá para validar depois de
      publicar no Streamlit Cloud ou por túnel `ngrok`.
- [ ] Decidir se o projeto vai para o Streamlit Cloud antes da apresentação.
- [ ] `app.py` não tem teste automatizado (é tela; foi verificado no navegador).
      Se a interface crescer, vale extrair as funções de montagem para um módulo
      testável.

## Decisões vigentes

| ID | Decisão | Data |
|---|---|---|
| D-01 | Nível de triagem **não é coluna** do banco — recalculado a cada leitura por `classificacao.aplicar()`. Só a reclassificação manual é persistida. | 19/09/2026 |
| D-02 | O contrato entre camadas é o **DataFrame enriquecido**, não um objeto de domínio. Quem consome `listar_ocorrencias()` recebe triagem, SLA e score já calculados e não recalcula nada. | 19/09/2026 |
| D-03 | Escalonamento sobe **um nível por avaliação**, só para alerta `Aberto` com SLA vencido, com **teto P2**. | 19/09/2026 |
| D-04 | São necessárias **2 confirmações** para mudar o nível (RN-09). Um relato isolado não é confirmação cruzada. | 19/09/2026 |
| D-05 | Protocolo `OC{ano}-{id:05d}` usa o **id global** do banco, não uma sequência por ano. Em 2027 a numeração continua de onde parou — é único e simples; renumerar por ano exigiria transação e contador separado. | 19/09/2026 |
| D-06 | `estatisticas()["emergencias_ativas"]` conta `emergencia = 1` (o checkbox do cidadão), **não** o nível P1. O número de P1 vem de `resumo_por_nivel()`. São duas perguntas diferentes e ambas aparecem no painel. | 19/09/2026 |
| D-07 | `buscar_proximas()` filtra `status <> 'Resolvido'` — alerta marcado como Improcedente continua aparecendo como vizinho. Proposital: se alguém relatou de novo no mesmo ponto, talvez o "improcedente" tenha sido engano. | 19/09/2026 |
| D-08 | Foto com nome `uuid4` e caminho relativo no banco. Dois envios simultâneos não se sobrescrevem e o `.db` não fica preso a um computador. | 19/09/2026 |
| D-09 | `atualizar_status` carimba `resolvido_em` apenas em **"Resolvido"**; "Improcedente" encerra sem entrar no tempo médio de resolução. | 19/09/2026 |
| D-10 | Cidade padrão do mapa: **Pirapozinho/SP**, `CENTRO_PADRAO = (-22.2747, -51.5019)`. | 19/09/2026 |
| D-11 | `config.texto_campo()` é a **única** porta para ler campo anulável vindo do banco. Mora em `config.py` (a base que todos importam) e detecta NaN com `valor != valor`, para não arrastar o pandas para dentro do módulo base. Nenhum `or` cru em campo que pode ser NULL. | 19/09/2026 |
| D-12 | Dado de terceiro que entra em **HTML** passa por `servicos.texto_html()` (escape). Dado que entra em **texto puro** (despacho de WhatsApp/rádio) passa por `config.texto_campo()`, sem escape — `&amp;` numa mensagem de rádio seria erro. | 19/09/2026 |
| D-13 | Identificadores, comentários e chaves de banco sem acento; texto de tela com acento. Evita problema de encoding em terminal Windows sem prejudicar a apresentação. | 19/09/2026 |

## Riscos conhecidos

| Risco | Mitigação |
|---|---|
| **GPS bloqueado em http://** — o navegador só libera geolocalização em HTTPS ou localhost. No IP da rede local o celular recusa. | O clique no mapa cobre 100 % do fluxo sem GPS. Para demonstrar GPS: Streamlit Cloud (HTTPS) ou `ngrok`. |
| Disco do Streamlit Cloud é efêmero: `.db` e fotos somem a cada redeploy. | Aceitável para a apresentação. Para uso real, trocar SQLite por PostgreSQL e as fotos por um bucket — `database.py` está isolado para que a troca fique em um arquivo só. |
| Folium carrega o Leaflet de CDN. Sem internet, o mapa não desenha. | Limitação conhecida da biblioteca; não afeta uso normal com rede. |
| Mudar peso, ordem de discriminador ou SLA reclassifica **todo** o histórico (é o desenho — D-01). | Os 40 testes de `test_classificacao.py` quebram se a tabela de triagem mudar sem intenção. Rodar `python -m pytest` antes de todo commit. |
| Novo trecho de HTML montado por f-string com dado do registro reabre o B-05. | `servicos.texto_html()` e os testes parametrizados de `test_servicos.py`, que tentam injetar em cada campo do popup. |
| Campo anulável lido direto do DataFrame com `or` ou `if` volta a vazar `NaN` (B-04). | `config.texto_campo()` e os testes de `test_fluxo_completo.py` que inserem um alerta com foto e outro sem. |
| Demonstração com banco vazio não mostra nada da triagem. | Popular a base antes de apresentar (ver pendência sobre `gerar_dados_exemplo.py`). |

## Histórico

Nada arquivado ainda. Quando este arquivo passar de ~200 linhas ou acumular
decisão revogada, mover o frio para `BKP/HISTORICO-alerta-cidadao-AAAAMM.md`.
