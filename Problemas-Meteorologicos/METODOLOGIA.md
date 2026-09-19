# METODOLOGIA — Alerta Cidadão (Problemas Meteorológicos)

> Arquivo pequeno, estável e **sempre anexado**. Regra de negócio e padrões inegociáveis.
> Estado atual, pendências e decisões em aberto ficam em `MEMORIA-PROJETO.md`.

## 1. O que o produto faz

Canal colaborativo entre o cidadão e a Defesa Civil. O cidadão marca no mapa —
**por GPS ou por clique** — um evento natural ocorrido na cidade; o sistema
classifica o risco automaticamente e devolve à autoridade uma **fila priorizada
por gravidade, com prazo de atendimento (SLA) por alerta**.

1. **Registrar** — tipo, gravidade, foto, emergência, pessoas em risco.
2. **Triar** — nível P1 a P4 decidido por discriminadores auditáveis.
3. **Despachar** — mensagem pronta para WhatsApp/rádio e registro do órgão acionado.
4. **Acompanhar** — painel de tempos médios, aderência ao SLA e mapa de calor.

## 2. Regras de negócio

| # | Regra |
|---|-------|
| RN-01 | Todo alerta recebe um nível P1–P4. A lista de discriminadores termina em `NIVEL_PADRAO` (P4) — **nunca existe alerta sem classificação**. |
| RN-02 | Os discriminadores em `classificacao.DISCRIMINADORES` são avaliados **em ordem**, de cima para baixo, parando no primeiro que se aplica. O motivo fica gravado junto com o nível: a decisão é auditável. |
| RN-03 | O **score de prioridade (`calcular_prioridade`) não define o nível**. Ele ordena a fila *dentro* de cada nível. Confundir os dois faz um buraco muito confirmado passar na frente de um deslizamento. |
| RN-04 | **Escalonamento por atraso para em `TETO_ESCALONAMENTO` (P2).** Atraso nunca transforma evento sem risco de vida em emergência — senão a fila inteira vira P1 e a triagem perde o sentido. P1 só se alcança por discriminador real de risco. |
| RN-05 | Só escalona alerta **`Aberto` e com SLA `VENCIDO`**. Quem já foi acionado ou já está em atendimento não escala: o relógio de acionamento para no `acionado_em`. |
| RN-06 | **A triagem humana prevalece.** `classificacao_manual` sobrepõe a regra automática e é a primeira coisa que `classificar()` verifica. A justificativa vai para `historico_status`. |
| RN-07 | O nível **não é coluna do banco**: é recalculado a cada leitura por `classificacao.aplicar()`. Mudar uma regra reclassifica todo o histórico sem migração. Só a reclassificação manual é persistida. |
| RN-08 | Alerta a menos de **`RAIO_DUPLICIDADE_M` (50 m)** de um já aberto dispara sugestão de **confirmar o existente** em vez de abrir protocolo duplicado. A confirmação eleva a prioridade. |
| RN-09 | São necessárias **2 confirmações** para um evento mudar de nível (`confirmacoes >= 2`). Um relato isolado não é confirmação cruzada. |
| RN-10 | Toda mudança de status e todo acionamento geram linha em `historico_status`. Acionamento sem registro de hora não é prova de resposta. |
| RN-11 | O sistema registra **de onde veio a coordenada** (`origem_coordenada`) e, no GPS, a precisão em metros. Acima de `PRECISAO_GPS_RUIM_M` a tela avisa: quem vai ao local precisa saber se pode confiar no ponto. |
| RN-12 | Tipos de evento carregam o código **COBRADE** quando existe, para a declaração de situação de emergência no S2iD. Evento operacional sem correspondência no catálogo fica com `cobrade` vazio — não se inventa classificação de desastre. |
| RN-13 | O cidadão nunca vê stacktrace. `classificar()` engole `KeyError`/`TypeError` por discriminador: um registro torto não pode derrubar a fila inteira da Defesa Civil. |

## 3. Tabela de triagem (não alterar sem revisar os testes)

| Nível | Nome | Critério | Acionar em | Resolver em |
|---|---|---|---|---|
| 🔴 P1 | EMERGENCIA | Risco iminente à vida ou à integridade física | 15 min | 2 h |
| 🟠 P2 | URGENCIA | Risco alto de agravamento, sem vítima identificada | 60 min | 12 h |
| 🟡 P3 | PRIORITARIO | Dano material ou transtorno relevante à circulação | 480 min (8 h) | 72 h |
| 🟢 P4 | ROTINA | Sem risco imediato | 2880 min (48 h) | 360 h (15 dias) |

