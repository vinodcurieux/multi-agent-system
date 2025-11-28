# Multi-Agent Insurance System - Productionization Plan

## Requirements Summary
- **Cloud Target**: Any cloud with container support (multi-cloud compatible)
- **API Type**: REST API (synchronous request/response)
- **Authentication**: None (internal/demo use)
- **State Management**: Session-based with Redis cache
- **Scale**: Low traffic (< 100 requests/day, single instance with auto-scaling capability)
- **Database**: PostgreSQL (scalable, cloud-agnostic)
- **Cost Model**: Minimize costs using serverless containers (pay-per-use)

---

## Phase 1: Project Restructure (Convert Notebook → Production Code)

### 1.1 New Project Structure
```
multi-agent-system/
├── src/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry point
│   ├── config.py                  # Configuration management (Pydantic Settings)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py           # Chat endpoints
│   │   │   ├── health.py         # Health check endpoints
│   │   │   └── sessions.py       # Session management
│   │   ├── models.py             # Pydantic request/response models
│   │   └── dependencies.py       # FastAPI dependencies
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py               # Base agent class
│   │   ├── supervisor.py         # Supervisor agent
│   │   ├── policy_agent.py       # Policy specialist
│   │   ├── billing_agent.py      # Billing specialist
│   │   ├── claims_agent.py       # Claims specialist
│   │   ├── general_help_agent.py # General help + RAG
│   │   ├── human_escalation.py   # Escalation handler
│   │   └── final_answer.py       # Final answer agent
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── policy_tools.py       # Policy-related tools
│   │   ├── billing_tools.py      # Billing-related tools
│   │   ├── claims_tools.py       # Claims-related tools
│   │   └── user_interaction.py   # User interaction tools
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py              # GraphState definition
│   │   ├── workflow.py           # LangGraph workflow builder
│   │   └── routing.py            # Routing logic
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py             # SQLAlchemy ORM models
│   │   ├── connection.py         # Database connection management
│   │   ├── repositories.py       # Data access layer
│   │   └── migrations/           # Alembic migrations
│   │       ├── alembic.ini
│   │       ├── env.py
│   │       └── versions/
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── vector_store.py       # ChromaDB integration
│   │   ├── embeddings.py         # Embedding management
│   │   └── retrieval.py          # Retrieval logic
│   ├── session/
│   │   ├── __init__.py
│   │   ├── manager.py            # Session manager with Redis
│   │   └── models.py             # Session state models
│   ├── observability/
│   │   ├── __init__.py
│   │   ├── tracing.py            # Phoenix tracing decorators
│   │   ├── logging_config.py     # Structured logging
│   │   └── metrics.py            # Metrics collection
│   └── utils/
│       ├── __init__.py
│       ├── llm_client.py         # OpenAI client wrapper
│       └── helpers.py            # Utility functions
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures
│   ├── unit/
│   │   ├── test_agents.py
│   │   ├── test_tools.py
│   │   └── test_routing.py
│   ├── integration/
│   │   ├── test_api.py
│   │   ├── test_workflow.py
│   │   └── test_database.py
│   └── fixtures/
│       ├── sample_data.py
│       └── mock_responses.py
├── scripts/
│   ├── setup_database.py         # Database initialization
│   ├── setup_vector_store.py     # ChromaDB initialization
│   ├── migrate_from_sqlite.py    # SQLite → PostgreSQL migration
│   └── seed_data.py              # Load synthetic data
├── deployment/
│   ├── docker/
│   │   ├── Dockerfile
│   │   ├── Dockerfile.dev
│   │   └── docker-compose.yml
│   ├── kubernetes/               # Optional K8s manifests
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── configmap.yaml
│   ├── terraform/                # IaC for cloud deployment
│   │   ├── aws/
│   │   ├── azure/
│   │   └── gcp/
│   └── cloud/
│       ├── aws-app-runner.yaml
│       ├── azure-container-app.yaml
│       └── gcp-cloud-run.yaml
├── .github/
│   └── workflows/
│       ├── ci.yml                # CI/CD pipeline
│       ├── build.yml
│       └── deploy.yml
├── .env.example                  # Environment variable template
├── .dockerignore
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Development dependencies
├── pyproject.toml                # Project metadata
├── README.md
└── PRODUCTIONIZATION_PLAN.md     # This file
```

