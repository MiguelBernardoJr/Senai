"""
Alerta Cidadao - Problemas Meteorologicos
-----------------------------------------
Canal colaborativo onde o cidadao marca no mapa (por GPS ou clique) eventos
naturais ocorridos na cidade e a Defesa Civil / Prefeitura recebe os alertas
ja triados em niveis P1 a P4, cada um com seu prazo de atendimento (SLA).

Stack: Python + Streamlit + Folium (OpenStreetMap) + SQLite.

Execucao:
    pip install -r requirements.txt
    streamlit run app.py
"""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

import classificacao as tri
import database as bd
from config import (
    CATEGORIAS,
    CENTRO_PADRAO,
    EXTENSOES_IMAGEM,
    NIVEIS,
    ORDEM_NIVEIS,
    ORGAOS,
    PASTA_BASE,
    PRECISAO_GPS_RUIM_M,
    RAIO_DUPLICIDADE_M,
    SEGUNDOS_AUTOREFRESH,
    SEVERIDADES,
    STATUS,
    ZOOM_PADRAO,
)
from servicos import (
    capturar_gps,
    criar_mapa,
    link_google_maps,
    salvar_foto,
    texto_despacho,
)

# ---------------------------------------------------------------------------
# Configuracao da pagina
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Alerta Cidadao - Eventos Naturais",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded",
)

bd.criar_tabelas()

for chave, valor in {
    "ponto": None, "precisao": None, "origem": "Mapa",
    "centro": CENTRO_PADRAO, "zoom": ZOOM_PADRAO,
}.items():
    st.session_state.setdefault(chave, valor)


def etiqueta_nivel(nivel: str, texto_extra: str = "") -> str:
    """Retorna o HTML da etiqueta colorida do nivel (P1..P4)."""
    regra = NIVEIS[nivel]
    return (
        f"<span style='background:{regra['cor']};color:#fff;padding:2px 10px;"
        f"border-radius:12px;font-size:12px;font-weight:700'>"
        f"{nivel} · {regra['nome']}</span> {texto_extra}"
    )


# ---------------------------------------------------------------------------
# Barra lateral
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🚨 Alerta Cidadao")
    st.caption("Eventos naturais · Defesa Civil e Prefeitura")

    perfil = st.radio(
        "Perfil de acesso", ["Cidadao", "Defesa Civil"],
        help="O perfil Defesa Civil libera a central de emergencias.",
    )

    st.divider()
    numeros = bd.estatisticas()
    fila_lateral = bd.fila_emergencia()
    if not fila_lateral.empty:
        contagem = fila_lateral["nivel"].value_counts()
        for nivel in ORDEM_NIVEIS:
            quantidade = int(contagem.get(nivel, 0))
            if quantidade:
                regra = NIVEIS[nivel]
                st.markdown(
                    f"{regra['emoji']} **{nivel} {regra['nome']}** — "
                    f"{quantidade} pendente(s)"
                )
        vencidos = int((fila_lateral["situacao_sla"] == "VENCIDO").sum())
        if vencidos:
            st.error(f"⏰ {vencidos} alerta(s) com SLA vencido")

    st.metric("Alertas registrados", numeros["total"])

    st.divider()
    with st.expander("Como funciona a classificacao"):
        for nivel in ORDEM_NIVEIS:
            regra = NIVEIS[nivel]
            st.markdown(
                f"{regra['emoji']} **{nivel} — {regra['nome']}**  \n"
                f"{regra['descricao']}  \n"
                f"*Acionar em {regra['sla_acionamento_min']} min · "
                f"resolver em {regra['sla_resolucao_h']} h*"
            )

    st.caption(
        "**Risco de vida:** ligue **193** (Bombeiros) ou **199** (Defesa Civil). "
        "Este aplicativo complementa, nao substitui, o telefone de emergencia."
    )


# ---------------------------------------------------------------------------
# Abas
# ---------------------------------------------------------------------------
abas = ["🆘 Registrar alerta", "🗺️ Mapa geral", "📊 Painel", "📜 Historico"]
if perfil == "Defesa Civil":
    abas.insert(0, "🚨 Central de emergencias")

