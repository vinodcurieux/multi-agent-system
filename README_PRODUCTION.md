# Multi-Agent Insurance Support System

**Production-Ready Implementation** | **LangGraph + FastAPI** | **PostgreSQL + ChromaDB**

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2%2B-orange.svg)](https://python.langchain.com/docs/langgraph)

---

## 🎯 Overview

An intelligent multi-agent system for insurance customer support that uses:
- **LangGraph** for agent orchestration
- **RAG (Retrieval-Augmented Generation)** for FAQ support
- **Specialized agents** for policy, billing, and claims
- **Phoenix tracing** for observability
- **Prometheus metrics** for monitoring

**Transformed from Jupyter notebook → Production-ready application**

---

## ✨ Features

### Core Capabilities
- 🤖 **7 Specialized Agents** - Supervisor, Policy, Billing, Claims, General Help, Escalation, Final Answer
- 🔄 **Intelligent Routing** - Automatic intent detection and agent selection
- 💬 **Clarification Handling** - Asks for missing information when needed
- 📚 **RAG-powered FAQ** - Retrieves relevant information from knowledge base
- 🚨 **Smart Escalation** - Automatic escalation after 3 iterations or on request
- 🎨 **Clean Responses** - Final answer agent summarizes specialist outputs

### Production Features
- 📊 **Full Observability** - Structured logging, distributed tracing, metrics
- 🔧 **Configuration Management** - Environment-based with Pydantic validation
- 🧪 **Comprehensive Testing** - Unit tests, integration tests, verification script
- 🐳 **Container-Ready** - Docker support for cloud deployment
- 📈 **Metrics Collection** - Prometheus metrics for monitoring
- 🔍 **Phoenix Tracing** - OpenTelemetry integration for debugging

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL (for production) or SQLite (for development)
- Redis (for session management)
- OpenAI API key

### Installation

```bash
# 1. Clone the repository
git clone <repository-url>
cd multi-agent-system

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your OpenAI API key

# 5. Verify installation
python test_phase1.py
```

### Configuration

Edit `.env` file:

```bash
# Essential configuration
OPENAI_API_KEY=sk-your-api-key-here
DATABASE_URL=postgresql://user:pass@localhost:5432/insurance_db
REDIS_URL=redis://localhost:6379/0

# Optional: Phoenix tracing
PHOENIX_ENABLED=true
PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006/v1/traces
```

---

## 📁 Project Structure

```
multi-agent-system/
├── src/                          # Application code
│   ├── agents/                  # Agent implementations
│   │   ├── supervisor.py        # Routes to specialists
│   │   ├── policy_agent.py      # Policy queries
│   │   ├── billing_agent.py     # Billing queries
│   │   ├── claims_agent.py      # Claims queries
│   │   ├── general_help_agent.py # FAQ/RAG
│   │   └── ...
│   ├── graph/                   # LangGraph workflow
│   │   ├── state.py            # State definition
│   │   ├── routing.py          # Routing logic
│   │   └── workflow.py         # Workflow builder
│   ├── tools/                   # Database tools
│   ├── rag/                     # Vector store (ChromaDB)
│   ├── database/                # Database layer
│   ├── observability/           # Logging, tracing, metrics
│   └── config.py                # Configuration
├── tests/                        # Test suites
├── scripts/                      # Utility scripts
├── deployment/                   # Deployment configs
├── test_phase1.py               # Verification script
├── requirements.txt             # Dependencies
└── README.md                    # This file
```

---

## 🧪 Testing

### Phase 1 Verification

Run the comprehensive test suite:

```bash
python test_phase1.py
```

This verifies:
- ✅ Configuration loading
- ✅ Logging and tracing setup
- ✅ Database connections
- ✅ Agent instantiation
- ✅ Workflow construction
- ✅ Tool functions
- ✅ Vector store operations

### Unit Tests (Coming in Phase 6)

```bash
pytest tests/
pytest tests/ --cov=src --cov-report=html
```

---

## 💻 Usage

### Running a Test Query (Development)

```python
from src.graph.workflow import get_workflow
from src.graph.state import create_initial_state

# Get compiled workflow
workflow = get_workflow()

# Create initial state
initial_state = create_initial_state(
    user_input="What is my auto insurance premium?",
    policy_number="POL000004"
)

# Execute workflow
result = workflow.invoke(initial_state)

# Get final answer
print(result["final_answer"])
```

### API Usage (Production)

#### Starting the API Server

```bash
# Development mode with hot reload
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4

# Or run directly
python src/main.py
```

Visit the interactive API docs at [http://localhost:8000/docs](http://localhost:8000/docs)

#### Basic Chat Request

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is my auto insurance premium?",
    "context": {"policy_number": "POL000004"}
  }'
```

**Response:**
```json
{
  "session_id": "sess_a1b2c3d4e5f6g7h8",
  "message": "Your auto insurance premium is $1,200 per year...",
  "agent_used": "policy_agent",
  "requires_clarification": false,
  "conversation_complete": false,
  "metadata": {
    "iterations": 2,
    "processing_time_ms": 1234,
    "total_messages": 2,
    "total_iterations": 2
  }
}
```

#### Multi-Turn Conversation with Sessions

**First message (creates new session):**
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need help with my insurance"
  }'
```

**Follow-up message (continues conversation):**
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is my billing status?",
    "session_id": "sess_a1b2c3d4e5f6g7h8",
    "context": {"customer_id": "C001"}
  }'