### 1.2 Extract Core Components from Notebook
- **Agents**: Extract each agent function into its own class/module
- **Tools**: Separate tool functions into dedicated modules
- **Prompts**: Move prompts to configuration or templates
- **State**: Formalize GraphState with proper typing
- **Workflow**: Extract LangGraph setup into reusable module

---

## Phase 2: FastAPI Application Layer

### 2.1 API Endpoints

#### **POST /api/v1/chat**
Start or continue a conversation
```json
Request:
{
  "session_id": "optional-session-id",
  "message": "What is my auto insurance premium?",
  "context": {
    "customer_id": "CUST00001",
    "policy_number": "POL000004"
  }
}

Response:
{
  "session_id": "generated-or-provided-id",
  "message": "Your auto insurance premium is $197.88.",
  "agent_used": "billing_agent",
  "requires_clarification": false,
  "conversation_complete": true,
  "metadata": {
    "tokens_used": 1234,
    "processing_time_ms": 1500
  }
}
```

#### **GET /api/v1/sessions/{session_id}**
Retrieve conversation history
```json
Response:
{
  "session_id": "abc-123",
  "created_at": "2025-11-28T10:00:00Z",
  "last_activity": "2025-11-28T10:05:00Z",
  "messages": [
    {"role": "user", "content": "What is my premium?"},
    {"role": "assistant", "content": "Your premium is $197.88"}
  ],
  "state": {
    "policy_number": "POL000004",
    "customer_id": "CUST00001"
  }
}
```

#### **DELETE /api/v1/sessions/{session_id}**
Clear conversation session

#### **GET /health**
Health check endpoint
```json
Response:
{
  "status": "healthy",
  "services": {
    "database": "connected",
    "redis": "connected",
    "vector_store": "connected",
    "openai": "available"
  },
  "version": "1.0.0"
}
```

#### **GET /metrics**
Prometheus-format metrics (optional)

### 2.2 Request/Response Models (Pydantic)
```python
# src/api/models.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=2000)
    context: Optional[Dict[str, str]] = {}

class ChatResponse(BaseModel):
    session_id: str
    message: str
    agent_used: str
    requires_clarification: bool
    conversation_complete: bool
    metadata: Dict[str, Any]

class HealthResponse(BaseModel):
    status: str
    services: Dict[str, str]
    version: str
```

---

## Phase 3: Database Migration (SQLite → PostgreSQL)

### 3.1 SQLAlchemy ORM Models
```python
# src/database/models.py
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Customer(Base):
    __tablename__ = 'customers'
    customer_id = Column(String(20), primary_key=True)
    first_name = Column(String(50))
    last_name = Column(String(50))
    email = Column(String(100))
    # ... other fields

class Policy(Base):
    __tablename__ = 'policies'
    policy_number = Column(String(20), primary_key=True)
    customer_id = Column(String(20), ForeignKey('customers.customer_id'))
    # ... other fields
```

### 3.2 Connection Management
```python
# src/database/connection.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

class DatabaseManager:
    def __init__(self, database_url: str):
        self.engine = create_engine(
            database_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True  # Health check before use
        )
        self.SessionLocal = sessionmaker(bind=self.engine)

    @contextmanager
    def get_session(self):
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
```

### 3.3 Alembic Migrations
- Initialize Alembic for schema version control
- Create migration scripts for all tables
- Support both PostgreSQL and MySQL dialects

### 3.4 Migration Script
```python
# scripts/migrate_from_sqlite.py
# Convert existing SQLite data to PostgreSQL
# Handle data transformation and validation
```

---

## Phase 4: Session Management with Redis

### 4.1 Session Manager
```python
# src/session/manager.py
import redis
import json
from typing import Optional, Dict, Any
from datetime import timedelta

class SessionManager:
    def __init__(self, redis_url: str, ttl_seconds: int = 3600):
        self.redis_client = redis.from_url(redis_url)
        self.ttl = ttl_seconds

    def create_session(self, session_id: str, initial_state: Dict[str, Any]):
        """Create new session with initial state"""
        self.redis_client.setex(
            f"session:{session_id}",
            timedelta(seconds=self.ttl),
            json.dumps(initial_state)
        )

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session state"""
        data = self.redis_client.get(f"session:{session_id}")
        return json.loads(data) if data else None

    def update_session(self, session_id: str, state: Dict[str, Any]):
        """Update session and refresh TTL"""
        self.create_session(session_id, state)

    def delete_session(self, session_id: str):
        """Delete session"""
        self.redis_client.delete(f"session:{session_id}")
```

