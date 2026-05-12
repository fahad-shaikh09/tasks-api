# AGENTS.md

## Project Overview

This project is an AI-enabled task management platform built using:

* Frontend: Python + Jinja templates
* Backend API: FastAPI
* Notifications Microservice: FastAPI
* Dapr sidecars for service invocation and pub/sub
* Kafka for asynchronous event-driven communication
* Kubernetes deployment model

The architecture is being transformed from a traditional backend-driven application into an AI-agent-based architecture using:

* OpenAI Agents SDK
* MCP (Model Context Protocol)
* Python-based MCP server

The goal is to convert the current backend API into an MCP server that exposes task management capabilities as tools consumable by AI agents.

The frontend and notifications microservice will remain mostly unchanged initially.

---

# Target Architecture

## Current Components

### Frontend

* Python application using Jinja templates
* Provides UI for users
* Will continue to exist initially
* May later integrate directly with agent APIs

### Backend API (To Be Converted)

Current responsibilities:

* Task CRUD operations
* Business logic
* Kafka event publishing
* Dapr service invocation

Target state:

* Become an MCP server
* Expose tools/resources/prompts via MCP
* Serve AI agents instead of only REST clients

### Notification Microservice

* FastAPI microservice
* Consumes Kafka events
* Sends notifications/emails/messages
* Will remain unchanged initially
* Can later expose its own MCP tools if needed

---

# High-Level Architecture Goals

The AI agent should:

1. Accept natural language requests from users
2. Use OpenAI Agents SDK
3. Discover and call MCP tools
4. Interact with the task management MCP server
5. Trigger workflows/events
6. Continue using Kafka + Dapr underneath

Example:

User:

> Create a task for tomorrow to review Kubernetes logs

Agent flow:

1. Agent interprets intent
2. Calls MCP tool `create_task`
3. MCP server validates request
4. Existing business logic executes
5. Kafka event emitted
6. Notification microservice processes event
7. User receives notification

---

# Migration Strategy

## Phase 1 — Convert Backend to MCP Server

Primary objective:

* Keep existing business logic
* Wrap functionality as MCP tools
* Avoid major refactoring initially

### Existing Backend Endpoints

Examples:

* POST /tasks
* GET /tasks
* PUT /tasks/{id}
* DELETE /tasks/{id}

### MCP Equivalent Tools

Expose as:

* create_task
* list_tasks
* get_task
* update_task
* delete_task

Important:

* Reuse existing services/business layer where possible
* Avoid duplicating logic
* MCP tools should call the same internal service methods currently used by FastAPI routes

---

# MCP Server Requirements

The MCP server should:

* Be implemented in Python
* Use FastMCP or official MCP Python SDK
* Expose task management tools
* Support structured tool schemas
* Return clean JSON responses
* Reuse existing authentication logic where possible
* Integrate with existing Kafka publishing logic
* Continue supporting Dapr sidecar communication

---

# Expected MCP Tools

## create_task

Description:
Create a new task.

Input:

* title
* description
* due_date
* priority
* assigned_to

Behavior:

* Validate input
* Store task
* Publish Kafka event
* Trigger notification workflow

---

## list_tasks

Description:
List tasks with optional filtering.

Optional filters:

* status
* assigned_to
* due_before
* priority

---

## get_task

Description:
Fetch a single task by ID.

---

## update_task

Description:
Update task details.

Supports:

* status updates
* due date changes
* reassignment
* metadata updates

Should emit update events.

---

## delete_task

Description:
Delete or archive tasks.

Should publish deletion events if required.

---

# Event-Driven Requirements

Kafka remains the primary async event bus.

The MCP server should continue publishing events such as:

* task.created
* task.updated
* task.deleted
* task.completed

Notification service continues consuming these events.

Do not remove Kafka during initial migration.

---

# Dapr Requirements

The platform already uses Dapr sidecars.

The MCP server should continue leveraging Dapr for:

* Service invocation
* Pub/Sub abstraction
* State management (if already used)
* Observability integration

