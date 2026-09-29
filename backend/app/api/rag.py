"""知识库面板接口。上传文档、列表、检索、删除。"""

from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile

from app.rag import ingest
from app.rag.retrieve import retrieve

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.get("/documents")
async def list_documents() -> dict:
    return {"documents": await ingest.list_documents()}


@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    collection: str = Form(...),
) -> dict:
    content = (await file.read()).decode("utf-8", errors="ignore")
    count = await ingest.ingest_document(file.filename or "未命名", collection, content)
    return {"name": file.filename, "collection": collection, "chunks": count}


@router.delete("/documents/{collection}/{name}")
async def delete_document(collection: str, name: str) -> dict:
    ok = await ingest.delete_document(name, collection)
    return {"ok": ok}


@router.post("/search")
async def search(payload: dict) -> dict:
    chunks = await retrieve(
        payload.get("query", ""),
        payload.get("collection", "schema"),
        int(payload.get("top_k", 5)),
    )
    return {"chunks": chunks}
