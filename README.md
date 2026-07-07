# VoxSales: B2B Enterprise AI Voice Sales Agent SaaS

VoxSales is a high-performance, multilingual, B2B AI Voice Sales Agent SaaS platform designed to automate dealer procurements. It connects telephony networks (Twilio) with conversational AI models and backend Enterprise Resource Planning (ERP) databases (SAP, NetSuite, etc.) to query inventory and book orders in real time.

---

## 1. Tech Stack
* **Frontend:** Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS
* **Backend:** FastAPI (ASGI), SQLAlchemy 2.0, Alembic, Pydantic v2
* **Databases:** PostgreSQL 16 (Transactional), Redis 7 (Caching & Streams)
* **DevOps:** Docker, Docker Compose, GitHub Actions CI/CD

---

## 2. Directory Layout
```
ai-sales-agent/
├── .github/                   # CI/CD workflows (Backend/Frontend tests)
├── apps/
│   ├── backend/               # FastAPI application code and main entrypoint
│   └── frontend/              # Next.js 15 dashboard and landing page code
├── packages/
│   ├── database/              # Alembic migrations config and seeds
│   ├── types/                 # Shared TypeScript interface packages
│   └── config/                # Central configurations
├── docker/
│   └── local/                 # Dockerfile.backend, Dockerfile.frontend, docker-compose.yml
├── docs/                      # Technical documentation and architecture wikis
├── README.md
└── .env.example
```

---

## 3. Local Development (Docker Compose)

### Prerequisites
* Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose).

### Step 1: Copy Environment Variables
Copy `.env.example` to `.env` in the root folder:
```bash
cp .env.example .env
```

### Step 2: Spin Up Containers
Navigate to the `docker/local/` directory and start Docker Compose:
```bash
cd docker/local
docker compose up --build -d
```
*This command compiles the frontend and backend applications, mounts folders for hot-reloading, and spins up local instances of PostgreSQL and Redis.*

### Step 3: Access Applications
* **Frontend Landing Page:** [http://localhost:3000](http://localhost:3000)
* **Backend Home Endpoint:** [http://localhost:8000](http://localhost:8000)
* **Swagger API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **API Health Check Endpoint:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

### Step 4: Stop Containers
To teardown all active services:
```bash
docker compose down -v
```

---

## 4. Local Development (Bare-Metal)

If you prefer to run services outside containers:

### Backend Setup
1. Create a virtual environment and activate it:
   ```bash
   cd apps/backend
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the development server (make sure local PostgreSQL and Redis are active):
   ```bash
   uvicorn main:app --reload
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd apps/frontend
   ```
2. Install node packages:
   ```bash
   npm install
   ```
3. Start Next.js development server:
   ```bash
   npm run dev
   ```

---

## 5. Verification Commands
To ensure everything operates successfully:
1. Verify API is running and returns health indices:
   ```bash
   curl http://localhost:8000/api/v1/health
   ```
2. Check Next.js server compilation responses:
   ```bash
   curl -I http://localhost:3000
   ```
3. Run backend lint tests locally:
   ```bash
   ruff check apps/backend
   ```
