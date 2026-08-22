import streamlit as st
import math

st.set_page_config(
    page_title="Ferramentas de Saúde",
    page_icon="💪",
    layout="centered",
    initial_sidebar_state="expanded",
)

# =========================================================
# DADOS PADRÃO DO USUÁRIO (editáveis por qualquer pessoa)
# =========================================================
DEFAULT_IDADE = 43
DEFAULT_PESO = 105.0
DEFAULT_ALTURA_M = 1.85
DEFAULT_ALTURA_CM = 185.0
DEFAULT_ATIVIDADE = "Sedentário"

# =========================================================
# PERFIL COMPARTILHADO ENTRE FERRAMENTAS
# Cada ferramenta lê e atualiza este perfil, para que dados
# informados em uma tela já apareçam pré-preenchidos nas outras.
# =========================================================
if "perfil" not in st.session_state:
    st.session_state.perfil = {
        "peso": DEFAULT_PESO,
        "altura_cm": DEFAULT_ALTURA_CM,
        "idade": DEFAULT_IDADE,
        "sexo": "Masculino",
        "atividade": DEFAULT_ATIVIDADE,
    }
perfil = st.session_state.perfil

ATIVIDADE_OPCOES = ["Sedentário", "Leve (1-3x/semana)", "Moderado (3-5x/semana)", "Intenso (6-7x/semana)", "Atleta (2x por dia)"]
FATORES_ATIVIDADE = {
    "Sedentário": 1.2, "Leve (1-3x/semana)": 1.375, "Moderado (3-5x/semana)": 1.55,
    "Intenso (6-7x/semana)": 1.725, "Atleta (2x por dia)": 1.9,
}

