"""
ETAPA 1 — Ingestão do PDF.

Lê um ou mais PDFs, extrai o texto página a página, divide em chunks com
sobreposição, gera os embeddings e grava o índice FAISS em disco para uso
pelo chatbot (Etapa 2).

Uso:
    python ingestao.py --pdf documentos/manual.pdf
    python ingestao.py --dir documentos --reset
    python ingestao.py --pdf a.pdf --pdf b.pdf --chunk-size 1200 --overlap 200
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import sys
from pathlib import Path

import numpy as np
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from core import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_MODEL,
    INDEX_DIR,
    Chunk,
    Manifesto,
    carregar_indice,
    configurar_log,
    criar_indice,
    dividir_em_chunks,
    embutir_passagens,
    indice_existe,
    salvar_indice,
)

logger = logging.getLogger("ingestao")


# --------------------------------------------------------------------------- #
# Leitura do PDF
# --------------------------------------------------------------------------- #


def hash_arquivo(caminho: Path, blocos: int = 1 << 20) -> str:
    """SHA-256 do arquivo, usado para evitar reprocessar o mesmo documento."""
    digest = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(blocos), b""):
            digest.update(bloco)
    return digest.hexdigest()


def extrair_paginas(caminho: Path) -> list[tuple[int, str]]:
    """Retorna [(numero_pagina, texto)] apenas das páginas com texto extraível."""
    try:
        leitor = PdfReader(str(caminho))
    except (PdfReadError, OSError) as exc:
        raise RuntimeError(f"Não foi possível abrir '{caminho.name}': {exc}") from exc

    if getattr(leitor, "is_encrypted", False):
        try:
            leitor.decrypt("")  # PDFs protegidos apenas contra edição
        except Exception as exc:  # noqa: BLE001 - qualquer falha aqui é fatal para o arquivo
            raise RuntimeError(f"'{caminho.name}' está protegido por senha: {exc}") from exc

    paginas: list[tuple[int, str]] = []
    for numero, pagina in enumerate(leitor.pages, start=1):
        try:
            texto = pagina.extract_text() or ""
        except Exception as exc:  # noqa: BLE001 - página corrompida não deve abortar o lote
            logger.warning("Falha ao extrair a página %d de %s: %s", numero, caminho.name, exc)
            continue
        if texto.strip():
            paginas.append((numero, texto))

    if not paginas:
        raise RuntimeError(
            f"Nenhum texto extraível em '{caminho.name}'. "
            "O arquivo provavelmente é digitalizado — aplique OCR antes (ex.: ocrmypdf)."
        )

    logger.info("%s: %d de %d páginas com texto.", caminho.name, len(paginas), len(leitor.pages))
    return paginas


def gerar_chunks(caminho: Path, id_inicial: int, chunk_size: int, overlap: int) -> list[Chunk]:
    """Converte o PDF em chunks numerados sequencialmente a partir de `id_inicial`."""
    chunks: list[Chunk] = []
    proximo_id = id_inicial
    for numero_pagina, texto in extrair_paginas(caminho):
        for trecho in dividir_em_chunks(texto, chunk_size=chunk_size, overlap=overlap):
            chunks.append(
                Chunk(id=proximo_id, texto=trecho, arquivo=caminho.name, pagina=numero_pagina)
            )
            proximo_id += 1
    logger.info("%s: %d chunks gerados.", caminho.name, len(chunks))
    return chunks


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #


def resolver_entradas(args: argparse.Namespace) -> list[Path]:
    caminhos: list[Path] = [Path(p).expanduser().resolve() for p in args.pdf]

    if args.dir:
        diretorio = Path(args.dir).expanduser().resolve()
        if not diretorio.is_dir():
            raise SystemExit(f"Diretório inexistente: {diretorio}")
        caminhos.extend(sorted(diretorio.glob("*.pdf")))

    invalidos = [c for c in caminhos if not c.is_file()]
    if invalidos:
        raise SystemExit("Arquivo(s) não encontrado(s): " + ", ".join(str(c) for c in invalidos))

    # Remove duplicatas preservando a ordem.
    unicos = list(dict.fromkeys(caminhos))
    if not unicos:
        raise SystemExit("Informe ao menos um PDF com --pdf ou --dir.")
    return unicos


def executar(args: argparse.Namespace) -> int:
    caminhos = resolver_entradas(args)

    chunks: list[Chunk] = []
    manifesto = Manifesto(
        modelo_embedding=args.modelo_embedding,
        chunk_size=args.chunk_size,
        chunk_overlap=args.overlap,
    )
    indice_anterior = None

    incremental = indice_existe() and not args.reset
    if incremental:
        indice_anterior, chunks, manifesto_atual = carregar_indice()
        if manifesto_atual.modelo_embedding != args.modelo_embedding:
            raise SystemExit(
                f"O índice existente usa '{manifesto_atual.modelo_embedding}' e você pediu "
                f"'{args.modelo_embedding}'. Rode novamente com --reset."
            )
        manifesto = manifesto_atual
        chunks = list(chunks)
        logger.info("Modo incremental: %d chunks já indexados.", len(chunks))
    elif args.reset and indice_existe():
        logger.info("--reset: o índice em %s será substituído.", INDEX_DIR)

    ja_indexados = {doc["sha256"]: doc["arquivo"] for doc in manifesto.documentos}
    novos_chunks: list[Chunk] = []

    for caminho in caminhos:
        sha = hash_arquivo(caminho)
        if sha in ja_indexados:
            logger.info("Ignorando '%s': conteúdo idêntico a '%s' já indexado.", caminho.name, ja_indexados[sha])
            continue

        chunks_documento = gerar_chunks(
            caminho,
            id_inicial=len(chunks) + len(novos_chunks),
            chunk_size=args.chunk_size,
            overlap=args.overlap,
        )
        if not chunks_documento:
            logger.warning("Nenhum chunk gerado para '%s'.", caminho.name)
            continue

        novos_chunks.extend(chunks_documento)
        manifesto.documentos.append(
            {
                "arquivo": caminho.name,
                "caminho": str(caminho),
                "sha256": sha,
                "chunks": len(chunks_documento),
            }
        )
        ja_indexados[sha] = caminho.name

    if not novos_chunks:
        logger.info("Nada novo para indexar. Índice mantido como está.")
        return 0

    logger.info("Gerando embeddings de %d chunks com '%s'...", len(novos_chunks), args.modelo_embedding)
    vetores = embutir_passagens(
        [c.texto for c in novos_chunks],
        nome_modelo=args.modelo_embedding,
        mostrar_progresso=True,
    )

    if incremental and indice_anterior is not None:
        if indice_anterior.d != vetores.shape[1]:
            raise SystemExit("Dimensão dos embeddings diferente do índice existente. Use --reset.")
        indice_anterior.add(vetores)
        indice = indice_anterior
    else:
        indice = criar_indice(np.asarray(vetores, dtype="float32"))

    chunks.extend(novos_chunks)
    manifesto.modelo_embedding = args.modelo_embedding
    manifesto.chunk_size = args.chunk_size
    manifesto.chunk_overlap = args.overlap

    salvar_indice(indice, chunks, manifesto)

    logger.info(
        "Concluído: %d documento(s) no índice, %d chunks, dimensão %d.",
        len(manifesto.documentos),
        len(chunks),
        indice.d,
    )
    logger.info("Próximo passo: streamlit run app.py")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Etapa 1 — lê PDFs e constrói o índice vetorial usado pelo RAG.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--pdf", action="append", default=[], metavar="ARQUIVO", help="PDF a indexar (pode repetir).")
    parser.add_argument("--dir", metavar="PASTA", help="Indexa todos os PDFs da pasta.")
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE, help="Tamanho do chunk em caracteres.")
    parser.add_argument("--overlap", type=int, default=CHUNK_OVERLAP, help="Sobreposição entre chunks.")
    parser.add_argument("--modelo-embedding", default=EMBEDDING_MODEL, help="Modelo sentence-transformers.")
    parser.add_argument("--reset", action="store_true", help="Recria o índice do zero.")
    parser.add_argument("--verbose", action="store_true", help="Log em nível DEBUG.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configurar_log(logging.DEBUG if args.verbose else logging.INFO)

    if args.overlap >= args.chunk_size:
        raise SystemExit("--overlap precisa ser menor que --chunk-size.")

    try:
        return executar(args)
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1
    except KeyboardInterrupt:
        logger.warning("Interrompido pelo usuário.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
