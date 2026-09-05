# Clima-Groq

App Streamlit que recebe o nome de uma cidade, busca o clima real na [Open-Meteo](https://open-meteo.com/)
(API gratuita, sem chave) e usa a Groq para recomendar roupa, comida e sugestões do dia — além de um
chat livre com o clima da cidade no contexto, um gráfico com a variação de temperatura (7 dias passados
+ 7 futuros) e um fundo de página que muda conforme a condição do tempo.

Regras de negócio e padrões técnicos fixos estão em `METODOLOGIA.md`. Contratos de API, estrutura de
pastas, prompts e fases de execução estão em `ESPECIFICACAO-TECNICA.md`. Decisões e pendências vigentes
estão em `MEMORIA-PROJETO.md`.

## Rodando localmente

```
pip install -r requirements.txt
cp .env.example .env      # preencha GROQ_API_KEY (e opcionalmente OPENROUTER_API_KEY)
streamlit run app.py
```

Sem nenhuma chave configurada, o app continua funcional: cai automaticamente para recomendações
geradas por regras locais determinísticas (`src/fallback.py`), sem quebrar.

## Testes

```
pytest tests/ -v
```

Os testes cobrem apenas parsing e regras determinísticas (`weather.py`, `fallback.py`) com JSON fixo,
sem chamada de rede. `llm.py` depende de rede e chave válida, por isso não tem teste automatizado —
foi validado manualmente contra a API real da Groq.

## Estrutura

```
app.py              # UI Streamlit — só orquestra, sem regra e sem HTTP
src/
├─ config.py         # carrega .env, expõe Settings
├─ weather.py        # geocode_city(), get_forecast(), get_daily_history(), WMO_CODES, to_context()
├─ llm.py             # get_client(), ask_structured(), ask_free() (Groq + fallback OpenRouter)
├─ prompts.py         # prompts de sistema e templates de usuário
├─ schemas.py         # contratos Pydantic (City, WeatherContext, Recommendation, DailyTemperature)
├─ fallback.py        # regras determinísticas quando o LLM falha ou está ausente
├─ history.py         # SQLite local: log de pesquisas + série diária de temperatura (para o gráfico)
└─ theme.py           # fundo de página em CSS conforme a condição do tempo
tests/               # testes de parsing e de regras, sem rede
clima_historico.db   # banco SQLite local, gerado em runtime — não versionado (.gitignore)
```

## Limitações da v1

Sem login, previsão além de 7 dias futuros, mapas, geolocalização por GPS, multi-idioma ou deploy em
cloud (fora de escopo original — ver `METODOLOGIA.md`, seção 4). O histórico de pesquisas e o gráfico
de temperatura foram adicionados depois da v1 (ver decisão D-10 em `MEMORIA-PROJETO.md`).

## Atribuição

Dados meteorológicos: [Open-Meteo](https://open-meteo.com/), licença [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
