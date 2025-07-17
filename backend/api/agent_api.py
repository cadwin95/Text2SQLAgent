"""Agent API endpoints"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from ..database.connection_manager import ConnectionManager, get_connection_manager
from ..agent import nl2sql

router = APIRouter(prefix="/api/agent", tags=["agent"])


class AgentQueryRequest(BaseModel):
    question: str = Field(..., description="Natural language question")
    connection_id: Optional[str] = Field(None, description="Connection ID")
    params: Optional[Dict[str, Any]] = None


class AgentQueryResponse(BaseModel):
    success: bool
    sql_query: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


async def get_db_manager() -> ConnectionManager:
    return get_connection_manager()


@router.post("/query", response_model=AgentQueryResponse)
async def query_via_agent(
    request: AgentQueryRequest,
    manager: ConnectionManager = Depends(get_db_manager),
):
    """Convert question to SQL and execute it."""
    try:
        sql = await nl2sql(request.question)
        query_result = await manager.execute_query(sql, request.connection_id, request.params)
        if query_result.success:
            return AgentQueryResponse(success=True, sql_query=sql, result=query_result.model_dump())
        return AgentQueryResponse(success=False, sql_query=sql, error=query_result.error)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
