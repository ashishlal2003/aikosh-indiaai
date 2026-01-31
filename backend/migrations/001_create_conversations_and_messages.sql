-- Migration: Create conversations and messages tables
-- Purpose: Support flexible conversation tracking with text, voice, and document messages
-- Created: 2024-01-31

-- ============================================================================
-- 1. CONVERSATIONS TABLE
-- ============================================================================
-- Tracks chat sessions that may or may not become claims

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id TEXT UNIQUE NOT NULL, -- Frontend-friendly ID like "conv_123"
    user_session_id TEXT, -- Optional session tracking
    status TEXT NOT NULL DEFAULT 'active', -- active, completed, abandoned
    claim_id UUID, -- References claims table when conversation becomes a claim
    metadata JSONB DEFAULT '{}', -- Flexible field for additional data
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT conversations_status_check CHECK (status IN ('active', 'completed', 'abandoned'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_conversations_conversation_id ON conversations(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_claim_id ON conversations(claim_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_last_message_at ON conversations(last_message_at DESC);

-- ============================================================================
-- 2. MESSAGES TABLE
-- ============================================================================
-- Unified table for all message types: text, voice, AI responses, documents

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,

    -- Message basics
    message_type TEXT NOT NULL, -- user_text, user_voice, ai_response, document, action, system
    content TEXT, -- Message content (transcription for voice, text for chat)
    role TEXT NOT NULL, -- user, assistant, system

    -- Voice message fields
    audio_file_url TEXT, -- URL to stored audio file (if voice message)
    transcription_text TEXT, -- Transcribed text from audio
    detected_language TEXT, -- Language code (en, hi, etc.)
    audio_duration_seconds INTEGER, -- Duration of audio file
    audio_filename TEXT, -- Original filename
    audio_file_size_bytes INTEGER, -- File size
    audio_content_type TEXT, -- MIME type (audio/webm, audio/mp3, etc.)
    transcription_model TEXT, -- Model used (e.g., whisper-large-v3-turbo)

    -- Document message fields
    document_id UUID, -- References documents table if applicable
    document_filename TEXT, -- Original document filename
    document_type TEXT, -- invoice, contract, receipt, etc.

    -- Metadata and tracking
    metadata JSONB DEFAULT '{}', -- Flexible field for additional data
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ, -- When message was processed (for async operations)

    -- Constraints
    CONSTRAINT messages_message_type_check CHECK (
        message_type IN ('user_text', 'user_voice', 'ai_response', 'document', 'action', 'system')
    ),
    CONSTRAINT messages_role_check CHECK (role IN ('user', 'assistant', 'system'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_message_type ON messages(message_type);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);

-- Composite index for common query pattern: get messages for a conversation ordered by time
CREATE INDEX IF NOT EXISTS idx_messages_conversation_created ON messages(conversation_id, created_at DESC);

-- ============================================================================
-- 3. TRIGGERS
-- ============================================================================
-- Auto-update updated_at and last_message_at

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for conversations table
CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to update last_message_at in conversations
CREATE OR REPLACE FUNCTION update_conversation_last_message()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversations
    SET last_message_at = NEW.created_at,
        updated_at = NOW()
    WHERE id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update last_message_at when new message is inserted
CREATE TRIGGER update_conversation_on_message_insert
    AFTER INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_last_message();

-- ============================================================================
-- 4. FOREIGN KEY TO CLAIMS (OPTIONAL - ADD ONLY IF claims TABLE EXISTS)
-- ============================================================================
-- Uncomment if you want strict foreign key enforcement to claims table
-- ALTER TABLE conversations
--     ADD CONSTRAINT fk_conversations_claim_id
--     FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE SET NULL;

-- ============================================================================
-- 5. COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE conversations IS 'Chat sessions that may or may not become formal claims';
COMMENT ON COLUMN conversations.conversation_id IS 'Frontend-friendly ID like conv_1769865449664_icv7di7ih';
COMMENT ON COLUMN conversations.claim_id IS 'Links to claims table when conversation becomes a formal claim';
COMMENT ON COLUMN conversations.status IS 'active: ongoing, completed: ended successfully, abandoned: user left';

COMMENT ON TABLE messages IS 'Unified message table for text, voice, AI responses, and documents';
COMMENT ON COLUMN messages.message_type IS 'Type: user_text, user_voice, ai_response, document, action, system';
COMMENT ON COLUMN messages.content IS 'Message content (text or transcription)';
COMMENT ON COLUMN messages.transcription_text IS 'Transcribed text for voice messages';
COMMENT ON COLUMN messages.audio_file_url IS 'URL to stored audio file (Supabase Storage or external)';

-- ============================================================================
-- ROLLBACK SCRIPT (if needed)
-- ============================================================================
-- DROP TRIGGER IF EXISTS update_conversation_on_message_insert ON messages;
-- DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations;
-- DROP FUNCTION IF EXISTS update_conversation_last_message();
-- DROP FUNCTION IF EXISTS update_updated_at_column();
-- DROP TABLE IF EXISTS messages;
-- DROP TABLE IF EXISTS conversations;
