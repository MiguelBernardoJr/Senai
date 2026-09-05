"""
Núcleo compartilhado entre a Etapa 1 (ingestão do PDF) e a Etapa 2 (chatbot).

Concentra: configuração via .env, limpeza e chunking de texto, geração de
embeddings locais (sentence-transformers) e persistência/consulta do índice
FAISS. Nenhum dos dois scripts duplica essa lógica.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Sequence

import faiss
import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Configuração
# --------------------------------------------------------------------------- #

BASE_DIR = Path(__file__).resolve().parent

INDEX_DIR = Path(os.getenv("INDEX_DIR", str(BASE_DIR / "indice"))).expanduser()
INDEX_PATH = INDEX_DIR / "faiss.index"
CHUNKS_PATH = INDEX_DIR / "chunks.jsonl"
MANIFEST_PATH = INDEX_DIR / "manifest.json"

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "32"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_TEMPERATURE = float(os.getenv("GROQ_TEMPERATURE", "0.2"))
GROQ_MAX_COMPLETION_TOKENS = int(os.getenv("GROQ_MAX_COMPLETION_TOKENS", "2048"))
GROQ_REASONING_EFFORT = os.getenv("GROQ_REASONING_EFFORT", "low")

TOP_K = int(os.getenv("TOP_K", "5"))
MIN_SCORE = float(os.getenv("MIN_SCORE", "0.70"))

# Modelos de reasoning da Groq que aceitam reasoning_effort/reasoning_format.
MODELOS_REASONING = ("openai/gpt-oss-20b", "openai/gpt-oss-120b")


def configurar_log(nivel: int = logging.INFO) -> None:
    logging.basicConfig(
        level=nivel,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


# --------------------------------------------------------------------------- #
# Modelo de dados
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Chunk:
    """Trecho indexado do documento."""

    id: int
    texto: str
    arquivo: str
    pagina: int

    @property
    def referencia(self) -> str:
        return f"{self.arquivo} — página {self.pagina}"


@dataclass(frozen=True)
class Resultado:
    """Chunk recuperado com o respectivo score de similaridade (cosseno)."""

    chunk: Chunk
    score: float


@dataclass
class Manifesto:
    """Metadados do índice, gravados junto com os vetores."""

    modelo_embedding: str = EMBEDDING_MODEL
    dimensao: int = 0
    chunk_size: int = CHUNK_SIZE
    chunk_overlap: int = CHUNK_OVERLAP
    total_chunks: int = 0
    atualizado_em: str = ""
    documentos: list[dict] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Limpeza e chunking
# --------------------------------------------------------------------------- #

_HIFEN_QUEBRA_RE = re.compile(r"(\w)-\n(\w)")
_QUEBRA_SIMPLES_RE = re.compile(r"(?<!\n)\n(?!\n)")
_ESPACOS_RE = re.compile(r"[ \t\x0b\f\r]+")
_LINHAS_VAZIAS_RE = re.compile(r"\n{3,}")
_SEPARADOR_RE = re.compile(r"(?<=[.!?;])\s+|\n{2,}")


def normalizar_texto(texto: str) -> str:
    """Remove hifenização de fim de linha, quebras artificiais e espaços duplicados."""
    if not texto:
        return ""
    texto = texto.replace("\x00", " ").replace("\ufeff", "")
    texto = _HIFEN_QUEBRA_RE.sub(r"\1\2", texto)
    texto = _QUEBRA_SIMPLES_RE.sub(" ", texto)
    texto = _ESPACOS_RE.sub(" ", texto)
    texto = _LINHAS_VAZIAS_RE.sub("\n\n", texto)
    return texto.strip()


def _cauda(texto: str, tamanho: int) -> str:
    """Últimos `tamanho` caracteres respeitando a fronteira de palavra."""
    if tamanho <= 0 or len(texto) <= tamanho:
        return texto
    recorte = texto[-tamanho:]
    espaco = recorte.find(" ")
    return recorte[espaco + 1 :] if espaco != -1 else recorte


def dividir_em_chunks(
    texto: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Divide o texto em janelas com sobreposição, cortando em fim de frase."""
    texto = normalizar_texto(texto)
    if not texto:
        return []
    if overlap >= chunk_size:
        raise ValueError("CHUNK_OVERLAP deve ser menor que CHUNK_SIZE.")

    partes = [p.strip() for p in _SEPARADOR_RE.split(texto) if p and p.strip()]
    chunks: list[str] = []
    atual = ""

    for parte in partes:
        # Frase maior que a janela (tabelas, listas coladas, OCR ruim).
        while len(parte) > chunk_size:
            if atual:
                chunks.append(atual)
                atual = ""
            chunks.append(parte[:chunk_size].strip())
            parte = parte[chunk_size - overlap :]

        if not atual:
            atual = parte
        elif len(atual) + len(parte) + 1 <= chunk_size:
            atual = f"{atual} {parte}"
        else:
            chunks.append(atual)
            prefixo = _cauda(atual, overlap)
            atual = f"{prefixo} {parte}".strip() if len(prefixo) + len(parte) + 1 <= chunk_size else parte

    if atual:
        chunks.append(atual)

    return [c.strip() for c in chunks if c.strip()]


