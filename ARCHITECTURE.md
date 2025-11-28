# Architecture Documentation

## Overview

This is a production-ready multi-agent insurance support system built with LangGraph, transformed from a Jupyter notebook into a modular, scalable application.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI REST API                         │
│         /api/v1/chat  |  /api/v1/sessions  |  /health        │
│          Middleware: CORS, Request ID, Metrics               │
└──────────────┬──────────────────┬────────────────────────────┘
               │                  │
               │          ┌───────▼──────────┐
               │          │  Redis Sessions  │
               │          │   (TTL: 1 hour)  │
               │          └──────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────┐
│                   LangGraph Workflow                         │
│  ┌──────────────┐                                            │
│  │  Supervisor  │◄──────┐                                    │
│  │    Agent     │       │                                    │
│  └───┬──────────┘       │                                    │
│      │                  │                                    │
│      ├─────────►┌───────┴───────┐                            │
│      │          │ Policy Agent  │                            │
│      │          └───────────────┘                            │
│      │                  │                                    │
│      ├─────────►┌───────┴───────┐                            │
│      │          │ Billing Agent │                            │
│      │          └───────────────┘                            │
│      │                  │                                    │
│      ├─────────►┌───────┴───────┐                            │
│      │          │ Claims Agent  │                            │
│      │          └───────────────┘                            │
│      │                  │                                    │
│      ├─────────►┌───────┴───────┐                            │
│      │          │General Help   │                            │
│      │          │  Agent (RAG)  │                            │
│      │          └───────────────┘                            │
│      │                                                        │
│      ├─────────►┌─────────────────┐                          │
│      │          │ Human Escalation│                          │
│      │          │     Agent       │                          │
│      │          └─────────────────┘                          │
│      │                                                        │
│      └─────────►┌─────────────────┐                          │
│                 │  Final Answer   │                          │
│                 │     Agent       │                          │
│                 └─────────────────┘                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼────────┐           ┌────────▼────────┐
│   PostgreSQL   │           │    ChromaDB     │
│   (Policies,   │           │  (FAQ Vectors)  │
│ Billing, etc)  │           │                 │
└────────────────┘           └─────────────────┘
```

---

## Project Structure

### Root Level
```
multi-agent-system/
├── src/                    # Application source code
├── tests/                  # Test suites
├── scripts/                # Utility scripts
├── deployment/             # Deployment configurations
├── .env.example            # Environment template
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Development dependencies
├── test_phase1.py          # Phase 1 verification script
├── ARCHITECTURE.md         # This file
├── PRODUCTIONIZATION_PLAN.md  # Implementation plan
└── README.md               # Project README
```

### Source Code Organization

```
src/
├── config.py              # Configuration management
│
├── agents/                # Agent implementations
│   ├── base.py           # Abstract base agent class
│   ├── prompts.py        # Centralized prompt templates
│   ├── supervisor.py     # Routing & orchestration agent
│   ├── policy_agent.py   # Policy specialist
│   ├── billing_agent.py  # Billing specialist
│   ├── claims_agent.py   # Claims specialist
│   ├── general_help_agent.py  # FAQ/RAG agent
│   ├── human_escalation.py    # Escalation handler
│   └── final_answer.py   # Response summarizer
│
├── tools/                 # Database query tools
│   ├── policy_tools.py   # Policy data access
│   ├── billing_tools.py  # Billing data access
│   ├── claims_tools.py   # Claims data access
│   └── user_interaction.py  # User clarification
│
├── graph/                 # LangGraph workflow
│   ├── state.py          # GraphState TypedDict
│   ├── routing.py        # Routing decision logic
│   └── workflow.py       # Workflow builder
│
├── database/              # Database layer
│   ├── connection.py     # Connection management
│   ├── models.py         # SQLAlchemy ORM models (TODO)
│   └── repositories.py   # Data access patterns (TODO)
│
├── rag/                   # RAG / Vector store
│   └── vector_store.py   # ChromaDB integration
│
├── session/               # Session management
│   ├── manager.py        # Redis session manager (✅)
│   └── models.py         # Session state models (✅)
│
├── observability/         # Monitoring & observability
│   ├── logging_config.py # Structured logging
│   ├── tracing.py        # Phoenix tracing
│   └── metrics.py        # Prometheus metrics
│
├── utils/                 # Utility functions
│   └── llm_client.py     # OpenAI client wrapper
│
├── api/                   # FastAPI application
│   ├── models.py         # Pydantic request/response models (✅)
│   └── routes/           # API route handlers
│       ├── chat.py       # Chat endpoint (✅)
│       ├── sessions.py   # Session CRUD endpoints (✅)
│       └── health.py     # Health check endpoints (✅)
│
└── main.py                # FastAPI application entry point (✅)
```

---

## Core Components

### 1. Configuration Management

**File**: `src/config.py`

Uses Pydantic Settings for type-safe configuration:

```python
from src.config import settings

