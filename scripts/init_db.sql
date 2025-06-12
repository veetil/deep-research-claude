-- Initialize Deep Research Claude Database

-- Create schemas
CREATE SCHEMA IF NOT EXISTS agents;
CREATE SCHEMA IF NOT EXISTS research;
CREATE SCHEMA IF NOT EXISTS memory;

-- Agent-related tables
CREATE TABLE IF NOT EXISTS agents.agents (
    id UUID PRIMARY KEY,
    agent_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    parent_id UUID REFERENCES agents.agents(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_agents_type ON agents.agents(agent_type);
CREATE INDEX idx_agents_status ON agents.agents(status);
CREATE INDEX idx_agents_parent ON agents.agents(parent_id);

CREATE TABLE IF NOT EXISTS agents.agent_capabilities (
    agent_id UUID REFERENCES agents.agents(id) ON DELETE CASCADE,
    capability VARCHAR(50) NOT NULL,
    PRIMARY KEY (agent_id, capability)
);

CREATE TABLE IF NOT EXISTS agents.agent_messages (
    id UUID PRIMARY KEY,
    source_agent_id UUID REFERENCES agents.agents(id),
    target_agent_id UUID REFERENCES agents.agents(id),
    message_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'pending'
);

CREATE INDEX idx_messages_source ON agents.agent_messages(source_agent_id);
CREATE INDEX idx_messages_target ON agents.agent_messages(target_agent_id);
CREATE INDEX idx_messages_status ON agents.agent_messages(status);

-- Research-related tables
CREATE TABLE IF NOT EXISTS research.research_sessions (
    id UUID PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    query TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_research_user ON research.research_sessions(user_id);
CREATE INDEX idx_research_status ON research.research_sessions(status);

CREATE TABLE IF NOT EXISTS research.research_findings (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES research.research_sessions(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents.agents(id),
    finding_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    relevance_score FLOAT,
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_findings_session ON research.research_findings(session_id);
CREATE INDEX idx_findings_agent ON research.research_findings(agent_id);

-- Memory-related tables
CREATE TABLE IF NOT EXISTS memory.short_term_memory (
    id UUID PRIMARY KEY,
    agent_id UUID REFERENCES agents.agents(id) ON DELETE CASCADE,
    key VARCHAR(255) NOT NULL,
    value JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(agent_id, key)
);

CREATE INDEX idx_stm_agent ON memory.short_term_memory(agent_id);
CREATE INDEX idx_stm_expires ON memory.short_term_memory(expires_at);

CREATE TABLE IF NOT EXISTS memory.long_term_memory (
    id UUID PRIMARY KEY,
    key VARCHAR(255) NOT NULL UNIQUE,
    value JSONB NOT NULL,
    category VARCHAR(50),
    importance_score FLOAT DEFAULT 0.5,
    access_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_ltm_category ON memory.long_term_memory(category);
CREATE INDEX idx_ltm_importance ON memory.long_term_memory(importance_score DESC);

-- Audit and logging
CREATE TABLE IF NOT EXISTS agents.audit_log (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    agent_id UUID,
    user_id VARCHAR(100),
    event_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_type ON agents.audit_log(event_type);
CREATE INDEX idx_audit_agent ON agents.audit_log(agent_id);
CREATE INDEX idx_audit_user ON agents.audit_log(user_id);
CREATE INDEX idx_audit_time ON agents.audit_log(created_at DESC);

-- Functions
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers
CREATE TRIGGER update_agents_updated_at BEFORE UPDATE
    ON agents.agents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Initial data
INSERT INTO agents.audit_log (event_type, event_data)
VALUES ('system_initialized', '{"version": "0.1.0", "timestamp": "now"}'::jsonb);