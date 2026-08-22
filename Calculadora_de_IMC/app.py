import streamlit as st

st.set_page_config(page_title="Ferramentas de Saúde", page_icon="💧", layout="centered")

st.title("🧮 Ferramentas de Saúde")
st.caption("Calculadora de IMC e Meta de Hidratação Diária — Python + Streamlit")
st.caption("by Miguel Bernardo")

opcao = st.sidebar.radio(
    "Escolha a ferramenta:",
    ["⚖️ Calculadora de IMC", "💧 Consumo de Água Diário"]
)

# -----------------------------
# FERRAMENTA 1 - CALCULADORA DE IMC
# -----------------------------
if opcao == "⚖️ Calculadora de IMC":
    st.header("Calculadora de IMC")
    st.write("Informe seu peso e altura para calcular o Índice de Massa Corporal.")

    col1, col2 = st.columns(2)
    with col1:
        peso = st.number_input("Peso (kg)", min_value=1.0, max_value=400.0, value=70.0, step=0.1)
    with col2:
        altura = st.number_input("Altura (m)", min_value=0.5, max_value=2.5, value=1.70, step=0.01)

    if st.button("Calcular IMC", type="primary"):
        imc = peso / (altura ** 2)

        if imc < 18.5:
            classificacao, cor = "Abaixo do peso", "orange"
        elif imc < 25:
            classificacao, cor = "Peso normal", "green"
        elif imc < 30:
            classificacao, cor = "Sobrepeso", "orange"
        elif imc < 35:
            classificacao, cor = "Obesidade Grau I", "red"
        elif imc < 40:
            classificacao, cor = "Obesidade Grau II", "red"
        else:
            classificacao, cor = "Obesidade Grau III", "red"

        st.metric("Seu IMC", f"{imc:.2f}")
        st.markdown(f"Classificação: :{cor}[**{classificacao}**]")

        with st.expander("Ver tabela de referência"):
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

# -----------------------------
# FERRAMENTA 2 - CONSUMO DE ÁGUA DIÁRIO
# -----------------------------
else:
    st.header("Calculadora de Consumo de Água Diário")
    st.write("Estimativa da meta ideal de hidratação com base no seu peso (35ml por kg).")

    peso_agua = st.number_input("Peso (kg)", min_value=1.0, max_value=400.0, value=70.0, step=0.1)

    if st.button("Calcular Meta de Água", type="primary"):
        ml_dia = peso_agua * 35
        litros_dia = ml_dia / 1000
        copos_250ml = ml_dia / 250

        st.metric("Meta diária recomendada", f"{litros_dia:.2f} litros")
        st.write(f"Equivale a aproximadamente **{ml_dia:.0f} ml** por dia.")
        st.write(f"Ou cerca de **{copos_250ml:.1f} copos** de 250 ml.")

        st.info(
            "Estimativa geral. Necessidades de hidratação variam conforme clima, "
            "nível de atividade física e condições de saúde."
        )

st.divider()
st.caption("Desenvolvido com Python + Streamlit.")