paginas = dict(zip(abas, st.tabs(abas)))


# ===========================================================================
# ABA - REGISTRAR ALERTA
# ===========================================================================
with paginas["🆘 Registrar alerta"]:
    st.subheader("Registrar alerta de evento natural")

    passo_gps, passo_mapa = st.columns([1, 1.6])

    with passo_gps:
        st.markdown("**Passo 1 — onde esta o problema?**")
        st.caption(
            "Use o GPS do aparelho se voce esta no local, ou clique direto "
            "no mapa ao lado."
        )

        posicao = capturar_gps()   # componente precisa ficar FORA do st.form
        if posicao and "erro" in posicao:
            st.warning(posicao["erro"])
        elif posicao:
            novo_ponto = (posicao["latitude"], posicao["longitude"])
            if novo_ponto != st.session_state.ponto:
                st.session_state.update(
                    ponto=novo_ponto, precisao=posicao["precisao"],
                    origem="GPS", centro=novo_ponto, zoom=17,
                )
                st.rerun()

        if st.session_state.ponto is None:
            st.info("Nenhum local definido ainda.")
        else:
            latitude, longitude = st.session_state.ponto
            precisao = st.session_state.precisao
            st.success(
                f"📍 {st.session_state.origem}: `{latitude}, {longitude}`"
                + (f" · ±{precisao:.0f} m" if precisao else "")
            )
            if precisao and precisao > PRECISAO_GPS_RUIM_M:
                st.warning(
                    f"Precisao baixa (±{precisao:.0f} m). Se possivel, ajuste "
                    "o ponto clicando no mapa."
                )
            st.link_button(
                "Conferir no Google Maps",
                link_google_maps(latitude, longitude),
                use_container_width=True,
            )
            if st.button("Limpar local", use_container_width=True):
                st.session_state.update(ponto=None, precisao=None, origem="Mapa")
                st.rerun()

    with passo_mapa:
        mapa_registro = criar_mapa(
            centro=st.session_state.centro,
            zoom=st.session_state.zoom,
            dados=bd.listar_ocorrencias(status=["Aberto", "Em atendimento"]),
            ponto_selecionado=st.session_state.ponto,
            raio_precisao=st.session_state.precisao,
            agrupar=True, colorir_por="nivel",
        )
        retorno = st_folium(
            mapa_registro, key="mapa_registro", height=430,
            use_container_width=True,
            returned_objects=["last_clicked", "center", "zoom"],
        )
        if retorno and retorno.get("last_clicked"):
            clique = retorno["last_clicked"]
            ponto_clicado = (round(clique["lat"], 6), round(clique["lng"], 6))
            if ponto_clicado != st.session_state.ponto:
                st.session_state.update(
                    ponto=ponto_clicado, precisao=None, origem="Mapa"
                )
                if retorno.get("center"):
                    st.session_state.centro = (
                        retorno["center"]["lat"], retorno["center"]["lng"]
                    )
                if retorno.get("zoom"):
                    st.session_state.zoom = retorno["zoom"]
                st.rerun()

    # Sugestao de confirmacao em vez de protocolo duplicado
    if st.session_state.ponto:
        latitude, longitude = st.session_state.ponto
        vizinhas = bd.buscar_proximas(latitude, longitude, RAIO_DUPLICIDADE_M)
        if not vizinhas.empty:
            st.warning(
                f"Ja existe {len(vizinhas)} alerta(s) ativo(s) num raio de "
                f"{RAIO_DUPLICIDADE_M} m. Confirmar o alerta existente eleva a "
                "prioridade dele e evita protocolo duplicado."
            )
            for _, vizinha in vizinhas.head(3).iterrows():
                texto, botao = st.columns([4, 1])
                texto.markdown(
                    f"**{vizinha['protocolo']}** · {vizinha['categoria']} · "
                    f"a {vizinha['distancia_m']:.0f} m · "
                    f"{int(vizinha['confirmacoes'])} confirmacao(oes)"
                )
                if botao.button("Confirmar", key=f"conf_{vizinha['id']}",
                                use_container_width=True):
                    bd.confirmar_ocorrencia(int(vizinha["id"]),
                                            comentario="Confirmado no registro")
                    st.success(f"Confirmacao registrada em {vizinha['protocolo']}.")
                    st.rerun()

    st.divider()
    st.markdown("**Passo 2 — descreva o evento**")

    with st.form("form_ocorrencia", clear_on_submit=True):
        coluna_1, coluna_2 = st.columns(2)
        categoria = coluna_1.selectbox("Tipo de evento", list(CATEGORIAS.keys()))
        severidade = coluna_2.select_slider(
            "Gravidade", options=list(SEVERIDADES.keys()), value="Media"
        )
        emergencia = st.checkbox(
            "🚨 EMERGENCIA — risco imediato, precisa de atendimento agora"
        )
        pessoas_em_risco = st.checkbox(
            "⚠️ Ha pessoas ilhadas, feridas ou presas no local"
        )
        descricao = st.text_area(
            "O que esta acontecendo?",
            placeholder="Ex.: Agua invadindo casas na altura do joelho apos a "
                        "chuva das 15h. Duas familias estao no telhado.",
            height=100,
        )
        coluna_3, coluna_4 = st.columns(2)
        referencia = coluna_3.text_input(
            "Ponto de referencia", placeholder="Rua Sao Paulo, proximo ao n. 450"
        )
        bairro = coluna_4.text_input("Bairro", placeholder="Centro")

        coluna_5, coluna_6 = st.columns(2)
        autor = coluna_5.text_input("Seu nome", placeholder="Opcional")
        contato = coluna_6.text_input(
            "Telefone de contato", placeholder="Importante em emergencias"
        )
        foto = st.file_uploader(
            "Foto do local (opcional)", type=EXTENSOES_IMAGEM,
            help="A imagem e reduzida automaticamente antes de ser salva.",
        )
        enviar = st.form_submit_button(
            "Enviar alerta", type="primary", use_container_width=True
        )

    if enviar:
        if st.session_state.ponto is None:
            st.error("Defina o local pelo GPS ou clicando no mapa antes de enviar.")
        elif not descricao.strip():
            st.error("Descreva o evento para a equipe entender a situacao.")
        else:
            latitude, longitude = st.session_state.ponto
            protocolo = bd.inserir_ocorrencia(
                categoria=categoria, severidade=severidade,
                descricao=descricao.strip(), latitude=latitude, longitude=longitude,
                precisao_gps=st.session_state.precisao,
                origem_coordenada=st.session_state.origem,
                referencia=referencia.strip(), bairro=bairro.strip(),
                autor=autor.strip(), contato=contato.strip(),
                foto=salvar_foto(foto), emergencia=emergencia,
                pessoas_em_risco=pessoas_em_risco,
            )
            st.session_state.update(ponto=None, precisao=None, origem="Mapa")

            # Mostra ao cidadao o resultado da triagem automatica
            registrado = bd.listar_ocorrencias(texto=protocolo)
            st.success(f"✅ Alerta enviado. Protocolo **{protocolo}**.")
            if not registrado.empty:
                linha = registrado.iloc[0]
                regra = NIVEIS[linha["nivel"]]
                st.markdown(
                    etiqueta_nivel(
                        linha["nivel"],
                        f"— acionamento em ate <b>{regra['sla_acionamento_min']} "
                        f"min</b>",
                    ),
                    unsafe_allow_html=True,
                )
                st.caption(f"Criterio aplicado: {linha['motivo_nivel']}")
                if linha["nivel"] == "P1":
                    orgao = CATEGORIAS[categoria]["orgao"]
                    st.error(
                        f"🚨 Classificado como EMERGENCIA. **Se ha risco de vida, "
                        f"ligue agora para {orgao} — {ORGAOS.get(orgao, '199')}.**"
                    )


