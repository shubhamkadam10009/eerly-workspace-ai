# Eerly Workspace AI

AI Engineer Take-Home Assessment - Problem A: Workspace Consultant

## Overview

Eerly Workspace AI is a production-oriented AI workspace consultant that analyzes user-provided documents, selects and loads task-specific skills, performs workspace operations, generates a deliverable, validates the result, and pauses for explicit human approval before final delivery.

The system is built around secure per-user workspace isolation, durable LangGraph execution, PostgreSQL persistence, human-in-the-loop approval, live SSE progress events, artifact delivery, structured logging, correlation IDs, and automated testing.

## Assessment Problem

### Problem A - Workspace Consultant

The system acts as an AI consultant over a user's private workspace.

A typical execution is:

1. Authenticate the user.
2. Analyze the user's request.
3. Discover applicable SKILL.md skills.
4. Load only the required skills.
5. Inspect the user's workspace.
6. Read relevant source files.
7. Analyze the source material.
8. Generate an output.
9. Validate the generated output.
10. Pause for human approval.
11. Allow the human to approve, edit, or reject.
12. Deliver the approved artifact.
13. Persist artifact metadata.

The execution state is checkpointed in PostgreSQL so an interrupted workflow can be resumed.

## Key Capabilities

- FastAPI HTTP API with typed Pydantic request and response models
- LangGraph-based agent orchestration
- PostgreSQL-backed durable checkpoints
- SQLAlchemy application persistence
- Alembic database migrations
- JWT bearer authentication
- Secure per-user filesystem isolation
- Path traversal and symlink escape protection
- Real filesystem tools for listing, reading, and writing files
- On-demand SKILL.md discovery and loading
- Human approval using LangGraph interrupt()
- Approve, edit, and reject workflow
- SSE live progress streaming
- Artifact generation and delivery
- Structured JSON logging
- Request correlation IDs
- Health and database health endpoints
- Docker Compose deployment
- Persistent PostgreSQL Docker volume
- Unit, integration, security, and durability tests

## Architecture

```text
                         +----------------------+
                         |      Streamlit       |
                         |   Thin Frontend UI   |
                         +----------+-----------+
                                    |
                              HTTP / SSE
                                    |
                                    v
                         +----------------------+
                         |       FastAPI        |
                         |    HTTP API Layer    |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |   JWT Authentication |
                         |   Trusted user_id    |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |      LangGraph       |
                         |   Agent Workflow     |
                         +----------+-----------+
                                    |
              +---------------------+---------------------+
              |                     |                     |
              v                     v                     v
      Request Analysis       Skill Discovery       Workspace Tools
              |                     |                     |
              v                     v                     v
      Source Reading          Skill Loading        Secure File I/O
              |                     |
              +----------+----------+
                         |
                         v
                  Content Analysis
                         |
                         v
                 Output Generation
                         |
                         v
                 Output Validation
                         |
                         v
                  Human Approval
                   +-----+-----+
                   |     |     |
                Approve Edit  Reject
                   |     |     |
                   |     v     |
                   | Revalidate|
                   |     |     |
                   +--+--+     |
                      |        |
                      v        v
                Artifact     END
                Delivery
                      |
                      v
              PostgreSQL Metadata