"""
Gera alertas ficticios para demonstracao em sala de aula.

Uso:
    python gerar_dados_exemplo.py             # cria 25 alertas
    python gerar_dados_exemplo.py 60          # cria 60 alertas
    python gerar_dados_exemplo.py --limpar    # apaga tudo antes de gerar
    python gerar_dados_exemplo.py --cobertura # cria 2 alertas por categoria
                                               # (combinavel com --limpar)

Os pontos sao espalhados ao redor do CENTRO_PADRAO definido em config.py.
"""

from __future__ import annotations

import random
import sqlite3
import sys
from datetime import datetime, timedelta

from config import (
    CAMINHO_BANCO,
    CATEGORIAS,
    CENTRO_PADRAO,
    RAIO_DUPLICIDADE_M,
    SEVERIDADES,
)
import database as bd

BAIRROS = ["Centro", "Jardim Planalto", "Vila Sao Jose", "Parque Alvorada",
           "Jardim Brasil", "Distrito Industrial", "Vila Nova", "Cohab"]

RELATOS = {
    "Alagamento / enchente": "Agua acumulada na via apos a chuva, passagem impedida.",
    "Enxurrada / inundacao": "Correnteza forte invadindo as casas da rua baixa.",
    "Deslizamento de terra": "Barranco cedeu sobre a calcada, risco para os moradores.",
    "Arvore caida": "Arvore de grande porte caida sobre a pista.",
    "Vendaval / destelhamento": "Telhas arrancadas pelo vento em varias casas.",
    "Granizo": "Queda de granizo com danos em veiculos e telhados.",
    "Raio / incendio": "Principio de incendio apos descarga eletrica.",
    "Fio de energia rompido": "Cabo rompido ao alcance de pedestres.",
    "Erosao / rachadura em encosta": "Rachadura aumentando apos as chuvas.",
    "Bueiro entupido / boca de lobo": "Boca de lobo obstruida por folhas e entulho.",
    "Buraco na via": "Buraco profundo no meio da pista.",
    "Via interditada / obstruida": "Via bloqueada por queda de estrutura.",
    "Outros": "Situacao atipica relatada pelo cidadao.",
}

NOMES = ["Ana", "Carlos", "Fernanda", "Joao", "Luciana", "Marcos",
         "Patricia", "Rafael", "Simone", "Tiago"]


def limpar_banco() -> None:
    with bd.conectar() as conexao:
        conexao.executescript(
            "DELETE FROM confirmacoes;"
            "DELETE FROM historico_status;"
            "DELETE FROM ocorrencias;"
            "DELETE FROM sqlite_sequence WHERE name IN "
            "('ocorrencias','historico_status','confirmacoes');"
        )
    print("Banco limpo.")


def gerar(quantidade: int = 25) -> None:
    bd.criar_tabelas()
    latitude_base, longitude_base = CENTRO_PADRAO
    categorias = list(CATEGORIAS.keys())
    severidades = list(SEVERIDADES.keys())

    for _ in range(quantidade):
        categoria = random.choice(categorias)
        severidade = random.choices(severidades, weights=[3, 4, 3, 2])[0]
        emergencia = severidade in ("Alta", "Critica") and random.random() < 0.4
        risco = emergencia and random.random() < 0.5
        usa_gps = random.random() < 0.6

        protocolo = bd.inserir_ocorrencia(
            categoria=categoria,
            severidade=severidade,
            descricao=RELATOS[categoria],
            latitude=round(latitude_base + random.uniform(-0.035, 0.035), 6),
            longitude=round(longitude_base + random.uniform(-0.035, 0.035), 6),
            precisao_gps=round(random.uniform(5, 45), 1) if usa_gps else None,
            origem_coordenada="GPS" if usa_gps else "Mapa",
            referencia=f"Rua {random.randint(1, 30)}, n. {random.randint(10, 900)}",
            bairro=random.choice(BAIRROS),
            autor=random.choice(NOMES),
            contato=f"18 9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
            emergencia=emergencia,
            pessoas_em_risco=risco,
        )

        with bd.conectar() as conexao:
            linha = conexao.execute(
                "SELECT id FROM ocorrencias WHERE protocolo = ?", (protocolo,)
            ).fetchone()
            registro_id = linha["id"]

            # 70% nas ultimas 48h (fila "viva"), o resto nos ultimos 20 dias
            if random.random() < 0.7:
                criado = datetime.now() - timedelta(
                    hours=random.randint(0, 47), minutes=random.randint(0, 59)
                )
            else:
                criado = datetime.now() - timedelta(
                    days=random.randint(3, 20), hours=random.randint(0, 23)
                )
            conexao.execute(
                "UPDATE ocorrencias SET criado_em = ?, atualizado_em = ? WHERE id = ?",
                (criado.isoformat(timespec="seconds"),
                 criado.isoformat(timespec="seconds"), registro_id),
            )

        for _ in range(random.choice([0, 0, 0, 1, 2, 4])):
            bd.confirmar_ocorrencia(registro_id, autor=random.choice(NOMES))

        sorteio = random.random()
        if sorteio < 0.30:
            bd.registrar_acionamento(
                registro_id, CATEGORIAS[categoria]["orgao"], "Defesa Civil"
            )
        if sorteio < 0.35:
            bd.atualizar_status(registro_id, "Resolvido",
                                "Atendimento concluido pela equipe", "Defesa Civil")
        elif sorteio < 0.55:
            bd.atualizar_status(registro_id, "Em atendimento",
                                "Equipe deslocada ao local", "Defesa Civil")

    print(f"{quantidade} alertas gerados em {CAMINHO_BANCO}")
    print(bd.estatisticas())


