# ESPECIFICAÇÃO TÉCNICA — Clima-Groq

Documento de implementação. Ler junto com `METODOLOGIA.md`.

---

## 1. Stack

| Camada | Escolha | Motivo |
|---|---|---|
| UI | Streamlit | pedido do projeto, prototipagem rápida |
| Clima | **Open-Meteo** (`api.open-meteo.com`) | free, **sem chave e sem cadastro**, JSON via GET |
| Geocoding | **Open-Meteo Geocoding** (`geocoding-api.open-meteo.com`) | mesma família, sem chave, retorna lat/lon + admin1/país |
| LLM primário | **Groq** — `openai/gpt-oss-120b` | latência baixa, chave já disponível |
| LLM fallback | **OpenRouter** — mesma interface OpenAI | redundância de quota |
| Validação | Pydantic v2 | contrato de saída do LLM |

### Aviso de modelo (verificado)

`llama-3.3-70b-versatile` e `llama-3.1-8b-instant` **foram descontinuados na Groq em 16/08/2026**. Não usar. Substitutos de produção recomendados pela própria Groq:

- `openai/gpt-oss-120b` → **default do projeto** (raciocínio melhor para as sugestões)
- `openai/gpt-oss-20b` → alternativa mais rápida/barata

O nome do modelo **deve ser configurável por variável de ambiente** (`GROQ_MODEL`), nunca hardcoded.

---

## 2. Contratos de API externa

### 2.1 Geocoding (resolver cidade → coordenadas)

```
GET https://geocoding-api.open-meteo.com/v1/search
  ?name={cidade}
  &count=5
  &language=pt
  &format=json
```

Resposta relevante:

```json
{
  "results": [
    {
      "id": 3452925,
      "name": "Pirapozinho",
      "latitude": -22.27417,
      "longitude": -51.49889,
      "country": "Brasil",
      "country_code": "BR",
      "admin1": "São Paulo",
      "timezone": "America/Sao_Paulo"
    }
  ]
}
```

- Chave `results` **ausente** quando não há match → tratar como "cidade não encontrada".
- Mais de 1 resultado → `st.selectbox` com `f"{name} — {admin1}, {country}"` (RN-06).

### 2.2 Previsão

```
GET https://api.open-meteo.com/v1/forecast
  ?latitude={lat}
  &longitude={lon}
  &current=temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,is_day
  &daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,uv_index_max,sunrise,sunset
  &timezone=auto
  &forecast_days=3
```

Resposta (recortada):

```json
{
  "current": {
    "time": "2026-09-05T14:30",
    "temperature_2m": 27.4,
    "apparent_temperature": 29.1,
    "relative_humidity_2m": 58,
    "precipitation": 0.0,
    "weather_code": 2,
    "wind_speed_10m": 11.5,
    "is_day": 1
  },
  "current_units": { "temperature_2m": "°C", "wind_speed_10m": "km/h" },
  "daily": {
    "time": ["2026-09-05", "2026-09-06", "2026-09-07"],
    "temperature_2m_max": [29.8, 31.2, 24.0],
    "temperature_2m_min": [17.1, 18.4, 16.2],
    "precipitation_probability_max": [10, 5, 80],
    "uv_index_max": [9.1, 9.4, 5.2]
  }
}
```

Sem header de autenticação. Sem body. Apenas GET com query params.

### 2.3 Tabela WMO `weather_code` → pt-BR

Implementar como `dict[int, tuple[str, str]]` = (descrição, ícone/emoji):

| Código | Descrição |
|---|---|
| 0 | Céu limpo |
| 1, 2, 3 | Predominantemente limpo / Parcialmente nublado / Encoberto |
| 45, 48 | Névoa / Névoa com geada |
| 51, 53, 55 | Garoa fraca / moderada / forte |
| 56, 57 | Garoa congelante fraca / forte |
| 61, 63, 65 | Chuva fraca / moderada / forte |
| 66, 67 | Chuva congelante fraca / forte |
| 71, 73, 75 | Neve fraca / moderada / forte |
| 77 | Grãos de neve |
| 80, 81, 82 | Pancadas de chuva fracas / moderadas / violentas |
| 85, 86 | Pancadas de neve fracas / fortes |
| 95 | Tempestade |
| 96, 99 | Tempestade com granizo fraco / forte |