# Access configuration
api_key = settings.OPENAI_API_KEY
db_url = settings.DATABASE_URL
log_level = settings.LOG_LEVEL
```

**Key Features**:
- Environment variable loading from `.env`
- Type validation
- Default values
- Singleton pattern via `@lru_cache`

---

### 2. Agent System

**Base Agent Class**: `src/agents/base.py`

All agents inherit from `BaseAgent`:

```python
class MyCustomAgent(BaseAgent):
    def __init__(self):
        super().__init__("my_agent")

    def process(self, state: GraphState) -> GraphState:
        # Your agent logic here
        return updated_state
```

**Built-in Features**:
- Automatic tracing with `@trace_agent`
- Metrics collection (invocations, duration, errors)
- Structured logging
- Message management
- Conversation history tracking

**Agents**:

| Agent | Responsibility | Tools Used |
|-------|---------------|------------|
| Supervisor | Routes requests, asks clarifications | `ask_user` |
| Policy | Policy details, coverage | `get_policy_details`, `get_auto_policy_details` |
| Billing | Billing info, payments | `get_billing_info`, `get_payment_history` |
| Claims | Claim status, filing | `get_claim_status` |
| General Help | FAQ, general questions | Vector store (ChromaDB) |
| Human Escalation | Handles escalations | None |
| Final Answer | Creates clean summaries | None |

---

### 3. LangGraph Workflow

**Workflow Construction**: `src/graph/workflow.py`

The workflow is a state machine with:
- **7 agent nodes**
- **Conditional routing** from supervisor
- **Loop-back edges** to supervisor after specialists
- **Terminal nodes** (final answer, human escalation)

**Key Functions**:

```python
from src.graph.workflow import get_workflow

# Get compiled workflow
workflow = get_workflow()

# Execute workflow
result = workflow.invoke(initial_state)
```

**Routing Logic**: `src/graph/routing.py`

```python
def decide_next_agent(state: GraphState) -> str:
    # Returns next agent name based on state
    # Handles: clarification, escalation, end