# ===========================================================================
# ABA - CENTRAL DE EMERGENCIAS (perfil Defesa Civil)
# ===========================================================================
if perfil == "Defesa Civil":

    def _cartao(linha) -> None:
        """Bloco de atendimento de um alerta."""
        regra = NIVEIS[linha["nivel"]]
        prazo = tri.formatar_prazo(linha["minutos_sla"])
        sinal = {"VENCIDO": "⏰", "Atencao": "⚠️"}.get(linha["situacao_sla"], "")
        escalado = " · ⬆️ ESCALADO" if linha["escalado"] else ""
        emoji_sev = SEVERIDADES.get(linha["severidade"], {}).get("emoji", "")

        titulo = (
            f"{regra['emoji']} {linha['nivel']} · {linha['protocolo']} · "
            f"{linha['categoria']} · {emoji_sev} {linha['severidade']} · "
            f"{sinal} {prazo}{escalado}"
        )

        with st.expander(titulo, expanded=linha["nivel"] == "P1"):
            st.markdown(
                etiqueta_nivel(
                    linha["nivel"],
                    f"<span style='color:#666;font-size:12px'>"
                    f"triagem {linha['origem_nivel'].lower()} · "
                    f"{linha['motivo_nivel']}</span>",
                ),
                unsafe_allow_html=True,
            )
            if linha["situacao_sla"] == "VENCIDO":
                st.error(f"SLA de acionamento estourado ({prazo}). {regra['acao']}")
            elif linha["situacao_sla"] == "Atencao":
                st.warning(f"SLA perto do limite: {prazo}.")

            detalhe, acao = st.columns([1.3, 1])

            with detalhe:
                if int(linha["pessoas_em_risco"]):
                    st.error("⚠️ PESSOAS ILHADAS, FERIDAS OU PRESAS NO LOCAL")
                st.markdown(f"**Relato:** {linha['descricao'] or '—'}")
                st.markdown(
                    f"**Local:** {linha['referencia'] or '—'} · "
                    f"Bairro {linha['bairro'] or '—'}"
                )
                precisao = (
                    f" (±{linha['precisao_gps']:.0f} m)"
                    if pd.notna(linha["precisao_gps"]) else ""
                )
                st.markdown(
                    f"**Coordenadas:** `{linha['latitude']}, {linha['longitude']}` "
                    f"· {linha['origem_coordenada']}{precisao}"
                )
                st.markdown(
                    f"**Solicitante:** {linha['autor'] or 'Anonimo'} · "
                    f"{linha['contato'] or 'sem contato'} · "
                    f"**{int(linha['confirmacoes'])}** confirmacao(oes)"
                )
                cobrade = CATEGORIAS.get(linha["categoria"], {}).get("cobrade")
                if cobrade:
                    st.caption(f"COBRADE: {cobrade}")
                if linha["orgao_acionado"]:
                    st.info(
                        f"Acionado: {linha['orgao_acionado']} em "
                        f"{str(linha['acionado_em'])[:16].replace('T', ' ')}"
                    )
                if linha["foto"]:
                    caminho = PASTA_BASE / linha["foto"]
                    if caminho.exists():
                        st.image(str(caminho), use_container_width=True)

            with acao:
                st.link_button(
                    "🧭 Abrir rota no Maps",
                    link_google_maps(linha["latitude"], linha["longitude"]),
                    use_container_width=True,
                )
                sugerido = CATEGORIAS.get(linha["categoria"], {}).get(
                    "orgao", "Defesa Civil"
                )
                orgao = st.selectbox(
                    "Orgao a acionar", list(ORGAOS.keys()),
                    index=list(ORGAOS.keys()).index(sugerido),
                    key=f"orgao_{linha['id']}",
                )
                st.caption(f"Telefone: **{ORGAOS[orgao]}**")
                if st.button("📞 Registrar acionamento",
                             key=f"acionar_{linha['id']}", type="primary",
                             use_container_width=True):
                    bd.registrar_acionamento(int(linha["id"]), orgao)
                    bd.atualizar_status(int(linha["id"]), "Em atendimento",
                                        f"{orgao} acionado", "Defesa Civil")
                    st.rerun()

                novo_status = st.selectbox(
                    "Status", STATUS, index=STATUS.index(linha["status"]),
                    key=f"status_{linha['id']}",
                )
                observacao = st.text_input(
                    "Observacao", key=f"obs_{linha['id']}",
                    placeholder="Equipe a caminho, ETA 20 min",
                )
                if st.button("Atualizar status", key=f"upd_{linha['id']}",
                             use_container_width=True):
                    if bd.atualizar_status(int(linha["id"]), novo_status,
                                           observacao, "Defesa Civil"):
                        st.rerun()
                    else:
                        st.warning("Status ja era esse.")

            # Triagem humana sobrepondo a automatica
            with st.popover("Reclassificar", use_container_width=True):
                st.caption(
                    "A triagem manual prevalece sobre a automatica e fica "
                    "registrada no historico."
                )
                novo_nivel = st.selectbox(
                    "Novo nivel",
                    ORDEM_NIVEIS,
                    index=ORDEM_NIVEIS.index(linha["nivel"]),
                    format_func=lambda n: f"{n} — {NIVEIS[n]['nome']}",
                    key=f"nivel_{linha['id']}",
                )
                justificativa = st.text_input(
                    "Justificativa", key=f"just_{linha['id']}",
                    placeholder="Ex.: equipe confirmou no local que nao ha risco",
                )
                if st.button("Aplicar reclassificacao",
                             key=f"reclass_{linha['id']}",
                             use_container_width=True):
                    if not justificativa.strip():
                        st.warning("Informe a justificativa.")
                    else:
                        bd.reclassificar(int(linha["id"]), novo_nivel,
                                         justificativa.strip(), "Defesa Civil")
                        st.rerun()

            st.markdown("**Mensagem pronta para despacho**")
            st.code(texto_despacho(linha), language=None)

    def _painel_emergencias() -> None:
        """Fila agrupada por nivel. Atualiza sozinha a cada 30 segundos."""
        st.caption(
            f"Atualizado em {datetime.now():%d/%m/%Y %H:%M:%S} · "
            f"recarrega a cada {SEGUNDOS_AUTOREFRESH}s"
        )

        fila = bd.fila_emergencia()
        if fila.empty:
            st.success("Nenhum alerta pendente no momento. 👏")
            return

        # Termometro por nivel
        colunas = st.columns(len(ORDEM_NIVEIS))
        for coluna, nivel in zip(colunas, ORDEM_NIVEIS):
            do_nivel = fila[fila["nivel"] == nivel]
            vencidos = int((do_nivel["situacao_sla"] == "VENCIDO").sum())
            coluna.metric(
                f"{NIVEIS[nivel]['emoji']} {nivel} {NIVEIS[nivel]['nome']}",
                len(do_nivel),
                f"{vencidos} fora do SLA" if vencidos else "no prazo",
                delta_color="inverse" if vencidos else "off",
            )

        mapa_fila = criar_mapa(
            centro=(fila["latitude"].mean(), fila["longitude"].mean()),
            zoom=13, dados=fila, agrupar=False, colorir_por="nivel",
        )
        st_folium(mapa_fila, key="mapa_emergencia", height=360,
                  use_container_width=True, returned_objects=[])

        niveis_visiveis = st.multiselect(
            "Filtrar por nivel", ORDEM_NIVEIS, default=ORDEM_NIVEIS,
            format_func=lambda n: f"{n} — {NIVEIS[n]['nome']}",
        )

        for nivel in ORDEM_NIVEIS:
            if nivel not in niveis_visiveis:
                continue
            do_nivel = fila[fila["nivel"] == nivel]
            if do_nivel.empty:
                continue
            regra = NIVEIS[nivel]
            st.markdown(
                f"### {regra['emoji']} {nivel} — {regra['nome']} "
                f"({len(do_nivel)})"
            )
            st.caption(f"{regra['descricao']} · {regra['acao']}")
            for _, linha in do_nivel.iterrows():
                _cartao(linha)

    if hasattr(st, "fragment"):
        _painel_emergencias = st.fragment(run_every=SEGUNDOS_AUTOREFRESH)(
            _painel_emergencias
        )

    with paginas["🚨 Central de emergencias"]:
        st.subheader("Central de emergencias")
        st.caption(
            "Triagem automatica por discriminadores. Dentro de cada nivel, "
            "ordena pelo prazo de SLA mais apertado."
        )
        _painel_emergencias()


