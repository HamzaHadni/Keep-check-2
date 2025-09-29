import os, glob, requests
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pypdf import PdfReader
import faiss
import numpy as np
from typing import List
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

INDEX_DIR = "/tmp/index"
DOCS_DIR  = "/tmp/docs"
PAPERLESS_URL = os.getenv("PAPERLESS_URL", "http://paperless:8000")
PAPERLESS_TOKEN = os.getenv("PAPERLESS_TOKEN", "")

app = FastAPI(title="KEEPCHECK API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def embed(texts: List[str]) -> np.ndarray:
    if not client:
        return np.zeros((len(texts), 1536), dtype="float32")
    resp = client.embeddings.create(model="text-embedding-3-small", input=texts)
    vecs = [np.array(d.embedding, dtype="float32") for d in resp.data]
    return np.vstack(vecs) if vecs else np.zeros((0,1536), dtype="float32")

def split_text(txt: str, chunk_size=800, overlap=80) -> List[str]:
    out, i = [], 0
    while i < len(txt):
        chunk = txt[i:i+chunk_size]
        if chunk.strip(): out.append(chunk)
        i += (chunk_size - overlap)
    return out

def build_index():
    chunks = []
    for pdf in glob.glob(os.path.join(DOCS_DIR, "*.pdf")):
        try:
            text = "".join((p.extract_text() or "") for p in PdfReader(pdf).pages)
            chunks += split_text(text)
        except Exception:
            continue
    if not chunks:
        return faiss.IndexFlatIP(1536), []
    X = embed(chunks).astype("float32")
    if X.size == 0:
        return faiss.IndexFlatIP(1536), []
    faiss.normalize_L2(X)
    index = faiss.IndexFlatIP(X.shape[1])
    index.add(X)
    return index, chunks

INDEX, CHUNKS = build_index()

@app.get("/health")
def health():
    return {"ok": True, "chunks": len(CHUNKS)}

@app.get("/ask")
def ask(q: str = Query(...)):
    if not q.strip():
        return JSONResponse({"error":"Question vide"}, 400)
    if not client:
        return JSONResponse({"error":"OPENAI_API_KEY manquante"}, 500)
    if len(CHUNKS) == 0:
        r = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content": q}])
        return {"answer": r.choices[0].message.content, "mode": "no-index"}
    qv = embed([q]).astype("float32")
    faiss.normalize_L2(qv)
    sims, ids = INDEX.search(qv, k=5)
    ctx = "\n\n---\n\n".join(CHUNKS[i] for i in ids[0] if i < len(CHUNKS))
    prompt = f"Réponds en t'appuyant STRICTEMENT sur ce contexte.\n\nContexte:\n{ctx}\n\nQuestion: {q}"
    r = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content": prompt}])
    return {"answer": r.choices[0].message.content, "mode": "rag"}

@app.get("/extract")
def extract(doc_id: int = Query(...), doc_type: str = Query(...)):
    if not client:
        return JSONResponse({"error":"OPENAI_API_KEY manquante"}, 500)
    if not PAPERLESS_TOKEN:
        return JSONResponse({"error":"PAPERLESS_TOKEN requis"}, 500)
    url = f"{PAPERLESS_URL}/api/documents/{doc_id}/download/"
    h  = {"Authorization": f"Token {PAPERLESS_TOKEN}"}
    r = requests.get(url, headers=h)
    if r.status_code != 200:
        return JSONResponse({"error":"Document introuvable"}, 404)
    tmp = f"/tmp/doc_{doc_id}.pdf"
    with open(tmp,"wb") as f: f.write(r.content)
    text = "".join((p.extract_text() or "") for p in PdfReader(tmp).pages)
    fields_map = {
        "facture": "fournisseur, ICE, date, numero facture, HT, TVA, TTC, echeance, mode de paiement, coordonnees bancaires",
        "contrat": "parties, objet, date signature, date fin, renouvellement automatique, penalites",
        "cnss":    "numero affiliation, periode, montant du, date limite"
    }
    fields = fields_map.get(doc_type.lower())
    if not fields:
        return JSONResponse({"error":"Type inconnu"}, 400)
    prompt = f"Extrait ces champs ({fields}) du texte suivant et rends un JSON strict.\n\nTexte:\n{text}"
    out = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content": prompt}],
        response_format={"type":"json_object"}
    )
    return JSONResponse(out.choices[0].message.content)