```

---

### 4. GraphState

**Definition**: `src/graph/state.py`

The `GraphState` TypedDict contains 25+ fields:

**Core Fields**:
- `user_input`: Current user query
- `messages`: Conversation messages
- `conversation_history`: Full history string

**Context Fields**:
- `customer_id`, `policy_number`, `claim_id`
- `user_intent`, `task`, `justification`

**Control Flow Fields**:
- `next_agent`: Routing decision
- `n_iteration`: Loop counter
- `needs_clarification`: Clarification flag
- `end_conversation`: Termination flag

**Results**:
- `final_answer`: User-facing response
- `database_lookup_result`: DB query results
- `retrieved_faqs`: RAG retrieval results

---

### 5. Tools

**Tool Functions**: `src/tools/*.py`

All tools follow this pattern:

```python
@trace_function(name="tool_name", attributes={"db.table": "table"})
def get_data(param: str) -> Dict[str, Any]:
    """Query database and return results."""
    # Implementation
    return result
```

**Available Tools**:

| Tool | Module | Purpose |
|------|--------|---------|
| `get_policy_details` | policy_tools | Get policy by number |
| `get_auto_policy_details` | policy_tools | Get auto-specific details |
| `get_billing_info` | billing_tools | Get billing information |
| `get_payment_history` | billing_tools | Get payment records |
| `get_claim_status` | claims_tools | Get claim details |
| `ask_user` | user_interaction | Request clarification |

---

### 6. RAG System

**Vector Store**: `src/rag/vector_store.py`

ChromaDB integration for FAQ retrieval:

```python
from src.rag.vector_store import get_vector_store

vector_store = get_vector_store()

# Query for FAQs
results = vector_store.query("What is life insurance?", n_results=3)

# Format for LLM
context = vector_store.format_faq_context(results)
```

**Features**:
- Persistent storage
- Automatic embedding generation
- Similarity search
- Metadata filtering
- Result formatting

---

### 7. Session Management

**Session Manager**: `src/session/manager.py`

Redis-based session persistence with in-memory fallback:

```python
from src.session.manager import get_session_manager

session_manager = get_session_manager()

# Get or create session
session = session_manager.get_or_create("sess_abc123")

# Add messages to session
from src.session.models import MessageRole
session.add_message(
    role=MessageRole.USER,
    content="What's my policy status?",
    metadata={"request_id": "req_123"}
)

# Update context
session.update_context(
    customer_id="C001",
    policy_number="P123456"
)

# Save session
session_manager.update_session(session)

# Retrieve conversation history
history = session.get_conversation_history()
```

**Session Models**: `src/session/models.py`

- **SessionState**: Complete session with messages, context, metadata
- **ConversationMessage**: Individual message with role, content, timestamp
- **SessionContext**: Extracted entities (customer_id, policy_number, etc.)
- **SessionMetadata**: Analytics (agents_used, iterations, escalation)

**Features**:
- **Redis Storage**: Persistent sessions with TTL (default: 1 hour)
- **In-Memory Fallback**: Automatic fallback if Redis unavailable
- **Conversation History**: Full message tracking with timestamps
- **Context Extraction**: Automatic entity extraction from conversations
- **Metadata Tracking**: Agent usage, iterations, escalations
- **Auto-Cleanup**: Background task removes expired sessions every hour
- **Tracing & Metrics**: Full observability for all session operations

**Session API Endpoints**: `src/api/routes/sessions.py`

```bash
# List all sessions
GET /api/v1/sessions?limit=100

# Get specific session
GET /api/v1/sessions/{session_id}

# Get session summary (without full messages)
GET /api/v1/sessions/{session_id}/summary

# Refresh session TTL
POST /api/v1/sessions/{session_id}/refresh

# Delete session
DELETE /api/v1/sessions/{session_id}
```

**Session Integration with Chat**: `src/api/routes/chat.py`

The chat endpoint automatically:
1. Creates or retrieves session by ID
2. Adds user message to session
3. Includes conversation history in workflow state
4. Saves assistant response to session
5. Updates session context from workflow results
6. Tracks agents used and iterations
7. Persists updated session to Redis

**Background Cleanup**: `src/main.py`

Automatic cleanup task runs hourly:
```python
async def session_cleanup_task():
    # Removes expired sessions from in-memory store
    # Redis handles cleanup automatically via TTL
```

---

### 8. FastAPI REST API

**Application Entry**: `src/main.py`

```python
# Start server
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

**Features**:
- CORS middleware (configurable origins)
- Request ID tracking (X-Request-ID header)
- Metrics middleware (Prometheus)
- Exception handlers (validation, general errors)
- Lifespan management (startup/shutdown)
- Background tasks (session cleanup)
- Health checks (liveness, readiness)

**Request/Response Models**: `src/api/models.py`

```python
# Chat request
{
  "message": "What's my billing status?",
  "session_id": "sess_abc123",  # Optional
  "context": {                  # Optional
    "customer_id": "C001",
    "policy_number": "P123456"
  }
}

# Chat response
{
  "session_id": "sess_abc123",
  "message": "Your billing is up to date...",
  "agent_used": "billing_agent",
  "requires_clarification": false,
  "conversation_complete": false,
  "metadata": {
    "iterations": 2,
    "processing_time_ms": 1234,
    "total_messages": 4,
    "total_iterations": 3
  }
}
```

**Health Endpoints**: `src/api/routes/health.py`

- `GET /health` - Comprehensive health check (all services)
- `GET /health/live` - Kubernetes liveness probe
- `GET /health/ready` - Kubernetes readiness probe
- `GET /metrics` - Prometheus metrics endpoint

---

### 9. Observability Stack

#### Logging: `src/observability/logging_config.py`

```python
from src.observability.logging_config import get_logger

logger = get_logger(__name__)
logger.info("Message", extra={"request_id": "123"})
```

**Formats**:
- JSON (production)
- Text with colors (development)

#### Tracing: `src/observability/tracing.py`

```python
from src.observability.tracing import trace_agent, trace_function

@trace_agent
def my_agent(state):
    # Automatically traced with metadata
    return result

@trace_function(name="custom_op", attributes={"key": "value"})
def my_function():
    # Custom function tracing
    pass
```

**Integrations**:
- Arize Phoenix
- OpenTelemetry
- Automatic span creation
- Error recording

#### Metrics: `src/observability/metrics.py`

```python
from src.observability import metrics

# Increment counter
metrics.agent_invocations_total.labels(
    agent_name="policy_agent",
    status="success"
).inc()

# Record histogram
metrics.agent_duration_seconds.labels(
    agent_name="policy_agent"
).observe(duration)

# Export metrics
metrics_data = metrics.get_metrics()
```

**Metric Categories**:
- API metrics (requests, duration, status)
- Agent metrics (invocations, errors, duration)
- LLM metrics (requests, tokens, latency)
- Database metrics (queries, duration, pool)
- Vector store metrics (queries, retrieval time)
- Session metrics (active, operations)

---

## Data Flow

### Complete Request Flow with Session Management

```
1. User sends HTTP POST to /api/v1/chat
   ├─► Middleware adds request_id
   └─► Request validated with Pydantic

2. Chat Endpoint (FastAPI)
   ├─► Get or create session from Redis (or memory fallback)
   ├─► Add user message to session
   ├─► Update session context if provided
   └─► Build initial state with conversation history

3. LangGraph Workflow Execution
   │
   ├─► Supervisor Agent
   │    ├─► Analyzes intent from conversation history
   │    ├─► Checks if clarification needed
   │    │   └─► If yes: uses ask_user tool, waits for response
   │    └─► Routes to specialist agent
   │
   ├─► Specialist Agent (e.g., Billing)
   │    ├─► Receives task from supervisor
   │    ├─► Uses tools to query database
   │    ├─► Calls LLM with tool results
   │    └─► Returns response to supervisor
   │
   ├─► Supervisor Agent (iteration 2)
   │    ├─► Evaluates if question answered
   │    ├─► If yes: routes to "end"
   │    └─► If no: routes to another specialist
   │
   └─► Final Answer Agent
        ├─► Receives specialist responses
        ├─► Generates clean, user-friendly summary
        └─► Sets end_conversation=True

4. Workflow Result Processing
   ├─► Extract final_answer, agent_used, metadata
   ├─► Add assistant message to session
   ├─► Update session context from workflow results
   ├─► Update session metadata (agents_used, iterations)
   └─► Mark conversation complete if needed

5. Session Persistence
   ├─► Store updated session in Redis (with TTL)
   └─► Session available for next request

6. Response
   ├─► Build ChatResponse with metadata
   ├─► Track metrics (duration, iterations, tokens)
   ├─► Add X-Request-ID header
   └─► Return JSON response to user

Background: Session Cleanup Task (runs hourly)
   ├─► Clean up expired sessions from memory
   └─► Redis handles automatic TTL expiration
```

### Session Lifecycle

```
Session Creation:
├─► User sends first message
├─► Generate session_id (sess_XXXXXXXX)
├─► Create SessionState in Redis
└─► Return session_id to user

Subsequent Messages:
├─► User includes session_id in request
├─► Load SessionState from Redis
├─► Add to conversation_history
├─► Workflow uses full context
└─► Update session with new messages

Session Expiration:
├─► Default TTL: 1 hour (configurable)
├─► Each request refreshes TTL
├─► Expired sessions auto-deleted
└─► User can manually refresh with /sessions/{id}/refresh
```

---

## Configuration

### Environment Variables

See [.env.example](.env.example) for all configuration options.

**Critical Settings**:

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Database
DATABASE_URL=postgresql://user:pass@host:port/db

# Redis
REDIS_URL=redis://localhost:6379/0
SESSION_TTL_SECONDS=3600

# ChromaDB
CHROMA_PERSIST_DIR=./chroma_db
CHROMA_COLLECTION_NAME=insurance_FAQ_collection

# Observability
LOG_LEVEL=INFO
LOG_FORMAT=json
PHOENIX_ENABLED=true
PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006/v1/traces
```

---

## Testing

### Phase 1 Verification

Run the comprehensive test script:

```bash
python test_phase1.py
```

Tests include:
- ✅ Configuration loading
- ✅ Logging setup
- ✅ Tracing initialization
- ✅ Database connection
- ✅ Tool functions
- ✅ Vector store operations
- ✅ GraphState management
- ✅ Agent instantiation
- ✅ Workflow construction
- ✅ LLM client setup
- ✅ Metrics collection

### Unit Tests (Phase 6)

```bash
# Run all tests
pytest tests/

# With coverage
pytest tests/ --cov=src --cov-report=html

# Specific test file
pytest tests/unit/test_agents.py
```

---

## Performance Considerations

### Optimization Strategies

1. **Connection Pooling**
   - Database connections reused
   - Configurable pool size

2. **Caching**
   - Redis for session state
   - Short TTL for active conversations

3. **Lazy Loading**
   - Singletons for expensive resources
   - On-demand initialization

4. **Async Operations** (Phase 2)
   - FastAPI async endpoints
   - Non-blocking I/O

### Monitoring

**Key Metrics to Watch**:
- Agent invocation duration (p50, p95, p99)
- LLM token usage
- Database query latency
- Vector store retrieval time
- Session count and memory usage

---

## Security Considerations

### Current State (Phase 1)

- ✅ No hardcoded credentials
- ✅ Environment variable configuration
- ✅ SQL injection protection (parameterized queries)
- ⚠️ No authentication (internal use only)

### Phase 2 Additions

- API key authentication
- Rate limiting
- Input validation
- CORS configuration

---

## Deployment

See [PRODUCTIONIZATION_PLAN.md](PRODUCTIONIZATION_PLAN.md) for full deployment guide.

### Quick Start (Development)

```bash
# 1. Install dependencies
pip install -r requirements-dev.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your values

# 3. Verify Phase 1
python test_phase1.py

# 4. (After Phase 2) Run API server
uvicorn src.main:app --reload
```

---

## Future Enhancements

### Phase 2: API Layer (Next)
- FastAPI REST API
- Session management with Redis
- Health check endpoints
- OpenAPI documentation

### Phase 3: Database Migration
- PostgreSQL migration
- SQLAlchemy ORM models
- Alembic migrations

### Phase 4: Containerization
- Docker multi-stage build
- Docker Compose for local dev
- Cloud deployment configs

### Phase 5: Advanced Features
- Streaming responses
- WebSocket support
- Multi-tenant support
- Advanced caching strategies

---

## Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Solution: Ensure src is in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

**2. Database Not Found**
```bash
# Solution: Run database setup script
python scripts/setup_database.py
```

**3. ChromaDB Empty**
```bash
# Solution: Load FAQ data
python scripts/setup_vector_store.py
```

**4. Phoenix Connection Failed**
```bash
# Solution: Either run Phoenix server or disable tracing
PHOENIX_ENABLED=false
```

---

## Contributing

### Code Style

- Follow PEP 8
- Use type hints
- Document functions with docstrings
- Keep functions small and focused

### Adding a New Agent

1. Create agent file in `src/agents/`
2. Inherit from `BaseAgent`
3. Implement `process(state: GraphState)` method
4. Add node function for LangGraph
5. Update workflow in `src/graph/workflow.py`
6. Add tests in `tests/unit/test_agents.py`

### Adding a New Tool

1. Create tool function in appropriate `src/tools/` file
2. Add `@trace_function` decorator
3. Use database connection manager
4. Add error handling
5. Update agent prompts to reference tool
6. Add tests

---

## License

MIT License - See LICENSE file

---

## Support

For issues or questions:
- Check [PRODUCTIONIZATION_PLAN.md](PRODUCTIONIZATION_PLAN.md)
- Run `python test_phase1.py` for diagnostics
- Check logs in `insurance_agent.log`
- Review Phoenix traces at http://localhost:6006
