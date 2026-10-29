DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'repuser') THEN
        CREATE USER repuser WITH REPLICATION SUPERUSER LOGIN PASSWORD 'rep_secret_password';
    END IF;
END
$$;