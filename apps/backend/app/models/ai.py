"""
AI Platform Domain Models
=========================

Domain: AI Platform (Conversations, RAG, Memory, Tools, Models)

Entities:
  - Conversations : Core multi-modal tracking (Voice, Web, Mobile).
  - Voice Context : Voice-specific entities (Call, Recording, Transcripts).
  - Memory        : Fact storage (Customer facts, Product preferences, Session context).
  - Knowledge     : RAG architecture (Documents, Chunks, Embeddings).
  - Tools         : Function calling (Definition, Execution, Results).
  - Intelligence  : System logic (Recommendations, Reasoning Traces).
  - Configuration : Prompt management and Model versioning.

Design Decisions:
  - Multi-modal Interface: The core `Conversation` is decoupled from the `Call`. A Conversation
    can be voice, chat, web, or mobile. If it's a voice conversation, a 1:1 `Call` record extends it.
  - Granular Turn Tracking: `ConversationTurn` logs every interaction, while `AIReasoning` tracks
    the hidden thought process (LangChain/LangGraph traces) separately for debugging.
  - Tool Execution Lifecycle: Tools are defined centrally (`ToolDefinition`), executed inside a turn
    (`ToolExecution`), and their outputs logged (`ToolResult`). This is critical for auditing AI actions.
  - Tiered Memory: Memory is split into `CustomerMemory` (persistent facts), `ProductMemory`
    (dealer-specific product relationships), and `ConversationMemory` (volatile session facts).
  - RAG Preparation: `KnowledgeDocument` and `KnowledgeChunk` manage content. `EmbeddingReference`
    links chunks (or products) to an external Vector DB without forcing vector arrays into PostgreSQL.
  - Prompt Versioning: AI prompts are versioned (`PromptVersion`) allowing safe A/B testing and rollback.
"""

import uuid
from datetime import datetime
from typing import Optional
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedBase


# -----------------------------------------------------------------------------
# Conversation & Interaction Base
# -----------------------------------------------------------------------------


class Conversation(TimestampedBase):
    """
    Core interaction session. Agnostic to the medium (voice, chat, web).
    """

    __tablename__ = "conversations"

    dealer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    platform: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="voice | chat | web | mobile"
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active",
        comment="active | completed | abandoned | failed",
    )
    language_code: Mapped[str] = mapped_column(String(10), nullable=False, default="en")

    # Relationships
    turns: Mapped[list["ConversationTurn"]] = relationship(
        "ConversationTurn",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationTurn.created_at.asc()",
    )
    summary: Mapped[Optional["ConversationSummary"]] = relationship(
        "ConversationSummary",
        back_populates="conversation",
        uselist=False,
        cascade="all, delete-orphan",
    )
    call: Mapped[Optional["Call"]] = relationship(
        "Call",
        back_populates="conversation",
        uselist=False,
        cascade="all, delete-orphan",
    )
    memories: Mapped[list["ConversationMemory"]] = relationship(
        "ConversationMemory",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        "Recommendation", back_populates="conversation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_conversations_dealer_created", "dealer_id", "created_at"),
    )


class ConversationTurn(TimestampedBase):
    """
    A single turn (message/interaction) within a conversation.
    """

    __tablename__ = "conversation_turns"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="system | user | assistant | tool",
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="turns"
    )
    tool_executions: Mapped[list["ToolExecution"]] = relationship(
        "ToolExecution", back_populates="turn", cascade="all, delete-orphan"
    )
    reasoning: Mapped[Optional["AIReasoning"]] = relationship(
        "AIReasoning",
        back_populates="turn",
        uselist=False,
        cascade="all, delete-orphan",
    )


class ConversationSummary(TimestampedBase):
    """
    Post-interaction LLM-generated summary for quick review.
    """

    __tablename__ = "conversation_summaries"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_intents: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="e.g. ['order_placed', 'pricing_inquiry']"
    )
    sentiment_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 4), nullable=True
    )

    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="summary"
    )


# -----------------------------------------------------------------------------
# Voice & Telephony Specifics
# -----------------------------------------------------------------------------


