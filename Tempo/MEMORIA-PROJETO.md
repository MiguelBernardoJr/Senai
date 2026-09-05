# MEMÓRIA DO PROJETO — Clima-Groq

> Estado atual, decisões vigentes e pendências. **Sempre anexado.**
> Última atualização: 05/09/2026 · Fase: **F6 concluída — v1 completa, todas as fases do plano de execução entregues**

## Situação

Projeto iniciado dentro da própria pasta `Tempo/` (sem subpasta `clima-groq/` — esta pasta É o repositório do projeto).

**F1 entregue:** `.gitignore` (com `.env` excluído), `.env.example`, `.env` (chaves reais do usuário, local, nunca commitado), `requirements.txt`, `src/__init__.py`, `src/config.py` (`load_settings()`, não lança erro se faltar chave), `app.py` (página mínima). Validado com `streamlit run app.py` → HTTP 200, sem traceback. Ainda não é um repositório git (`git init` não foi rodado).

**F2 entregue:** `src/schemas.py` (`City`, `CurrentWeather`, `WeatherContext`, `Recommendation` — este último adiantado da seção 4, só schema, sem lógica de LLM ainda). `src/weather.py` com `geocode_city()`, `get_forecast()`, `WMO_CODES` (tabela completa da seção 2.3 + `describe_weather_code()`), `to_context()` e `parse_geocode_results()` (helper extraído para permitir teste sem rede). `tests/test_weather.py` com 6 casos usando os JSONs fixos da especificação (geocoding, forecast, código WMO desconhecido, UV ausente) — todos passando, sem chamada HTTP real. `pytest` instalado no venv do projeto Groq (ambiente Python compartilhado, único disponível no momento).

**F3 entregue:** `src/fallback.py` com `build_recommendation()` (faixas de sensação térmica da seção 6, modificadores de chuva/vento/UV/noite, alerta só quando há risco real: tempestade/UV alto/frio extremo < 5°C — limiar de frio extremo é interpretação minha, não está explícito na especificação) e `offline_chat_reply()`. `app.py` reescrito com formulário de cidade, seleção de cidade ambígua (RN-06), métricas (`st.metric`), colunas de roupa/comida, sugestões e alerta, aviso de modo offline, rodapé com atribuição Open-Meteo. `tests/test_fallback.py` com 15 casos (faixas de temperatura, chuva, vento, UV, tempestade, frio extremo, noite) — todos passando. Testado also com dado real (Pirapozinho, geocoding + forecast reais) end-to-end sem erro.

**F4 entregue:** `src/prompts.py` (`SYSTEM_PROMPT`, `FREE_QA_SYSTEM_PROMPT`, `build_recommendation_prompt()`, `build_free_qa_prompt()`). `src/llm.py` com `get_client()` (único cliente `openai` reaproveitado para Groq e OpenRouter, troca só `base_url`/`api_key`/`model` — D-04), `ask_structured()` (1 retry com `temperature=0` e instrução reforçada, depois cai pro `fallback.build_recommendation`) e `ask_free()`. `app.py` agora chama `ask_structured()` em vez do fallback direto. **Testado com a chave Groq real**: chamada HTTP 200, JSON válido, `Recommendation` populada, `used_offline=False`. Sem testes automatizados para `llm.py` (não está na lista de `tests/` da especificação — depende de rede/chave, não faz sentido mockar com JSON fixo como os outros).

**F5 entregue:** chat livre em `app.py` com `st.chat_input` + `st.chat_message`, histórico em `st.session_state.messages` (zerado ao trocar de cidade, como no F3), chamando `ask_free()`. Testado com pergunta real ("posso levar a bicicleta hoje?") — resposta usou os dados reais de chuva/umidade do contexto, sem inventar número.

**F6 entregue:**
- Cache: `_cached_geocode()` / `_cached_forecast()` em `app.py` com `st.cache_data(ttl=900)` — evita nova chamada HTTP a cada rerun.
- Tratamento de erro: `except Exception` (era só `requests.RequestException`) ao redor de geocoding/forecast, sempre com `logger.exception` + mensagem amigável, nunca stacktrace pro usuário. `.streamlit/config.toml` com `showErrorDetails = false` reforça isso no nível do Streamlit.
- Testado o critério "chave inválida → modo offline sem quebrar": com chaves Groq e OpenRouter inválidas de propósito, `ask_structured` voltou `used_offline=True` e uma `Recommendation` válida — sem exceção não tratada.
- Testado RN-06 com dado real: "Santa Rita" retorna 5 candidatos (Paraíba, Zulia/Venezuela, RS, MG, Zacatecas/México) — dispara a lista de seleção.
- `README.md` criado (setup, testes, estrutura, limitações, atribuição).
- `.gitignore` corrigido: `BKP/` **não deve** ser ignorado (é histórico versionado, conforme seção 3 da especificação) — removido do `.gitignore` (erro meu na F1, corrigido aqui).

## Pendência residual

- [ ] Este diretório ainda **não é um repositório git** (`git init` não foi rodado). Antes de decidir GitHub público/privado (pendência já registrada acima), inicializar o repo e confirmar que `.env` está de fato ignorado no primeiro `git status` antes de qualquer `git add`.

## Decisões vigentes

| ID | Decisão | Data |
|---|---|---|
| D-01 | API de clima: **Open-Meteo** (forecast + geocoding). Sem chave, sem cadastro, sem cartão. | 05/09/2026 |
| D-02 | LLM primário **Groq**, modelo `openai/gpt-oss-120b`, configurável por env. | 05/09/2026 |
| D-03 | `llama-3.3-70b-versatile` **proibido** — descontinuado na Groq em 16/08/2026. | 05/09/2026 |
| D-04 | **OpenRouter como fallback** de provedor, mesmo SDK (`openai`) trocando `base_url`. | 05/09/2026 |
| D-05 | Saída de recomendação em **JSON validado por Pydantic**; texto livre só no chat. | 05/09/2026 |
| D-06 | App precisa funcionar **sem LLM** (regras determinísticas) antes de plugar o modelo. | 05/09/2026 |
| D-07 | Sem banco de dados na v1. Estado só em `st.session_state`. | 05/09/2026 |
| D-08 | Chaves Groq/OpenRouter existentes **não serão rotacionadas** — são chaves de estudo, risco aceito pelo usuário. | 05/09/2026 |
| D-09 | Pasta do projeto = a própria `Tempo/` (raiz do repo), não uma subpasta `clima-groq/`. | 05/09/2026 |

## Pendências

- [ ] Decidir se o repositório vai para o GitHub e se será público (se público, atenção redobrada ao `.gitignore` — mesmo com chaves de estudo, não commitar `.env`).
- [ ] Validar se o geocoding da Open-Meteo resolve bem cidades pequenas do interior de SP; se falhar, avaliar entrada por CEP ou lista fixa.

## Riscos conhecidos

| Risco | Mitigação |
|---|---|
| Modelo da Groq ser descontinuado de novo | `GROQ_MODEL` em `.env`, nunca hardcoded (D-02) |
| Open-Meteo é gratuita para uso **não comercial** até ~10.000 chamadas/dia; exige atribuição CC BY 4.0 | Rodapé com crédito + cache de 15 min. Se virar uso corporativo na Vista Alegre, revisar licença. |
| Quota da Groq estourar em demo | Fallback OpenRouter (D-04) e modo offline (D-06) |

## Histórico

Nada arquivado ainda. Quando `MEMORIA-PROJETO.md` passar de ~200 linhas ou acumular decisão revogada, mover para `BKP/HISTORICO-clima-groq-AAAAMM.md`.