Código desconhecido → "Condição não identificada".

---

## 3. Estrutura de pastas

```
clima-groq/
├─ app.py                    # UI Streamlit — só orquestra, sem regra e sem HTTP
├─ src/
│  ├─ __init__.py
│  ├─ config.py              # carrega .env, expõe Settings (pydantic-settings ou dataclass)
│  ├─ weather.py             # geocode_city(), get_forecast(), WMO_CODES, to_context()
│  ├─ llm.py                 # get_client(), ask_structured(), ask_free()  + fallback OpenRouter
│  ├─ prompts.py             # SYSTEM_PROMPT, USER_TEMPLATE, FREE_QA_TEMPLATE
│  ├─ schemas.py             # City, CurrentWeather, WeatherContext, Recommendation
│  └─ fallback.py            # regras determinísticas quando o LLM falha (RN-05)
├─ tests/
│  ├─ test_weather.py        # parsing com JSON fixo, sem rede
│  └─ test_fallback.py       # faixas de temperatura/chuva
├─ .env.example
├─ .gitignore
├─ requirements.txt
├─ README.md
├─ METODOLOGIA.md
├─ MEMORIA-PROJETO.md
└─ BKP/                      # históricos frios
```

---

## 4. Contratos internos (Pydantic)

```python
class City(BaseModel):
    name: str
    admin1: str | None = None
    country: str
    latitude: float
    longitude: float
    timezone: str

class CurrentWeather(BaseModel):
    temperature: float
    feels_like: float
    humidity: int
    precipitation: float
    wind_speed: float
    weather_code: int
    description: str
    is_day: bool

class WeatherContext(BaseModel):
    city: City
    current: CurrentWeather
    max_today: float
    min_today: float
    rain_chance_today: int
    uv_max_today: float | None

class Recommendation(BaseModel):
    resumo: str                 # 1 frase sobre o tempo agora
    roupa: str                  # 2 a 4 frases
    comida: str                 # 2 a 4 frases, com 1 prato específico nomeado
    sugestoes: list[str]        # 3 a 5 itens, cada um com no máx. 120 caracteres
    alerta: str | None = None   # só quando houver risco real (UV alto, tempestade, frio extremo)
```