```

#### Session Management

**List all active sessions:**
```bash
curl http://localhost:8000/api/v1/sessions?limit=10
```

**Get specific session:**
```bash
curl http://localhost:8000/api/v1/sessions/sess_a1b2c3d4e5f6g7h8
```

**Get session summary:**
```bash
curl http://localhost:8000/api/v1/sessions/sess_a1b2c3d4e5f6g7h8/summary
```

**Refresh session TTL:**
```bash
curl -X POST http://localhost:8000/api/v1/sessions/sess_a1b2c3d4e5f6g7h8/refresh
```

**Delete session:**
```bash
curl -X DELETE http://localhost:8000/api/v1/sessions/sess_a1b2c3d4e5f6g7h8
```

#### Health Check

```bash
# Comprehensive health check
curl http://localhost:8000/health

# Liveness probe (Kubernetes)
curl http://localhost:8000/health/live

# Readiness probe (Kubernetes)
curl http://localhost:8000/health/ready

# Prometheus metrics
curl http://localhost:8000/metrics
```

#### Python Client Example

```python
import requests

# Create session
response = requests.post(
    "http://localhost:8000/api/v1/chat",
    json={
        "message": "What's my policy coverage?",
        "context": {"policy_number": "POL000004"}
    }
)

data = response.json()
session_id = data["session_id"]
print(f"Assistant: {data['message']}")

# Continue conversation
response = requests.post(
    "http://localhost:8000/api/v1/chat",
    json={
        "message": "What about billing?",
        "session_id": session_id
    }
)

print(f"Assistant: {response.json()['message']}")
```

---

## 🏗️ Architecture

### Agent Flow

```
User Query
    ↓
Supervisor Agent (routes to specialist)
    ↓
┌───────────────────┬───────────────────┬────────────────┐
│  Policy Agent     │  Billing Agent    │  Claims Agent  │
│  (get details)    │  (get payments)   │  (get status)  │
└───────────────────┴───────────────────┴────────────────┘
                         │
                    General Help Agent (FAQ/RAG)
                         │
                    ↓ Back to Supervisor
    ↓ (if complete)
Final Answer Agent (clean summary)
    ↓
