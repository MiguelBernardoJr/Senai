# Alerta Cidadao — Problemas Meteorologicos

Projeto final — SENAI.
Canal colaborativo em **Python + Streamlit + Folium (OpenStreetMap) + SQLite**:
o cidadao marca no mapa, **por GPS ou por clique**, eventos naturais ocorridos na
cidade, e a Defesa Civil / Prefeitura recebe os alertas em uma **fila priorizada
por risco**.

## Fluxo

```
Cidadao                          Sistema                       Autoridade
   |                                |                               |
   | GPS ou clique no mapa -------->|                               |
   | tipo + gravidade + foto ------>| calcula prioridade            |
   |                                | detecta duplicidade (50 m)    |
   |                                |------ fila de emergencia ---->|
   |                                |                               | aciona orgao
   |<------ protocolo OC2026-00001 -|<----- historico registrado ---|
```

## Funcionalidades

**Cidadao**
- Localizacao por **GPS do aparelho** (com a precisao em metros gravada) ou por
  clique no mapa — o app registra qual das duas origens foi usada
- Tipos meteorologicos: alagamento, deslizamento, arvore caida, vendaval,
  granizo, raio/incendio, fio rompido, erosao, bueiro entupido, buraco, via
  interditada
- Marcacao de **EMERGENCIA** (risco imediato) e de **pessoas em risco**
- Foto do local (redimensionada automaticamente antes de salvar)
- Protocolo automatico `OC2026-00001`
- **Confirmacao cruzada**: se ja existe alerta a menos de 50 m, o app sugere
  confirmar o existente em vez de abrir protocolo duplicado — e a confirmacao
  eleva a prioridade

**Defesa Civil**
- **Central de emergencias** agrupada por nivel (P1 a P4), com contador de SLA
  por alerta, destaque para prazos vencidos e atualizacao automatica a cada 30 s
- **Reclassificacao manual** com justificativa obrigatoria
- Mensagem de despacho pronta para WhatsApp/radio, com coordenadas e link do mapa
- Registro de qual orgao foi acionado e quando (prova de resposta)
- Fluxo Aberto -> Em atendimento -> Resolvido / Improcedente com observacao e
  responsavel
- Destaque para alertas abertos ha mais de 6 h sem atendimento

**Painel**
- Emergencias ativas, tempo medio ate o acionamento, tempo medio ate a resolucao
- Graficos por tipo, por status e evolucao diaria
- Bairros mais atingidos e exportacao CSV


## Classificacao de emergencia (triagem)

Todo alerta recebe automaticamente um nivel de prioridade, com prazo proprio de
atendimento (SLA):

| Nivel | Nome | Criterio | Acionar em | Resolver em |
|---|---|---|---|---|
| 🔴 **P1** | EMERGENCIA | Risco iminente a vida ou a integridade fisica | 15 min | 2 h |
| 🟠 **P2** | URGENCIA | Risco alto de agravamento, sem vitima identificada | 1 h | 12 h |
| 🟡 **P3** | PRIORITARIO | Dano material ou transtorno relevante a circulacao | 8 h | 72 h |
| 🟢 **P4** | ROTINA | Sem risco imediato | 48 h | 15 dias |

### Como o nivel e decidido

A logica segue os protocolos de triagem usados em emergencia: uma lista
**ordenada de discriminadores**, avaliada de cima para baixo, parando no
primeiro que se aplica. O criterio que definiu o nivel fica gravado no alerta —
a decisao e auditavel.

```
P1  1. Pessoas ilhadas, feridas ou presas no local
    2. Evento com risco vital direto (deslizamento, fio rompido, enxurrada,
       raio/incendio, erosao) com gravidade alta ou critica
    3. Emergencia declarada pelo cidadao + gravidade critica
    4. Evento critico com 3+ confirmacoes (evento de massa)

P2  5. Emergencia declarada pelo cidadao
    6. Gravidade critica sem vitima identificada
    7. Evento com risco vital direto
    8. Gravidade alta confirmada por outros cidadaos

P3  9. Gravidade alta
   10. Evento confirmado por outros cidadaos
   11. Tipo de evento com risco relevante de agravamento

P4 12. Nenhum criterio acima -> rotina
```

### Regras complementares

- **Escalonamento automatico**: alerta aberto que estoura o SLA de acionamento
  sobe um nivel. O teto e **P2** — atraso nunca transforma um evento sem risco
  de vida em emergencia, senao a fila inteira vira P1 e a triagem perde o
  sentido.
- **Triagem humana prevalece**: a Defesa Civil pode reclassificar qualquer
  alerta informando justificativa; a alteracao vai para o historico.
