from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from typing import List
from uuid import UUID
import asyncpg

from app.schemas import TravelPlanCreate, TravelPlanUpdate, TravelPlanResponse, LocationResponse
from app.database import get_db_connection

router = APIRouter(
    prefix="/api/travel-plans",
    tags=["Travel Plans"]
)

@router.post("", response_model=TravelPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_travel_plan(plan: TravelPlanCreate, conn: asyncpg.Connection = Depends(get_db_connection)):
    query = """
        INSERT INTO travel_plans (title, description, start_date, end_date, budget, currency, is_public)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING *;
    """
    row = await conn.fetchrow(
        query, 
        plan.title, plan.description, plan.start_date, plan.end_date, plan.budget, plan.currency, plan.is_public
    )
    return TravelPlanResponse.model_validate(dict(row))

@router.get("", response_model=List[TravelPlanResponse])
async def get_travel_plans(limit: int = 10, offset: int = 0, conn: asyncpg.Connection = Depends(get_db_connection)):
    query = "SELECT * FROM travel_plans ORDER BY created_at DESC LIMIT $1 OFFSET $2;"
    rows = await conn.fetch(query, limit, offset)
    return [TravelPlanResponse.model_validate(dict(row)) for row in rows]

@router.get("/{plan_id}")
async def get_travel_plan(plan_id: UUID, conn: asyncpg.Connection = Depends(get_db_connection)):
    plan_query = "SELECT * FROM travel_plans WHERE id = $1;"
    plan_row = await conn.fetchrow(plan_query, plan_id)
    
    if not plan_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Travel plan not found")
    
    loc_query = "SELECT * FROM locations WHERE travel_plan_id = $1 ORDER BY visit_order ASC;"
    loc_rows = await conn.fetch(loc_query, plan_id)
    
    result = TravelPlanResponse.model_validate(dict(plan_row)).model_dump()
    result["locations"] = [LocationResponse.model_validate(dict(loc)).model_dump() for loc in loc_rows]
    return result

@router.put("/{plan_id}", response_model=TravelPlanResponse)
async def update_travel_plan(plan_id: UUID, plan: TravelPlanUpdate, conn: asyncpg.Connection = Depends(get_db_connection)):
    check_query = "SELECT id FROM travel_plans WHERE id = $1;"
    if not await conn.fetchval(check_query, plan_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Travel plan not found")

    update_query = """
        UPDATE travel_plans
        SET title = $1, description = $2, start_date = $3, end_date = $4, 
            budget = $5, currency = $6, is_public = $7, version = version + 1
        WHERE id = $8 AND version = $9
        RETURNING *;
    """
    updated_row = await conn.fetchrow(
        update_query,
        plan.title, plan.description, plan.start_date, plan.end_date, 
        plan.budget, plan.currency, plan.is_public, plan_id, plan.version
    )
    
    if not updated_row:
        current_version = await conn.fetchval("SELECT version FROM travel_plans WHERE id = $1;", plan_id)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "Conflict: The travel plan has been modified",
                "current_version": current_version
            }
        )
        
    return TravelPlanResponse.model_validate(dict(updated_row))

@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_travel_plan(plan_id: UUID, conn: asyncpg.Connection = Depends(get_db_connection)):
    delete_query = "DELETE FROM travel_plans WHERE id = $1 RETURNING id;"
    deleted_id = await conn.fetchval(delete_query, plan_id)
    
    if not deleted_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Travel plan not found")
    
    return None