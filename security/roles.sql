-- Create login credentials out-of-band. This file contains no passwords.
DO $$ BEGIN CREATE ROLE etl_service NOINHERIT; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE analyst NOINHERIT; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE bi_reader NOINHERIT; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE admin NOINHERIT; EXCEPTION WHEN duplicate_object THEN NULL; END $$;

GRANT USAGE ON SCHEMA raw,staging,core,marts,ops TO etl_service;
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA raw,staging,core,marts,ops TO etl_service;

GRANT USAGE ON SCHEMA core,marts TO analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA core,marts TO analyst;
REVOKE ALL ON SCHEMA raw FROM analyst;

GRANT USAGE ON SCHEMA marts TO bi_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA marts TO bi_reader;
REVOKE ALL ON SCHEMA raw,staging,core FROM bi_reader;

GRANT ALL PRIVILEGES ON SCHEMA raw,staging,core,marts,ops TO admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA raw,staging,core,marts,ops TO admin;

ALTER DEFAULT PRIVILEGES IN SCHEMA marts GRANT SELECT ON TABLES TO analyst,bi_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA core GRANT SELECT ON TABLES TO analyst;
