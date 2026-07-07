# System Architecture Specification

This document details the high-level architecture, subsystem relationships, and data flows of the VoxSales AI Voice Sales Agent SaaS.

---

## 1. System Topology Overview

The VoxSales platform consists of three distinct layers executing asynchronously:

1. **Telephony Ingestion Gateway:** Twilio Voice SIP trunk and streaming websockets processing binary audio streams.
2. **AI Reasoning Orchestrator:** Multi-agent pipeline resolving voice transcription, parsing intents, querying databases, and synthesizing voice output.
3. **Core API / ERP Sync Service:** Stateless FastAPI backend and database transaction queue syncing completed orders to client ERP systems.

```
       ┌────────────────────────┐
       │      Twilio voice      │
       └───────────┬────────────┘
                   │ Secure RTP / WebSockets (G.711)
                   ▼
       ┌────────────────────────┐
       │   Voice Gateway Node   │ (ASR / TTS Conversational Stream)
       └───────────┬────────────┘
                   │ Pydantic JSON Payload
                   ▼
       ┌────────────────────────┐
       │   FastAPI Web Engine   │ (Stateless routing & validation)
       └───────────┬────────────┘
         ┌─────────┴─────────┐
         ▼                   ▼
┌────────────────┐   ┌────────────────┐
│ PostgreSQL DB  │   │ Redis Message  │
│ (Transactional)│   │  Queue/Cache   │
└────────────────┘   └───────┬────────┘
                             │
                             ▼
                     ┌────────────────┐
                     │ Celery Workers │
                     └───────┬────────┘
                             │
                             ▼
                     ┌────────────────┐
                     │ Client ERP API │
                     └────────────────┘
```

---

## 2. Latency Budget & SLA Thresholds

To keep conversations natural, the system enforces a strict latency budget from the end of user speech to the start of AI speech:

| Stage | Target Latency | P95 Limit | Description |
| :--- | :--- | :--- | :--- |
| **Ingestion & ASR** | 100ms | 150ms | Audio packet buffer reading & transcription to text. |
| **NLU & LLM Engine** | 300ms | 400ms | Multi-agent context resolution and tool matching. |
| **TTS Synthesis** | 150ms | 200ms | Text translation to audio waves. |
| **Websocket Transit** | 50ms | 100ms | Stream transit times to Twilio. |
| **Total Round-trip** | **600ms** | **850ms** | **Target benchmark for conversational continuity.** |

---

## 3. Transaction Sinking Resiliency

To prevent third-party ERP downtime from impacting live voice calls, order writes utilize a deferred transactional flow:
1. The voice agent confirms the order details verbally.
2. The agent commits the order to PostgreSQL in a `pending_sync` state.
3. A background Celery worker picks up the transaction and attempts to sync it with the client ERP.
4. If sync fails, the order enters a retry queue using exponential backoff with jitter. The caller's session is never blocked.