class Call(TimestampedBase):
    """Voice-specific extension of a conversation (e.g. Twilio metadata)."""

    __tablename__ = "calls"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    telephony_sid: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Twilio/Plivo Call SID",
    )
    from_number: Mapped[str] = mapped_column(String(20), nullable=False)
    to_number: Mapped[str] = mapped_column(String(20), nullable=False)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="call"
    )
    recording: Mapped[Optional["CallRecording"]] = relationship(
        "CallRecording",
        back_populates="call",
        uselist=False,
        cascade="all, delete-orphan",
    )
    transcript: Mapped[Optional["Transcript"]] = relationship(
        "Transcript", back_populates="call", uselist=False, cascade="all, delete-orphan"
    )


class CallRecording(TimestampedBase):
    """Audio recording metadata."""

    __tablename__ = "call_recordings"

    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    recording_url: Mapped[str] = mapped_column(String(500), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)

    call: Mapped["Call"] = relationship("Call", back_populates="recording")


class Transcript(TimestampedBase):
    """Full raw STT transcript of a call."""

    __tablename__ = "transcripts"

    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    full_text: Mapped[str] = mapped_column(Text, nullable=False)

    call: Mapped["Call"] = relationship("Call", back_populates="transcript")
    segments: Mapped[list["SpeechSegment"]] = relationship(
        "SpeechSegment",
        back_populates="transcript",
        cascade="all, delete-orphan",
        order_by="SpeechSegment.start_time_ms.asc()",
    )


class SpeechSegment(TimestampedBase):
    """Granular word/sentence level STT segments with confidence tracking."""

    __tablename__ = "speech_segments"

    transcript_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transcripts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    speaker: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="dealer | agent"
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)

    transcript: Mapped["Transcript"] = relationship(
        "Transcript", back_populates="segments"
    )


# -----------------------------------------------------------------------------
# AI Memory System
# -----------------------------------------------------------------------------


class CustomerMemory(TimestampedBase):
    """Persistent facts learned about a dealer over time."""

    __tablename__ = "customer_memories"

    dealer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    memory_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="e.g. 'preferred_delivery_time'",
    )
    memory_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=1.0
    )

    __table_args__ = (
        UniqueConstraint("dealer_id", "memory_key", name="uq_customer_memory"),
    )


class ProductMemory(TimestampedBase):
    """Preferences and habits linking a dealer to specific products."""

    __tablename__ = "product_memories"

    dealer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dealers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    memory_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="frequently_bought | often_returned | price_sensitive",
    )
    context_value: Mapped[dict] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "dealer_id", "product_variant_id", "memory_type", name="uq_product_memory"
        ),
    )


class ConversationMemory(TimestampedBase):
    """Volatile scratchpad memory for an active conversation (e.g., 'they just asked about 50kg bags')."""

    __tablename__ = "conversation_memories"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)

    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="memories"
    )


# -----------------------------------------------------------------------------
# Knowledge & RAG Architecture
# -----------------------------------------------------------------------------


class KnowledgeDocument(TimestampedBase):
    """Source documents for RAG (e.g., PDF manuals, scheme PDFs)."""

    __tablename__ = "knowledge_documents"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    doc_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="pdf | text | web"
    )
    source_uri: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        "KnowledgeChunk", back_populates="document", cascade="all, delete-orphan"
    )


class KnowledgeChunk(TimestampedBase):
    """Split text chunks used for vector search."""

    __tablename__ = "knowledge_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)

    document: Mapped["KnowledgeDocument"] = relationship(
        "KnowledgeDocument", back_populates="chunks"
    )