Prefer reusing existing Dapr client integrations.

---

# AI Agent Requirements

The user-facing AI agent should:

* Use OpenAI Agents SDK
* Connect to MCP server
* Discover tools dynamically
* Execute task workflows
* Handle conversational interactions
* Maintain short-term conversation context

Examples:

User:

> Show my pending tasks

User:

> Mark the Kubernetes deployment task as completed

User:

> Create a high priority task for tomorrow

---

# Recommended Repository Structure

```text
project-root/
│
├── frontend/
│   └── jinja-ui
│
├── backend-mcp/
│   ├── server.py
│   ├── tools/
│   │   ├── create_task.py
│   │   ├── update_task.py
│   │   ├── delete_task.py
│   │   └── list_tasks.py
│   ├── services/
│   ├── kafka/
│   ├── dapr/
│   ├── models/
│   └── auth/
│
├── notifications-service/
│
├── shared/
│
└── kubernetes/
```

---

# Coding Guidelines

## General Principles

* Keep business logic separated from transport layer
* MCP tool layer should remain thin
* Reuse existing services
* Avoid embedding logic directly inside MCP tool handlers
* Keep functions small and testable

---

## Tool Design

Each MCP tool should:

* Have a clear description
* Use structured input schemas
* Return structured JSON
* Include proper error handling
* Log tool execution
* Support tracing where possible

---

## Error Handling

Tools should:

* Return meaningful validation errors
* Avoid leaking internal stack traces
* Log internal exceptions
* Preserve existing FastAPI validation behavior where reusable

---

# Observability Requirements

Maintain or improve current observability.

Preferred integrations:

* OpenTelemetry
* Dapr tracing
* Structured JSON logging
* Correlation IDs
* Kafka message tracing

Important:

* Tool invocations should be traceable end-to-end
* Correlate:

  * User request
  * Agent action
  * MCP tool call
  * Kafka event
  * Notification processing

---

# Security Requirements

* Preserve existing authentication mechanisms
* Validate authorization for task operations
* Avoid exposing internal-only tools
* Sanitize user-generated content
* Protect MCP endpoints appropriately

Future enhancement:

* Multi-tenant isolation
* Role-based tool access

---

# Deployment Requirements

The system runs in Kubernetes.

Requirements:

* MCP server should run as a containerized service
* Continue sidecar-based Dapr deployment
* Maintain compatibility with existing Kafka infrastructure
* Support rolling deployments
* Support horizontal scaling

---

# Initial Non-Goals

The following are NOT part of the initial migration:

* Replacing Kafka
* Removing Dapr
* Rebuilding frontend
* Multi-agent orchestration
* Long-term memory systems
* Autonomous planning agents
* RAG/vector databases

Focus first on:

* MCP conversion
* Tool exposure
* AI-driven task operations

---

# Suggested MCP Development Approach

Recommended implementation order:

1. Create basic MCP server
2. Expose simple health tool
3. Add list_tasks tool
4. Add create_task tool
5. Reuse existing backend service layer
6. Integrate Kafka publishing
7. Integrate authentication
8. Add observability
9. Connect OpenAI agent
10. Test end-to-end workflows

---

# Example Interaction Flow

## Scenario: Task Creation

User
→ OpenAI Agent
→ MCP tool: create_task
→ Internal service layer
→ Database write
→ Kafka event
→ Notification service
→ User notification

---

# Future Enhancements

Potential future improvements:

* Separate MCP servers per domain
* Notification MCP server
* Calendar integration
* Slack/Teams integration
* AI workflow planning
* Agent memory
* Vector search
* Semantic task search
* Multi-agent orchestration
* Human approval workflows

---

# Important Architectural Principle

The MCP server is not intended to replace all backend logic.

Instead:

* MCP becomes the AI-facing interface layer
* Existing business logic/services remain reusable
* Kafka and Dapr remain core infrastructure
* AI agents become consumers of platform capabilities

This minimizes migration risk while enabling AI-native workflows.
