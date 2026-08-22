import streamlit as st

st.set_page_config(
    page_title="Ferramentas de Saúde",
    page_icon="💪",
    layout="centered",
    initial_sidebar_state="expanded",
)

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
        <p>Calculadoras de IMC, hidratação diária e necessidade calórica — construídas em Python + Streamlit.</p>
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
    ],
)
st.sidebar.markdown("---")
st.sidebar.caption("Projeto acadêmico — Python & Streamlit\nDesenvolvido por Miguel Bernardo Jr.")

# =========================================================
# FERRAMENTA 1 — CALCULADORA DE IMC
# =========================================================
if opcao.startswith("⚖️"):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h2>⚖️ Calculadora de IMC</h2>", unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Informe seu peso e altura para calcular o Índice de Massa Corporal.</p>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        peso = st.number_input("Peso (kg)", min_value=1.0, max_value=400.0, value=70.0, step=0.1)
    with col2:
        altura = st.number_input("Altura (m)", min_value=0.5, max_value=2.5, value=1.70, step=0.01)

    if st.button("Calcular IMC", key="btn_imc"):
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

    peso_agua = st.number_input("Peso (kg)", min_value=1.0, max_value=400.0, value=70.0, step=0.1, key="peso_agua")

    if st.button("Calcular Meta de Água", key="btn_agua"):
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
# FERRAMENTA 3 — NECESSIDADE CALÓRICA DIÁRIA (TMB)
# =========================================================
else:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h2>🔥 Necessidade Calórica Diária (TMB)</h2>", unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">Calcula sua Taxa Metabólica Basal (fórmula de Mifflin-St Jeor) e o gasto calórico total conforme seu nível de atividade.</p>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        sexo = st.selectbox("Sexo biológico", ["Masculino", "Feminino"])
    with col2:
        idade = st.number_input("Idade", min_value=10, max_value=100, value=30, step=1)
    with col3:
        peso_tmb = st.number_input("Peso (kg)", min_value=1.0, max_value=400.0, value=70.0, step=0.1, key="peso_tmb")

    altura_tmb = st.number_input("Altura (cm)", min_value=100.0, max_value=250.0, value=170.0, step=1.0)

    atividade = st.select_slider(
        "Nível de atividade física",
        options=[
            "Sedentário",
            "Leve (1-3x/semana)",
            "Moderado (3-5x/semana)",
            "Intenso (6-7x/semana)",
            "Atleta (2x por dia)",
        ],
        value="Moderado (3-5x/semana)",
    )

    fatores = {
        "Sedentário": 1.2,
        "Leve (1-3x/semana)": 1.375,
        "Moderado (3-5x/semana)": 1.55,
        "Intenso (6-7x/semana)": 1.725,
        "Atleta (2x por dia)": 1.9,
    }

    if st.button("Calcular Necessidade Calórica", key="btn_tmb"):
        if sexo == "Masculino":
            tmb = (10 * peso_tmb) + (6.25 * altura_tmb) - (5 * idade) + 5
        else:
            tmb = (10 * peso_tmb) + (6.25 * altura_tmb) - (5 * idade) - 161

        gasto_total = tmb * fatores[atividade]

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

st.markdown(
    "<div style='text-align:center; color:#94a3b8; font-size:0.8rem; margin-top:20px;'>"
    "Desenvolvido com Python + Streamlit</div>",
    unsafe_allow_html=True,
)
