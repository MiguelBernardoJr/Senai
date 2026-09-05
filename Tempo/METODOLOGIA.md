# METODOLOGIA — Clima-Groq

> Arquivo pequeno, estável e **sempre anexado**. Regra de negócio e padrões inegociáveis.
> Estado atual, pendências e decisões em aberto ficam em `MEMORIA-PROJETO.md`.

## 1. O que o produto faz

Aplicação Streamlit que recebe **o nome de uma cidade** e devolve, com base no clima real daquele momento:

1. **Roupa** — o que vestir para sair agora.
2. **Comida** — o que cozinhar / comer combinando com o tempo.
3. **Sugestões** — 3 a 5 ideias práticas (atividade, cuidado, alerta).
4. **Campo aberto** — pergunta livre do usuário respondida **com o clima da cidade no contexto**.

## 2. Regras de negócio

| # | Regra |
|---|-------|
| RN-01 | Nenhuma resposta ao usuário pode ser gerada sem dado climático real carregado. Sem clima → sem LLM. |
| RN-02 | O LLM **nunca inventa número**. Temperatura, chuva, vento e umidade vêm exclusivamente do payload da API e são exibidos pela UI, não pelo texto do modelo. |
| RN-03 | Toda resposta em **português do Brasil**, tom direto, sem emoji excessivo (máx. 1 por bloco). |
| RN-04 | Unidades sempre métricas: °C, km/h, mm, %. |
| RN-05 | Se o LLM falhar (timeout, quota, JSON inválido), a aplicação **degrada para regras locais determinísticas** e sinaliza na UI que a resposta é do modo offline. Nunca mostrar stacktrace. |
| RN-06 | Cidade ambígua (mais de um resultado no geocoding) → usuário escolhe numa lista com estado/país. Nunca adivinhar. |
| RN-07 | Toda a lógica de vestuário/comida é **sugestiva**, não prescritiva. Nada de recomendação médica. |

## 3. Padrões técnicos fixos

- **Python 3.11+**, Streamlit, `requests`, `pydantic`, `python-dotenv`, SDK `groq`.
- **Nenhuma chave no código.** Sempre `.env` + `os.getenv`. `.env` no `.gitignore` desde o primeiro commit.
- **API de clima sem chave e sem cadastro: Open-Meteo.** Não trocar por OpenWeather/WeatherAPI (exigem cadastro).
- **Atribuição obrigatória** no rodapé: dados meteorológicos Open-Meteo, licença CC BY 4.0.
- Camadas separadas: `weather` (dados) → `llm` (interpretação) → `app` (UI). A UI não chama HTTP direto.
- Toda saída estruturada do LLM é validada por **modelo Pydantic**. JSON inválido = 1 retry, depois fallback.
- Cache de rede com `st.cache_data(ttl=900)`. Não bater na API a cada rerun do Streamlit.
- Timeout de 10s em toda chamada HTTP. `raise_for_status()` sempre.
- Código de produção: type hints, docstrings curtas, sem `print` (usar `logging`).

## 4. Fora de escopo (v1)

Login, banco de dados, histórico de consultas, previsão além de 3 dias, mapas, geolocalização por GPS, multi-idioma, deploy em cloud.
