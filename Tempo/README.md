# Clima-Groq

App Streamlit que recebe o nome de uma cidade, busca o clima real na [Open-Meteo](https://open-meteo.com/)
(API gratuita, sem chave) e usa a Groq para recomendar roupa, comida e sugestões do dia — além de um
chat livre com o clima da cidade no contexto.

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
├─ weather.py        # geocode_city(), get_forecast(), WMO_CODES, to_context()
├─ llm.py             # get_client(), ask_structured(), ask_free() (Groq + fallback OpenRouter)
├─ prompts.py         # prompts de sistema e templates de usuário
├─ schemas.py         # contratos Pydantic (City, WeatherContext, Recommendation)
└─ fallback.py        # regras determinísticas quando o LLM falha ou está ausente
tests/               # testes de parsing e de regras, sem rede
```

## Limitações da v1

Sem login, banco de dados, histórico persistente, previsão além de 3 dias, mapas, geolocalização por
GPS, multi-idioma ou deploy em cloud (fora de escopo — ver `METODOLOGIA.md`, seção 4).

## Atribuição

Dados meteorológicos: [Open-Meteo](https://open-meteo.com/), licença [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
