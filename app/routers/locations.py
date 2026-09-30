from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.responses import JSONResponse
from uuid import UUID
import asyncpg
from typing import List, Optional

from app.schemas import LocationCreate, LocationUpdate, LocationResponse
from app.database import get_db_connection

router = APIRouter(
    tags=["Locations"]
)


@router.post("/api/travel-plans/{plan_id}/locations", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def add_location(
    plan_id: UUID, 
    location: LocationCreate, 
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    async with conn.transaction():
        # блокуємо батьківський план та підвищуємо його версію
        plan = await conn.fetchrow(
            "UPDATE travel_plans SET version = version + 1 WHERE id = $1 RETURNING id;", 
            plan_id
        )
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Travel plan not found"
            )
        
        # вираховуємо наступний порядковий номер у тій самій транзакції
        next_order = await conn.fetchval(
            "SELECT COALESCE(MAX(visit_order), 0) + 1 FROM locations WHERE travel_plan_id = $1;", 
            plan_id
        )
        
        insert_query = """
            INSERT INTO locations (travel_plan_id, name, address, latitude, longitude, arrival_date, departure_date, budget, notes, visit_order)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING *;
        """
        row = await conn.fetchrow(
            insert_query,
            plan_id, location.name, location.address, location.latitude, location.longitude,
            location.arrival_date, location.departure_date, location.budget, location.notes, next_order
        )
        return LocationResponse.model_validate(dict(row))


@router.put("/api/locations/{location_id}", response_model=LocationResponse)
@router.put("/locations/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: UUID, 
    location: LocationUpdate, 
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    if location.arrival_date and location.departure_date:
        if location.departure_date < location.arrival_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="departure_date cannot be earlier than arrival_date"
            )

    if location.budget is not None and location.budget < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="budget cannot be negative"
        )

    try:
        async with conn.transaction():
            # блокуємо рядок локації для читання
            loc = await conn.fetchrow(
                "SELECT id, travel_plan_id FROM locations WHERE id = $1 FOR UPDATE;", 
                location_id
            )
            if not loc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail="Location not found"
                )

            plan_id = loc["travel_plan_id"]

            # якщо передано plan_version — перевіряємо оптимістичне блокування батьківського плану
            if location.plan_version is not None:
                update_plan = await conn.fetchrow(
                    """
                    UPDATE travel_plans 
                    SET version = version + 1 
                    WHERE id = $1 AND version = $2 
                    RETURNING version;
                    """,
                    plan_id, location.plan_version
                )

                if not update_plan:
                    current_plan_version = await conn.fetchval(
                        "SELECT version FROM travel_plans WHERE id = $1;", 
                        plan_id
                    )
                    if current_plan_version is None:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND, 
                            detail="Parent travel plan not found"
                        )
                    return JSONResponse(
                        status_code=status.HTTP_409_CONFLICT,
                        content={
                            "error": "Conflict: Parent travel plan has been modified",
                            "current_version": current_plan_version
                        }
                    )
            else:
                await conn.execute(
                    "UPDATE travel_plans SET version = version + 1 WHERE id = $1;", 
                    plan_id
                )

            # оновлюємо дані локації
            update_query = """
                UPDATE locations
                SET name = COALESCE($1, name),
                    address = COALESCE($2, address),
                    latitude = COALESCE($3, latitude),
                    longitude = COALESCE($4, longitude), 
                    arrival_date = COALESCE($5, arrival_date),
                    departure_date = COALESCE($6, departure_date),
                    budget = COALESCE($7, budget),
                    notes = COALESCE($8, notes),
                    visit_order = COALESCE($9, visit_order)
                WHERE id = $10
                RETURNING *;
            """
            row = await conn.fetchrow(
                update_query,
                location.name, location.address, location.latitude, location.longitude,
                location.arrival_date, location.departure_date, location.budget, location.notes, 
                location.visit_order, location_id
            )
            return LocationResponse.model_validate(dict(row))

    except HTTPException:
        raise
    except (asyncpg.CheckViolationError, asyncpg.DataError, asyncpg.IntegrityConstraintViolationError) as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": f"Validation error: {e}"}
        )


@router.delete("/api/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    location_id: UUID, 
    plan_version: Optional[int] = Query(None, description="Current parent plan version"),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    async with conn.transaction():
        # блокуємо рядок локації перед видаленням
        loc = await conn.fetchrow(
            "SELECT travel_plan_id FROM locations WHERE id = $1 FOR UPDATE;", 
            location_id
        )
        if not loc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Location not found"
            )

        plan_id = loc["travel_plan_id"]

        # якщо передано версію плану - валідуємо її перед видаленням
        if plan_version is not None:
            updated_plan = await conn.fetchrow(
                "UPDATE travel_plans SET version = version + 1 WHERE id = $1 AND version = $2 RETURNING id;",
                plan_id, plan_version
            )
            if not updated_plan:
                current_plan_version = await conn.fetchval(
                    "SELECT version FROM travel_plans WHERE id = $1;", 
                    plan_id
                )
                if current_plan_version is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Travel plan not found")
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={
                        "error": "Conflict: Parent travel plan has been modified",
                        "current_version": current_plan_version
                    }
                )
        else:
            await conn.execute("UPDATE travel_plans SET version = version + 1 WHERE id = $1;", plan_id)

        # видаляємо локацію
        await conn.execute("DELETE FROM locations WHERE id = $1;", location_id)
        return None