class EmbeddingReference(TimestampedBase):
    """Links database entities to external Vector DB references (Pinecone/Milvus)."""

    __tablename__ = "embedding_references"

    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="knowledge_chunk | product_variant | dealer",
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    external_vector_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("model_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )


# -----------------------------------------------------------------------------
# Tool Execution Lifecycle
# -----------------------------------------------------------------------------


class ToolDefinition(TimestampedBase):
    """Available functions the AI can call (e.g., 'check_inventory', 'apply_discount')."""

    __tablename__ = "tool_definitions"

    name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    schema_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, comment="JSON Schema for parameters"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ToolExecution(TimestampedBase):
    """Instance of an AI calling a tool during a conversation."""

    __tablename__ = "tool_executions"

    conversation_turn_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversation_turns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tool_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    input_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    execution_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        comment="pending | success | failed",
    )
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    turn: Mapped["ConversationTurn"] = relationship(
        "ConversationTurn", back_populates="tool_executions"
    )
    result: Mapped[Optional["ToolResult"]] = relationship(
        "ToolResult",
        back_populates="execution",
        uselist=False,
        cascade="all, delete-orphan",
    )


class ToolResult(TimestampedBase):
    """The output returned to the AI after tool execution."""

    __tablename__ = "tool_results"

    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tool_executions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    output_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    execution: Mapped["ToolExecution"] = relationship(
        "ToolExecution", back_populates="result"
    )


# -----------------------------------------------------------------------------
# AI Intelligence & Reasoning
# -----------------------------------------------------------------------------


class Recommendation(TimestampedBase):
    """Proactive product suggestions generated by the AI."""

    __tablename__ = "recommendations"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recommended_product_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
    )
    reasoning_text: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Why this was recommended"
    )
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)

    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="recommendations"
    )
    feedback: Mapped[Optional["RecommendationFeedback"]] = relationship(
        "RecommendationFeedback",
        back_populates="recommendation",
        uselist=False,
        cascade="all, delete-orphan",
    )


class RecommendationFeedback(TimestampedBase):
    """Whether the dealer accepted the recommendation."""

    __tablename__ = "recommendation_feedback"

    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recommendations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    was_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    explicit_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    recommendation: Mapped["Recommendation"] = relationship(
        "Recommendation", back_populates="feedback"
    )


class AIReasoning(TimestampedBase):
    """Hidden thought traces (e.g., ReAct loop steps) logged for debugging and alignment."""

    __tablename__ = "ai_reasoning_traces"

    conversation_turn_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversation_turns.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    trace_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    thought_process: Mapped[dict] = mapped_column(
        JSONB, nullable=False, comment="Detailed LangGraph/Agent logic trace"
    )
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    turn: Mapped["ConversationTurn"] = relationship(
        "ConversationTurn", back_populates="reasoning"
    )


# -----------------------------------------------------------------------------
# Configuration (Prompts & Models)
# -----------------------------------------------------------------------------


class PromptTemplate(TimestampedBase):
    """Master record for system prompts."""

    __tablename__ = "prompt_templates"

    name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    active_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Will FK to prompt_versions after creation",
    )

    versions: Mapped[list["PromptVersion"]] = relationship(
        "PromptVersion",
        back_populates="template",
        cascade="all, delete-orphan",
        foreign_keys="[PromptVersion.template_id]",
    )


class PromptVersion(TimestampedBase):
    """Immutable versions of a prompt for A/B testing and rollback."""

    __tablename__ = "prompt_versions"

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    variables_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    template: Mapped["PromptTemplate"] = relationship(
        "PromptTemplate", back_populates="versions", foreign_keys=[template_id]
    )

    __table_args__ = (
        UniqueConstraint("template_id", "version_number", name="uq_prompt_version"),
    )


class AIModel(TimestampedBase):
    """Providers and Base Models."""

    __tablename__ = "ai_models"

    provider: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="e.g. Google, OpenAI, Anthropic",
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="llm | tts | stt | embedding"
    )

    versions: Mapped[list["ModelVersion"]] = relationship(
        "ModelVersion", back_populates="model", cascade="all, delete-orphan"
    )


class ModelVersion(TimestampedBase):
    """Specific pinned versions (e.g., gemini-1.5-pro-001)."""

    __tablename__ = "model_versions"

    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_tag: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    model: Mapped["AIModel"] = relationship("AIModel", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("model_id", "version_tag", name="uq_model_version"),
    )
