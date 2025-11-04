# SINAS - Semantic Intelligence & Automation System

**A comprehensive AI-powered platform combining LLM chat, semantic data layer, Python function execution, and workflow automation.**

SINAS is a self-hosted platform that integrates:
- 🤖 **AI Chat & Assistants** - Multi-provider LLM integration (OpenAI, Ollama, local models, private cloud)
- 📊 **Ontology & Semantic Layer** - Define, manage, and query your data with a semantic layer
- ⚡ **Function Execution** - Python function runtime with automatic tracking
- 🔗 **MCP Integration** - Model Context Protocol tools for extended capabilities
- 🌐 **Webhooks & Scheduling** - Event-driven and time-based automation
- 🔐 **Group-Based Access Control** - Fine-grained permissions system

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Ontology System](#ontology-system)
- [AI Chat & Assistants](#ai-chat--assistants)
- [Function Execution](#function-execution)
- [API Documentation](#api-documentation)
- [Development](#development)

---

## Features

### 🧠 AI & Assistants
- **Multi-Provider LLM Support**: OpenAI, Ollama, local models, private cloud endpoints
- **Conversational AI**: Full chat management with conversation history
- **Custom Assistants**: Create specialized AI assistants with system prompts
- **Memory System**: Context persistence across conversations
- **MCP Tools**: Extend AI capabilities with Model Context Protocol

### 📊 Ontology & Semantic Layer
- **Define Concepts**: Model your domain with concepts, properties, and relationships
- **Three Data Modes**:
  1. **External Sources**: Query external databases (Postgres, Snowflake, BigQuery)
  2. **Synced Data**: Periodically sync external data to local tables
  3. **Self-Managed**: Fully managed data with auto-generated CRUD APIs
- **Query Compiler**: Declarative endpoint configuration compiled to SQL
- **Schema Management**: Dynamic table creation with automatic migrations

### ⚡ Automation & Workflows
- **Python Functions**: Write functions that call each other automatically
- **Webhooks**: HTTP endpoints that trigger function execution
- **Scheduling**: Cron-based job scheduling with APScheduler
- **Execution Tracking**: Complete audit trail of all executions
- **Package Management**: Install Python packages for functions

### 🔐 Security & Access Control
- **OTP Authentication**: Email-based one-time password login
- **JWT & API Keys**: Flexible authentication options
- **Group-Based Permissions**: Fine-grained access control
- **Encrypted Credentials**: Database connection strings encrypted at rest

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         SINAS API                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   AI Chat    │  │  Ontology    │  │  Functions   │     │
│  │              │  │              │  │              │     │
│  │ • Chats      │  │ • Concepts   │  │ • Execution  │     │
│  │ • Messages   │  │ • Properties │  │ • Webhooks   │     │
│  │ • Assistants │  │ • Queries    │  │ • Schedules  │     │
│  │ • Memories   │  │ • Endpoints  │  │ • Tracking   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                   Core Services                              │
│                                                              │
│  • Authentication & Authorization                            │
│  • Query Compiler & Executor                                 │
│  • Schema Manager                                            │
│  • Function Execution Engine                                 │
│  • APScheduler (Cron Jobs)                                   │
│  • Redis Logger                                              │
│  • MCP Client                                                │
└─────────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
    PostgreSQL              Redis            External DBs
```

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- (Optional) Python 3.11+ and Poetry for local development

### Docker Setup (Recommended)

1. **Clone the repository:**
```bash
git clone <repository-url>
cd SINAS
```

2. **Set up environment variables:**
```bash
cp .env.example .env
```

3. **Configure your `.env` file:**

Required settings:
```bash
# Security - REQUIRED
SECRET_KEY=your-secret-key-change-in-production
ENCRYPTION_KEY=your-fernet-encryption-key

# Database - choose one option:
# Option 1: Use docker-compose postgres (recommended for local dev)
POSTGRES_PASSWORD=your-secure-postgres-password

# Option 2: Use external database (production)
# DATABASE_URL=postgresql://user:password@host:5432/sinas

# SMTP (for OTP emails) - REQUIRED
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_DOMAIN=yourdomain.com

# Admin user (optional but recommended)
SUPERADMIN_EMAIL=admin@yourdomain.com
```

4. **Generate encryption key:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

5. **Start the application:**

**Option A: With docker-compose postgres (local development):**
```bash
docker-compose --profile local-db up
```

**Option B: With external database (production):**
```bash
docker-compose up
```

6. **Access the API:**
- API: http://localhost:8000
- Interactive Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

7. **Login as admin:**

If you configured `SUPERADMIN_EMAIL`, that user is automatically created in the Admins group with full system access. Request an OTP:

```bash
curl -X POST http://localhost:8000/api/v1/auth/request-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@yourdomain.com"}'
```

### Local Development Setup (Without Docker)

1. **Install Poetry:**
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. **Install dependencies:**
```bash
poetry install
```

3. **Set up PostgreSQL and Redis:**
```bash
# Install and start PostgreSQL
createdb sinas

# Install and start Redis
redis-server
```

4. **Configure `.env`:**
```bash
DATABASE_URL=postgresql://postgres:password@localhost:5432/sinas
# Redis will use default localhost:6379
```

5. **Run migrations:**
```bash
poetry run alembic upgrade head
```

6. **Start the server:**
```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Configuration

### Required Environment Variables

```bash
# Security
SECRET_KEY=your-secret-key-change-in-production
ENCRYPTION_KEY=your-fernet-encryption-key

# Database - Choose one:
# Option 1: Docker-compose postgres (local development)
POSTGRES_PASSWORD=your-secure-postgres-password

# Option 2: External database (production)
# DATABASE_URL=postgresql://user:password@host:5432/sinas

# SMTP (for OTP emails)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_DOMAIN=yourdomain.com
```

### Optional Environment Variables

```bash
# Admin user (created automatically on startup)
SUPERADMIN_EMAIL=admin@yourdomain.com

# Redis (only override if not using docker-compose)
# REDIS_URL=redis://localhost:6379/0
```

### LLM Configuration

```bash
# LLM Providers
# OpenAI
OPENAI_API_KEY=sk-...
DEFAULT_LLM_PROVIDER=openai

# Ollama (local models)
LOCAL_LLM_ENDPOINT=http://localhost:11434
DEFAULT_LLM_PROVIDER=ollama

# Private cloud deployment
PRIVATE_CLOUD_ENDPOINT=https://your-llm-endpoint.com
PRIVATE_CLOUD_API_KEY=your-api-key

# Function Execution
FUNCTION_TIMEOUT=300
MAX_FUNCTION_MEMORY=512
ALLOW_PACKAGE_INSTALLATION=true
```

See `.env.example` for complete configuration options.

---

## Authentication & Groups

SINAS uses a group-based permission system with OTP authentication.

### Default Groups

- **GuestUsers**: Minimal permissions, read-only access to own data
- **Users**: Standard users with access to chats, functions, ontology data (`:own` scope)
- **Admins**: Full system access (`:all` scope), automatically created on startup if configured

### Admin Setup

Set `SUPERADMIN_EMAIL` in `.env` to automatically create an admin user on startup:

```bash
SUPERADMIN_EMAIL=admin@yourdomain.com
```

**Behavior:**
- Creates user with specified email if Admins group is empty
- Adds user to "Admins" group with full system access (`sinas.*:all`)
- Only creates user if Admins group has no members (prevents auto-creation after manual setup)

### Logging In

```bash
# 1. Request OTP
POST /api/v1/auth/request-otp
{
  "email": "admin@yourdomain.com"
}

# 2. Check email for OTP code

# 3. Verify OTP
POST /api/v1/auth/verify-otp
{
  "session_id": "...",
  "otp_code": "123456"
}

# Returns JWT token for API access
```

---

## Ontology System

The ontology system provides a semantic layer over your data sources.

### Core Concepts

- **DataSource**: External database connection (Postgres, Snowflake, BigQuery)
- **Concept**: A domain entity (e.g., Customer, Order, Product)
- **Property**: Attributes of a concept (e.g., email, name, price)
- **Relationship**: Connections between concepts
- **ConceptQuery**: SQL query that materializes a concept
- **Endpoint**: Configurable API endpoint for querying data

### Three Data Management Modes

#### 1. External Data Sources (Query in Place)

Query external databases without copying data:

```bash
# Create data source
POST /api/v1/ontology/datasources
{
  "group_id": "...",
  "name": "Production DB",
  "type": "postgres",
  "conn_string": "postgresql://user:pass@host/db"
}

# Define concept
POST /api/v1/ontology/concepts
{
  "group_id": "...",
  "namespace": "commerce",
  "name": "customer",
  "is_self_managed": false
}

# Add properties
POST /api/v1/ontology/properties
{
  "concept_id": "...",
  "name": "email",
  "data_type": "STRING",
  "is_identifier": true
}

# Define query
POST /api/v1/ontology/queries
{
  "concept_id": "...",
  "data_source_id": "...",
  "sql_text": "SELECT id, email, name FROM customers"
}

# Create endpoint
POST /api/v1/ontology/endpoints
{
  "subject_concept_id": "...",
  "name": "customers",
  "route": "/data/customers"
}

# Query data
GET /api/v1/ontology/execute/{endpoint_id}?email=user@example.com
```

#### 2. Synced Data (Periodic Sync)

Sync external data to local tables on a schedule:

```bash
# Enable sync when creating query
POST /api/v1/ontology/queries
{
  "concept_id": "...",
  "data_source_id": "...",
  "sql_text": "SELECT * FROM customers",
  "sync_enabled": true,
  "sync_schedule": "0 * * * *"  # Every hour (cron format)
}

# Manual sync trigger
POST /api/v1/ontology/sync/{concept_id}/trigger

# Check sync status
GET /api/v1/ontology/sync/{concept_id}/status
```

Data is synced to table: `ontology_sync_{namespace}_{concept_name}`

#### 3. Self-Managed Data (Full CRUD)

Data managed entirely within SINAS with auto-generated APIs:

```bash
# Create self-managed concept
POST /api/v1/ontology/concepts
{
  "group_id": "...",
  "namespace": "crm",
  "name": "contact",
  "is_self_managed": true
}

# Add properties (creates columns automatically)
POST /api/v1/ontology/properties
{
  "concept_id": "...",
  "name": "email",
  "data_type": "STRING",
  "is_identifier": true
}

# Auto-generated CRUD endpoints:
POST   /api/v1/ontology/data/crm/contact
GET    /api/v1/ontology/data/crm/contact
GET    /api/v1/ontology/data/crm/contact/{id}
PUT    /api/v1/ontology/data/crm/contact/{id}
DELETE /api/v1/ontology/data/crm/contact/{id}
```

Data stored in table: `ontology_{namespace}_{concept_name}`

### Schema Management

Self-managed concepts support automatic schema migration:

- **Add Property**: `ALTER TABLE ADD COLUMN` automatically
- **Change Property Type**: Old column renamed to `{name}_{timestamp}`, new column created
- **Delete Property**: Column renamed to `deleted_{name}_{timestamp}`

Old columns are preserved for manual cleanup.

---

## AI Chat & Assistants

### Authentication

```bash
# Request OTP
POST /api/v1/auth/request-otp
{
  "email": "user@example.com"
}

# Verify OTP
POST /api/v1/auth/verify-otp
{
  "session_id": "...",
  "otp_code": "123456"
}
# Returns JWT token
```

### Chat Management

```bash
# Create chat
POST /api/v1/chats
{
  "title": "My Conversation"
}

# Send message
POST /api/v1/chats/{chat_id}/messages
{
  "content": "What is the capital of France?",
  "provider": "openai",
  "model": "gpt-4"
}

# List messages
GET /api/v1/chats/{chat_id}/messages
```

### Assistants

```bash
# Create assistant (with OpenAI)
POST /api/v1/assistants
{
  "name": "Code Helper",
  "system_prompt": "You are an expert Python developer...",
  "provider": "openai",
  "model": "gpt-4"
}

# Or with Ollama
POST /api/v1/assistants
{
  "name": "Local Code Helper",
  "system_prompt": "You are an expert Python developer...",
  "provider": "ollama",
  "model": "codellama"
}

# Use assistant in chat
POST /api/v1/chats/{chat_id}/messages
{
  "content": "How do I use async/await?",
  "assistant_id": "..."
}
```

---

## Function Execution

### Creating Functions

```bash
POST /api/v1/functions
{
  "name": "process_order",
  "code": "def process_order(input):\n    return {'status': 'processed', 'order_id': input['id']}",
  "input_schema": {
    "type": "object",
    "properties": {
      "id": {"type": "string"}
    }
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "status": {"type": "string"},
      "order_id": {"type": "string"}
    }
  }
}
```

### Webhooks

```bash
# Create webhook
POST /api/v1/webhooks
{
  "path": "process-order",
  "function_name": "process_order",
  "http_method": "POST"
}

# Trigger webhook
POST /api/v1/h/process-order
{
  "id": "ORD-123"
}
```

### Scheduling

```bash
# Create scheduled job
POST /api/v1/schedules
{
  "name": "daily-report",
  "function_name": "generate_report",
  "cron_expression": "0 9 * * *",  # 9 AM daily
  "input_data": {"type": "daily"}
}
```

---

## API Documentation

Once running, full API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Main API Endpoints

**Authentication:**
- `POST /api/v1/auth/request-otp` - Request OTP code
- `POST /api/v1/auth/verify-otp` - Verify OTP and get JWT

**Chats:**
- `POST /api/v1/chats` - Create chat
- `GET /api/v1/chats` - List chats
- `POST /api/v1/chats/{id}/messages` - Send message

**Ontology:**
- `/api/v1/ontology/datasources` - Data source management
- `/api/v1/ontology/concepts` - Concept definitions
- `/api/v1/ontology/properties` - Property management
- `/api/v1/ontology/queries` - Query definitions
- `/api/v1/ontology/execute/{id}` - Execute queries
- `/api/v1/ontology/data/{ns}/{concept}` - Self-managed CRUD

**Functions:**
- `POST /api/v1/functions` - Create function
- `GET /api/v1/functions` - List functions
- `POST /api/v1/webhooks` - Create webhook
- `POST /api/v1/schedules` - Schedule function

---

## Development

### Project Structure

```
SINAS/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/          # Auth, chats, assistants, MCP
│   │       ├── ontology_*.py       # Ontology endpoints
│   │       └── __init__.py
│   ├── core/
│   │   ├── auth.py                 # Authentication & permissions
│   │   ├── config.py               # Configuration
│   │   ├── database.py             # Database connection
│   │   ├── encryption.py           # Encryption service
│   │   └── permissions.py          # Permission system
│   ├── models/
│   │   ├── ontology.py             # Ontology models
│   │   ├── user.py                 # User & group models
│   │   ├── chat.py                 # Chat models
│   │   └── ...
│   ├── schemas/
│   │   └── ontology.py             # Pydantic schemas
│   ├── services/
│   │   ├── ontology/               # Ontology services
│   │   │   ├── query_compiler.py
│   │   │   ├── query_executor.py
│   │   │   ├── schema_manager.py
│   │   │   ├── sync_service.py
│   │   │   └── query_validator.py
│   │   ├── execution_engine.py     # Function execution
│   │   ├── scheduler.py            # APScheduler
│   │   └── mcp/                    # MCP integration
│   └── main.py                     # FastAPI app
├── alembic/                        # Database migrations
├── pyproject.toml                  # Dependencies
└── .env.example                    # Configuration template
```

### Running Tests

```bash
poetry run pytest
```

### Code Quality

```bash
# Format
poetry run black .

# Lint
poetry run ruff check .

# Type check
poetry run mypy .
```

---

## Docker Deployment

```bash
# Build
docker build -t sinas .

# Run
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host/db \
  -e REDIS_URL=redis://host:6379/0 \
  -e SECRET_KEY=your-secret-key \
  -e ENCRYPTION_KEY=your-encryption-key \
  sinas
```

---

## Security Considerations

- ✅ Connection strings encrypted at rest (Fernet encryption)
- ✅ SQL queries validated (no DROP, DELETE, injection patterns)
- ✅ OTP-based authentication
- ✅ JWT token expiration
- ✅ Group-based permissions
- ✅ API key management
- ✅ HTTPS recommended for production

---

## License

GNU GPL v3.0 License

---

## Support

For issues, questions, or feature requests, please open an issue on GitHub.