# ===========================================================================
# ABA - MAPA GERAL
# ===========================================================================
with paginas["🗺️ Mapa geral"]:
    st.subheader("Mapa geral dos eventos")

    filtro_1, filtro_2, filtro_3, filtro_4 = st.columns(4)
    categorias_sel = filtro_1.multiselect(
        "Tipo de evento", list(CATEGORIAS.keys()), placeholder="Todos"
    )
    status_sel = filtro_2.multiselect(
        "Status", STATUS, default=["Aberto", "Em atendimento"]
    )
    severidade_sel = filtro_3.multiselect(
        "Gravidade", list(SEVERIDADES.keys()), placeholder="Todas"
    )
    niveis_sel = filtro_4.multiselect(
        "Nivel", ORDEM_NIVEIS, placeholder="Todos",
        format_func=lambda n: f"{n} — {NIVEIS[n]['nome']}",
    )

    filtro_5, filtro_6, filtro_7 = st.columns([1, 1, 2])
    data_de = filtro_5.date_input("De", value=None, format="DD/MM/YYYY")
    data_ate = filtro_6.date_input("Ate", value=None, format="DD/MM/YYYY")
    busca = filtro_7.text_input(
        "Buscar", placeholder="Protocolo, descricao, bairro ou referencia"
    )

    opcao_1, opcao_2, opcao_3 = st.columns(3)
    agrupar = opcao_1.toggle("Agrupar marcadores", value=True)
    calor = opcao_2.toggle("Mapa de calor", value=False)
    colorir = opcao_3.selectbox("Cor por", ["nivel", "categoria", "status"])

    dados = bd.listar_ocorrencias(
        categorias=categorias_sel, status=status_sel,
        severidades=severidade_sel,
        data_inicio=data_de.isoformat() if isinstance(data_de, date) else None,
        data_fim=data_ate.isoformat() if isinstance(data_ate, date) else None,
        texto=busca,
    )
    if niveis_sel and not dados.empty:
        dados = dados[dados["nivel"].isin(niveis_sel)]

    st.caption(f"{len(dados)} evento(s) encontrado(s).")

    centro = (
        (dados["latitude"].mean(), dados["longitude"].mean())
        if not dados.empty else CENTRO_PADRAO
    )
    mapa_geral = criar_mapa(
        centro=centro, zoom=ZOOM_PADRAO if dados.empty else 13,
        dados=dados, agrupar=agrupar, mapa_calor=calor, colorir_por=colorir,
    )
    st_folium(mapa_geral, key="mapa_geral", height=520,
              use_container_width=True, returned_objects=[])

    with st.expander("Ver lista em tabela"):
        if dados.empty:
            st.info("Nenhum registro para os filtros aplicados.")
        else:
            colunas = [
                "protocolo", "nivel", "nivel_nome", "motivo_nivel", "categoria",
                "severidade", "status", "situacao_sla", "confirmacoes",
                "bairro", "referencia", "origem_coordenada", "criado_em",
            ]
            st.dataframe(dados[colunas], use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ Exportar CSV",
                data=dados.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"eventos_{datetime.now():%Y%m%d_%H%M}.csv",
                mime="text/csv",
            )


