# Analytics Service

Production-ready FastAPI microservice for restaurant analytics with automated batch processing and forecasting.

## 🏗️ Dual-Database Architecture

```
┌─────────────┐         ┌─────────────┐         ┌──────────────┐
│  order_db   │────────▶│  Analytics  │────────▶│ analytics_db │
│  (orders,   │ READ    │   Service   │  WRITE  │  (analytics  │
│ order_items)│         │             │         │    tables)   │
└─────────────┘         └─────────────┘         └──────────────┘
```

**order_db** (Read-Only): Source database with `orders` and `order_items` tables  
**analytics_db** (Read-Write): Dedicated database for precomputed analytics and forecasts

## 🚀 Quick Start

### Docker Compose (Recommended)

```bash
docker-compose up -d
```

### Local Development

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### Manual Batch Execution

```bash
python run_batch.py
```

## ⚙️ Configuration

## ⚙️ Configuration

Copy `.env.example` to `.env` and configure your settings:

```bash
cp .env.example .env
```

```ini
# Server
SERVER__HOST=0.0.0.0
SERVER__PORT=8087

# Database
ORDER_DATABASE__HOST=localhost
ORDER_DATABASE__PORT=3306
# ... see .env.example for full list
```

## 🕛 Midnight Batch Process

Automatically runs daily at midnight (configurable):

1. **Reads** order data from `order_db`
2. **Computes** daily revenue, order counts, hourly breakdown
3. **Generates** forecasts using statistical models
4. **Stores** results in `analytics_db`

All API endpoints read from precomputed data for fast responses.

## 📊 Analytics Tables (analytics_db)

**daily_revenue_cache** - Daily aggregated metrics  
**hourly_order_cache** - Hourly order counts (24 rows per day)  
**forecast_history** - Generated forecasts

Tables are automatically created on service startup.

## 📡 API Endpoints

### GET `/api/admin/analytics/summary`
Daily analytics summary (revenue, orders, averages)

### GET `/api/admin/analytics/top-items`
Top selling items with quantities and revenue

### GET `/api/admin/analytics/hourly`
Hourly order breakdown

### GET `/api/admin/analytics/forecast/daily`
Daily revenue forecasts (next 7 days)

### GET `/api/admin/analytics/forecast/hourly`
Hourly order forecasts (next 24 hours)

**Example:**
```bash
curl http://localhost:8087/api/admin/analytics/summary
```

## 🔍 Testing

```bash
# Health check
curl http://localhost:8087/health

# View logs
docker-compose logs -f analytics-service

# Run batch manually
python run_batch.py
```

## 📁 Project Structure

```
analytics-service/
├── app/
│   ├── config.py              # Configuration loader
│   ├── database.py            # Dual database setup
│   ├── main.py                # FastAPI app
│   ├── models/                # SQLAlchemy models
│   │   ├── order.py          # Order models (OrderBase → order_db)
│   │   └── analytics.py      # Analytics models (AnalyticsBase → analytics_db)
│   ├── routers/               # API endpoints
│   ├── schemas/               # Pydantic schemas
│   ├── services/              # Business logic
│   └── scheduler/             # Batch processor
├── .env                   # Environment variables (local dev)
├── .env.example           # Environment template
├── requirements.txt           # Dependencies
├── Dockerfile                 # Container image
├── docker-compose.yml         # Multi-container setup
└── run_batch.py              # Manual batch execution
```

## 🔐 Security

- Use separate database users with minimal permissions
- Read-only user for `order_db`
- Read-write user for `analytics_db`
- Never commit credentials (use environment variables)

## 📈 Performance

- **Connection Pooling**: 10-20 connections per database
- **Precomputed Data**: Batch process runs once daily
- **Fast APIs**: Read from cached analytics tables
- **Indexed Tables**: Date fields indexed for quick queries

## ⚠️ Important Rules

1. **Never modify** `orders` or `order_items` tables
2. Only **read** from `order_db`, **write** to `analytics_db`
3. Only count orders with `status = 'SERVED'`
4. Use `orders.total_amount` for revenue (never recompute from items)

## 📝 Environment Variables

Alternatively, configure via environment variables:

```bash
ORDER_DB_HOST=localhost
ORDER_DB_PORT=3306
ORDER_DB_USER=root
ORDER_DB_PASSWORD=password
ORDER_DB_NAME=order_db

ANALYTICS_DB_HOST=localhost
ANALYTICS_DB_PORT=3306
ANALYTICS_DB_USER=root
ANALYTICS_DB_PASSWORD=password
ANALYTICS_DB_NAME=analytics_db
```

---

**Version**: 2.0.0 (Dual-Database Architecture)  
**Python**: 3.9+  
**FastAPI**: Latest  
**MySQL**: 8.0+