O LLM deve responder **exclusivamente** o JSON de `Recommendation`, sem crase, sem markdown, sem preâmbulo. Rotina de parse: `strip()` → remover cercas ```` ```json ```` se vierem → `json.loads` → `Recommendation.model_validate`. Falhou? 1 retry com `temperature=0` e instrução reforçada. Falhou de novo → `fallback.build_recommendation(ctx)`.

---

## 5. Prompts

**System:**

> Você é um assistente brasileiro que recomenda roupa, comida e atividades a partir de dados meteorológicos reais. Você recebe os dados já medidos — nunca invente, altere ou estime números. Escreva em português do Brasil, direto e prático, sem floreio. Responda SOMENTE com o objeto JSON solicitado, sem markdown e sem texto fora do JSON.

**User (recomendação):** serializar o `WeatherContext` como bloco de dados + instrução de campos e limites.

**User (pergunta livre):** mesmo contexto + a pergunta do usuário; aqui a saída é **texto livre**, não JSON. Se a pergunta não tiver relação com clima/cidade, responder normalmente, mas sem inventar dado meteorológico.

Parâmetros: `temperature=0.7` na recomendação, `0.3` na pergunta livre, `max_tokens=1000`.

---

## 6. Regras do modo offline (`fallback.py`)

Determinístico, sem LLM. Base de decisão: `feels_like`, `rain_chance_today`, `wind_speed`, `uv_max_today`.

| Sensação térmica | Roupa | Comida |
|---|---|---|
| < 10 °C | Casaco pesado, camadas, touca e luvas | Caldo, sopa, fondue, chocolate quente |
| 10–17 °C | Jaqueta leve ou moletom, calça comprida | Massa, ensopado, feijoada, sopa leve |
| 18–24 °C | Camiseta + camada extra à noite | Refeição comum, risoto, grelhados |
| 25–31 °C | Roupa leve e clara, tecido respirável | Saladas, peixe grelhado, frutas, sucos |
| > 31 °C | Mínimo de tecido, boné, protetor solar | Comida fria, ceviche, gelados, muita água |

Modificadores: chuva ≥ 50 % → guarda-chuva/capa + calçado fechado; vento > 30 km/h → corta-vento; UV ≥ 8 → protetor solar e evitar 10h–16h; `is_day == False` → sugerir camada extra.

Quando o fallback for usado, a UI mostra: `st.info("Modo offline — sugestões geradas por regras locais.")`

---

## 7. UI (`app.py`)

```
┌─────────────────────────────────────────┐
│ 🌤️  Clima-Groq                          │
│ [ input cidade            ] [Consultar] │
├─────────────────────────────────────────┤
│ Pirapozinho — São Paulo, Brasil         │
│ [27,4 °C] [Sensação 29,1] [58 %] [11 km/h] │  ← st.metric em colunas
│ Parcialmente nublado · máx 29,8 / mín 17,1 · chuva 10 % │
├─────────────────────────────────────────┤
│ 👕 O que vestir     │ 🍲 O que comer    │  ← 2 colunas
├─────────────────────────────────────────┤
│ 💡 Sugestões para hoje  (lista)         │
│ ⚠️ Alerta (só se existir)               │
├─────────────────────────────────────────┤
│ 💬 Pergunte qualquer coisa sobre o dia  │
│ [ st.chat_input ]  → histórico na sessão │
└─────────────────────────────────────────┘
```

- `st.session_state` guarda `context`, `recommendation`, `messages`.
- Trocar de cidade limpa o histórico do chat.
- `st.spinner` em toda chamada de rede.
- Rodapé fixo: fonte dos dados Open-Meteo (CC BY 4.0) + modelo em uso.

---

## 8. Configuração

`.env.example`:

```
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-120b
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openai/gpt-oss-120b
LLM_PROVIDER=groq
```

`requirements.txt`:

```
streamlit>=1.40
groq>=0.11
openai>=1.50
requests>=2.32
pydantic>=2.9
python-dotenv>=1.0
```

Groq também é acessível pelo SDK `openai` apontando para `https://api.groq.com/openai/v1` — usar isso permite **um único cliente** para Groq e OpenRouter, trocando só `base_url`, `api_key` e `model`. É o caminho recomendado.

---

## 9. Plano de execução (fases)

| Fase | Entrega | Aceite |
|---|---|---|
| F1 | Scaffold: pastas, `.env`, `.gitignore`, requirements, `config.py` | `streamlit run app.py` sobe uma página em branco sem erro |
| F2 | `weather.py` + `schemas.py` + testes de parsing | Digitar "Pirapozinho" retorna `WeatherContext` preenchido |
| F3 | `fallback.py` + UI de métricas | App funcional **sem nenhum LLM**, já útil |
| F4 | `llm.py` + `prompts.py` + saída estruturada | Cards de roupa/comida/sugestões vindos do modelo |
| F5 | Chat de pergunta livre com contexto | Perguntar "posso levar a bicicleta?" gera resposta coerente com a chuva |
| F6 | Tratamento de erro, cache, rodapé, README | Derrubar a chave da Groq → app cai para modo offline sem quebrar |

## 10. Critérios de aceite finais

1. Cidade inexistente mostra mensagem amigável, não exceção.
2. Cidade ambígua ("Santa Rita") abre lista de escolha.
3. Nenhuma chave aparece no código, no repositório ou na tela.
4. Com a chave inválida, o app continua entregando as 4 seções (modo offline).
5. Reruns do Streamlit não disparam nova chamada HTTP dentro de 15 minutos.
6. Todos os números da tela batem exatamente com o JSON da Open-Meteo.