# =========================================================
# CSS CUSTOMIZADO — visual profissional "health-tech"
# =========================================================
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Poppins', sans-serif;
        }

        .stApp {
            background: linear-gradient(180deg, #0f172a 0%, #0f172a 260px, #f4f6fb 260px, #f4f6fb 100%);
        }

        .hero {
            padding: 34px 30px 40px 30px;
            border-radius: 0 0 24px 24px;
            margin: -1rem -1rem 24px -1rem;
            background: linear-gradient(120deg, #0f172a 0%, #1e293b 55%, #0d9488 130%);
            color: white;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.25);
        }
        .hero h1 {
            font-size: 2.1rem;
            font-weight: 800;
            margin-bottom: 4px;
            color: #ffffff;
        }
        .hero p {
            color: #cbd5e1;
            font-size: 0.95rem;
            margin: 0;
        }
        .hero .badge {
            display: inline-block;
            background: rgba(13, 148, 136, 0.18);
            border: 1px solid rgba(45, 212, 191, 0.4);
            color: #5eead4;
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.04em;
            margin-bottom: 14px;
        }

        .card {
            background: white;
            border-radius: 18px;
            padding: 26px 28px;
            box-shadow: 0 4px 18px rgba(15, 23, 42, 0.06);
            border: 1px solid #eef1f6;
            margin-bottom: 18px;
        }

        .card h2 {
            font-weight: 700;
            font-size: 1.35rem;
            color: #0f172a;
            margin-bottom: 4px;
        }

        .card .subtitle {
            color: #64748b;
            font-size: 0.92rem;
            margin-bottom: 18px;
        }

        .stButton > button {
            background: linear-gradient(90deg, #0d9488, #0f766e);
            color: white;
            border: none;
            border-radius: 10px;
            padding: 0.6rem 1.4rem;
            font-weight: 600;
            transition: transform 0.15s ease;
            width: 100%;
        }
        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 14px rgba(13, 148, 136, 0.35);
        }

        section[data-testid="stSidebar"] {
            background: #0f172a;
        }
        section[data-testid="stSidebar"] * {
            color: #e2e8f0 !important;
        }
        section[data-testid="stSidebar"] label span {
            font-weight: 500;
        }

        .result-box {
            border-radius: 14px;
            padding: 20px 22px;
            margin-top: 10px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .result-good { background: #ecfdf5; border: 1px solid #a7f3d0; }
        .result-warn { background: #fff7ed; border: 1px solid #fed7aa; }
        .result-bad  { background: #fef2f2; border: 1px solid #fecaca; }

        .result-value {
            font-size: 2.1rem;
            font-weight: 800;
            color: #0f172a;
        }
        .result-label {
            font-size: 0.85rem;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .school-badge {
            width: 46px;
            height: 46px;
            border-radius: 10px;
            background: linear-gradient(135deg, #0d9488, #0f766e);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 1.1rem;
            color: white;
            flex-shrink: 0;
        }
        .school-card {
            display: flex;
            gap: 12px;
            align-items: flex-start;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 14px;
            margin-top: 10px;
        }
        .school-card .school-name {
            font-weight: 700;
            font-size: 0.88rem;
            color: #f1f5f9 !important;
            margin-bottom: 2px;
        }
        .school-card .school-info {
            font-size: 0.76rem;
            color: #94a3b8 !important;
            line-height: 1.4;
        }

        .zone-bar {
            height: 10px;
            border-radius: 6px;
            margin: 4px 0 14px 0;
        }

        .author-footer {
            text-align: center;
            margin-top: 26px;
            padding-top: 16px;
            border-top: 1px solid #e2e8f0;
            color: #94a3b8;
            font-size: 0.82rem;
        }
        .author-footer a {
            color: #0d9488;
            text-decoration: none;
            font-weight: 600;
            margin: 0 8px;
        }
        .author-footer a:hover {
            text-decoration: underline;
        }

        .macro-bar {
            height: 30px;
            border-radius: 8px;
            display: flex;
            overflow: hidden;
            margin: 12px 0;
        }

        footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# HERO / BANNER
# =========================================================
st.markdown(
    """
    <div class="hero">
        <div class="badge">SUITE DE SAÚDE &amp; PERFORMANCE</div>
        <h1>💪 Ferramentas de Saúde</h1>
        <p>IMC, hidratação, gasto calórico, frequência cardíaca, composição corporal e macronutrientes — Python + Streamlit.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# SIDEBAR — NAVEGAÇÃO
# =========================================================
st.sidebar.markdown("### 🧭 Escolha a ferramenta")
opcao = st.sidebar.radio(
    label="",
    options=[
        "⚖️  Calculadora de IMC",
        "💧  Consumo de Água Diário",
        "🔥  Necessidade Calórica (TMB)",
        "❤️  Frequência Cardíaca de Treino",
        "📏  Percentual de Gordura Corporal",
        "🍽️  Distribuição de Macronutrientes",
        "🎯  Meta de Peso",
        "🍱  Proposta de Alimentação",
    ],
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div class="school-card">
        <div class="school-badge">SP</div>
        <div>
            <div class="school-name">SENAI Presidente Prudente<br>"Santo Paschoal Crepaldi"</div>
            <div class="school-info">
                Rua Roberto Mange, 151 – Jardim Marupiara<br>
                Presidente Prudente/SP – CEP 19060-030<br>
                (18) 3902-8500 · sp.senai.br
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# FERRAMENTA 1 — CALCULADORA DE IMC
# =========================================================
if opcao.startswith("⚖️"):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h2>⚖️ Calculadora de IMC</h2>", unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Campos pré-preenchidos com dados padrão — altere livremente se outra pessoa for usar.</p>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        peso = st.number_input("Peso (kg)", min_value=1.0, max_value=400.0, value=perfil["peso"], step=0.1, key="peso_imc")
    with col2:
        altura = st.number_input("Altura (m)", min_value=0.5, max_value=2.5, value=round(perfil["altura_cm"] / 100, 2), step=0.01, key="altura_imc")

    perfil["peso"] = peso
    perfil["altura_cm"] = altura * 100

    imc = peso / (altura ** 2)

    if imc < 18.5:
        classificacao, estilo, emoji = "Abaixo do peso", "result-warn", "🟠"
    elif imc < 25:
        classificacao, estilo, emoji = "Peso normal", "result-good", "🟢"
    elif imc < 30:
        classificacao, estilo, emoji = "Sobrepeso", "result-warn", "🟠"
    else:
        classificacao, estilo, emoji = "Obesidade", "result-bad", "🔴"

    st.markdown(
        f"""
        <div class="result-box {estilo}">
            <div>
                <div class="result-label">Seu IMC</div>
                <div class="result-value">{imc:.2f}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:1.6rem;">{emoji}</div>
                <div style="font-weight:700; color:#0f172a;">{classificacao}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("📊 Ver tabela de referência"):
        st.markdown(
            """
            | IMC | Classificação |
            |---|---|
            | Abaixo de 18,5 | Abaixo do peso |
            | 18,5 – 24,9 | Peso normal |
            | 25,0 – 29,9 | Sobrepeso |
            | 30,0 – 34,9 | Obesidade Grau I |
            | 35,0 – 39,9 | Obesidade Grau II |
            | Acima de 40,0 | Obesidade Grau III |
            """
        )
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# FERRAMENTA 2 — CONSUMO DE ÁGUA DIÁRIO
# =========================================================
elif opcao.startswith("💧"):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h2>💧 Consumo de Água Diário</h2>", unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Meta ideal de hidratação com base no seu peso (35ml por kg).</p>', unsafe_allow_html=True)

    peso_agua = st.number_input("Peso (kg)", min_value=1.0, max_value=400.0, value=perfil["peso"], step=0.1, key="peso_agua")
    perfil["peso"] = peso_agua

    ml_dia = peso_agua * 35
    litros_dia = ml_dia / 1000
    copos_250ml = ml_dia / 250

    st.markdown(
        f"""
        <div class="result-box result-good">
            <div>
                <div class="result-label">Meta diária</div>
                <div class="result-value">{litros_dia:.2f} L</div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:1.6rem;">🥤</div>
                <div style="font-weight:700; color:#0f172a;">{copos_250ml:.1f} copos (250ml)</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(min(litros_dia / 5, 1.0))
    st.info("Estimativa geral. Necessidades reais variam conforme clima, atividade física e saúde individual.")
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# FERRAMENTA 3 — NECESSIDADE CALÓRICA DIÁRIA (TMB) — LIVE
# =========================================================
elif opcao.startswith("🔥"):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h2>🔥 Necessidade Calórica Diária (TMB)</h2>", unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">Fórmula de Mifflin-St Jeor. Atualiza automaticamente conforme você ajusta os campos.</p>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        sexo = st.selectbox("Sexo biológico", ["Masculino", "Feminino"], index=["Masculino", "Feminino"].index(perfil["sexo"]), key="sexo_tmb")
    with col2:
        idade = st.number_input("Idade", min_value=10, max_value=100, value=perfil["idade"], step=1, key="idade_tmb")
    with col3:
        peso_tmb = st.number_input("Peso (kg)", min_value=1.0, max_value=400.0, value=perfil["peso"], step=0.1, key="peso_tmb")

    altura_tmb = st.number_input("Altura (cm)", min_value=100.0, max_value=250.0, value=perfil["altura_cm"], step=1.0, key="altura_tmb")

    atividade = st.select_slider(
        "Nível de atividade física",
        options=ATIVIDADE_OPCOES,
        value=perfil["atividade"],
        key="atividade_tmb",
    )

    perfil.update(sexo=sexo, idade=idade, peso=peso_tmb, altura_cm=altura_tmb, atividade=atividade)

    if sexo == "Masculino":
        tmb = (10 * peso_tmb) + (6.25 * altura_tmb) - (5 * idade) + 5
    else:
        tmb = (10 * peso_tmb) + (6.25 * altura_tmb) - (5 * idade) - 161

    gasto_total = tmb * FATORES_ATIVIDADE[atividade]

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"""
            <div class="result-box result-good">
                <div>
                    <div class="result-label">TMB (repouso)</div>
                    <div class="result-value">{tmb:.0f}</div>
                </div>
                <div style="font-size:1.6rem;">🛌</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="result-box result-warn">
                <div>
                    <div class="result-label">Gasto total / dia</div>
                    <div class="result-value">{gasto_total:.0f}</div>
                </div>
                <div style="font-size:1.6rem;">🔥</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Sugestões de meta calórica:**")
    cc1, cc2, cc3 = st.columns(3)
    cc1.metric("Emagrecimento", f"{gasto_total - 500:.0f} kcal", "-500 kcal")
    cc2.metric("Manutenção", f"{gasto_total:.0f} kcal", "0 kcal")
    cc3.metric("Ganho de massa", f"{gasto_total + 400:.0f} kcal", "+400 kcal")

    st.info("Valores calculados via fórmula de Mifflin-St Jeor. Não substitui orientação de nutricionista ou médico.")
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# FERRAMENTA 4 — FREQUÊNCIA CARDÍACA DE TREINO
# =========================================================
elif opcao.startswith("❤️"):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h2>❤️ Frequência Cardíaca de Treino</h2>", unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">Calcula sua FC máxima estimada e as zonas de intensidade de treino.</p>',
        unsafe_allow_html=True,
    )

    idade_fc = st.number_input("Idade", min_value=10, max_value=100, value=perfil["idade"], step=1, key="idade_fc")
    perfil["idade"] = idade_fc
    fc_repouso = st.number_input(
        "Frequência cardíaca de repouso (bpm) — opcional",
        min_value=30, max_value=120, value=70, step=1,
        help="Meça ao acordar, antes de levantar da cama, para maior precisão."
    )

    fc_max = 220 - idade_fc

    st.markdown(
        f"""
        <div class="result-box result-bad">
            <div>
                <div class="result-label">FC Máxima estimada</div>
                <div class="result-value">{fc_max} bpm</div>
            </div>
            <div style="font-size:1.6rem;">❤️</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    zonas = [
        ("Zona 1 — Aquecimento", 0.50, 0.60, "#93c5fd"),
        ("Zona 2 — Queima de gordura", 0.60, 0.70, "#5eead4"),
        ("Zona 3 — Cardio (aeróbico)", 0.70, 0.80, "#fbbf24"),
        ("Zona 4 — Intenso (anaeróbico)", 0.80, 0.90, "#fb923c"),
        ("Zona 5 — Máximo esforço", 0.90, 1.00, "#f87171"),
    ]

    st.markdown("**Zonas de treino (% da FC máxima):**")
    for nome, pmin, pmax, cor in zonas:
        bpm_min = round(fc_max * pmin)
        bpm_max = round(fc_max * pmax)
        st.markdown(
            f"""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px;">
                <span style="font-weight:600; color:#0f172a; font-size:0.9rem;">{nome}</span>
                <span style="color:#475569; font-size:0.85rem;">{bpm_min}–{bpm_max} bpm</span>
            </div>
            <div class="zone-bar" style="background: linear-gradient(90deg, {cor} {int(pmin*100)}%, {cor} {int(pmax*100)}%); width:100%; opacity:0.85;"></div>
            """,
            unsafe_allow_html=True,
        )

    st.info("Fórmula simplificada (220 - idade). Métodos como Karvonen (usando FC de repouso) são mais precisos para atletas.")
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# FERRAMENTA 5 — PERCENTUAL DE GORDURA CORPORAL (MÉTODO NAVY)
# =========================================================
elif opcao.startswith("📏"):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h2>📏 Percentual de Gordura Corporal</h2>", unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">Estimativa via método da Marinha dos EUA (medidas de circunferência corporal).</p>',
        unsafe_allow_html=True,
    )

    sexo_bf = st.selectbox("Sexo biológico", ["Masculino", "Feminino"], index=["Masculino", "Feminino"].index(perfil["sexo"]), key="sexo_bf")
    altura_bf = st.number_input("Altura (cm)", min_value=100.0, max_value=250.0, value=perfil["altura_cm"], step=1.0, key="altura_bf")
    perfil.update(sexo=sexo_bf, altura_cm=altura_bf)
    pescoco = st.number_input("Circunferência do pescoço (cm)", min_value=20.0, max_value=60.0, value=38.0, step=0.5)
    cintura = st.number_input("Circunferência da cintura (cm)", min_value=40.0, max_value=200.0, value=95.0, step=0.5)

    quadril = None
    if sexo_bf == "Feminino":
        quadril = st.number_input("Circunferência do quadril (cm)", min_value=40.0, max_value=200.0, value=95.0, step=0.5)

    try:
        if sexo_bf == "Masculino":
            bf = 495 / (1.0324 - 0.19077 * math.log10(cintura - pescoco) + 0.15456 * math.log10(altura_bf)) - 450
        else:
            bf = 495 / (1.29579 - 0.35004 * math.log10(cintura + quadril - pescoco) + 0.22100 * math.log10(altura_bf)) - 450

        if bf < 0 or bf > 60 or math.isnan(bf):
            raise ValueError

        if sexo_bf == "Masculino":
            faixas = [(6, "Essencial"), (14, "Atlético"), (18, "Fitness"), (25, "Aceitável"), (100, "Elevado")]
        else:
            faixas = [(14, "Essencial"), (21, "Atlético"), (25, "Fitness"), (32, "Aceitável"), (100, "Elevado")]

        categoria = next(nome for limite, nome in faixas if bf < limite)
        estilo = "result-good" if categoria in ("Atlético", "Fitness") else "result-warn"

        st.markdown(
            f"""
            <div class="result-box {estilo}">
                <div>
                    <div class="result-label">Gordura corporal estimada</div>
                    <div class="result-value">{bf:.1f}%</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:1.6rem;">📏</div>
                    <div style="font-weight:700; color:#0f172a;">{categoria}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    except (ValueError, ZeroDivisionError):
        st.warning("Confira as medidas informadas — a cintura precisa ser maior que o pescoço para o cálculo funcionar.")

    st.info("Método de estimativa por circunferências (US Navy). Precisão inferior a métodos clínicos como bioimpedância ou DEXA.")
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# FERRAMENTA 6 — DISTRIBUIÇÃO DE MACRONUTRIENTES
# =========================================================
elif opcao.startswith("🍽️"):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h2>🍽️ Distribuição de Macronutrientes</h2>", unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">Calcula gramas de proteína, carboidrato e gordura a partir do seu gasto calórico e objetivo.</p>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        sexo_m = st.selectbox("Sexo biológico", ["Masculino", "Feminino"], index=["Masculino", "Feminino"].index(perfil["sexo"]), key="sexo_m")
    with col2:
        idade_m = st.number_input("Idade", min_value=10, max_value=100, value=perfil["idade"], step=1, key="idade_m")
    with col3:
        peso_m = st.number_input("Peso (kg)", min_value=1.0, max_value=400.0, value=perfil["peso"], step=0.1, key="peso_m")

    altura_m = st.number_input("Altura (cm)", min_value=100.0, max_value=250.0, value=perfil["altura_cm"], step=1.0, key="altura_m")

    atividade_m = st.select_slider(
        "Nível de atividade física",
        options=ATIVIDADE_OPCOES,
        value=perfil["atividade"],
        key="atividade_m",
    )

    objetivo = st.radio(
        "Objetivo",
        ["Emagrecimento", "Manutenção", "Ganho de massa"],
        horizontal=True,
    )

    perfil.update(sexo=sexo_m, idade=idade_m, peso=peso_m, altura_cm=altura_m, atividade=atividade_m)

    if sexo_m == "Masculino":
        tmb_m = (10 * peso_m) + (6.25 * altura_m) - (5 * idade_m) + 5
    else:
        tmb_m = (10 * peso_m) + (6.25 * altura_m) - (5 * idade_m) - 161

    gasto_m = tmb_m * FATORES_ATIVIDADE[atividade_m]

    ajuste = {"Emagrecimento": -500, "Manutenção": 0, "Ganho de massa": 400}
    calorias_alvo = gasto_m + ajuste[objetivo]

    # Distribuição de macros por objetivo (% de calorias)
    percentuais = {
        "Emagrecimento": {"Proteína": 0.40, "Carboidrato": 0.30, "Gordura": 0.30},
        "Manutenção": {"Proteína": 0.30, "Carboidrato": 0.40, "Gordura": 0.30},
        "Ganho de massa": {"Proteína": 0.30, "Carboidrato": 0.50, "Gordura": 0.20},
    }[objetivo]

    prot_g = (calorias_alvo * percentuais["Proteína"]) / 4
    carb_g = (calorias_alvo * percentuais["Carboidrato"]) / 4
    gord_g = (calorias_alvo * percentuais["Gordura"]) / 9

    st.markdown(
        f"""
        <div class="result-box result-warn">
            <div>
                <div class="result-label">Meta calórica diária</div>
                <div class="result-value">{calorias_alvo:.0f} kcal</div>
            </div>
            <div style="font-size:1.6rem;">🎯</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="macro-bar">
            <div style="width:{percentuais['Proteína']*100}%; background:#0d9488;"></div>
            <div style="width:{percentuais['Carboidrato']*100}%; background:#fbbf24;"></div>
            <div style="width:{percentuais['Gordura']*100}%; background:#f87171;"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("🥩 Proteína", f"{prot_g:.0f} g", f"{percentuais['Proteína']*100:.0f}% kcal")
    m2.metric("🍞 Carboidrato", f"{carb_g:.0f} g", f"{percentuais['Carboidrato']*100:.0f}% kcal")
    m3.metric("🥑 Gordura", f"{gord_g:.0f} g", f"{percentuais['Gordura']*100:.0f}% kcal")

    st.info("Distribuição estimada com base em diretrizes gerais de nutrição esportiva. Ajustes finos exigem acompanhamento de nutricionista.")
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# FERRAMENTA 7 — META DE PESO
# =========================================================
elif opcao.startswith("🎯"):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h2>🎯 Meta de Peso</h2>", unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">Defina seu peso atual, sua meta e um ritmo saudável de progressão para estimar o prazo.</p>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        peso_atual = st.number_input("Peso atual (kg)", min_value=1.0, max_value=400.0, value=perfil["peso"], step=0.1, key="peso_atual_meta")
    with col2:
        peso_meta = st.number_input("Peso meta (kg)", min_value=1.0, max_value=400.0, value=perfil["peso"] - 10, step=0.1, key="peso_meta")

    perfil["peso"] = peso_atual

    ritmo = st.slider(
        "Ritmo semanal desejado (kg/semana)",
        min_value=0.25, max_value=1.0, value=0.5, step=0.05,
        help="Faixa considerada segura pela literatura: 0,25 a 1kg por semana."
    )

    diferenca = peso_meta - peso_atual

    if abs(diferenca) < 0.1:
        st.success("Você já está no peso meta! 🎉")
    else:
        direcao = "emagrecimento" if diferenca < 0 else "ganho de peso"
        semanas = math.ceil(abs(diferenca) / ritmo)
        meses = semanas / 4.345

        c1, c2, c3 = st.columns(3)
        c1.metric("Diferença", f"{abs(diferenca):.1f} kg", direcao.capitalize())
        c2.metric("Prazo estimado", f"{semanas} semanas", f"~{meses:.1f} meses")
        c3.metric("Ritmo", f"{ritmo:.2f} kg/sem", "")

        # Projeção de progresso
        pesos_projetados = [peso_atual + (diferenca * i / semanas) for i in range(semanas + 1)]
        st.markdown("**Curva de progressão projetada:**")
        st.line_chart(pesos_projetados)

        if ritmo > 1.0:
            st.warning("Ritmos acima de 1kg/semana por longos períodos costumam ser insustentáveis e podem indicar perda de massa magra, não apenas gordura.")
        st.info("Estimativa linear simplificada. O progresso real varia — platôs são normais e não significam falha.")

    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# FERRAMENTA 8 — PROPOSTA DE ALIMENTAÇÃO
# =========================================================
else:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h2>🍱 Proposta de Alimentação</h2>", unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">Cardápio ilustrativo distribuído em 5 refeições, com base no seu gasto calórico estimado.</p>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        sexo_a = st.selectbox("Sexo biológico", ["Masculino", "Feminino"], index=["Masculino", "Feminino"].index(perfil["sexo"]), key="sexo_a")
    with col2:
        idade_a = st.number_input("Idade", min_value=10, max_value=100, value=perfil["idade"], step=1, key="idade_a")
    with col3:
        peso_a = st.number_input("Peso (kg)", min_value=1.0, max_value=400.0, value=perfil["peso"], step=0.1, key="peso_a")

    altura_a = st.number_input("Altura (cm)", min_value=100.0, max_value=250.0, value=perfil["altura_cm"], step=1.0, key="altura_a")

    atividade_a = st.select_slider(
        "Nível de atividade física",
        options=ATIVIDADE_OPCOES,
        value=perfil["atividade"],
        key="atividade_a",
    )

    objetivo_a = st.radio("Objetivo", ["Emagrecimento", "Manutenção", "Ganho de massa"], horizontal=True, key="objetivo_a")

    perfil.update(sexo=sexo_a, idade=idade_a, peso=peso_a, altura_cm=altura_a, atividade=atividade_a)

    if sexo_a == "Masculino":
        tmb_a = (10 * peso_a) + (6.25 * altura_a) - (5 * idade_a) + 5
    else:
        tmb_a = (10 * peso_a) + (6.25 * altura_a) - (5 * idade_a) - 161

    ajuste_a = {"Emagrecimento": -500, "Manutenção": 0, "Ganho de massa": 400}
    calorias_dia = (tmb_a * FATORES_ATIVIDADE[atividade_a]) + ajuste_a[objetivo_a]

    st.markdown(
        f"""
        <div class="result-box result-good">
            <div>
                <div class="result-label">Meta calórica diária</div>
                <div class="result-value">{calorias_dia:.0f} kcal</div>
            </div>
            <div style="font-size:1.6rem;">🍽️</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    refeicoes = [
        ("☀️ Café da manhã", 0.25, "Ovos mexidos ou omelete, pão integral, fruta e café/chá sem açúcar"),
        ("🍛 Almoço", 0.30, "Proteína magra (frango, peixe ou carne), arroz integral e feijão, legumes e salada crua"),
        ("🍎 Lanche da tarde", 0.15, "Iogurte natural, oleaginosas (castanhas/amêndoas) e uma fruta"),
        ("🌙 Jantar", 0.25, "Proteína magra, vegetais variados e uma porção menor de carboidrato complexo"),
        ("🥛 Ceia", 0.05, "Leite ou iogurte, ou chá — refeição leve antes de dormir"),
    ]

    st.markdown("**Distribuição sugerida ao longo do dia:**")
    for nome, pct, sugestao in refeicoes:
        kcal_refeicao = calorias_dia * pct
        st.markdown(
            f"""
            <div style="display:flex; justify-content:space-between; align-items:baseline; margin-top:14px;">
                <span style="font-weight:700; color:#0f172a;">{nome}</span>
                <span style="color:#0d9488; font-weight:700; font-size:0.9rem;">{kcal_refeicao:.0f} kcal ({int(pct*100)}%)</span>
            </div>
            <div style="color:#64748b; font-size:0.85rem; margin-top:2px;">{sugestao}</div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("Cardápio genérico e ilustrativo, baseado em diretrizes gerais de alimentação equilibrada. Não substitui avaliação de nutricionista, que considera exames, restrições e preferências individuais.")
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# RODAPÉ — AUTOR / CONTATO
# =========================================================
st.markdown(
    """
    <div class="author-footer">
        Desenvolvido por <strong>Miguel Bernardo Jr.</strong> · Python + Streamlit<br>
        <a href="https://www.linkedin.com/in/miguelbernardojr/" target="_blank">🔗 LinkedIn</a>
        <a href="https://github.com/MiguelBernardoJr" target="_blank">💻 GitHub</a>
    </div>
    """,
    unsafe_allow_html=True,
)