# --------------------------------------------------------------------------- #
# Embeddings
# --------------------------------------------------------------------------- #


@lru_cache(maxsize=2)
def carregar_embedder(nome_modelo: str = EMBEDDING_MODEL) -> SentenceTransformer:
    """Carrega o modelo de embedding (baixado na primeira execução e cacheado)."""
    logger.info("Carregando modelo de embedding: %s", nome_modelo)
    return SentenceTransformer(nome_modelo)


def _usa_prefixo_e5(nome_modelo: str) -> bool:
    """Modelos da família E5 exigem os prefixos 'query:' e 'passage:'."""
    return "e5" in nome_modelo.lower()


def embutir_passagens(
    textos: Sequence[str],
    nome_modelo: str = EMBEDDING_MODEL,
    batch_size: int = EMBED_BATCH_SIZE,
    mostrar_progresso: bool = False,
) -> np.ndarray:
    """Gera embeddings normalizados (float32) para os trechos do documento."""
    modelo = carregar_embedder(nome_modelo)
    entradas = [f"passage: {t}" for t in textos] if _usa_prefixo_e5(nome_modelo) else list(textos)
    vetores = modelo.encode(
        entradas,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=mostrar_progresso,
    )
    return np.asarray(vetores, dtype="float32")


def embutir_consulta(texto: str, nome_modelo: str = EMBEDDING_MODEL) -> np.ndarray:
    """Gera o embedding normalizado da pergunta (shape 1 x d)."""
    modelo = carregar_embedder(nome_modelo)
    entrada = f"query: {texto}" if _usa_prefixo_e5(nome_modelo) else texto
    vetor = modelo.encode(
        [entrada],
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.asarray(vetor, dtype="float32")


# --------------------------------------------------------------------------- #
# Índice FAISS
# --------------------------------------------------------------------------- #


def indice_existe() -> bool:
    return INDEX_PATH.exists() and CHUNKS_PATH.exists() and MANIFEST_PATH.exists()


def criar_indice(vetores: np.ndarray) -> faiss.Index:
    """Índice de produto interno; com vetores normalizados equivale ao cosseno."""
    if vetores.ndim != 2 or vetores.size == 0:
        raise ValueError("Matriz de vetores vazia ou com formato inválido.")
    indice = faiss.IndexFlatIP(vetores.shape[1])
    indice.add(vetores)
    return indice


def salvar_indice(indice: faiss.Index, chunks: Sequence[Chunk], manifesto: Manifesto) -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(indice, str(INDEX_PATH))

    with CHUNKS_PATH.open("w", encoding="utf-8") as arquivo:
        for chunk in chunks:
            arquivo.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")

    manifesto.total_chunks = len(chunks)
    manifesto.dimensao = indice.d
    manifesto.atualizado_em = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    MANIFEST_PATH.write_text(
        json.dumps(asdict(manifesto), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Índice salvo em %s (%d chunks).", INDEX_DIR, len(chunks))


def carregar_indice() -> tuple[faiss.Index, list[Chunk], Manifesto]:
    """Carrega índice, chunks e manifesto do disco."""
    if not indice_existe():
        raise FileNotFoundError(
            f"Índice não encontrado em '{INDEX_DIR}'. Rode a Etapa 1: python ingestao.py --pdf <arquivo.pdf>"
        )

    indice = faiss.read_index(str(INDEX_PATH))

    chunks: list[Chunk] = []
    with CHUNKS_PATH.open("r", encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if linha:
                chunks.append(Chunk(**json.loads(linha)))

    manifesto = Manifesto(**json.loads(MANIFEST_PATH.read_text(encoding="utf-8")))

    if indice.ntotal != len(chunks):
        raise RuntimeError(
            f"Índice inconsistente: {indice.ntotal} vetores para {len(chunks)} chunks. "
            "Reprocesse com: python ingestao.py --pdf <arquivo.pdf> --reset"
        )

    return indice, chunks, manifesto


def buscar(
    pergunta: str,
    indice: faiss.Index,
    chunks: Sequence[Chunk],
    k: int = TOP_K,
    min_score: float = MIN_SCORE,
    nome_modelo: str = EMBEDDING_MODEL,
) -> list[Resultado]:
    """Recupera os k trechos mais próximos da pergunta, filtrando por score mínimo."""
    if not pergunta.strip() or indice.ntotal == 0:
        return []

    vetor = embutir_consulta(pergunta, nome_modelo)
    scores, ids = indice.search(vetor, min(k, indice.ntotal))

    resultados: list[Resultado] = []
    for score, idx in zip(scores[0], ids[0]):
        if idx < 0 or float(score) < min_score:
            continue
        resultados.append(Resultado(chunk=chunks[int(idx)], score=float(score)))
    return resultados


def montar_contexto(resultados: Sequence[Resultado], limite_caracteres: int = 12_000) -> str:
    """Formata os trechos recuperados como fontes numeradas para o prompt."""
    blocos: list[str] = []
    total = 0
    for posicao, resultado in enumerate(resultados, start=1):
        bloco = f"[Fonte {posicao}] {resultado.chunk.referencia}\n{resultado.chunk.texto}"
        if total + len(bloco) > limite_caracteres:
            break
        blocos.append(bloco)
        total += len(bloco)
    return "\n\n---\n\n".join(blocos)
