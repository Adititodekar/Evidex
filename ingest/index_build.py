"""
Multi-Vector, BM25 Indexing, and Isolated Named Collection Storage Engine.
Supports multiple named collections under data/<collection_name>/ with complete isolation.
"""

import os
import shutil
import json
import sqlite3
import pickle
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import faiss
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from app.config import settings

logger = logging.getLogger(__name__)

_embed_model = None

def get_embed_model():
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embed_model

def get_collection_dir(collection_name: str) -> str:
    return os.path.join(settings.DATA_DIR, collection_name)

def collection_exists(collection_name: str) -> bool:
    cdir = get_collection_dir(collection_name)
    db_path = os.path.join(cdir, "corpus.db")
    return os.path.exists(cdir) and os.path.exists(db_path)

def list_collections() -> List[str]:
    if not os.path.exists(settings.DATA_DIR):
        return []
    return [d for d in os.listdir(settings.DATA_DIR) if collection_exists(d)]

def delete_collection(collection_name: str):
    cdir = get_collection_dir(collection_name)
    if os.path.exists(cdir):
        shutil.rmtree(cdir)
        logger.info(f"Deleted collection '{collection_name}' at {cdir}")

def init_collection_db(collection_name: str) -> sqlite3.Connection:
    cdir = get_collection_dir(collection_name)
    os.makedirs(cdir, exist_ok=True)
    db_path = os.path.join(cdir, "corpus.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        doc_id TEXT PRIMARY KEY,
        total_pages INTEGER,
        card_json TEXT
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sections (
        section_id TEXT,
        doc_id TEXT,
        title TEXT,
        level INTEGER,
        start_page INTEGER,
        end_page INTEGER,
        summary TEXT,
        keywords TEXT,
        PRIMARY KEY (doc_id, section_id)
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chunks (
        chunk_id TEXT PRIMARY KEY,
        doc_id TEXT,
        page INTEGER,
        section TEXT,
        chunk_type TEXT,
        text TEXT,
        word_count INTEGER
    )
    """)
    conn.commit()
    return conn

def tokenize_for_bm25(text: str) -> List[str]:
    clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', text).lower()
    return [w for w in clean.split() if len(w) > 1]

class CollectionIndex:
    """
    In-memory / disk accessor for a specific named collection's vectors, BM25, and metadata.
    """
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.dir = get_collection_dir(collection_name)
        if not collection_exists(collection_name):
            raise ValueError(f"Collection '{collection_name}' does not exist.")
            
        self.db_path = os.path.join(self.dir, "corpus.db")
        self.faiss_path = os.path.join(self.dir, "vectors.faiss")
        self.ids_path = os.path.join(self.dir, "chunk_ids.json")
        self.bm25_path = os.path.join(self.dir, "bm25.pkl")
        
        # Load FAISS index if present
        self.index = None
        self.chunk_ids = []
        if os.path.exists(self.faiss_path) and os.path.exists(self.ids_path):
            self.index = faiss.read_index(self.faiss_path)
            with open(self.ids_path, "r", encoding="utf-8") as f:
                self.chunk_ids = json.load(f)

        # Load BM25 if present
        self.bm25 = None
        self.bm25_chunk_ids = []
        if os.path.exists(self.bm25_path):
            with open(self.bm25_path, "rb") as f:
                data = pickle.load(f)
                self.bm25 = data["bm25"]
                self.bm25_chunk_ids = data["chunk_ids"]

    def get_document_cards(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT card_json FROM documents")
        rows = cur.fetchall()
        conn.close()
        return [json.loads(r[0]) for r in rows]

    def get_sections_for_doc(self, doc_id: str) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT section_id, title, level, start_page, end_page, summary, keywords FROM sections WHERE doc_id = ?", (doc_id,))
        rows = cur.fetchall()
        conn.close()
        sections = []
        for r in rows:
            sections.append({
                "section_id": r[0],
                "title": r[1],
                "level": r[2],
                "start_page": r[3],
                "end_page": r[4],
                "summary": r[5],
                "keywords": json.loads(r[6]) if r[6] else []
            })
        return sections

    def get_chunks_for_section(self, doc_id: str, start_page: int, end_page: int) -> List[Dict[str, Any]]:
        """
        Retrieves all chunks within a page range (Failure Mode 2: leaf-section take-all).
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
        SELECT chunk_id, doc_id, page, section, chunk_type, text, word_count 
        FROM chunks 
        WHERE doc_id = ? AND page >= ? AND page <= ?
        ORDER BY page ASC, chunk_id ASC
        """, (doc_id, start_page, end_page))
        rows = cur.fetchall()
        conn.close()
        chunks = []
        for r in rows:
            chunks.append({
                "chunk_id": r[0],
                "document": r[1],
                "doc_id": r[1],
                "page": r[2],
                "section": r[3],
                "chunk_type": r[4],
                "text": r[5],
                "word_count": r[6]
            })
        return chunks

    def get_chunks_by_ids(self, chunk_ids: List[str]) -> List[Dict[str, Any]]:
        if not chunk_ids:
            return []
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        placeholders = ",".join("?" * len(chunk_ids))
        cur.execute(f"""
        SELECT chunk_id, doc_id, page, section, chunk_type, text, word_count 
        FROM chunks 
        WHERE chunk_id IN ({placeholders})
        """, chunk_ids)
        rows = cur.fetchall()
        conn.close()
        chunks = []
        for r in rows:
            chunks.append({
                "chunk_id": r[0],
                "document": r[1],
                "doc_id": r[1],
                "page": r[2],
                "section": r[3],
                "chunk_type": r[4],
                "text": r[5],
                "word_count": r[6]
            })
        return chunks

    def search_vectors(self, query: str, top_k: int = 50, filter_docs: Optional[List[str]] = None) -> List[Tuple[str, float]]:
        if self.index is None or not self.chunk_ids:
            return []
        model = get_embed_model()
        q_emb = model.encode([query])
        faiss.normalize_L2(q_emb)
        filter_set = set(filter_docs) if filter_docs else None
        search_k = min(len(self.chunk_ids), max(1500, top_k * 40)) if filter_set else min(top_k * 3, len(self.chunk_ids))
        scores, indices = self.index.search(q_emb.astype(np.float32), search_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.chunk_ids):
                continue
            cid = self.chunk_ids[idx]
            # Check filter
            if filter_set:
                doc_name = cid.split("_p")[0]
                if doc_name not in filter_set:
                    continue
            results.append((cid, float(score)))
            if len(results) >= top_k:
                break
        return results

    def search_bm25(self, query: str, top_k: int = 50, filter_docs: Optional[List[str]] = None) -> List[Tuple[str, float]]:
        if self.bm25 is None or not self.bm25_chunk_ids:
            return []
        toks = tokenize_for_bm25(query)
        scores = self.bm25.get_scores(toks)
        top_indices = np.argsort(scores)[::-1]
        
        results = []
        filter_set = set(filter_docs) if filter_docs else None
        for idx in top_indices:
            score = scores[idx]
            if score <= 0:
                break
            cid = self.bm25_chunk_ids[idx]
            if filter_set:
                doc_name = cid.split("_p")[0]
                if doc_name not in filter_set:
                    continue
            results.append((cid, float(score)))
            if len(results) >= top_k:
                break
        return results

def build_collection_index(
    collection_name: str,
    documents: List[Dict[str, Any]],
    sections_by_doc: Dict[str, List[Dict[str, Any]]],
    chunks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Builds the complete persistent database, FAISS index, and BM25 index for a collection.
    """
    conn = init_collection_db(collection_name)
    cur = conn.cursor()
    cdir = get_collection_dir(collection_name)

    # 1. Store documents
    for doc in documents:
        cur.execute(
            "INSERT OR REPLACE INTO documents (doc_id, total_pages, card_json) VALUES (?, ?, ?)",
            (doc["doc_id"], doc.get("total_pages", 0), json.dumps(doc))
        )

    # 2. Store sections
    for doc_id, secs in sections_by_doc.items():
        for s in secs:
            cur.execute("""
            INSERT OR REPLACE INTO sections 
            (section_id, doc_id, title, level, start_page, end_page, summary, keywords) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                s["section_id"],
                doc_id,
                s["title"],
                s["level"],
                s["start_page"],
                s["end_page"],
                s.get("summary", ""),
                json.dumps(s.get("keywords", []))
            ))

    # 3. Store chunks
    for c in chunks:
        cur.execute("""
        INSERT OR REPLACE INTO chunks 
        (chunk_id, doc_id, page, section, chunk_type, text, word_count) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            c["chunk_id"],
            c["doc_id"],
            c["page"],
            c.get("section", ""),
            c.get("chunk_type", "text"),
            c["text"],
            c.get("word_count", 0)
        ))

    conn.commit()
    conn.close()

    # 4. Build Vectors
    if chunks:
        model = get_embed_model()
        chunk_texts = [c["text"] for c in chunks]
        chunk_ids = [c["chunk_id"] for c in chunks]
        embeddings = model.encode(chunk_texts, batch_size=64, show_progress_bar=False)
        faiss.normalize_L2(embeddings)
        
        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings.astype(np.float32))
        
        faiss.write_index(index, os.path.join(cdir, "vectors.faiss"))
        with open(os.path.join(cdir, "chunk_ids.json"), "w", encoding="utf-8") as f:
            json.dump(chunk_ids, f)

        # 5. Build BM25
        tokenized_corpus = [tokenize_for_bm25(txt) for txt in chunk_texts]
        bm25 = BM25Okapi(tokenized_corpus)
        with open(os.path.join(cdir, "bm25.pkl"), "wb") as f:
            pickle.dump({"bm25": bm25, "chunk_ids": chunk_ids}, f)

    return {
        "status": "success",
        "collection_name": collection_name,
        "documents": len(documents),
        "chunks": len(chunks)
    }
