# Prompt de abertura — Claude Code

Colocar os três arquivos na raiz do projeto e colar o texto abaixo na primeira mensagem.

---

Projeto novo: **Clima-Groq** — app Streamlit que recebe o nome de uma cidade, busca o clima real na Open-Meteo (API grátis, sem chave) e usa a Groq para recomendar roupa, comida e sugestões do dia, além de um chat livre com o clima no contexto.

Leia `METODOLOGIA.md` (regras fixas), `ESPECIFICACAO-TECNICA.md` (contratos, estrutura, prompts, fases) e `MEMORIA-PROJETO.md` (decisões e pendências) antes de escrever qualquer código.

Regras de execução:

1. Implemente **fase por fase** conforme a seção 9 da especificação. Ao terminar cada fase, pare e me mostre o critério de aceite atendido antes de seguir.
2. Comece pela **F1** (scaffold + `.env.example` + `.gitignore` com `.env`) e a **F2** (`weather.py` com testes de parsing usando JSON fixo, sem rede).
3. Não coloque chave nenhuma no código. Só `os.getenv`.
4. Não use `llama-3.3-70b-versatile` — descontinuado. Default `openai/gpt-oss-120b`, configurável por `GROQ_MODEL`.
5. O app precisa rodar e ser útil **antes** do LLM entrar (fase F3, modo offline determinístico).
6. Código de produção: type hints, `logging`, tratamento de erro em toda chamada de rede, sem `print`.
7. Ao final de cada fase, atualize `MEMORIA-PROJETO.md` com o que foi entregue e o que mudou de decisão.

Comece pela F1.