### 4.2 Session State Schema
```python
# src/session/models.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class ConversationMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime

class SessionState(BaseModel):
    session_id: str
    customer_id: Optional[str] = None
    policy_number: Optional[str] = None
    claim_id: Optional[str] = None
    messages: List[ConversationMessage] = []
    graph_state: Dict[str, Any] = {}
    created_at: datetime
    last_activity: datetime
```

---

## Phase 5: Configuration Management

### 5.1 Pydantic Settings
```python
# src/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Insurance Agent API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 5

    # Redis
    REDIS_URL: str
    SESSION_TTL_SECONDS: int = 3600

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "insurance_FAQ_collection"

    # Phoenix Tracing
    PHOENIX_COLLECTOR_ENDPOINT: Optional[str] = None
    PHOENIX_PROJECT_NAME: str = "multi-agent-system-prod"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: list = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### 5.2 Environment Variables (.env.example)
```bash
# Application
APP_NAME="Insurance Agent API"
APP_VERSION="1.0.0"
DEBUG=false

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Database (PostgreSQL)
DATABASE_URL=postgresql://user:password@localhost:5432/insurance_db

# Redis
REDIS_URL=redis://localhost:6379/0
SESSION_TTL_SECONDS=3600

# ChromaDB
CHROMA_PERSIST_DIR=/app/data/chroma_db
CHROMA_COLLECTION_NAME=insurance_FAQ_collection

