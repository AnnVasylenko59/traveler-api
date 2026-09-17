from fastapi import APIRouter, HTTPException, Depends, status
from uuid import UUID
import asyncpg

from app.schemas import LocationCreate, LocationUpdate, LocationResponse
from app.database import get_db_connection

router = APIRouter(
    tags=["Locations"]
)

# 1. Додавання локації (POST) - ВИРІШЕННЯ ПРОБЛЕМИ 2
@router.post("/api/travel-plans/{plan_id}/locations", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def add_location(plan_id: UUID, location: LocationCreate, conn: asyncpg.Connection = Depends(get_db_connection)):
    # Використовуємо транзакцію! Вона гарантує, що операції виконаються як одне ціле.
    async with conn.transaction():
        # Блокуємо план подорожі (на рівні рядка БД) та підвищуємо його версію (Parent-level versioning).
        # Якщо два користувачі додають локацію одночасно, другий чекатиме, поки перший завершить.
        plan = await conn.fetchrow(
            "UPDATE travel_plans SET version = version + 1 WHERE id = $1 RETURNING id;", 
            plan_id
        )
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Travel plan not found")
        
        # Тепер ми можемо безпечно вирахувати наступний visit_order (MAX + 1)
        next_order = await conn.fetchval(
            "SELECT COALESCE(MAX(visit_order), 0) + 1 FROM locations WHERE travel_plan_id = $1;", 
            plan_id
        )
        
        # Зберігаємо нову локацію
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
        return LocationResponse(**dict(row))

# 2. Оновлення локації (PUT) - ВИРІШЕННЯ ПРОБЛЕМИ 3 (через Parent-level versioning)
@router.put("/api/locations/{location_id}", response_model=LocationResponse)
async def update_location(location_id: UUID, location: LocationUpdate, conn: asyncpg.Connection = Depends(get_db_connection)):
    async with conn.transaction():
        # Знаходимо id плану для цієї локації
        plan_id = await conn.fetchval("SELECT travel_plan_id FROM locations WHERE id = $1;", location_id)
        if not plan_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
        
        # Підвищуємо версію всього плану. Якщо інший користувач одночасно оновлює іншу локацію, 
        # версія плану зміниться, і клієнти отримають сигнал, що загальний стейт плану оновився.
        await conn.execute("UPDATE travel_plans SET version = version + 1 WHERE id = $1;", plan_id)
        
        update_query = """
            UPDATE locations
            SET name = $1, address = $2, latitude = $3, longitude = $4, 
                arrival_date = $5, departure_date = $6, budget = $7, notes = $8, visit_order = COALESCE($9, visit_order)
            WHERE id = $10
            RETURNING *;
        """
        row = await conn.fetchrow(
            update_query,
            location.name, location.address, location.latitude, location.longitude,
            location.arrival_date, location.departure_date, location.budget, location.notes, 
            location.visit_order, location_id
        )
        return LocationResponse(**dict(row))

# 3. Видалення локації (DELETE)
@router.delete("/api/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(location_id: UUID, conn: asyncpg.Connection = Depends(get_db_connection)):
    async with conn.transaction():
        plan_id = await conn.fetchval("SELECT travel_plan_id FROM locations WHERE id = $1;", location_id)
        if not plan_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
            
        await conn.execute("UPDATE travel_plans SET version = version + 1 WHERE id = $1;", plan_id)
        await conn.execute("DELETE FROM locations WHERE id = $1;", location_id)
        
        return None