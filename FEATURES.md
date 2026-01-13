# SINAS Features Documentation

Comprehensive guide to all features available in the SINAS (Semantic Intelligence & Natural Automation System) API.

---

## Table of Contents

1. [Authentication & Authorization](#1-authentication--authorization)
2. [User & Group Management](#2-user--group-management)
3. [AI Chat & Assistants](#3-ai-chat--assistants)
4. [Function Execution System](#4-function-execution-system)
5. [Webhook System](#5-webhook-system)
6. [Scheduling System](#6-scheduling-system)
7. [Ontology System](#7-ontology-system)
8. [Document Management](#8-document-management)
9. [Tagging System](#9-tagging-system)
10. [Email Management](#10-email-management)
11. [Context Store](#11-context-store)
12. [MCP Integration](#12-mcp-integration)
13. [Request Logging & Analytics](#13-request-logging--analytics)

---

## 1. Authentication & Authorization

### Overview
SINAS uses a passwordless OTP (One-Time Password) authentication system with JWT tokens and API keys for programmatic access.

### Features

#### 1.1 OTP Authentication
**Endpoint:** `POST /api/v1/auth/login`

- Passwordless email-based authentication
- 6-digit OTP code generation
- Automatic user creation on first login
- Users automatically assigned to "Users" group
- OTP sent via SMTP

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "message": "OTP sent to your email",
  "session_id": "uuid"
}
```

#### 1.2 OTP Verification
**Endpoint:** `POST /api/v1/auth/verify-otp`

- Verifies OTP code and issues JWT token
- Token includes user ID, email, and permissions
- Default token expiry: 7 days (configurable)
- Returns user information

**Request:**
```json
{
  "session_id": "uuid",
  "otp_code": "123456"
}
```

**Response:**
```json
{
  "access_token": "jwt_token",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "is_active": true,
    "created_at": "2025-01-15T10:00:00Z"
  }
}
```

#### 1.3 API Keys
**Endpoint:** `POST /api/v1/auth/api-keys`

- Create long-lived API keys for programmatic access
- API key permissions must be subset of user's group permissions
- Optional expiration date
- Key prefix for identification
- Keys hashed before storage (only shown once on creation)
- Track last used timestamp

**Request:**
```json
{
  "name": "Production API Key",
  "permissions": {
    "sinas.functions.read:own": true,
    "sinas.functions.execute:own": true
  },
  "expires_at": "2026-01-15T10:00:00Z"
}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "Production API Key",
  "key_prefix": "sk_1234",
  "api_key": "sk_1234567890abcdef...",
  "permissions": {...},
  "expires_at": "2026-01-15T10:00:00Z",
  "created_at": "2025-01-15T10:00:00Z"
}
```

**Management Endpoints:**
- `GET /api/v1/auth/api-keys` - List all API keys
- `DELETE /api/v1/auth/api-keys/{key_id}` - Revoke API key

#### 1.4 Current User
**Endpoint:** `GET /api/v1/auth/me`

- Get authenticated user information
- Returns user profile with timestamps

### Permission System

**Format:** `sinas.{service}.{resource}.{...segments}.{action}:{scope}`

**Scopes (hierarchical):**
- `:all` - Access to all resources (grants :group and :own)
- `:group` - Access to group resources (grants :own)
- `:own` - Access to own resources only

**Examples:**
- `sinas.functions.read:own` - Read own functions
- `sinas.ontology.concepts.crm.customer.read:group` - Read customer concept in CRM namespace
- `sinas.*:all` - Full system access (admin)

**Special Features:**
- Automatic scope hierarchy resolution
- Wildcard pattern matching (`sinas.ontology.*.create:group`)
- Permission checking via `check_permission()` function
- All API requests tracked with permission usage

---

## 2. User & Group Management

### 2.1 User Management

#### List Users
**Endpoint:** `GET /api/v1/users`

- List all users (admin only)
- Pagination support (skip/limit)
- Returns email, active status, created date

**Permission:** `sinas.users.read:all`

#### Get User
**Endpoint:** `GET /api/v1/users/{user_id}`

- Get user details with group memberships
- Users can view their own profile
- Admins can view any user

**Permissions:** `sinas.users.read:own` or `sinas.users.read:all`

#### Update User
**Endpoint:** `PATCH /api/v1/users/{user_id}`

- Update user active status
- Only admins can change active status
- Users can update their own profile (limited fields)

**Request:**
```json
{
  "is_active": false
}
```

#### Delete User
**Endpoint:** `DELETE /api/v1/users/{user_id}`

- Delete user account (admin only)
- Cannot delete yourself
- Cascading deletion of user's resources

**Permission:** `sinas.users.delete:all`

### 2.2 Group Management

Groups provide organizational structure and permission inheritance.

#### Create Group
**Endpoint:** `POST /api/v1/groups`

- Create new group
- Creator automatically added as admin member
- Optional email domain for auto-assignment

**Request:**
```json
{
  "name": "Engineering Team",
  "description": "Software engineering team",
  "email_domain": "eng.company.com"
}
```

**Permission:** `sinas.groups.create:own`

#### List Groups
**Endpoint:** `GET /api/v1/groups`

- List accessible groups
- Admins see all groups
- Regular users see only their groups
- Pagination support

#### Get Group
**Endpoint:** `GET /api/v1/groups/{group_id}`

- Get group details
- Check membership for access

#### Update Group
**Endpoint:** `PATCH /api/v1/groups/{group_id}`

- Update name, description, email domain
- Admin only

**Permission:** `sinas.groups.update:all`

#### Delete Group
**Endpoint:** `DELETE /api/v1/groups/{group_id}`

- Delete group (admin only)
- Removes all memberships

**Permission:** `sinas.groups.delete:all`

### 2.3 Group Membership

#### List Members
**Endpoint:** `GET /api/v1/groups/{group_id}/members`

- List all active members of a group
- Shows user ID, role, added date

#### Add Member
**Endpoint:** `POST /api/v1/groups/{group_id}/members`

**Request:**
```json
{
  "user_id": "uuid",
  "role": "member"
}
```

- Add user to group
- Optional role field
- Reactivates if previously removed
- Admin only

**Permission:** `sinas.groups.manage_members:all`

#### Remove Member
**Endpoint:** `DELETE /api/v1/groups/{group_id}/members/{user_id}`

- Soft delete (marks inactive)
- Records who removed and when
- Cannot remove from Admins group
- Admin only

**Permission:** `sinas.groups.manage_members:all`

### 2.4 Group Permissions

#### List Permissions
**Endpoint:** `GET /api/v1/groups/{group_id}/permissions`

- View all permissions assigned to group
- Admin only

#### Set Permission
**Endpoint:** `POST /api/v1/groups/{group_id}/permissions`

**Request:**
```json
{
  "permission_key": "sinas.functions.read:group",
  "permission_value": true
}
```

- Grant or revoke group permission
- Cannot modify Admins group permissions
- Upsert operation (creates or updates)

**Permission:** `sinas.groups.manage_permissions:all`

#### Delete Permission
**Endpoint:** `DELETE /api/v1/groups/{group_id}/permissions/{permission_key}`

- Remove permission from group
- Cannot modify Admins group

**Permission:** `sinas.groups.manage_permissions:all`

---

## 3. AI Chat & Assistants

### 3.1 Assistants

AI assistants with configurable providers, models, and capabilities.

#### Create Assistant
**Endpoint:** `POST /api/v1/assistants`

**Request:**
```json
{
  "name": "Customer Support Bot",
  "description": "Handles customer inquiries",
  "provider": "openai",
  "model": "gpt-4",
  "temperature": 0.7,
  "system_prompt": "You are a helpful customer support agent...",
  "input_schema": {"type": "object", "properties": {...}},
  "output_schema": {"type": "object", "properties": {...}},
  "initial_messages": [
    {"role": "system", "content": "Initial context..."}
  ],
  "group_id": "uuid",
  "enabled_webhooks": ["webhook-1", "webhook-2"],
  "enabled_mcp_tools": ["tool-1", "tool-2"],
  "enabled_assistants": ["assistant-uuid-1"],
  "webhook_parameters": {"webhook-1": {...}},
  "mcp_tool_parameters": {"tool-1": {...}},
  "context_namespaces": ["customer-data", "product-info"],
  "ontology_namespaces": ["crm"],
  "ontology_concepts": ["crm.customer", "crm.order"]
}
```

**Features:**
- Multi-provider support (OpenAI, Ollama, etc.)
- JSON schema validation for inputs/outputs
- Initial message configuration
- Tool enablement (webhooks, MCP tools, other assistants)
- Context injection from specific namespaces
- Ontology access control
- Per-tool parameter configuration

**Permission:** `sinas.assistants.create:own`

#### List Assistants
**Endpoint:** `GET /api/v1/assistants`

- List own assistants
- Admins can list all assistants with `read:all` permission
- Only returns active assistants

#### Get Assistant
**Endpoint:** `GET /api/v1/assistants/{assistant_id}`

- Get assistant configuration
- User must own the assistant

#### Update Assistant
**Endpoint:** `PUT /api/v1/assistants/{assistant_id}`

- Update assistant configuration
- Partial updates supported
- Can enable/disable assistant

**Permission:** `sinas.assistants.update:own`

#### Delete Assistant
**Endpoint:** `DELETE /api/v1/assistants/{assistant_id}`

- Soft delete (marks inactive)
- Assistant no longer callable

**Permission:** `sinas.assistants.delete:own`

### 3.2 Chat Management

#### Create Chat
**Endpoint:** `POST /api/v1/chats`

**Request:**
```json
{
  "title": "Customer Support Session",
  "assistant_id": "uuid",
  "group_id": "uuid",
  "enabled_webhooks": ["webhook-1"],
  "enabled_mcp_tools": ["tool-1"]
}
```

- Create conversation thread
- Optional assistant binding
- Per-chat tool enablement
- Group association for permissions

**Permission:** `sinas.chats.create:own`

#### List Chats
**Endpoint:** `GET /api/v1/chats`

- List user's chats
- Ordered by last updated
- Returns chat metadata (no messages)

#### Get Chat with Messages
**Endpoint:** `GET /api/v1/chats/{chat_id}`

- Get complete chat history
- Includes all messages in chronological order
- Message roles: user, assistant, system, tool

#### Update Chat
**Endpoint:** `PUT /api/v1/chats/{chat_id}`

- Update title
- Modify enabled tools
- Change webhook configuration

**Permission:** `sinas.chats.update:own`

#### Delete Chat
**Endpoint:** `DELETE /api/v1/chats/{chat_id}`

- Delete chat and all messages
- Permanent deletion

**Permission:** `sinas.chats.delete:own`

### 3.3 Messaging

#### Send Message (Non-Streaming)
**Endpoint:** `POST /api/v1/chats/{chat_id}/messages`

**Request:**
```json
{
  "content": "What are the system requirements?",
  "provider": "openai",
  "model": "gpt-4",
  "temperature": 0.7,
  "max_tokens": 2000,
  "enabled_webhooks": ["docs-search"],
  "disabled_webhooks": [],
  "enabled_mcp_tools": ["filesystem"],
  "disabled_mcp_tools": [],
  "inject_context": true,
  "context_namespaces": ["product-docs"],
  "context_limit": 5
}
```

**Features:**
- Override provider/model per message
- Per-message tool configuration
- Automatic context injection
- Context namespace filtering
- Relevance-based context ranking

**Response:**
```json
{
  "id": "uuid",
  "chat_id": "uuid",
  "role": "assistant",
  "content": "The system requirements are...",
  "tool_calls": null,
  "created_at": "2025-01-15T10:00:00Z"
}
```

**Permission:** `sinas.chats.messages.create:own`

#### Send Message (Streaming)
**Endpoint:** `POST /api/v1/chats/{chat_id}/messages/stream`

- Server-Sent Events (SSE) streaming
- Real-time token-by-token response
- Same request format as non-streaming
- Events: `message`, `done`, `error`

**Event Format:**
```
event: message
data: {"type": "content", "delta": "The ", ...}

event: message
data: {"type": "content", "delta": "system ", ...}

event: done
data: {"status": "completed"}
```

#### List Messages
**Endpoint:** `GET /api/v1/chats/{chat_id}/messages`

- Get all messages in chat
- Chronological order
- Includes tool calls and responses

**Permission:** `sinas.chats.messages.read:own`

---

## 4. Function Execution System

Python runtime environment for custom code execution with automatic tracking, versioning, and execution tree building.

### 4.1 Functions

#### Create Function
**Endpoint:** `POST /api/v1/functions`

**Request:**
```json
{
  "name": "calculate_discount",
  "description": "Calculate customer discount based on order history",
  "code": "def calculate_discount(order_value, customer_tier):\n    ...",
  "input_schema": {
    "type": "object",
    "properties": {
      "order_value": {"type": "number"},
      "customer_tier": {"type": "string", "enum": ["bronze", "silver", "gold"]}
    },
    "required": ["order_value", "customer_tier"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "discount_percentage": {"type": "number"},
      "final_price": {"type": "number"}
    }
  },
  "requirements": ["pandas>=1.5.0", "numpy>=1.24.0"],
  "tags": ["pricing", "customer"]
}
```

**Features:**
- Python code validation (AST parsing)
- JSON Schema validation for inputs/outputs
- Package requirements with version constraints
- Tagging for organization
- Automatic versioning on code changes
- Function names must be valid Python identifiers

**Execution Capabilities:**
- Functions can call other functions
- Automatic execution tracking via AST injection
- `@track` decorator automatically added to all function definitions
- Execution tree captured (parent → child → grandchild calls)
- Input/output validation via jsonschema
- Complex type support via dill serialization
- Configurable timeout and memory limits

**Permission:** `sinas.functions.create:own`

#### List Functions
**Endpoint:** `GET /api/v1/functions`

- List accessible functions
- Filter by tag
- Pagination support
- Scope-based access (own/group/all)

**Query Parameters:**
- `skip` - Pagination offset
- `limit` - Max results (1-1000)
- `tag` - Filter by tag

#### Get Function
**Endpoint:** `GET /api/v1/functions/{function_id}`

- Get function details including code
- Version history available separately

#### Update Function
**Endpoint:** `PATCH /api/v1/functions/{function_id}`

- Update code, schemas, requirements, tags
- Automatically creates new version when code changes
- Can activate/deactivate function

**Permission:** `sinas.functions.update:own`

#### Delete Function
**Endpoint:** `DELETE /api/v1/functions/{function_id}`

- Permanent deletion
- Removes all versions

**Permission:** `sinas.functions.delete:own`

### 4.2 Function Versions

#### List Versions
**Endpoint:** `GET /api/v1/functions/{function_id}/versions`

- View complete version history
- Ordered by version number (descending)
- Includes code snapshot, schemas, creator

**Version Tracking:**
- Automatic version increment on code changes
- Initial version created on function creation
- Immutable version records
- Each version stores: code, input_schema, output_schema, created_by, created_at

### 4.3 Executions

Function executions are automatically tracked with full execution trees.

#### List Executions
**Endpoint:** `GET /api/v1/executions`

**Query Parameters:**
- `function_name` - Filter by function
- `status` - Filter by status (pending, running, completed, failed, awaiting_input)
- `skip`, `limit` - Pagination

**Execution Statuses:**
- `pending` - Queued for execution
- `running` - Currently executing
- `completed` - Finished successfully
- `failed` - Execution error
- `awaiting_input` - Paused for user input

**Response:**
```json
[
  {
    "id": "uuid",
    "execution_id": "exec_123",
    "function_name": "calculate_discount",
    "trigger_type": "webhook",
    "trigger_id": "uuid",
    "status": "completed",
    "input_data": {"order_value": 1000, "customer_tier": "gold"},
    "output_data": {"discount_percentage": 15, "final_price": 850},
    "error": null,
    "traceback": null,
    "started_at": "2025-01-15T10:00:00Z",
    "completed_at": "2025-01-15T10:00:02Z",
    "duration_ms": 2000
  }
]
```

#### Get Execution
**Endpoint:** `GET /api/v1/executions/{execution_id}`

- Get execution details
- View inputs, outputs, errors
- Check duration and timestamps

#### Get Execution Steps
**Endpoint:** `GET /api/v1/executions/{execution_id}/steps`

- View complete execution tree
- Shows all function calls made during execution
- Nested function calls tracked as steps
- Each step includes: function name, inputs, outputs, duration, status

**Example Step Tree:**
```
Execution: calculate_order_total
├─ Step: get_customer_tier (completed, 100ms)
├─ Step: calculate_discount (completed, 50ms)
│  └─ Step: apply_promo_code (completed, 30ms)
└─ Step: calculate_tax (completed, 40ms)
```

#### Continue Execution
**Endpoint:** `POST /api/v1/executions/{execution_id}/continue`

**Request:**
```json
{
  "input": {
    "user_confirmation": true,
    "additional_data": "..."
  }
}
```

- Resume paused execution
- Provide user input for awaiting_input status
- Returns updated execution status

**Permission:** `sinas.executions.update:own`

---

## 5. Webhook System

HTTP endpoints that trigger function execution.

### 5.1 Webhook Management

#### Create Webhook
**Endpoint:** `POST /api/v1/webhooks`

**Request:**
```json
{
  "path": "customer/signup",
  "function_name": "process_customer_signup",
  "http_method": "POST",
  "description": "Handle new customer signups",
  "default_values": {
    "source": "web"
  },
  "requires_auth": true
}
```

**Features:**
- Custom URL paths (alphanumeric, underscores, hyphens, slashes)
- HTTP method selection (GET, POST, PUT, PATCH, DELETE)
- Default input values merged with request data
- Optional authentication requirement
- Automatic function binding
- Path uniqueness per user

**Permission:** `sinas.webhooks.create:own`

#### List Webhooks
**Endpoint:** `GET /api/v1/webhooks`

- List accessible webhooks
- Scope-based filtering
- Pagination support

#### Get Webhook
**Endpoint:** `GET /api/v1/webhooks/{webhook_id}`

- Get webhook configuration
- View associated function

#### Update Webhook
**Endpoint:** `PATCH /api/v1/webhooks/{webhook_id}`

- Change function binding
- Update HTTP method
- Modify default values
- Activate/deactivate webhook
- Update auth requirement

**Permission:** `sinas.webhooks.update:own`

#### Delete Webhook
**Endpoint:** `DELETE /api/v1/webhooks/{webhook_id}`

- Remove webhook endpoint
- Permanent deletion

**Permission:** `sinas.webhooks.delete:own`

### 5.2 Webhook Invocation

**Endpoint:** `POST/GET/PATCH/PUT/DELETE /h/{path}` (or configured HTTP method)

- Accepts JSON request body
- Query parameters merged with body
- Default values applied
- Function executed with combined input
- Returns execution result or queues for async processing
- Optional JWT/API key authentication

**Example:**
```bash
curl -X POST https://prod.my-org.sinas.cloud/api/v1/h/customer_signup \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@example.com",
    "name": "John Doe"
  }'
```

---

## 6. Scheduling System

Cron-based scheduled execution of functions.

### 6.1 Scheduled Jobs

#### Create Schedule
**Endpoint:** `POST /api/v1/schedules`

**Request:**
```json
{
  "name": "daily_report",
  "function_name": "generate_daily_report",
  "description": "Generate and email daily sales report",
  "cron_expression": "0 9 * * *",
  "timezone": "America/New_York",
  "input_data": {
    "report_type": "sales",
    "recipients": ["team@company.com"]
  }
}
```

**Features:**
- Standard cron expression syntax
- Timezone support (default: UTC)
- Cron validation on create/update
- Function binding with input data
- Track last run and next run times
- Activate/deactivate schedules

**Cron Expression Format:**
```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday to Saturday)
│ │ │ │ │
* * * * *
```

**Common Examples:**
- `0 * * * *` - Every hour
- `*/15 * * * *` - Every 15 minutes
- `0 9 * * 1-5` - 9 AM on weekdays
- `0 0 1 * *` - First day of every month at midnight

**Permission:** `sinas.schedules.create:own`

#### List Schedules
**Endpoint:** `GET /api/v1/schedules`

- List accessible schedules
- Pagination support
- View next run times

#### Get Schedule
**Endpoint:** `GET /api/v1/schedules/{schedule_id}`

- Get schedule configuration
- View execution history

#### Update Schedule
**Endpoint:** `PATCH /api/v1/schedules/{schedule_id}`

- Modify cron expression
- Change function or input data
- Update timezone
- Activate/deactivate

**Permission:** `sinas.schedules.update:own`

#### Delete Schedule
**Endpoint:** `DELETE /api/v1/schedules/{schedule_id}`

- Remove scheduled job
- Stops future executions

**Permission:** `sinas.schedules.delete:own`

---

## 7. Ontology System

Flexible semantic data layer with schema-on-read architecture, enabling instant CRUD APIs over any database with permission-based row-level security.

### 7.1 Overview

The ontology system provides a unified architecture for accessing data across multiple databases, whether SINAS-managed or external. All concepts map to physical tables/views through **TableMappings**, supporting:

- **Multi-datasource access** - Connect to any PostgreSQL database
- **Flexible table mapping** - Multiple concepts can map to the same table
- **Column aliasing** - Property names differ from column names
- **Ownership mapping** - Link external user/group IDs to SINAS permissions
- **Instant CRUD APIs** - Auto-generated REST endpoints with RLS
- **DDL operations** - Create/manage tables and views via API

**Key Components:**
- **Concepts** - Logical entity definitions (e.g., Customer, Order)
- **Properties** - Attributes of concepts (e.g., name, email, price)
- **Relationships** - Connections between concepts
- **Datasources** - Database connections (local or external)
- **TableMappings** - Maps concepts to physical tables with column mappings
- **External Mappings** - Links external user/group IDs to SINAS

### 7.2 Datasources

Database connections for ontology data access.

#### Create Datasource
**Endpoint:** `POST /api/v1/ontology/datasources`

**Request:**
```json
{
  "name": "Production CRM",
  "type": "postgres",
  "conn_string": "postgresql://user:pass@host:5432/crm",
  "default_database": "crm",
  "default_schema": "public",
  "is_read_only": false,
  "group_id": "uuid"
}
```

**Supported Types:**
- PostgreSQL (`postgres`)
- Snowflake (`snowflake`) - Future
- BigQuery (`bigquery`) - Future

**Features:**
- Connection string encryption (Fernet)
- Read-only flag prevents DDL operations
- Default database/schema configuration
- Group-based access control
- Supports both SINAS-managed and external databases

**Permission:** `sinas.ontology.datasources.create:group`

#### List/Get/Update/Delete Datasources
- Standard CRUD operations
- Connection strings remain encrypted in responses
- Cannot modify read-only datasources

### 7.3 DDL Operations

Manage database tables and views programmatically on writable datasources.

#### List Tables
**Endpoint:** `GET /api/v1/ddl/datasources/{datasource_id}/tables`

**Query Parameters:**
- `schema` - Database schema (default: datasource default_schema)

**Response:**
```json
{
  "tables": [
    {"table_name": "customers", "schema": "public"},
    {"table_name": "orders", "schema": "public"}
  ]
}
```

**Permission:** `sinas.datasources.{id}.ddl.read:group`

#### Get Table Schema
**Endpoint:** `GET /api/v1/ddl/datasources/{datasource_id}/tables/{table_name}`

**Response:**
```json
{
  "table_name": "customers",
  "schema": "public",
  "columns": [
    {
      "column_name": "id",
      "data_type": "uuid",
      "is_nullable": false,
      "column_default": "gen_random_uuid()",
      "is_primary_key": true
    },
    {
      "column_name": "name",
      "data_type": "text",
      "is_nullable": false
    }
  ]
}
```

#### Create Table
**Endpoint:** `POST /api/v1/ddl/datasources/{datasource_id}/tables`

**Request:**
```json
{
  "table_name": "customers",
  "schema": "public",
  "columns": [
    {
      "name": "id",
      "type": "UUID",
      "primary_key": true,
      "default": "gen_random_uuid()"
    },
    {
      "name": "name",
      "type": "TEXT",
      "nullable": false
    },
    {
      "name": "email",
      "type": "TEXT",
      "unique": true
    },
    {
      "name": "created_at",
      "type": "TIMESTAMP WITH TIME ZONE",
      "default": "NOW()"
    }
  ]
}
```

**Features:**
- Only works on non-read-only datasources
- Supports constraints (PRIMARY KEY, UNIQUE, NOT NULL)
- Column defaults
- Postgres-specific data types

**Permission:** `sinas.datasources.{id}.ddl:group`

#### Add Column
**Endpoint:** `POST /api/v1/ddl/datasources/{datasource_id}/tables/{table_name}/columns`

**Request:**
```json
{
  "name": "phone",
  "type": "TEXT",
  "nullable": true,
  "default": null,
  "schema": "public"
}
```

#### Drop Table
**Endpoint:** `DELETE /api/v1/ddl/datasources/{datasource_id}/tables/{table_name}`

**Query Parameters:**
- `schema` - Database schema
- `cascade` - Drop dependent objects (default: false)

**Permission:** `sinas.datasources.{id}.ddl:group`

#### Create View
**Endpoint:** `POST /api/v1/ddl/datasources/{datasource_id}/views`

**Request:**
```json
{
  "view_name": "active_customers_with_orders",
  "query": "SELECT c.*, COUNT(o.id) as order_count FROM customers c LEFT JOIN orders o ON c.id = o.customer_id WHERE c.status = 'active' GROUP BY c.id",
  "schema": "public",
  "replace": false
}
```

**Features:**
- SQL query validation (SELECT only)
- Replace existing views with `replace: true`
- Complex queries with JOINs, aggregations, filters
- Read-only data access layer

**Permission:** `sinas.datasources.{id}.ddl:group`

#### List/Drop Views
- `GET /api/v1/ddl/datasources/{id}/views` - List all views
- `DELETE /api/v1/ddl/datasources/{id}/views/{view_name}` - Drop view

### 7.4 Concepts

Logical entity definitions that map to physical tables.

#### Create Concept
**Endpoint:** `POST /api/v1/ontology/concepts`

**Request:**
```json
{
  "namespace": "crm",
  "name": "customer",
  "display_name": "Customer",
  "description": "Customer entity",
  "group_id": "uuid"
}
```

**Features:**
- Namespace organization (e.g., crm, inventory, hr)
- Logical schema definition
- No automatic table creation (use DDL API or map to existing tables)
- Unique namespace.name per group
- Properties define expected fields

**Permission:** `sinas.ontology.concepts.{namespace}.create:group`

#### List/Get/Update/Delete Concepts
- Standard CRUD operations
- Update display_name and description only
- Cannot change namespace or name after creation
- Deletion requires removing TableMapping first

**Permission Patterns:**
- `sinas.ontology.concepts.{namespace}.create:group`
- `sinas.ontology.concepts.{namespace}.{name}.read:group`
- `sinas.ontology.concepts.{namespace}.{name}.update:group`
- `sinas.ontology.concepts.{namespace}.{name}.delete:group`

#### Get Concept Properties
**Endpoint:** `GET /api/v1/ontology/concepts/{concept_id}/properties`

- List all properties defined for concept
- Ordered by name

### 7.5 Properties

Define attributes of concepts (logical schema).

#### Create Property
**Endpoint:** `POST /api/v1/ontology/properties`

**Request:**
```json
{
  "concept_id": "uuid",
  "name": "email",
  "display_name": "Email Address",
  "description": "Customer email",
  "data_type": "TEXT",
  "is_identifier": false,
  "is_required": true,
  "default_value": null
}
```

**Data Types:**
- `TEXT` - String data
- `INTEGER` - Whole numbers
- `DECIMAL` - Decimal numbers
- `BOOLEAN` - True/false
- `DATETIME` - Timestamp with timezone
- `DATE` - Date only
- `JSON` - JSON objects
- `UUID` - UUIDs

**Features:**
- Logical schema definition
- No automatic column creation (use DDL API)
- Maps to physical columns via TableMapping
- Identifier flag marks primary keys
- Required flag indicates NOT NULL

**Permission:** `sinas.ontology.properties.create:group`

#### List/Get/Update/Delete Properties
- Standard CRUD operations
- Property updates don't affect database schema (use DDL API)
- Maps to columns through `column_mappings` in TableMapping

### 7.6 Relationships

#### Create Relationship
**Endpoint:** `POST /api/v1/ontology/relationships`

**Request:**
```json
{
  "name": "customer_orders",
  "from_concept_id": "customer_uuid",
  "to_concept_id": "order_uuid",
  "from_property_id": "customer_id_property",
  "to_property_id": "order_customer_id_property",
  "cardinality": "one_to_many",
  "description": "Customer has multiple orders"
}
```

**Cardinality Options:**
- `one_to_one` - 1:1 relationship
- `one_to_many` - 1:N relationship
- `many_to_one` - N:1 relationship
- `many_to_many` - N:M relationship

**Features:**
- Define foreign key relationships
- Used in endpoint joins
- Bidirectional relationship modeling

### 7.7 Table Mappings

Maps concepts to physical tables/views with column mappings and ownership configuration.

#### Create Table Mapping
**Endpoint:** `POST /api/v1/ontology/table-mappings`

**Request:**
```json
{
  "concept_id": "uuid",
  "datasource_id": "uuid",
  "table_name": "customers",
  "column_mappings": {
    "fullName": "full_name",
    "emailAddress": "email"
  },
  "user_ownership_column": "assigned_to_email",
  "group_ownership_column": "department"
}
```

**Features:**
- **1:1 relationship** - One concept maps to one table/view
- **Column aliasing** - Property names map to different column names
- **Ownership columns** - Enable permission-based row filtering
- **Flexible mapping** - Same table can be used by multiple concepts (via different namespaces)
- **View support** - Map to database views for complex queries

**Ownership Filtering:**
- `user_ownership_column` - Column containing user identifier for `:own` scope
- `group_ownership_column` - Column containing group identifier for `:group` scope
- Combined with ExternalIdentityMapping/ExternalGroupMapping for row-level security

**Permission:** `sinas.ontology.table_mappings.create:group`

#### List/Get/Update/Delete Table Mappings
- Standard CRUD operations
- Update column mappings as schema evolves
- Update ownership columns for RLS changes

### 7.8 External Identity/Group Mappings

Link external user/group identifiers to SINAS for ownership-based queries.

#### Create External Identity Mapping
**Endpoint:** `POST /api/v1/ontology/external-mappings/identities`

**Request:**
```json
{
  "user_id": "sinas_user_uuid",
  "datasource_id": "external_crm_uuid",
  "external_user_ref": "alice@company.com"
}
```

**Usage:**
When querying with `:own` scope:
```sql
-- Automatic WHERE clause injection
WHERE user_ownership_column IN (
  SELECT external_user_ref
  FROM external_identity_mappings
  WHERE user_id = :current_user_id AND datasource_id = :datasource_id
)
```

**Permission:** `sinas.ontology.external_mappings.create:group`

#### Create External Group Mapping
**Endpoint:** `POST /api/v1/ontology/external-mappings/groups`

**Request:**
```json
{
  "group_id": "sinas_group_uuid",
  "datasource_id": "external_crm_uuid",
  "external_group_ref": "Region_West"
}
```

**Usage:**
When querying with `:group` scope, similar WHERE clause injection on `group_ownership_column`.

#### List/Get/Delete Mappings
- View all mappings for datasource
- Bulk import from external systems
- Remove stale mappings

### 7.10 Concept Data (CRUD APIs)

Auto-generated REST endpoints for all concepts with TableMapping.

#### Create Record
**Endpoint:** `POST /api/v1/ontology/records/{namespace}/{concept}`

**Request:**
```json
{
  "data": {
    "name": "John Doe",
    "email": "john@example.com",
    "tier": "gold"
  }
}
```

**Features:**
- Property validation against concept schema
- Column mapping applied via TableMapping
- Executes INSERT on configured datasource
- Works with external databases
- UUID/timestamp generation (if columns exist)

**Behavior:**
1. Lookup concept, TableMapping, datasource
2. Map property names to column names via `column_mappings`
3. Execute INSERT against datasource
4. Return created record with ID

**Permission:** `sinas.ontology.data.{namespace}.{concept}.create:group`

#### List Records
**Endpoint:** `GET /api/v1/ontology/records/{namespace}/{concept}`

**Query Parameters:**
- `skip` - Pagination offset
- `limit` - Max results
- `filter_{property}` - Filter by property values (e.g., `?filter_status=active`)

**Features:**
- Pagination support
- Ownership-based filtering (`:own` and `:group` scopes)
- Column mappings applied in reverse (column → property)
- Works across all datasources

**Permission:** `sinas.ontology.data.{namespace}.{concept}.read:group`

#### Get Record
**Endpoint:** `GET /api/v1/ontology/records/{namespace}/{concept}/{record_id}`

- Fetch single record by ID
- Ownership check applied

#### Update Record
**Endpoint:** `PATCH /api/v1/ontology/records/{namespace}/{concept}/{record_id}`

**Request:**
```json
{
  "data": {
    "tier": "platinum"
  }
}
```

**Features:**
- Partial updates
- Column mappings applied
- Ownership check (can only update own/group records)

**Permission:** `sinas.ontology.data.{namespace}.{concept}.update:group`

#### Delete Record
**Endpoint:** `DELETE /api/v1/ontology/records/{namespace}/{concept}/{record_id}`

**Features:**
- Ownership check
- Permanent deletion
- Works on writable datasources only

**Permission:** `sinas.ontology.data.{namespace}.{concept}.delete:group`

### 7.11 Query Optimization

**Database Views for Complex Queries:**
Instead of endpoint configurations, create views:

```sql
-- Via DDL API
POST /api/v1/ddl/datasources/{id}/views
{
  "view_name": "active_customers_with_orders",
  "query": "SELECT c.*, COUNT(o.id) as order_count
            FROM customers c
            LEFT JOIN orders o ON c.id = o.customer_id
            WHERE c.status = 'active'
            GROUP BY c.id"
}
```

Then map a concept to the view:
```json
// Create concept
POST /api/v1/ontology/concepts
{"namespace": "crm", "name": "ActiveCustomer", ...}

// Create table mapping to view
POST /api/v1/ontology/table-mappings
{
  "concept_id": "...",
  "datasource_id": "...",
  "table_name": "active_customers_with_orders"
}
```

Now query via CRUD API:
```
GET /api/v1/ontology/records/crm/ActiveCustomer
```

---

## 8. Document Management

Hierarchical document storage with folders, metadata in PostgreSQL, and content in MongoDB.

### 8.1 Folders

#### Create Folder
**Endpoint:** `POST /api/v1/documents/folders`

**Request:**
```json
{
  "name": "Product Documentation",
  "description": "Technical product docs",
  "owner_type": "group",
  "user_id": "uuid",
  "group_id": "uuid",
  "parent_folder_id": null
}
```

**Features:**
- Hierarchical folder structure
- Owner types: `user` or `group`
- Permission inheritance from parent
- Group or user ownership
- Nested folder support

**Permission:** `sinas.documents.folders.create:own` or `:group`

#### List Folders
**Endpoint:** `GET /api/v1/documents/folders`

**Query Parameters:**
- `user_id` - Filter by owner user
- `group_id` - Filter by owner group
- `parent_folder_id` - Filter by parent

#### Get/Update/Delete Folder
- Standard CRUD operations
- Delete cascades to subfolders and documents
- Permission checks based on ownership

### 8.2 Documents

#### Create Document
**Endpoint:** `POST /api/v1/documents`

**Request:**
```json
{
  "name": "API Reference Guide",
  "description": "Complete API documentation",
  "content": "# API Reference\n\n## Authentication\n...",
  "filetype": "markdown",
  "source": "manual",
  "folder_id": "uuid",
  "user_id": "uuid",
  "auto_description_webhook_id": "uuid"
}
```

**Features:**
- Content stored in MongoDB (separate from metadata)
- Filetype tracking (markdown, pdf, txt, html, etc.)
- Source attribution
- Optional folder organization
- Auto-description via webhook
- Version tracking
- Tag support

**Permission:** `sinas.documents.create:own` or `:group`

#### List Documents
**Endpoint:** `GET /api/v1/documents`

**Query Parameters:**
- `folder_id` - Filter by folder
- `user_id` - Filter by owner
- `filetype` - Filter by type
- `tags` - JSON array of tag filters
- `tag_match` - Match mode: `AND` or `OR`

**Tag Filtering Examples:**
```
?tags=[{"key":"year","value":"2025"}]&tag_match=AND
?tags=[{"key":"category","value":"technical"},{"key":"category","value":"business"}]&tag_match=OR
```

**Features:**
- Returns document metadata with tags (no content for performance)
- Tag-based filtering with AND/OR logic
- Efficient tag value matching

#### Get Document
**Endpoint:** `GET /api/v1/documents/{document_id}`

- Returns full document with content
- Includes all tags with definitions

#### Update Document
**Endpoint:** `PATCH /api/v1/documents/{document_id}`

**Request:**
```json
{
  "name": "Updated Guide",
  "content": "# Updated Content...",
  "description": "Updated description"
}
```

- Partial updates
- Content updates increment version
- Auto-tagger can run on update
- Permission checks based on ownership

**Permission:** `sinas.documents.update:own` or `:group`

#### Delete Document
**Endpoint:** `DELETE /api/v1/documents/{document_id}`

- Removes from PostgreSQL and MongoDB
- Deletes associated tags

**Permission:** `sinas.documents.delete:own` or `:group`

#### Generate Description
**Endpoint:** `POST /api/v1/documents/{document_id}/generate-description`

- Manually trigger auto-description webhook
- Webhook must be configured on document
- Uses document content as webhook input
- Updates document description with result

**Permission:** `sinas.documents.generate_description:own` or `:group`

---

## 9. Tagging System

Flexible metadata system with tag definitions, instances, and AI-powered auto-tagging.

### 9.1 Tag Definitions

#### Create Tag Definition
**Endpoint:** `POST /api/v1/tags/definitions`

**Request:**
```json
{
  "name": "priority",
  "display_name": "Priority Level",
  "value_type": "enum",
  "applies_to": ["document", "email"],
  "description": "Task or document priority",
  "allowed_values": ["low", "medium", "high", "critical"],
  "is_required": false
}
```

**Value Types:**
- `string` - Free text
- `enum` - Fixed set of values
- `number` - Numeric values
- `boolean` - True/false
- `date` - Date values

**Resource Types:**
- `document`
- `email`
- (extensible to other resources)

**Features:**
- Reusable tag schemas
- Value validation
- Multi-resource applicability
- Required tag enforcement
- Allowed values constraint

**Permission:** `sinas.tags.definitions.create:group`

#### List Tag Definitions
**Endpoint:** `GET /api/v1/tags/definitions`

**Query Parameters:**
- `applies_to` - Filter by resource type

#### Get/Update/Delete Tag Definition
- Standard CRUD operations
- Cannot modify name or value_type after creation
- Can update allowed_values, display_name, description

### 9.2 Tag Instances (Applied Tags)

#### Apply Tag
**Endpoint:** `POST /api/v1/tags/{resource_type}/{resource_id}/tags`

**Request:**
```json
{
  "tag_definition_id": "uuid",
  "value": "high"
}
```

- Apply tag to specific resource
- Value validated against definition
- Duplicate tags prevented (same key+value)

**Permission:** `sinas.tags.{resource_type}.create:own`

#### Apply Tags Bulk
**Endpoint:** `POST /api/v1/tags/{resource_type}/{resource_id}/tags/bulk`

**Request:**
```json
{
  "tags": [
    {"tag_definition_id": "uuid1", "value": "high"},
    {"tag_definition_id": "uuid2", "value": "2025"},
    {"tag_definition_id": "uuid3", "value": "technical"}
  ]
}
```

- Apply multiple tags at once
- Atomic operation
- Useful after AI tagging

#### Get Resource Tags
**Endpoint:** `GET /api/v1/tags/{resource_type}/{resource_id}/tags`

- List all tags on a resource
- Includes tag definitions

#### Delete Tag
**Endpoint:** `DELETE /api/v1/tags/{resource_type}/{resource_id}/tags/{tag_id}`

- Remove tag from resource

**Permission:** `sinas.tags.{resource_type}.delete:own`

### 9.3 Tag Value Counts

#### Get Tag Values with Counts
**Endpoint:** `GET /api/v1/tags/values/{tag_name}`

**Query Parameters:**
- `resource_type` - Filter by resource type

**Response:**
```json
{
  "tag_name": "priority",
  "values": [
    {"value": "high", "count": 45},
    {"value": "medium", "count": 32},
    {"value": "low", "count": 18},
    {"value": "critical", "count": 5}
  ]
}
```

**Features:**
- Get all distinct values for a tag
- Count occurrences of each value
- Useful for UI filters and analytics
- Ordered by count (descending)

### 9.4 Tagger Rules (AI Auto-Tagging)

#### Create Tagger Rule
**Endpoint:** `POST /api/v1/tags/tagger-rules`

**Request:**
```json
{
  "name": "Document Auto-Tagger",
  "description": "Automatically tag documents with priority, category, and year",
  "scope_type": "folder",
  "tag_definition_ids": ["priority_uuid", "category_uuid", "year_uuid"],
  "assistant_id": "uuid",
  "folder_id": "uuid",
  "inbox_id": null,
  "is_active": true,
  "auto_trigger": true
}
```

**Scope Types:**
- `folder` - Tags documents in a folder
- `inbox` - Tags incoming emails
- `global` - Tags any resource

**Features:**
- AI assistant-powered tagging
- Multiple tag definitions per rule
- Auto-trigger on document/email creation
- Manual trigger support
- Folder or inbox scoped

**Permission:** `sinas.tags.tagger_rules.create:group`

#### List/Get/Update/Delete Tagger Rules
- Standard CRUD operations
- Activate/deactivate rules
- Modify tag definitions and assistant

#### Run Tagger on Resource
**Endpoint:** `POST /api/v1/tags/{resource_type}/{resource_id}/run-tagger`

**Request:**
```json
{
  "tagger_rule_id": "uuid"
}
```

**Response:**
```json
{
  "success": true,
  "tags_created": [
    {"key": "priority", "value": "high"},
    {"key": "category", "value": "technical"},
    {"key": "year", "value": "2025"}
  ],
  "message": "Successfully tagged with 3 tags"
}
```

- Manually trigger tagging
- Assistant analyzes resource content
- Creates tag instances
- Returns created tags

**Permission:** `sinas.tags.{resource_type}.create:own`

#### Run Tagger Bulk
**Endpoint:** `POST /api/v1/tags/tagger-rules/{rule_id}/run-bulk`

**Request:**
```json
{
  "folder_id": "uuid",
  "force_retag": false
}
```

**Response:**
```json
{
  "success": true,
  "documents_processed": 150,
  "documents_failed": 2,
  "total_tags_created": 450,
  "errors": [
    "Document abc: Timeout error",
    "Document xyz: Invalid response"
  ],
  "message": "Processed 150 documents, created 450 tags"
}
```

**Features:**
- Tag all documents in a folder
- Skip already-tagged documents (unless force_retag)
- Error collection for failed documents
- Progress tracking
- Useful for:
  - Re-tagging after adding new tag definitions
  - Fixing incorrect tags
  - Tagging existing documents with new rule

**Permission:** `sinas.tags.tagger_rules.execute:group`

---

## 10. Email Management

Comprehensive email system with templates, inboxes, sending, and receiving capabilities.

### 10.1 Email Templates

#### Create Email Template
**Endpoint:** `POST /api/v1/email-templates`

**Request:**
```json
{
  "name": "welcome_email",
  "subject": "Welcome to {{company_name}}!",
  "html_template": "<html><body><h1>Hello {{user_name}}</h1><p>Welcome!</p></body></html>",
  "text_template": "Hello {{user_name}}\n\nWelcome to our service!",
  "description": "New user welcome email",
  "variables": ["user_name", "company_name"]
}
```

**Features:**
- Jinja2 template rendering
- HTML and plain text versions
- Variable substitution
- Template versioning
- Reusable across emails

**Permission:** `sinas.email.templates.create:group`

#### List/Get/Update/Delete Email Templates
- Standard CRUD operations
- Test rendering with sample variables
- View template usage statistics

### 10.2 Email Inboxes

#### Create Email Inbox
**Endpoint:** `POST /api/v1/email-inboxes`

**Request:**
```json
{
  "email_address": "support@company.com",
  "description": "Customer support inbox",
  "webhook_id": "uuid",
  "is_active": true,
  "auto_tagger_rule_id": "uuid"
}
```

**Features:**
- Receive emails at custom addresses
- Webhook triggers on email receipt
- Auto-tagging of incoming emails
- Active/inactive state
- Group-based access

**Permission:** `sinas.email.inboxes.create:group`

**Webhook Integration:**
- Webhook receives email data:
  ```json
  {
    "from": "customer@example.com",
    "to": "support@company.com",
    "subject": "Help needed",
    "body": "Email content...",
    "html_body": "<html>...",
    "attachments": [...]
  }
  ```
- Function can process email and respond
- Auto-tagging applied before webhook

#### List/Get/Update/Delete Email Inboxes
- Standard CRUD operations
- View received email count
- Configure webhook and tagger

### 10.3 Sending Emails

#### Send Email
**Endpoint:** `POST /api/v1/emails/send`

**Using Template:**
```json
{
  "to_email": "customer@example.com",
  "template_name": "welcome_email",
  "template_variables": {
    "user_name": "John Doe",
    "company_name": "ACME Corp"
  },
  "from_email": "noreply@company.com",
  "cc": ["manager@company.com"],
  "bcc": ["archive@company.com"],
  "attachments": [
    {
      "filename": "guide.pdf",
      "content": "base64_encoded_content",
      "content_type": "application/pdf"
    }
  ]
}
```

**Direct Content:**
```json
{
  "to_email": "customer@example.com",
  "subject": "Order Confirmation",
  "html_content": "<html><body><h1>Thank you for your order!</h1></body></html>",
  "text_content": "Thank you for your order!",
  "from_email": "orders@company.com"
}
```

**Features:**
- Template or direct content
- CC and BCC support
- Attachments (base64 encoded)
- HTML and plain text
- SMTP delivery
- Delivery status tracking
- Email record in database

**Statuses:**
- `pending` - Queued for sending
- `sent` - Successfully sent
- `failed` - Delivery failed
- `bounced` - Hard bounce
- `complained` - Spam complaint

**Permission:** `sinas.email.send:own`

#### List Emails
**Endpoint:** `GET /api/v1/emails/`

**Query Parameters:**
- `page` - Page number (default: 1)
- `per_page` - Results per page (1-100, default: 50)
- `to_email` - Filter by recipient
- `from_email` - Filter by sender
- `status_filter` - Filter by status
- `direction` - Filter by direction (inbound/outbound)
- `start_date` - Filter by date range
- `end_date` - Filter by date range

**Response:**
```json
{
  "emails": [...],
  "total": 150,
  "page": 1,
  "per_page": 50
}
```

#### List Received Emails
**Endpoint:** `GET /api/v1/emails/received`

- Filter inbound emails only
- Same query parameters as list
- Filter by recipient inbox

#### Get Email
**Endpoint:** `GET /api/v1/emails/{email_id}`

- Get complete email details
- Includes content, attachments, metadata
- View delivery status

#### Delete Email
**Endpoint:** `DELETE /api/v1/emails/{email_id}`

- Remove email record
- Permanent deletion

**Permission:** `sinas.email.delete:own`

#### Resend Email
**Endpoint:** `POST /api/v1/emails/{email_id}/resend`

- Resend failed or sent email
- Creates new email record
- Only for outbound emails
- Preserves original content and attachments

**Permission:** `sinas.email.send:own`

---

## 11. Context Store

Key-value store for AI context injection and semantic memory.

### 11.1 Context Management

#### Create Context
**Endpoint:** `POST /api/v1/contexts`

**Request:**
```json
{
  "namespace": "customer-support",
  "key": "return-policy",
  "value": "Our return policy allows returns within 30 days...",
  "visibility": "group",
  "group_id": "uuid",
  "assistant_id": "uuid",
  "description": "Return policy for customer support",
  "tags": ["policy", "returns"],
  "relevance_score": 0.95,
  "expires_at": "2026-01-15T00:00:00Z"
}
```

**Visibility Levels:**
- `private` - Only visible to creating user
- `group` - Visible to group members
- `public` - Visible to all (future)

**Features:**
- Namespace organization
- Key-value pairs
- Relevance scoring for ranking
- Tag-based retrieval
- Optional expiration
- Assistant-specific contexts
- Group or user scoping

**Permission:** `sinas.contexts.create:own` or `:group`

#### List Contexts
**Endpoint:** `GET /api/v1/contexts`

**Query Parameters:**
- `namespace` - Filter by namespace
- `visibility` - Filter by visibility
- `assistant_id` - Filter by assistant
- `tags` - Comma-separated tag list
- `search` - Search in keys and descriptions
- `skip`, `limit` - Pagination

**Access Control:**
- Users see own contexts and group contexts they have access to
- Admins see all contexts
- Expired contexts filtered out

**Permission:** `sinas.contexts.read:own`, `:group`, or `:all`

#### Get Context
**Endpoint:** `GET /api/v1/contexts/{context_id}`

- Get specific context entry
- Permission checks based on ownership and visibility
- 404 if expired

#### Update Context
**Endpoint:** `PUT /api/v1/contexts/{context_id}`

**Request:**
```json
{
  "value": "Updated policy text...",
  "description": "Updated description",
  "tags": ["policy", "returns", "updated"],
  "relevance_score": 0.98,
  "expires_at": null
}
```

- Update value, description, tags, relevance, expiration
- Cannot change namespace or key
- Permission checks based on ownership

**Permission:** `sinas.contexts.update:own`, `:group`, or `:all`

#### Delete Context
**Endpoint:** `DELETE /api/v1/contexts/{context_id}`

- Permanent deletion
- Permission checks based on ownership

**Permission:** `sinas.contexts.delete:own`, `:group`, or `:all`

### 11.2 Context Injection

Contexts are automatically injected into AI conversations when enabled.

**Assistant Configuration:**
```json
{
  "context_namespaces": ["customer-support", "product-info"],
  ...
}
```

**Message Request:**
```json
{
  "content": "What is your return policy?",
  "inject_context": true,
  "context_namespaces": ["customer-support"],
  "context_limit": 5
}
```

**Context Selection:**
1. Filters by namespace(s)
2. Filters by assistant_id if specified
3. Ranks by relevance_score
4. Limits to top N contexts
5. Injects into system message

**Injected Format:**
```
Context Information:

[customer-support/return-policy]
Our return policy allows returns within 30 days...

[customer-support/shipping-info]
We offer free shipping on orders over $50...
```

---

## 12. MCP Integration

Model Context Protocol (MCP) server integration for extending assistant capabilities.

### 12.1 MCP Servers

#### Register MCP Server
**Endpoint:** `POST /api/v1/mcp-servers`

**Request:**
```json
{
  "name": "filesystem",
  "description": "File system operations",
  "server_url": "http://localhost:3000/mcp",
  "is_active": true
}
```

**Features:**
- Register external MCP servers
- Tools discovered from server
- Enable/disable servers
- Server health monitoring

**Permission:** `sinas.mcp.servers.create:group`

#### List MCP Servers
**Endpoint:** `GET /api/v1/mcp-servers`

- List registered servers
- View available tools per server

#### Get MCP Server
**Endpoint:** `GET /api/v1/mcp-servers/{server_id}`

- Get server details and tools

#### Update/Delete MCP Server
- Standard CRUD operations
- Deactivate server to disable all tools

### 12.2 MCP Tools

Tools are automatically discovered from MCP servers and made available to assistants.

**Assistant Configuration:**
```json
{
  "enabled_mcp_tools": ["filesystem.read_file", "filesystem.write_file"],
  "mcp_tool_parameters": {
    "filesystem.read_file": {
      "base_path": "/data"
    }
  }
}
```

**Tool Invocation:**
- Assistant requests tool call
- SINAS proxies request to MCP server
- Response returned to assistant
- Tool calls logged in message history

---

## 13. Request Logging & Analytics

### 13.1 Request Logs

All HTTP requests logged to ClickHouse for analytics.

**Logged Data:**
- Timestamp
- Method, path, status code
- Request/response body (configurable)
- Duration (ms)
- User ID
- IP address
- User agent
- Permission used
- Error details

#### Get Request Logs
**Endpoint:** `GET /api/v1/request-logs`

**Query Parameters:**
- `start_date` - Filter by date range
- `end_date` - Filter by date range
- `user_id` - Filter by user
- `method` - Filter by HTTP method
- `status_code` - Filter by status
- `path` - Filter by path pattern
- `limit` - Max results

**Response:**
```json
{
  "logs": [
    {
      "timestamp": "2025-01-15T10:00:00Z",
      "method": "POST",
      "path": "/api/v1/functions",
      "status_code": 201,
      "duration_ms": 145,
      "user_id": "uuid",
      "permission_used": "sinas.functions.create:own",
      "ip_address": "192.168.1.1"
    }
  ],
  "total": 1000
}
```

**Permission:** `sinas.request_logs.read:all`

### 13.2 Analytics

**Use Cases:**
- API usage monitoring
- Performance tracking
- Error rate analysis
- User activity auditing
- Permission usage patterns
- Quota enforcement

**ClickHouse Integration:**
- High-performance time-series storage
- Efficient aggregation queries
- Real-time analytics
- Configurable retention

---

## Appendix

### A. Environment Variables

**Required:**
- `SECRET_KEY` - JWT signing
- `ENCRYPTION_KEY` - Datasource credential encryption
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_DOMAIN` - Email

**Database:**
- `DATABASE_URL` - PostgreSQL
- `REDIS_URL` - Redis
- `CLICKHOUSE_HOST`, `CLICKHOUSE_PORT` - ClickHouse (optional)
- `MONGODB_URI` - MongoDB (document content)

**LLM Providers:**
- `OPENAI_API_KEY`
- `LOCAL_LLM_ENDPOINT`
- `DEFAULT_LLM_PROVIDER`

**Admin:**
- `SUPERADMIN_EMAIL` - Auto-create admin

**Function Execution:**
- `FUNCTION_TIMEOUT` - Max execution time (default: 300s)
- `MAX_FUNCTION_MEMORY` - Max memory (default: 512MB)
- `ALLOW_PACKAGE_INSTALLATION` - Allow pip install (default: true)

### B. Default Groups

Created on startup:
- **GuestUsers** - Minimal permissions
- **Users** - Standard user permissions
- **Admins** - Full system access (`sinas.*:all`)

### C. Common Workflows

**1. Create AI Assistant with Tools:**
```
1. POST /api/v1/functions - Create function
2. POST /api/v1/webhooks - Create webhook
3. POST /api/v1/assistants - Create assistant with enabled_webhooks
4. POST /api/v1/chats - Create chat
5. POST /api/v1/chats/{id}/messages - Send message
```

**2. Setup Ontology with External Data:**
```
1. POST /api/v1/ontology/datasources - Add datasource
2. POST /api/v1/ontology/concepts - Create concept
3. POST /api/v1/ontology/properties - Add properties
4. POST /api/v1/ontology/queries - Configure query
5. POST /api/v1/ontology/endpoints - Create API endpoint
6. POST /api/v1/ontology/execute/{route} - Query data
```

**3. Document Management with Auto-Tagging:**
```
1. POST /api/v1/tags/definitions - Define tags
2. POST /api/v1/assistants - Create tagging assistant
3. POST /api/v1/tags/tagger-rules - Create tagger rule
4. POST /api/v1/documents/folders - Create folder
5. POST /api/v1/documents - Upload documents (auto-tagged)
6. GET /api/v1/documents?tags=[...] - Query by tags
```

**4. Scheduled Reports via Email:**
```
1. POST /api/v1/functions - Create report function
2. POST /api/v1/email-templates - Create email template
3. POST /api/v1/schedules - Schedule daily execution
4. Function sends email via internal API
```

### D. Security Best Practices

1. **API Keys:**
   - Use separate keys per application
   - Rotate keys regularly
   - Minimum required permissions
   - Set expiration dates

2. **Permissions:**
   - Follow least privilege principle
   - Use group permissions for teams
   - Regular permission audits
   - Monitor permission usage logs

3. **Functions:**
   - Code review before deployment
   - Limit package installations
   - Set appropriate timeouts
   - Monitor execution logs

4. **Webhooks:**
   - Enable authentication
   - Validate input data
   - Rate limiting
   - Monitor for abuse

5. **Data:**
   - Encrypt datasource credentials
   - Use group-based access control
   - Regular backups
   - Audit data access logs

---

## 14. Declarative Configuration

### 14.1 Overview

Declarative configuration allows defining SINAS resources in YAML files that can be applied idempotently, similar to Kubernetes and Terraform. This enables GitOps workflows, version-controlled infrastructure, and consistent environments across deployments.

**Key Features:**
- **Infrastructure as Code** - All resources defined in version-controlled YAML
- **Idempotent Operations** - Apply same config multiple times safely
- **Change Detection** - Updates existing resources when config changes
- **Resource Tracking** - Tracks which resources are managed by config
- **Environment Variables** - Support for `${ENV_VAR}` interpolation
- **Validation** - Schema validation before applying
- **Dry Run** - Preview changes before applying

### 14.2 YAML Schema

#### Root Structure

```yaml
apiVersion: sinas.co/v1
kind: SinasConfig
metadata:
  name: my-sinas-config
  description: Production configuration
  labels:
    environment: production
    team: platform

spec:
  # Resource definitions
  groups: [...]
  users: [...]
  llmProviders: [...]
  datasources: [...]
  ontology: {...}
  functions: [...]
  assistants: [...]
  schedules: [...]
  webhooks: [...]
  emailTemplates: [...]
  emailInboxes: [...]
  tagDefinitions: [...]
  taggerRules: [...]
  folders: [...]
```

#### Groups

```yaml
spec:
  groups:
    - name: Engineering
      description: Engineering team
      emailDomain: eng.company.com
      permissions:
        - key: sinas.functions.*:group
          value: true
        - key: sinas.ontology.*:group
          value: true
```

#### Users

```yaml
spec:
  users:
    - email: admin@company.com
      isActive: true
      groups:
        - Admins
      permissions:
        - key: sinas.*:all
          value: true
```

#### LLM Providers

```yaml
spec:
  llmProviders:
    - name: openai
      type: openai
      apiKey: ${OPENAI_API_KEY}  # Environment variable interpolation
      models:
        - gpt-4
        - gpt-4-turbo
        - gpt-3.5-turbo
      isActive: true

    - name: ollama_local
      type: ollama
      endpoint: http://localhost:11434
      models:
        - llama2
        - mistral
      isActive: true
```

#### Datasources

```yaml
spec:
  datasources:
    - name: main_postgres
      type: postgres
      connectionString: ${DATABASE_URL}
      defaultDatabase: sinas
      defaultSchema: public
      isReadOnly: false
      groupName: Admins
      permissions:
        ddl: true

    - name: external_crm
      type: postgres
      connectionString: ${CRM_DATABASE_URL}
      defaultSchema: public
      isReadOnly: true
      groupName: Engineering
```

#### Ontology

```yaml
spec:
  ontology:
    namespaces:
      - name: crm
        description: CRM data model

    concepts:
      - namespace: crm
        name: Customer
        displayName: Customer
        description: Customer entity
        groupName: Engineering
        properties:
          - name: id
            displayName: ID
            dataType: UUID
            isIdentifier: true
            isRequired: true

          - name: fullName
            displayName: Full Name
            dataType: TEXT
            isRequired: true

          - name: email
            displayName: Email
            dataType: TEXT
            isRequired: true

          - name: phone
            displayName: Phone
            dataType: TEXT
            isRequired: false

          - name: status
            displayName: Status
            dataType: TEXT
            defaultValue: active

          - name: createdAt
            displayName: Created At
            dataType: DATETIME
            defaultValue: NOW()

    tableMappings:
      - conceptRef: crm.Customer
        datasourceName: main_postgres
        tableName: customers
        columnMappings:
          fullName: full_name
          createdAt: created_at
        userOwnershipColumn: user_email
        groupOwnershipColumn: department

    externalIdentityMappings:
      - userEmail: alice@company.com
        datasourceName: external_crm
        externalUserRef: alice@company.com

    externalGroupMappings:
      - groupName: Engineering
        datasourceName: external_crm
        externalGroupRef: Engineering
```

#### Functions

```yaml
spec:
  functions:
    - name: send_email
      description: Send an email to a recipient
      groupName: Engineering
      code: |
        def send_email(to: str, subject: str, body: str):
            """Send an email to a recipient"""
            print(f"Sending email to {to}: {subject}")
            return {"status": "sent", "to": to}
      inputSchema:
        type: object
        properties:
          to:
            type: string
            format: email
          subject:
            type: string
          body:
            type: string
        required:
          - to
          - subject
          - body
      outputSchema:
        type: object
        properties:
          status:
            type: string
          to:
            type: string
      requirements:
        - requests>=2.28.0
      tags:
        - email
        - communication

    - name: create_customer
      description: Create a new customer in CRM
      groupName: Engineering
      code: |
        def create_customer(full_name: str, email: str, phone: str = None, status: str = "active"):
            """Create a new customer"""
            # Implementation here
            return {"id": "uuid", "full_name": full_name, "email": email}
      inputSchema:
        type: object
        properties:
          full_name:
            type: string
          email:
            type: string
            format: email
          phone:
            type: string
          status:
            type: string
        required:
          - full_name
          - email
```

#### Assistants

```yaml
spec:
  assistants:
    - name: CRM Assistant
      description: Helps manage CRM data
      groupName: Engineering
      llmProviderName: openai
      model: gpt-4
      temperature: 0.7
      systemPrompt: |
        You are a helpful CRM assistant. You can help users manage customers,
        contacts, and companies. Use the available tools to query and update data.
      enabledWebhooks: []
      enabledMcpTools: []
      enabledFunctions:
        - send_email
        - create_customer
      contextNamespaces:
        - customer-support
      ontologyNamespaces:
        - crm
      ontologyConcepts:
        - crm.Customer
        - crm.Contact
        - crm.Company

    - name: General Assistant
      description: General-purpose assistant
      groupName: Users
      llmProviderName: openai
      model: gpt-4-turbo
      temperature: 0.7
      systemPrompt: You are a helpful assistant.
      enabledFunctions:
        - send_email
```

#### Webhooks

```yaml
spec:
  webhooks:
    - path: customer/created
      functionName: send_email
      httpMethod: POST
      description: Notify team when customer created
      requiresAuth: true
      groupName: Engineering
      defaultValues:
        subject: New Customer Created
        body: A new customer has been created
```

#### Schedules

```yaml
spec:
  schedules:
    - name: daily_report
      functionName: generate_daily_report
      description: Generate daily sales report
      cronExpression: "0 9 * * *"
      timezone: America/New_York
      groupName: Engineering
      inputData:
        report_type: sales
        recipients:
          - team@company.com
```

#### Email Templates

```yaml
spec:
  emailTemplates:
    - name: welcome_email
      subject: Welcome to {{company_name}}!
      htmlTemplate: |
        <html>
          <body>
            <h1>Hello {{user_name}}</h1>
            <p>Welcome to our service!</p>
          </body>
        </html>
      textTemplate: |
        Hello {{user_name}}

        Welcome to our service!
      description: New user welcome email
      groupName: Engineering
      variables:
        - user_name
        - company_name
```

#### Email Inboxes

```yaml
spec:
  emailInboxes:
    - emailAddress: support@company.com
      description: Customer support inbox
      webhookName: process_support_email
      taggerRuleName: support_auto_tagger
      isActive: true
      groupName: Engineering
```

#### Tag Definitions

```yaml
spec:
  tagDefinitions:
    - name: priority
      displayName: Priority Level
      valueType: enum
      appliesTo:
        - document
        - email
      description: Priority level
      allowedValues:
        - low
        - medium
        - high
        - critical
      isRequired: false
      groupName: Engineering

    - name: document_type
      displayName: Document Type
      valueType: enum
      appliesTo:
        - document
      allowedValues:
        - invoice
        - contract
        - report
        - memo
      groupName: Engineering
```

#### Tagger Rules

```yaml
spec:
  taggerRules:
    - name: document_auto_tagger
      description: Automatically tag documents
      scopeType: folder
      folderName: Default Documents
      assistantName: Document Tagger
      tagDefinitions:
        - priority
        - document_type
      autoTrigger: true
      isActive: true
      groupName: Engineering
```

#### Folders

```yaml
spec:
  folders:
    - name: Default Documents
      description: Default document folder
      ownerType: group
      groupName: Engineering
      parentFolderName: null
      autoTaggerRuleName: document_auto_tagger
```

### 14.3 API Endpoints

#### Apply Configuration

**Endpoint:** `POST /api/v1/config/apply`

**Request:**
```json
{
  "config": "... YAML content ...",
  "dryRun": false,
  "force": false
}
```

**Features:**
- **Idempotent** - Can apply same config multiple times
- **Change Detection** - Only updates resources that changed
- **Dry Run** - Preview changes without applying
- **Force** - Skip validation warnings (use carefully)
- **Transaction** - All changes applied atomically (rollback on error)

**Response:**
```json
{
  "success": true,
  "summary": {
    "created": {
      "groups": 2,
      "users": 1,
      "functions": 3,
      "assistants": 2
    },
    "updated": {
      "datasources": 1,
      "ontology.concepts": 2
    },
    "unchanged": {
      "llmProviders": 2
    },
    "deleted": {
      "webhooks": 1
    }
  },
  "changes": [
    {
      "action": "create",
      "resourceType": "function",
      "resourceName": "send_email",
      "details": "Created new function"
    },
    {
      "action": "update",
      "resourceType": "ontology.concept",
      "resourceName": "crm.Customer",
      "changes": {
        "properties": {
          "added": ["phone"],
          "removed": [],
          "modified": ["email"]
        }
      }
    }
  ],
  "errors": [],
  "warnings": [
    "LLM provider 'openai' API key not set in environment"
  ]
}
```

**Permission:** `sinas.config.apply:all` (admin only)

#### Get Current Configuration

**Endpoint:** `GET /api/v1/config/export`

**Query Parameters:**
- `includeSecrets` - Include encrypted secrets (default: false)
- `managedOnly` - Only export config-managed resources (default: false)

**Response:** YAML configuration file representing current state

**Features:**
- Export current configuration as YAML
- Optionally exclude secrets
- Filter to only config-managed resources
- Use for backup or migration

**Permission:** `sinas.config.read:all`

#### Validate Configuration

**Endpoint:** `POST /api/v1/config/validate`

**Request:**
```json
{
  "config": "... YAML content ..."
}
```

**Response:**
```json
{
  "valid": false,
  "errors": [
    {
      "path": "spec.functions[0].code",
      "message": "Invalid Python syntax: unexpected indent"
    }
  ],
  "warnings": [
    {
      "path": "spec.llmProviders[0].apiKey",
      "message": "Environment variable OPENAI_API_KEY not set"
    }
  ]
}
```

**Permission:** `sinas.config.validate:all`

### 14.4 Resource Management

#### Resource Tracking

All resources created by declarative config are marked with:
- `managed_by: config`
- `config_name: {metadata.name}`
- `config_checksum: {resource_checksum}`

This allows:
1. Identifying config-managed resources
2. Detecting changes in config vs. actual state
3. Preventing manual modification of managed resources
4. Cleanup of removed resources

#### Idempotency Strategy

**Create:**
1. Check if resource exists (by unique identifier)
2. If exists and `managed_by: config`, update if changed
3. If exists and not managed, error (conflict)
4. If not exists, create

**Update:**
1. Calculate resource checksum from YAML
2. Compare with stored checksum
3. If different, update resource and checksum
4. If same, skip (no-op)

**Delete:**
1. Resources in database but not in config
2. Only delete if `managed_by: config`
3. Optionally protect critical resources

#### Change Detection

Hash-based change detection:
```python
def calculate_resource_hash(resource_data: dict) -> str:
    """Calculate stable hash of resource definition"""
    # Sort keys for consistent hashing
    sorted_data = json.dumps(resource_data, sort_keys=True)
    return hashlib.sha256(sorted_data.encode()).hexdigest()
```

Stored in resource metadata:
```sql
ALTER TABLE functions ADD COLUMN config_checksum TEXT;
ALTER TABLE assistants ADD COLUMN config_checksum TEXT;
-- ... for all resource types
```

#### Conflict Resolution

**Manual Changes:**
If a config-managed resource is modified manually:
1. Detect checksum mismatch
2. Warn user of conflict
3. Optionally:
   - Overwrite with config (default)
   - Skip update (preserve manual changes)
   - Fail and require manual resolution

**Resource References:**
Resources reference each other by name:
- `functionName: send_email` → resolve to function ID
- `groupName: Engineering` → resolve to group ID
- `datasourceName: main_postgres` → resolve to datasource ID

### 14.5 Implementation Details

#### Database Schema Changes

```sql
-- Add config tracking columns to all resource tables
ALTER TABLE groups ADD COLUMN managed_by TEXT;
ALTER TABLE groups ADD COLUMN config_name TEXT;
ALTER TABLE groups ADD COLUMN config_checksum TEXT;

ALTER TABLE users ADD COLUMN managed_by TEXT;
ALTER TABLE users ADD COLUMN config_name TEXT;
ALTER TABLE users ADD COLUMN config_checksum TEXT;

-- ... repeat for all resource tables
```

#### Environment Variable Interpolation

```python
def interpolate_env_vars(value: str) -> str:
    """Replace ${VAR_NAME} with environment variable value"""
    pattern = r'\$\{([A-Z_][A-Z0-9_]*)\}'

    def replacer(match):
        var_name = match.group(1)
        if var_name not in os.environ:
            raise ValueError(f"Environment variable {var_name} not set")
        return os.environ[var_name]

    return re.sub(pattern, replacer, value)
```

#### Validation Pipeline

1. **YAML Parsing** - Parse YAML and check syntax
2. **Schema Validation** - Validate against JSON schema
3. **Reference Validation** - Check all references resolve
4. **Semantic Validation** - Business logic validation
5. **Conflict Detection** - Check for conflicts with existing resources

#### Application Order

Resources applied in dependency order:
1. Groups (no dependencies)
2. Users (depends on groups)
3. LLM Providers (no dependencies)
4. Datasources (depends on groups)
5. Ontology (depends on datasources, groups)
6. Functions (depends on groups)
7. Assistants (depends on llm providers, functions, ontology)
8. Webhooks (depends on functions)
9. Schedules (depends on functions)
10. Email Templates (depends on groups)
11. Email Inboxes (depends on webhooks, groups)
12. Tag Definitions (depends on groups)
13. Tagger Rules (depends on assistants, tag definitions)
14. Folders (depends on groups, tagger rules)

### 14.6 Startup Integration

#### Auto-Apply on Startup

**Environment Variable:**
```bash
CONFIG_FILE=/path/to/sinas-config.yaml
AUTO_APPLY_CONFIG=true
```

**Startup Sequence:**
```python
async def startup_event():
    # ... existing startup ...

    # Apply declarative config if specified
    config_file = os.getenv("CONFIG_FILE")
    auto_apply = os.getenv("AUTO_APPLY_CONFIG", "false").lower() == "true"

    if config_file and auto_apply:
        logger.info(f"Auto-applying config from {config_file}")
        with open(config_file) as f:
            config_yaml = f.read()

        result = await apply_config(config_yaml, dry_run=False)
        if not result.success:
            logger.error(f"Config application failed: {result.errors}")
            raise RuntimeError("Failed to apply startup config")

        logger.info(f"Config applied successfully: {result.summary}")
```

#### Replace Default Data

Current `app/services/default_data.py` can be replaced with:
`config/default-data.yaml`

```yaml
apiVersion: sinas.co/v1
kind: SinasConfig
metadata:
  name: default-demo-data
  description: Default data for development and demo

spec:
  # All default data defined here instead of Python code
  ...
```

Set in development:
```bash
CONFIG_FILE=config/default-data.yaml
AUTO_APPLY_CONFIG=true
ENABLE_DEFAULT_DATA=false  # Disable old approach
```

### 14.7 Example Workflows

#### GitOps Deployment

```bash
# 1. Define infrastructure in Git
git clone https://github.com/company/sinas-config.git
cd sinas-config

# 2. Edit config
vim production.yaml

# 3. Validate before commit
curl -X POST http://localhost:8000/api/v1/config/validate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"config\": \"$(cat production.yaml)\"}"

# 4. Commit and push
git add production.yaml
git commit -m "Add new CRM functions"
git push

# 5. CI/CD applies config
# In CI pipeline:
curl -X POST http://localhost:8000/api/v1/config/apply \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"config\": \"$(cat production.yaml)\", \"dryRun\": false}"
```

#### Multi-Environment Management

```
config/
├── base.yaml              # Shared config
├── dev.yaml               # Dev overrides
├── staging.yaml           # Staging overrides
└── production.yaml        # Production config
```

**base.yaml:**
```yaml
apiVersion: sinas.co/v1
kind: SinasConfig
metadata:
  name: base-config

spec:
  groups:
    - name: Engineering
      # ...

  functions:
    - name: send_email
      # ... shared function definition
```

**production.yaml:**
```yaml
apiVersion: sinas.co/v1
kind: SinasConfig
metadata:
  name: production-config
  extends: base-config  # Inherit from base

spec:
  llmProviders:
    - name: openai
      apiKey: ${PROD_OPENAI_API_KEY}

  datasources:
    - name: main_postgres
      connectionString: ${PROD_DATABASE_URL}
```

#### Local Development

```bash
# Local dev config
cat > local-dev.yaml <<EOF
apiVersion: sinas.co/v1
kind: SinasConfig
metadata:
  name: local-dev

spec:
  llmProviders:
    - name: ollama
      type: ollama
      endpoint: http://localhost:11434
      models:
        - llama2

  datasources:
    - name: dev_postgres
      type: postgres
      connectionString: postgresql://localhost/sinas_dev
EOF

# Apply locally
docker-compose up -d
docker exec -it sinas-app curl -X POST http://localhost:8000/api/v1/config/apply \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"config\": \"$(cat local-dev.yaml)\"}"
```

### 14.8 Migration from Default Data

**Before (Python):**
```python
# app/services/default_data.py
async def create_default_data(db: AsyncSession):
    # Create datasource
    datasource = Datasource(
        name="managed_datasource",
        type="postgres",
        conn_string=managed_conn_string,
        ...
    )
    db.add(datasource)

    # Create concept
    customer_concept = Concept(
        namespace="crm",
        name="Customer",
        ...
    )
    db.add(customer_concept)
    # ... many lines of imperative code
```

**After (YAML):**
```yaml
# config/default-data.yaml
apiVersion: sinas.co/v1
kind: SinasConfig
metadata:
  name: default-data

spec:
  datasources:
    - name: managed_datasource
      type: postgres
      connectionString: ${MANAGED_DATABASE_URL}
      # ...

  ontology:
    concepts:
      - namespace: crm
        name: Customer
        # ...
```

**Benefits:**
- ✅ Version controlled and diffable
- ✅ Declarative and readable
- ✅ Idempotent and safe to re-apply
- ✅ Can be shared across environments
- ✅ Easier to review and audit
- ✅ GitOps compatible

---