# ===========================================================================
# ABA - PAINEL
# ===========================================================================
with paginas["📊 Painel"]:
    st.subheader("Painel gerencial")

    numeros = bd.estatisticas()
    sla = bd.aderencia_sla()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total de alertas", numeros["total"])
    m2.metric("Pendentes", numeros["abertas"] + numeros["em_atendimento"])
    m3.metric("Resolvidos", numeros["resolvidas"])
    m4.metric(
        "Acionamentos no prazo",
        f"{sla['percentual']}%" if sla["percentual"] is not None else "—",
        help=f"{sla['no_prazo']} de {sla['acionados']} acionamentos dentro do "
             "SLA do respectivo nivel.",
    )

    m5, m6 = st.columns(2)
    m5.metric(
        "Tempo medio ate o acionamento",
        f"{numeros['tempo_medio_acionamento_min']} min"
        if numeros["tempo_medio_acionamento_min"] is not None else "—",
    )
    m6.metric(
        "Tempo medio ate a resolucao",
        f"{numeros['tempo_medio_horas']} h"
        if numeros["tempo_medio_horas"] is not None else "—",
    )

    st.markdown("### Quadro de classificacao")
    st.dataframe(bd.resumo_por_nivel(), use_container_width=True, hide_index=True)

    todas = bd.listar_ocorrencias()
    if todas.empty:
        st.info("Ainda nao ha dados suficientes para os graficos.")
    else:
        todas["data"] = pd.to_datetime(todas["criado_em"]).dt.date

        graf_1, graf_2 = st.columns(2)
        with graf_1:
            st.markdown("**Alertas por nivel de classificacao**")
            contagem = (
                todas["nivel"].value_counts()
                .reindex(ORDEM_NIVEIS, fill_value=0)
                .rename_axis("nivel").reset_index(name="quantidade")
                .set_index("nivel")
            )
            st.bar_chart(contagem)
        with graf_2:
            st.markdown("**Alertas por tipo de evento**")
            st.bar_chart(
                todas["categoria"].value_counts().rename_axis("categoria")
                .reset_index(name="quantidade").set_index("categoria"),
                horizontal=True,
            )

        st.markdown("**Evolucao diaria de alertas**")
        st.line_chart(todas.groupby("data").size().rename("quantidade").to_frame())

        st.markdown("**Bairros mais atingidos**")
        bairros = todas[todas["bairro"].astype(str).str.strip() != ""]
        if bairros.empty:
            st.caption("Nenhum bairro informado ate agora.")
        else:
            st.dataframe(
                bairros["bairro"].value_counts().head(10)
                .rename_axis("bairro").reset_index(name="quantidade"),
                use_container_width=True, hide_index=True,
            )

    with st.expander("Criterios de triagem aplicados (discriminadores)"):
        st.caption(
            "A avaliacao percorre a lista de cima para baixo e para no primeiro "
            "criterio que se aplica — mesma logica dos protocolos de triagem "
            "usados em emergencia."
        )
        st.dataframe(
            pd.DataFrame(
                [{"Ordem": indice + 1, "Nivel": nivel, "Discriminador": motivo}
                 for indice, (nivel, motivo, _) in enumerate(tri.DISCRIMINADORES)]
                + [{"Ordem": len(tri.DISCRIMINADORES) + 1,
                    "Nivel": tri.NIVEL_PADRAO[0],
                    "Discriminador": tri.NIVEL_PADRAO[1]}]
            ),
            use_container_width=True, hide_index=True,
        )
        st.caption(
            "Regra adicional: alerta aberto que estoura o SLA de acionamento "
            "sobe automaticamente um nivel (escalonamento)."
        )


# ===========================================================================
# ABA - HISTORICO
# ===========================================================================
with paginas["📜 Historico"]:
    st.subheader("Historico de movimentacoes")
    st.caption(
        "Cada mudanca de status, acionamento e reclassificacao gera uma linha "
        "aqui. E o que permite auditar a decisao e medir a evolucao."
    )

    historico = bd.listar_historico()
    if historico.empty:
        st.info("Nenhuma movimentacao registrada.")
    else:
        visao = historico[[
            "criado_em", "protocolo", "categoria",
            "status_anterior", "status_novo", "responsavel", "observacao",
        ]].rename(columns={
            "criado_em": "data/hora", "status_anterior": "de", "status_novo": "para",
        })
        st.dataframe(visao, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Exportar historico (CSV)",
            data=visao.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"historico_{datetime.now():%Y%m%d_%H%M}.csv",
            mime="text/csv",
        )