User receives response
```

### Data Layer

- **PostgreSQL**: Structured data (policies, billing, claims)
- **ChromaDB**: Vector embeddings for FAQ retrieval
- **Redis**: Session state and caching

### Observability

- **Logs**: Structured JSON logs to stdout
- **Traces**: Phoenix/OpenTelemetry spans for each agent
- **Metrics**: Prometheus format metrics at `/metrics`

---

## 📊 Monitoring

### Phoenix Tracing

Start Phoenix server:

```bash
python -m phoenix.server.main serve
# Visit http://localhost:6006
```

### Prometheus Metrics

Available metrics:
- `api_requests_total` - Total API requests
- `agent_invocations_total` - Agent invocations by name
- `agent_duration_seconds` - Agent execution time
- `llm_requests_total` - LLM API calls
- `llm_tokens_used_total` - Token consumption
- `db_queries_total` - Database queries

---

## 🔧 Configuration Options

### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | Insurance Agent API | Application name |
| `DEBUG` | false | Debug mode |
| `ENVIRONMENT` | development | Environment (dev/staging/prod) |

### OpenAI Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *required* | OpenAI API key |
| `OPENAI_MODEL` | gpt-4o-mini | Model to use |
| `OPENAI_TIMEOUT` | 60 | Request timeout (seconds) |

### Agent Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPERVISOR_MAX_ITERATIONS` | 3 | Max routing loops before escalation |
| `AGENT_TIMEOUT` | 30 | Agent execution timeout |

See [.env.example](.env.example) for full configuration options.

---

## 🐳 Deployment

### Docker (Phase 5)

```bash
# Build image
docker build -t insurance-agent .

# Run with docker-compose
docker-compose up -d
```

### Cloud Deployment

See [PRODUCTIONIZATION_PLAN.md](PRODUCTIONIZATION_PLAN.md) for deployment guides:
- AWS (App Runner, ECS)
- Azure (Container Apps)
- GCP (Cloud Run)
- Kubernetes

---

## 📈 Current Status

### ✅ Completed (Phase 1)

- [x] Project restructure from notebook
- [x] Configuration management
- [x] All 7 agents extracted and modularized
- [x] LangGraph workflow construction
- [x] Database connection layer
- [x] RAG/Vector store integration
- [x] Observability stack (logging, tracing, metrics)
- [x] Comprehensive test script
- [x] Documentation

### 🚧 In Progress

- [ ] **Phase 2: API Layer** - FastAPI REST API (Starting now)
- [ ] **Phase 3: Database Migration** - PostgreSQL + SQLAlchemy
- [ ] **Phase 4: Session Management** - Redis integration
- [ ] **Phase 5: Containerization** - Docker + Compose
- [ ] **Phase 6: Testing** - Unit and integration tests
- [ ] **Phase 7: CI/CD** - GitHub Actions pipeline

---

## 📚 Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed architecture documentation
- [PRODUCTIONIZATION_PLAN.md](PRODUCTIONIZATION_PLAN.md) - Full implementation plan
- `.env.example` - Configuration template
- `test_phase1.py` - Verification script with inline docs

---

## 🤝 Contributing

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for all functions
- Add tests for new features

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run linting
black src/ tests/
isort src/ tests/
flake8 src/ tests/

# Run tests
pytest tests/ --cov=src
```

---

## 🐛 Troubleshooting

### Common Issues

**1. "Module not found" errors**
```bash
# Add src to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

**2. Database not initialized**
```bash
# Run setup script (coming in Phase 3)
python scripts/setup_database.py
```

**3. ChromaDB collection empty**
```bash
# Load FAQ data (coming in Phase 3)
python scripts/setup_vector_store.py
```

**4. Phoenix connection failed**
```bash
# Disable tracing or start Phoenix server
PHOENIX_ENABLED=false python your_script.py
```

### Getting Help

1. Run diagnostic script: `python test_phase1.py`
2. Check logs: `cat insurance_agent.log`
3. Review traces: http://localhost:6006 (if Phoenix running)
4. See [ARCHITECTURE.md](ARCHITECTURE.md) for details

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- **LangGraph** - Agent orchestration framework
- **LangChain** - LLM application framework
- **FastAPI** - Modern Python web framework
- **ChromaDB** - Vector database for embeddings
- **Arize Phoenix** - LLM observability platform

---

## 📞 Contact

For questions or support, please refer to the documentation or open an issue.

---

**⭐ If you find this project useful, please star the repository!**
