-- Initialization script for VideoBot database
-- This script is executed when PostgreSQL container starts for the first time

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE videobot TO videobot;

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS public;

-- Grant permissions on schema
GRANT ALL ON SCHEMA public TO videobot;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO videobot;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO videobot;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO videobot;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO videobot; 