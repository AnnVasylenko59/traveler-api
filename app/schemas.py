from pydantic import BaseModel, Field, model_validator, field_validator
from typing import Optional
from datetime import date, datetime
from uuid import UUID
from decimal import Decimal


# ==========================================
# Схеми для Travel Plans
# ==========================================

class TravelPlanBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    currency: str = Field(
        'USD',
        min_length=3,
        max_length=3,
        pattern=r'^[A-Z]{3}$'
    )
    is_public: bool = False

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Title cannot be empty or whitespace')
        return v

    @model_validator(mode='after')
    def check_dates(self) -> 'TravelPlanBase':
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError(
                'end_date must be greater than or equal to start_date'
            )
        return self

    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if v is None:
            return None

        if isinstance(v, str):
            try:
                return datetime.strptime(v, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError('Invalid date format')

        return v

    model_config = {
        "json_encoders": {Decimal: float},
        "from_attributes": True,
        "extra": "forbid"
    }


class TravelPlanCreate(TravelPlanBase):
    pass


class TravelPlanUpdate(TravelPlanBase):
    version: int = Field(
        ...,
        ge=1,
        description="Поточна версія плану для Optimistic Locking"
    )


class TravelPlanResponse(TravelPlanBase):
    id: UUID
    version: int
    created_at: datetime
    updated_at: datetime


# ==========================================
# Схеми для Locations
# ==========================================

class LocationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    address: Optional[str] = None
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    arrival_date: Optional[datetime] = None
    departure_date: Optional[datetime] = None
    budget: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    notes: Optional[str] = None

    @model_validator(mode='after')
    def check_dates(self) -> 'LocationBase':
        if (
            self.arrival_date
            and self.departure_date
            and self.departure_date < self.arrival_date
        ):
            raise ValueError(
                'departure_date must be greater than or equal to arrival_date'
            )
        return self

    model_config = {
        "json_encoders": {Decimal: float},
        "from_attributes": True,
        "extra": "forbid"
    }


class LocationCreate(LocationBase):
    pass


class LocationUpdate(LocationBase):
    visit_order: Optional[int] = Field(None, gt=0)


class LocationResponse(LocationBase):
    id: UUID
    travel_plan_id: UUID
    visit_order: int
    created_at: datetime