def gerar_cobertura(semente: int = 42) -> None:
    """Cria exatamente 2 alertas para CADA categoria de CATEGORIAS.

    Um par por categoria, com os dois extremos da triagem: um ponto grave
    (severidade Critica, emergencia, GPS) e um ponto leve (severidade Baixa,
    sem emergencia, coordenada de mapa). Serve para a apresentacao: toda
    categoria aparece no mapa e mostra os dois extremos de prioridade.

    Usa uma instancia local de random.Random (nunca o modulo random global)
    para que a mesma semente sempre produza as mesmas coordenadas.
    """
    bd.criar_tabelas()
    sorteio = random.Random(semente)
    latitude_base, longitude_base = CENTRO_PADRAO
    pontos_usados: list[tuple[float, float]] = []

    def sortear_coordenada() -> tuple[float, float]:
        """Sorteia lat/lon ate ficar a >= RAIO_DUPLICIDADE_M de todo ponto ja usado."""
        while True:
            lat = round(latitude_base + sorteio.uniform(-0.035, 0.035), 6)
            lon = round(longitude_base + sorteio.uniform(-0.035, 0.035), 6)
            if all(
                bd.distancia_metros(lat, lon, outra_lat, outra_lon)
                >= RAIO_DUPLICIDADE_M
                for outra_lat, outra_lon in pontos_usados
            ):
                pontos_usados.append((lat, lon))
                return lat, lon

    contagem: dict[str, int] = {}

    for categoria, dados_categoria in CATEGORIAS.items():
        pares = (
            {  # Ponto A: grave
                "severidade": "Critica",
                "emergencia": True,
                "pessoas_em_risco": bool(dados_categoria["risco_vital"]),
                "origem_coordenada": "GPS",
                "precisao_gps": round(sorteio.uniform(5, 45), 1),
            },
            {  # Ponto B: leve
                "severidade": "Baixa",
                "emergencia": False,
                "pessoas_em_risco": False,
                "origem_coordenada": "Mapa",
                "precisao_gps": None,
            },
        )

        for dados_ponto in pares:
            latitude, longitude = sortear_coordenada()

            protocolo = bd.inserir_ocorrencia(
                categoria=categoria,
                severidade=dados_ponto["severidade"],
                descricao=RELATOS[categoria],
                latitude=latitude,
                longitude=longitude,
                precisao_gps=dados_ponto["precisao_gps"],
                origem_coordenada=dados_ponto["origem_coordenada"],
                referencia=f"Rua {sorteio.randint(1, 30)}, n. {sorteio.randint(10, 900)}",
                bairro=sorteio.choice(BAIRROS),
                autor=sorteio.choice(NOMES),
                contato=f"18 9{sorteio.randint(1000, 9999)}-{sorteio.randint(1000, 9999)}",
                emergencia=dados_ponto["emergencia"],
                pessoas_em_risco=dados_ponto["pessoas_em_risco"],
            )

            with bd.conectar() as conexao:
                linha = conexao.execute(
                    "SELECT id FROM ocorrencias WHERE protocolo = ?", (protocolo,)
                ).fetchone()
                registro_id = linha["id"]

                # Recentes e em aberto: precisam aparecer na fila da Central.
                criado = datetime.now() - timedelta(
                    hours=sorteio.randint(0, 5), minutes=sorteio.randint(0, 59)
                )
                conexao.execute(
                    "UPDATE ocorrencias SET criado_em = ?, atualizado_em = ? "
                    "WHERE id = ?",
                    (criado.isoformat(timespec="seconds"),
                     criado.isoformat(timespec="seconds"), registro_id),
                )

            contagem[categoria] = contagem.get(categoria, 0) + 1

    print("Alertas de cobertura gerados por categoria:")
    for categoria, quantidade in contagem.items():
        print(f"  {categoria}: {quantidade}")
    print(f"Total: {sum(contagem.values())} alertas em {CAMINHO_BANCO}")


if __name__ == "__main__":
    argumentos = sys.argv[1:]
    if "--limpar" in argumentos:
        limpar_banco()
        argumentos = [a for a in argumentos if a != "--limpar"]
    if "--cobertura" in argumentos:
        gerar_cobertura()
    else:
        total = int(argumentos[0]) if argumentos else 25
        gerar(total)
