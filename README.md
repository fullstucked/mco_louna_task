# Асинхронный сервис процессинга платежей

<!--toc:start-->
- [Асинхронный сервис процессинга платежей](#асинхронный-сервис-процессинга-платежей)
    - [Следующие шаги:](#следующие-шаги)
    - [Возможные дорабтки:](#возможные-дорабтки)
    - [**Create Payment**](#create-payment)
    - [**Get Payment**](#get-payment)
  - [Переменные окружения](#переменные-окружения)
  - [Setup & Run:](#setup-run)
<!--toc:end-->

Сервис написан в формате монорепозитория, согласованно с прицнипами DDD+Clean Architecture + CQRS;
запускается коммандой



Написан в cогласовании с тз[./docs/task/task.md]
Базовые доменные структуры находятся в ./src/shared


### Следующие шаги:
- Подробная документации
- Настройка логгирования structlog
- Обработка ошибок со стороны api с описанием по Scope
- Починка тестов
- Починка DEV-валидации у Aggregate и Value Object
- кеширование
- оптимизация БД
- Мониторинг(prometheus, graphana, loki)
- CICD+IaC

### Возможные дорабтки:
- Перенос подхватчика простаивающих событий на самоотправляющую очередь с ttl
- Эмуляция отправки алертов при критических ошибках
- создание healthcheck метода для api по которому уже будет подниматься воркер

### **Create Payment**
```http
POST /v1/payments
Headers:
Idempotency-Key: <unique_key>
Body:
{
"amount": 123.45,
"currency": "USD",
"description": "Invoice 123",
"metadata": {"order_id": "ABC123"},
"webhook_url": "https://example.com/webhook
"
}
```
**Response:**

```json
{
  "payment_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "PENDING",
  "created_at": "2026-04-02T12:34:56Z"
}
```
### **Get Payment**
```http
GET /v1/payments/{payment_id}
```
**Response:**
```json
{
  "payment_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "amount": 123.45,
  "currency": "USD",
  "description": "Invoice 123",
  "metadata": {"order_id": "ABC123"},
  "status": "PENDING",
  "key": "idempotency_key",
  "created_at": "2026-04-02T12:34:56Z",
  "processed_at": null
}
```

## Переменные окружения


| Variable                | Default / Example                          | Description                                      |
|-------------------------|-------------------------------------------|---------------------------------------------------|
| `API_KEY`               | `secret`                                  | HTTP API authentication key                      |
| `DB_USER`               | `payments_user`                            | Database user (alias for POSTGRES_USER)          |
| `DB_PASSWORD`           | `supersecret`                              | Database password (alias for POSTGRES_PASSWORD)  |
| `DB_NAME`               | `payments`                                 | Database name (alias for POSTGRES_DB)            |
| `DB_PORT`               | `5432`                                     | Database port                                    |
| `DB_TYPE`               | `postgresql+asyncpg`                       | SQLAlchemy database driver                       |
| `API_PORT`              | `8000`                                     | HTTP API port                                    |
| `BROKER_PORT`           | `5672`                                     | RabbitMQ port                                    |
| `BROKER_USER`           | `payments_user`                                      | RabbitMQ username                                |
| `BROKER_PASS`           | `supersecret`                                      | RabbitMQ password                                |
| `BROKER_URL`            | `"ampq://payments:supersecret@rabbitmq:5672/"`         | RabbitMQ connection URL                           |


## Setup & Run:
**Clone**
```bash
git clone  https://github.com/fullstucked/mco_louna_task
cd mco_luna_task
mv .env.example .env
```
make docker
```
