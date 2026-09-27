"""知识库面板接口。第 1 步为桩实现，第 11 步替换为真实现。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.get("/documents")
async def list_documents() -> dict:
    return {"documents": []}


@router.post("/documents")
async def upload_document() -> dict:
    return {"doc_id": "d_demo", "chunks": 0}


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str) -> dict:
    return {"ok": True}


@router.post("/search")
async def search(payload: dict) -> dict:
    return {"chunks": []}


@router.post("/collections/{collection}/rebuild")
async def rebuild_collection(collection: str) -> dict:
    return {"ok": True}
