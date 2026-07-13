# Asynchronous Payment Processing Service

## Event-driven payment processing system built with DDD, Clean Architecture, and CQRS.

<!--toc:start-->
- [Asynchronous Payment Processing Service](#asynchronous-payment-processing-service)
  - [Event-driven payment processing system built with DDD, Clean Architecture, and CQRS.](#event-driven-payment-processing-system-built-with-ddd-clean-architecture-and-cqrs)
  - [Overview](#overview)
  - [Key Features](#key-features)
  - [API Endpoints](#api-endpoints)
    - [Create Payment](#create-payment)
      - [Endpoint: POST /v1/payments](#endpoint-post-v1payments)
- [Error Responses:](#error-responses)
  - [Get Payment](#get-payment)
- [Error Responses:](#error-responses-1)
  - [Environment Variables](#environment-variables)
    - [Example .env](#example-env)
  - [Setup & Run](#setup-run)
    - [Prerequisites](#prerequisites)
    - [Using Docker Compose (Recommended)](#using-docker-compose-recommended)
  - [Testing](#testing)
  - [Payment Flow](#payment-flow)
    - [1. Create Payment (Command)](#1-create-payment-command)
    - [2. Process Payment (Event Handler)](#2-process-payment-event-handler)
    - [3. Send Notification (Event Handler)](#3-send-notification-event-handler)
    - [4. Fetch Pending Tasks (Background Job)](#4-fetch-pending-tasks-background-job)
  - [Key Design Decisions](#key-design-decisions)
    - [Idempotency](#idempotency)
    - [Transactional Outbox](#transactional-outbox)
    - [Circuit Breaker](#circuit-breaker)
    - [Database Resilience](#database-resilience)
  - [Next Steps](#next-steps)
<!--toc:end-->

## Overview 

Asynchronous Payment Processing Service is a monorepo-structured payment gateway built according to principles of Domain-Driven Design (DDD), Clean Architecture, and Command-Query Responsibility Segregation (CQRS).
## Key Features

- Event-Driven Architecture: Payment state transitions emit domain events via RabbitMQ
- Idempotency: Duplicate payment requests prevented via unique idempotency keys
-   Transactional Outbox Pattern: Events committed to database before publishing ensures eventual consistency
-   Circuit Breaker Pattern: Resilient broker communication with automatic failure recovery
-   Async-First: Built on FastAPI + asyncio for high concurrency
-   Dual Interface: HTTP API for payment creation/queries; AMQP consumer for event processing
-   Event Sourcing Ready: Outbox table tracks pending event deliveries; automatic retry logic


| Layer| Purpose| Key Components|
| --------------- | --------------- | --------------- |
| Domain | Business logic, invariants, value objects |  **Payment**, **PaymentDomainEvent**, value objects, PaymentService|
| Application | Use case orchestration, external concerns | Commands, Queries, Event Handlers, Interfaces, Strategies |
| Infrastucture | Technical implementations |  Database, Broker, ORM, Migrations, Logger|
| Presentation | HTTP/AMQP api|  FastAPI routes, AMQP consumers, Schemas, Exception handlers|


Pattern Stack
- DDD: Aggregate Payment encapsulates domain rules and state transitions
- CQRS: Commands (CreatePayment) separated from Queries (GetPayment, FetchPendingTasks)
- Event Sourcing: All state changes emit domain events; events persisted in outbox
- Unit of Work: PaymentUoW coordinates repositories and ensures transactional boundaries
- Circuit Breaker: Prevents cascading failures when broker is unavailable
- Transactional Outbox: Events saved to DB in same transaction as payment; background job publishes to broker


```tree
src/payments/
├── application/                 # Use cases & application services
│   ├── handlers/
│   │   ├── commands/           # Command handlers (CreatePayment)
│   │   ├── events/             # Event handlers (ProcessPayment, SendNotification)
│   │   └── queries/            # Query handlers (GetPayment, FetchPendingTasks)
│   ├── interfaces/             # Abstract contracts
│   │   ├── event_publisher.py
│   │   ├── notifier.py
│   │   ├── outbox_repository.py
│   │   └── uow.py              # Unit of Work interface
│   └── strategies/             # Strategy pattern for notifications
│
├── domain/                      # Business logic layer
│   ├── enums/                  # Currency, Status, TaskStatus
│   ├── value_objects/          # ID, Amount, Key, Timestamp, etc.
│   ├── events.py               # Domain events (PaymentCreatedEvent, etc.)
│   ├── payment.py              # Payment aggregate root
│   ├── repository.py           # Abstract PaymentRepository
│   └── service.py              # PaymentService (domain logic)
│
├── infrastructure/              # Technical implementations
│   ├── broker/
│   │   ├── event_bus.py        # RabbitMQ event publisher with circuit breaker
│   │   └── routes.py           # AMQP exchange/queue configuration
│   ├── database/
│   │   ├── migrations/         # Alembic migrations
│   │   ├── session.py          # SQLAlchemy AsyncSession factory
│   │   ├── uow.py              # PaymentUoW implementation
│   │   ├── payments/           # PaymentRepository implementation
│   │   └── outbox/             # OutboxRepository implementation
│   ├── logger/                 # Logging setup
│   ├── notifications/          # HTTP webhook sender (httpx)
│   └── utils/events/           # Event serialization & rebuilding
│
├── presentation/                # HTTP & AMQP frontends
│   ├── http/
│   │   ├── api/v1/
│   │   │   ├── routes/         # FastAPI route handlers
│   │   │   ├── schemas/        # Request/Response DTOs
│   │   │   └── dependencies/   # Dependency injection
│   │   ├── handlers/           # Exception handlers
│   │   └── factory.py          # FastAPI app factory
│   ├── amqp/
│   │   ├── api/v1/
│   │   │   ├── events/         # AMQP event handlers
│   │   │   └── schemas/        # Event DTOs
│   │   └── factory.py          # AMQP consumer factory
│   ├── main.py                 # HTTP server entry point
│   └── consumer.py             # AMQP consumer entry point
...
src/shared/
└──                             # Shared structs such as Generic Aggregate and ValueObject
```


## API Endpoints
### Create Payment
#### Endpoint: POST /v1/payments

```
Headers:
X-API-Key: <static_api_key>
Idempotency-Key: <unique_uuid>
Content-Type: application/json
```
Request Body:
```JSON
{
  "amount": 123.45,
  "currency": "USD",
  "description": "Invoice ABC-123",
  "metadata": {
    "order_id": "ORD-001",
    "customer_email": "customer@example.com"
  },
  "webhook_url": "https://your-domain.com/webhooks/payment"
}
```
Response Body:
```JSON
{
  "payment_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "PENDING",
  "created_at": "2026-07-13T12:34:56Z"
}
```

# Error Responses:
| Status | Code | Cause |
|--------|------|-------|
| 400 | VALIDATION_ERROR | Invalid amount, currency, or schema |
| 400 | DUPLICATE_PAYMENT | Idempotency key already processed |
| 409 | CONFLICT | Payment already exists for this key |
| 503 | REPOSITORY_UNAVAILABLE | Database unavailable, retry later |
| 500 | INTERNAL_ERROR | Unexpected server error |

## Get Payment

**Endpoint:** `GET /v1/payments/{payment_id}`

**Headers:**
```
X-API-Key: <your_api_key>
```

**Response (200 OK):**
```json
{
  "payment_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "amount": 123.45,
  "currency": "USD",
  "description": "Invoice ABC-123",
  "metadata": {
    "order_id": "ORD-001",
    "customer_email": "customer@example.com"
  },
  "status": "PROCESSED",
  "key": "unique-idempotency-key",
  "created_at": "2026-07-13T12:34:56Z",
  "processed_at": "2026-07-13T12:35:10Z"
}
```

# Error Responses:
| Status | Code | Cause |
|--------|------|-------|
| 401 | UNAUTHORIZED | Missing/invalid API key |
| 404 | NOT_FOUND | Payment ID does not exist |
| 503 | REPOSITORY_UNAVAILABLE | Database unavailable, retry later |

## Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| API_KEY | secret | HTTP API authentication key (required for all endpoints) |
| API_PORT | 8000 | Port for FastAPI HTTP server |
| DB_USER | payments_user | PostgreSQL username |
| DB_PASSWORD | supersecret | PostgreSQL password |
| DB_HOST | localhost | PostgreSQL hostname |
| DB_PORT | 5432 | PostgreSQL port |
| DB_NAME | payments | PostgreSQL database name |
| DB_TYPE | postgresql+asyncpg | SQLAlchemy async driver |
| BROKER_URL | amqp://payments_user:supersecret@localhost:5672/ | RabbitMQ connection URL |
| BROKER_USER | payments_user | RabbitMQ username |
| BROKER_PASS | supersecret | RabbitMQ password |
| BROKER_PORT | 5672 | RabbitMQ port |
| LOG_LEVEL | INFO | Python logging level (DEBUG, INFO, WARNING, ERROR) |
| ENV | DEV | Stage (DEV,STAGE, PROD) |

### Example .env
```bash
# API
API_KEY=secret
API_PORT=8000

# Database
DB_USER=payments_user
DB_PASSWORD=supersecret
DB_NAME=payments
DB_PORT=5432
DB_TYPE=postgresql+asyncpg

# Broker (RabbitMQ)
BROKER_PORT=5672
BROKER_USER=payments_user
BROKER_PASS=supersecret
BROKER_URL="ampq://payments_user:supersecret@rabbitmq:5672/"

# Logging
LOG_LEVEL=INFO
ENV=INFO
```

## Setup & Run

### Prerequisites
- Docker & Docker Compose
- Python 3.13+ (for local development)
- PostgreSQL 15+
- RabbitMQ 3.12+

### Using Docker Compose (Recommended)

**Clone and setup:**
```bash
git clone https://github.com/fullstucked/mco_louna_task
cd mco_louna_task
cp .env.example .env
```

**Start all services:**
```bash
make docker
```

This starts:
- PostgreSQL on localhost:5432
- RabbitMQ on localhost:5672 (Admin UI: localhost:15672)
- HTTP API on localhost:8000
- AMQP Consumer (background worker)

<!-- **Check API health:** -->
<!-- ```bash -->
<!-- curl -H "X-API-Key: secret" http://localhost:8000/health -->
<!-- ``` -->

**View RabbitMQ Admin UI:**
```
http://localhost:15672
Username: BROKER_USER=payments_user
Password: BROKER_PASS=
```

<!-- ### Local Development -->
<!---->
<!-- **Setup Python environment:** -->
<!-- ```bash -->
<!-- make install -->
<!-- ``` -->
<!---->
<!-- **Run migrations:** -->
<!-- ```bash -->
<!-- alembic upgrade head -->
<!-- ``` -->
<!---->
<!-- **Start PostgreSQL & RabbitMQ (via Docker):** -->
<!-- ```bash -->
<!-- docker-compose up postgres rabbitmq -d -->
<!-- ``` -->
<!---->
<!-- **Start HTTP API:** -->
<!-- ```bash -->
<!-- python -m uvicorn src.payments.main:app --reload --host 0.0.0.0 --port 8000 -->
<!-- ``` -->
<!---->
<!-- **Start AMQP Consumer (in another terminal):** -->
<!-- ```bash -->
<!-- python src/payments/consumer.py -->
<!-- ``` -->
<!---->
## Testing

**Run basic tests :**
```bash
make tests
```

<!-- **Integration tests (requires running services):** -->
<!-- ```bash -->
<!-- pytest tests/integration/ -v -m integration -->
<!-- ``` -->

## Payment Flow

### 1. Create Payment (Command)
```
Client HTTP Request
    ↓
CreatePaymentCommand (DTO)
    ↓
PaymentService.create()  [Domain Logic]
    ↓
Payment Aggregate Root (emits PaymentCreatedEvent)
    ↓
UoW.outbox.add(events)   [Transactional Outbox]
    ↓
UoW.commit()             [DB Transaction]
    ↓
EventBus.publish_payment_events()  [RabbitMQ via Circuit Breaker]
    ↓
Response 201 Created
```

### 2. Process Payment (Event Handler)
```
PaymentCreatedEvent (from AMQP)
    ↓
ProcessPaymentUseCase
    ↓
Emulate Gateway Processing (2–5s delay, 90% success rate)
    ↓
PaymentService.update_processed_payment()
    ↓
Payment.pull_events()  [Emits PaymentProcessedEvent]
    ↓
UoW.outbox.add(PaymentProcessedEvent)
    ↓
UoW.commit()
    ↓
EventBus.publish_payment_events()  [RabbitMQ]
```

### 3. Send Notification (Event Handler)
```
PaymentProcessedEvent (from AMQP)
    ↓
SendNotificationUseCase
    ↓
PayloadStrategyFactory.resolve(event.status)
    ↓
Strategy.build(event)  [Format webhook payload]
    ↓
WebhookSender.send(url, payload)  [HTTP POST with timeout]
    ↓
Mark event as delivered  [Outbox.mark_processed()]
```

### 4. Fetch Pending Tasks (Background Job)
```
Poll Outbox every N seconds
    ↓
SELECT * FROM outbox WHERE status = PENDING
    ↓
FOR EACH pending event:
    EventBus.publish_payment_events(event)
    Outbox.mark_processed(event_id)
    ↓
Retry on failure (eventual consistency guaranteed)
```

## Key Design Decisions

### Idempotency
All payments are idempotent via idempotency_key. If the same key is submitted twice, the service returns the original payment without creating a duplicate.

```python
# Implementation: Explicit check in PaymentRepository.add()
if self.get_by_key(idempotency_key):
    raise DomainResourceExistsError(f"Payment already exists for key: {idempotency_key}")
```

### Transactional Outbox
Events are committed to the database in the same transaction as the payment, then published to the broker. If the broker is temporarily unavailable, the background job (FetchPendingTasks) ensures eventual delivery.

### Circuit Breaker
The AMQPEventPublisher wraps broker calls in a Circuit Breaker with:
- Fail Max: 5 consecutive failures
- Reset Timeout: 60 seconds
- Excluded Exceptions: EventRoutingError, EventSerializationError (config errors don't trip the circuit)

When the circuit opens, PublisherUnavailableError is raised; clients should retry.

### Database Resilience
Connection errors are centralized in PaymentUoW.commit():
- SQLAlchemy.TimeoutError → RepositoriesExhaustedError
- SQLAlchemy.OperationalError → RepositoriesUnavailableError

Use case layer applies exponential backoff retry (3 attempts, 1–10s delays) specifically for these exceptions.

## Next Steps
- Comprehensive API Documentation: OpenAPI/Swagger with detailed request/response examples
- Structured Logging: Integrate structlog for JSON-structured logs with correlation IDs
- Test Suite Repair: expand  integration, and end-to-end tests
- Caching Strategy: Redis caching for frequently accessed payments
