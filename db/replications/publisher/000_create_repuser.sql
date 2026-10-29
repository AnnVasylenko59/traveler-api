DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'repuser') THEN
        CREATE USER repuser WITH REPLICATION LOGIN PASSWORD 'rep_secret_password';
    END IF;
END
$$;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO repuser;