- **Score de prioridade** (gravidade x2 + risco do tipo + bonus de emergencia +
  pessoas em risco + confirmacoes) nao define o nivel — ele ordena a fila
  *dentro* de cada nivel, junto com o prazo de SLA mais apertado.
- **COBRADE**: os tipos de evento trazem o codigo da Classificacao e Codificacao
  Brasileira de Desastres, usada pelo S2iD na declaracao de situacao de
  emergencia (ex.: alagamento 1.2.3.0.0, deslizamento 1.1.3.2.1,
  vendaval 1.3.2.1.5, granizo 1.3.2.1.3).

## Calculo do score de prioridade

```
score = gravidade x 2
      + risco do tipo de evento (1 a 5)
      + 6  se marcado como emergencia
      + 5  se ha pessoas em risco
      + 2  por confirmacao de outro cidadao (ate 5)
```

Ordenacao final da fila: **nivel** (P1 antes de P2...), depois **prazo de SLA
mais apertado**, depois **score**.

## Stack e por que cada peca

| Camada | Escolha | Motivo |
|---|---|---|
| Interface | Streamlit | App web em Python puro |
| Mapa | Folium + streamlit-folium | Unica opcao que devolve o clique (`last_clicked`) ao Python |
| Base cartografica | OpenStreetMap | Gratuita, sem chave de API |
| GPS | streamlit-geolocation | Acessa `navigator.geolocation` do navegador |
| Banco | SQLite | Arquivo unico, zero instalacao, historico persistente |
| Imagem | Pillow | Reduz a foto antes de gravar |

> OpenStreetMap **nao substitui** o Streamlit: um e o mapa, o outro e a
> aplicacao. O Folium liga os dois.

## Estrutura

```
Problemas Metereologicos/
├── app.py                     # Interface Streamlit (abas)
├── classificacao.py           # Triagem P1-P4, discriminadores e SLA
├── database.py                # SQLite: CRUD, filtros, prioridade, estatisticas
├── servicos.py                # GPS, imagem, mapa Folium, texto de despacho
├── config.py                  # Tipos de evento, pesos, orgaos, constantes
├── gerar_dados_exemplo.py     # Popula o banco para demonstracao
├── requirements.txt
└── data/
    ├── ocorrencias.db         # criado na primeira execucao
    └── fotos/
```

## Como executar

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m streamlit run app.py
```

Para a apresentacao, popule a base antes:

```powershell
python gerar_dados_exemplo.py 40
```

Ajuste `CENTRO_PADRAO` em `config.py` para a sua cidade.

### Sobre o GPS

O navegador so libera a geolocalizacao em **https://** ou em
**http://localhost**. Ao abrir pelo IP da rede local (`http://192.168.x.x:8501`)
o celular **bloqueia** o GPS — nesse caso o app continua funcionando pelo clique
no mapa. Para testar GPS no celular, publique com HTTPS (Streamlit Cloud) ou use
um tunel como `ngrok`.

## Modelo de dados

**ocorrencias** — estado atual
`id, protocolo, categoria, severidade, descricao, latitude, longitude,
precisao_gps, origem_coordenada, referencia, bairro, autor, contato, foto,
emergencia, pessoas_em_risco, status, classificacao_manual, motivo_classificacao,
orgao_acionado, acionado_em, criado_em, atualizado_em, resolvido_em`

O nivel de triagem **nao e gravado** como coluna: ele e recalculado a cada
leitura por `classificacao.py`. Assim, mudar uma regra de prioridade reclassifica
todo o historico sem migracao de dados. Apenas a reclassificacao manual e
persistida.

**historico_status** — auditoria (uma linha por mudanca e por acionamento)

**confirmacoes** — outros cidadaos confirmando o mesmo evento

`database.py` traz uma rotina de migracao que adiciona colunas novas sem
precisar apagar o banco existente.

## Publicacao online

**Streamlit Community Cloud** (gratuito, com HTTPS — necessario para o GPS):
1. Suba o projeto no GitHub (o `.gitignore` ja exclui banco e fotos)
2. Em share.streamlit.io, conecte o repositorio e aponte para `app.py`

O disco do Streamlit Cloud e efemero: o `.db` e as fotos se perdem a cada
redeploy. Para uso real, trocar SQLite por **PostgreSQL** (Supabase/Neon) e as
fotos por um bucket. A camada `database.py` esta isolada justamente para que essa
troca exija mexer em um arquivo so.

## Evolucoes possiveis

- Notificacao push/WhatsApp ao orgao no momento do alerta de emergencia
- Cruzamento com alertas do INMET/CEMADEN para antecipar picos de chamados
- Geocodificacao reversa (Nominatim) preenchendo o endereco pelo GPS
- Zonas de risco desenhadas em polígono, com alerta quando um evento cai dentro
- App mobile consumindo a mesma base via API FastAPI
