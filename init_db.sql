-- Додаємо підтримку генерації UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Функція для автоматичного оновлення поля updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Таблиця travel_plans
CREATE TABLE IF NOT EXISTS travel_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(200) NOT NULL CHECK (length(title) > 0),
    description TEXT,
    start_date DATE,
    end_date DATE CHECK (end_date >= start_date),
    budget DECIMAL(10, 2) CHECK (budget >= 0),
    currency VARCHAR(3) DEFAULT 'USD' CHECK (length(currency) = 3),
    is_public BOOLEAN DEFAULT FALSE,
    version INTEGER DEFAULT 1 CHECK (version >= 1), -- Для Optimistic Locking
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Тригер для travel_plans
CREATE TRIGGER update_travel_plans_updated_at
    BEFORE UPDATE ON travel_plans
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Таблиця locations
CREATE TABLE IF NOT EXISTS locations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    travel_plan_id UUID NOT NULL REFERENCES travel_plans(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL CHECK (length(name) > 0),
    address TEXT,
    latitude DECIMAL(10, 6) CHECK (latitude BETWEEN -90 AND 90),
    longitude DECIMAL(11, 6) CHECK (longitude BETWEEN -180 AND 180),
    visit_order INTEGER NOT NULL CHECK (visit_order > 0), -- Будемо вираховувати через MAX() + 1
    arrival_date TIMESTAMP WITH TIME ZONE,
    departure_date TIMESTAMP WITH TIME ZONE CHECK (departure_date >= arrival_date),
    budget DECIMAL(10, 2) CHECK (budget >= 0),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Індекси для швидкого пошуку та з'єднання
CREATE INDEX idx_locations_travel_plan_id ON locations(travel_plan_id);
CREATE INDEX idx_locations_visit_order ON locations(travel_plan_id, visit_order);