# Phoenix (Optional)
PHOENIX_COLLECTOR_ENDPOINT=http://phoenix:6006/v1/traces
PHOENIX_PROJECT_NAME=insurance-agent-prod
```

---

## Phase 6: Containerization

### 6.1 Multi-Stage Dockerfile
```dockerfile
# deployment/docker/Dockerfile
# Stage 1: Base dependencies
FROM python:3.11-slim as base
WORKDIR /app
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Dependencies
FROM base as dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Application
FROM dependencies as application
COPY src/ /app/src/
COPY scripts/ /app/scripts/
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Stage 4: Production (optimized)
FROM python:3.11-slim as production
WORKDIR /app
RUN apt-get update && apt-get install -y libpq-dev && rm -rf /var/lib/apt/lists/*
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=application /app /app
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

### 6.2 Docker Compose (Local Development)
```yaml
# deployment/docker/docker-compose.yml
version: '3.8'

services:
  api:
    build:
      context: ../..
      dockerfile: deployment/docker/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://insurance:password@postgres:5432/insurance_db
      - REDIS_URL=redis://redis:6379/0
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - postgres
      - redis
    volumes:
      - chroma-data:/app/data/chroma_db
    networks:
      - insurance-network

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: insurance
      POSTGRES_PASSWORD: password
      POSTGRES_DB: insurance_db
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - insurance-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - insurance-network

  phoenix:
    image: arizephoenix/phoenix:latest
    ports:
      - "6006:6006"
    networks:
      - insurance-network

volumes:
  postgres-data:
  redis-data:
  chroma-data:

networks:
  insurance-network:
    driver: bridge
```

---

## Phase 7: Cloud Deployment Configurations

### 7.1 AWS App Runner
```yaml
# deployment/cloud/aws-app-runner.yaml
version: 1.0
runtime: python3
build:
  commands:
    build:
      - pip install -r requirements.txt
run:
  runtime-version: 3.11
  command: uvicorn src.main:app --host 0.0.0.0 --port 8000
  network:
    port: 8000
  env:
    - name: DATABASE_URL
      value: ${DATABASE_URL}
    - name: REDIS_URL
      value: ${REDIS_URL}
```

**Additional AWS Setup:**
- RDS PostgreSQL (db.t3.micro for cost optimization)
- ElastiCache Redis (cache.t3.micro)
- App Runner service with auto-scaling (min: 1, max: 3)
- Secrets Manager for API keys

### 7.2 Azure Container Apps
```yaml
# deployment/cloud/azure-container-app.yaml
apiVersion: 2022-03-01
name: insurance-agent
location: eastus
properties:
  managedEnvironmentId: /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.App/managedEnvironments/{env}
  configuration:
    ingress:
      external: true
      targetPort: 8000
    secrets:
      - name: openai-key
        value: ${OPENAI_API_KEY}
  template:
    containers:
      - name: api
        image: {registry}/insurance-agent:latest
        resources:
          cpu: 0.5
          memory: 1Gi
        env:
          - name: DATABASE_URL
            value: postgresql://...
          - name: REDIS_URL
            value: redis://...
    scale:
      minReplicas: 1
      maxReplicas: 3
```

**Additional Azure Setup:**
- Azure Database for PostgreSQL (Flexible Server - Burstable B1ms)
- Azure Cache for Redis (Basic C0)
- Container Registry for images
- Key Vault for secrets

### 7.3 GCP Cloud Run
```yaml
# deployment/cloud/gcp-cloud-run.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: insurance-agent
spec:
  template:
    spec:
      containerConcurrency: 80
      containers:
        - image: gcr.io/{project}/insurance-agent:latest
          ports:
            - containerPort: 8000
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: database-url
                  key: latest
            - name: REDIS_URL
              valueFrom:
                secretKeyRef:
                  name: redis-url
                  key: latest
          resources:
            limits:
              cpu: 1000m
              memory: 512Mi
  traffic:
    - percent: 100
      latestRevision: true
```

**Additional GCP Setup:**
- Cloud SQL PostgreSQL (db-f1-micro)
- Memorystore Redis (Basic 1GB)
- Artifact Registry for container images
- Secret Manager for API keys

### 7.4 Generic Kubernetes (Any Cloud)
```yaml
# deployment/kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: insurance-agent
spec:
  replicas: 1
  selector:
    matchLabels:
      app: insurance-agent
  template:
    metadata:
      labels:
        app: insurance-agent
    spec:
      containers:
      - name: api
        image: {registry}/insurance-agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 500m
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

---

## Phase 8: Observability & Monitoring

### 8.1 Structured Logging
```python
# src/observability/logging_config.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

def setup_logging(level=logging.INFO):
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.basicConfig(level=level, handlers=[handler])
```

### 8.2 Keep Phoenix Tracing
- Maintain `@trace_agent` decorator
- Add FastAPI middleware for request tracing
- Trace database queries and Redis operations

### 8.3 Metrics Collection
```python
# src/observability/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
request_count = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('api_request_duration_seconds', 'Request duration')

# Agent metrics
agent_invocations = Counter('agent_invocations_total', 'Agent invocations', ['agent_name'])
agent_errors = Counter('agent_errors_total', 'Agent errors', ['agent_name'])

# Database metrics
db_query_duration = Histogram('db_query_duration_seconds', 'Database query duration')
active_sessions = Gauge('active_sessions', 'Number of active sessions')
```

### 8.4 Health Checks
```python
# src/api/routes/health.py
from fastapi import APIRouter
from src.config import settings

router = APIRouter()

@router.get("/health")
async def health_check():
    # Check database connection
    # Check Redis connection
    # Check ChromaDB availability
    # Check OpenAI API
    return {
        "status": "healthy",
        "services": {...},
        "version": settings.APP_VERSION
    }
```

---

## Phase 9: Testing Strategy

### 9.1 Unit Tests
```python
# tests/unit/test_agents.py
import pytest
from src.agents.billing_agent import BillingAgent

def test_billing_agent_extracts_policy_number(mock_state):
    agent = BillingAgent()
    result = agent.process(mock_state)
    assert result["policy_number"] == "POL000004"
```

### 9.2 Integration Tests
```python
# tests/integration/test_api.py
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_chat_endpoint():
    response = client.post("/api/v1/chat", json={
        "message": "What is my premium?",
        "context": {"policy_number": "POL000004"}
    })
    assert response.status_code == 200
    assert "premium" in response.json()["message"].lower()
```

### 9.3 Test Fixtures
```python
# tests/conftest.py
import pytest
from src.database.connection import DatabaseManager

@pytest.fixture
def test_db():
    # Create test database
    # Seed with test data
    yield db
    # Cleanup
```

---

## Phase 10: CI/CD Pipeline

### 10.1 GitHub Actions
```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
      redis:
        image: redis:7
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt -r requirements-dev.txt
      - name: Run tests
        run: pytest tests/ --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: docker build -f deployment/docker/Dockerfile -t insurance-agent:${{ github.sha }} .
      - name: Push to registry
        run: |
          echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
          docker push insurance-agent:${{ github.sha }}
```

---

## Implementation Timeline

### **Week 1-2: Project Restructure**
- [ ] Create new project structure
- [ ] Extract agents from notebook into modules
- [ ] Extract tools into separate files
- [ ] Create GraphState and workflow modules
- [ ] Set up configuration management

### **Week 3: API Layer**
- [ ] Implement FastAPI application
- [ ] Create chat endpoints
- [ ] Create session management endpoints
- [ ] Add health check endpoint
- [ ] Implement request/response models

### **Week 4: Database Migration**
- [ ] Create SQLAlchemy ORM models
- [ ] Set up Alembic migrations
- [ ] Write migration script from SQLite
- [ ] Implement database repositories
- [ ] Set up connection pooling

### **Week 5: Session & State Management**
- [ ] Implement Redis session manager
- [ ] Create session state models
- [ ] Integrate with FastAPI middleware
- [ ] Add session cleanup logic

### **Week 6: Containerization & Deployment**
- [ ] Create Dockerfile (multi-stage)
- [ ] Create docker-compose.yml for local dev
- [ ] Write deployment configs for cloud providers
- [ ] Test local container deployment
- [ ] Document deployment process

### **Week 7: Testing & Observability**
- [ ] Write unit tests for agents and tools
- [ ] Write integration tests for API
- [ ] Set up structured logging
- [ ] Configure Phoenix tracing
- [ ] Add metrics collection

### **Week 8: CI/CD & Documentation**
- [ ] Set up GitHub Actions pipeline
- [ ] Create deployment automation
- [ ] Write API documentation
- [ ] Create deployment guides
- [ ] Final testing and optimization

---

## Cost Optimization Strategies

### 1. **Serverless Containers**
- Use Cloud Run / Azure Container Apps / AWS App Runner
- Scale to zero when no traffic
- Pay only for actual request processing time

### 2. **Database Optimization**
- Use smallest instance tier (db.t3.micro, B1ms, db-f1-micro)
- Consider Aurora Serverless v2 (AWS) for variable workload
- Enable connection pooling to reduce overhead

### 3. **Redis/Cache**
- Use smallest Redis instance (cache.t3.micro, C0, 1GB)
- Set aggressive TTL on sessions (1 hour)
- Consider cloud provider's managed cache

### 4. **Storage**
- Use cloud storage for ChromaDB persistence (S3, Blob, GCS)
- Enable lifecycle policies to archive old data
- Compress vector embeddings

### 5. **API Optimization**
- Implement response caching for common queries
- Use CDN for static content
- Batch database queries where possible

### 6. **Monitoring**
- Use free tiers (CloudWatch, Azure Monitor, GCP Logging)
- Set budget alerts
- Monitor cold start times and optimize

**Estimated Monthly Cost (Low Traffic):**
- Container platform: $5-15 (with scale-to-zero)
- PostgreSQL: $10-20 (smallest instance)
- Redis: $10-15 (smallest instance)
- Storage: $1-5
- **Total: ~$25-55/month**

---

## Deployment Options Comparison

| Feature | AWS App Runner | Azure Container Apps | GCP Cloud Run |
|---------|---------------|---------------------|---------------|
| Pricing | Per-request + memory | Per-request + memory | Per-request + CPU/memory |
| Scale to Zero | ✅ Yes | ✅ Yes | ✅ Yes |
| Cold Start | ~2-3s | ~2-3s | ~1-2s |
| Min Cost/month | ~$5 | ~$7 | ~$5 |
| Auto-scaling | ✅ Built-in | ✅ Built-in | ✅ Built-in |
| Custom domains | ✅ Yes | ✅ Yes | ✅ Yes |
| Managed DB | RDS | Azure SQL | Cloud SQL |
| Managed Cache | ElastiCache | Azure Cache | Memorystore |

---

## Next Steps

1. **Review this plan** - Confirm approach and priorities
2. **Set up development environment** - Install dependencies, set up local services
3. **Start Phase 1** - Begin project restructure
4. **Incremental development** - Build and test each phase
5. **Deploy to staging** - Test in cloud environment
6. **Production deployment** - Launch to production

---

## Success Metrics

- ✅ API response time < 3 seconds (p95)
- ✅ 99.9% uptime
- ✅ Zero security vulnerabilities
- ✅ Unit test coverage > 80%
- ✅ Monthly cost < $100
- ✅ Deploy time < 10 minutes
- ✅ Easy to extend with new agents

---

**Questions or modifications needed? Let's discuss before starting implementation!**