Discriminadores, na ordem de avaliação (`classificacao.DISCRIMINADORES`):

```
P1  1. Pessoas ilhadas, feridas ou presas no local
    2. Evento com risco vital direto e gravidade alta ou crítica
    3. Emergência declarada pelo cidadão com gravidade crítica
    4. Múltiplas confirmações em evento crítico (3+, evento de massa)
P2  5. Emergência declarada pelo cidadão
    6. Gravidade crítica sem vítima identificada
    7. Evento com risco vital direto
    8. Gravidade alta confirmada por outros cidadãos (2+)
P3  9. Gravidade alta
   10. Evento confirmado por outros cidadãos (2+)
   11. Tipo de evento com peso >= 4 (risco relevante de agravamento)
P4 12. NIVEL_PADRAO — nenhum critério acima
```

`risco_vital` é atributo do tipo de evento em `config.CATEGORIAS`: enxurrada,
deslizamento, raio/incêndio, fio rompido e erosão. São os que podem matar em
minutos.

Score de ordenação dentro do nível (`database.calcular_prioridade`):

```
score = peso da gravidade × PESO_SEVERIDADE (2)
      + peso do tipo de evento (1 a 5)
      + BONUS_EMERGENCIA (6)        se marcado como emergência
      + BONUS_PESSOAS_RISCO (5)     se há pessoas em risco
      + BONUS_POR_CONFIRMACAO (2) × confirmações, até MAX_CONFIRMACOES_PONTUADAS (5)
                                                                    máximo = 34
```

Ordem final da fila (`database.fila_emergencia`): **nível** → **`minutos_sla`
mais apertado** → **score**.

## 4. Padrões técnicos fixos

- **Python 3.11+**, Streamlit, Folium + streamlit-folium, pandas, Pillow,
  SQLite (`sqlite3` da biblioteca padrão).
- **Camadas separadas, dependência em um só sentido:**
  `config` → `classificacao` → `database` → `servicos` → `app`.
  `app.py` só cuida de tela; a regra de prioridade mora em `classificacao.py`;
  **SQL só existe em `database.py`**.
- O contrato entre as camadas é o **DataFrame enriquecido**: `listar_ocorrencias()`
  devolve as colunas do banco mais `confirmacoes`, `horas_aberta`, `prioridade` e
  toda a triagem (`nivel`, `nivel_nome`, `nivel_cor`, `motivo_nivel`,
  `origem_nivel`, `escalado`, `prazo_acionamento`, `minutos_sla`, `situacao_sla`).
  Quem consome não recalcula nada.
- `classificacao.classificar()` e `avaliar_sla()` recebem a linha e devolvem
  dict — não tocam no banco. É o que torna a triagem testável isoladamente.
- **Base cartográfica OpenStreetMap** — gratuita, sem chave de API. Camada de
  satélite Esri como overlay opcional, útil para conferir encosta e alagamento.
- `criar_tabelas()` roda **as tabelas, depois a migração, depois os índices**.
  A ordem é obrigatória: um índice sobre coluna que a migração ainda vai criar
  aborta a inicialização de um banco antigo.
- `_agora()` é a única fonte de "agora": ISO com precisão de segundos.
  Consultas que ordenam por `criado_em` **precisam de desempate por `id`** —
  dois eventos do mesmo segundo sairiam em ordem arbitrária.
- Banco e fotos **nunca** vão para o repositório (`.gitignore`).
- Foto gravada com nome `uuid4` em `data/fotos/`, caminho **relativo** no banco:
  o registro não fica preso a um computador específico.
- Identificadores, comentários e chaves de banco **sem acento**; textos que
  aparecem na tela **com acento**.
- Toda mudança em `DISCRIMINADORES`, `NIVEIS` ou nos pesos exige rodar
  `python -m pytest` antes do commit.

## 5. Fora de escopo (v1)

Login e perfis de usuário, notificação push/WhatsApp automática, integração com
INMET/CEMADEN, geocodificação reversa, polígonos de zona de risco, API REST,
app mobile nativo, banco em nuvem.
