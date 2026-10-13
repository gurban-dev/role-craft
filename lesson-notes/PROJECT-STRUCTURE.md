# Role-Craft: Project Structure and APIs

## 1. What Is Role-Craft?

Role-Craft is a full-stack job application assistant. It helps users find jobs, evaluate opportunities, prepare resumes, research contacts, and manage applications.

The project has two main applications:

- **Frontend:** Next.js and React, running at `http://localhost:3000`.
- **Backend:** FastAPI, running at `http://localhost:8000`.

The frontend communicates with the backend API. The backend handles business logic and database operations.

Other technologies include PostgreSQL for persistent storage, Redis and Celery for background tasks, and Playwright for browser automation.

## 2. The Restaurant Analogy

Think of the application as a restaurant:

| Component | Restaurant analogy | Responsibility |
|---|---|---|
| Frontend | Dining room | Displays the interface |
| API | Waiter | Receives and processes requests |
| Services | Kitchen | Implements business logic |
| Database | Pantry | Stores data |
| Background workers | Separate kitchen staff | Handle slow or scheduled tasks |

Each component has a specific responsibility. This separation makes the application easier to maintain and extend.

## 3. Project Structure

The repository's main folders are:

```text
role-craft/
├── apps/
│   ├── web/          # Next.js frontend
│   └── api/          # FastAPI backend
├── packages/
│   └── shared/       # Shared constants
├── infrastructure/  # Docker and deployment files
├── docker-compose.yml
├── .env.example
└── README.md
```

### Frontend: `apps/web/`

The frontend uses Next.js and React.

Important locations:

```text
apps/web/src/
├── app/              # Pages and layouts
├── components/       # Reusable UI components
└── lib/
    ├── api.ts        # HTTP request helper
    ├── endpoints.ts  # Functions for API endpoints
    └── types.ts      # TypeScript types
```

With the Next.js App Router, folders determine URL paths.

For example:

- `app/page.tsx` -> `/`
- `app/(app)/jobs/page.tsx` -> `/jobs`
- `app/(app)/jobs/[id]/page.tsx` -> `/jobs/123`

Folders in parentheses are organizational groups and do not appear in the URL.

### Backend: `apps/api/`

The backend uses Python and FastAPI.

Important locations:

```text
apps/api/
├── app/
│   ├── main.py        # Initializes the application
│   ├── api/           # API routes
│   ├── schemas/       # Request and response structures
│   ├── services/      # Business logic
│   ├── repositories/  # Database queries
│   ├── models/        # Database models
│   ├── db/            # Database sessions
│   ├── core/          # Configuration and security
│   └── workers/       # Background tasks
├── alembic/           # Database migrations
└── tests/             # Automated tests
```

The main responsibilities are:

- **Routes:** Receive HTTP requests and return responses.
- **Schemas:** Validate incoming data and define response structures.
- **Services:** Implement business rules.
- **Repositories:** Handle database queries.
- **Models:** Represent database tables.

## 4. What Is an API?

API stands for Application Programming Interface.

An API defines how one program communicates with another. A client sends a request, and the server returns a response.

For example:

```http
GET /api/jobs
```

This requests a list of jobs.

The server might respond with JSON:

```json
[
  {
    "id": 1,
    "company": "Google",
    "title": "Backend Engineer"
  }
]
```

An API acts as a contract between programs. It defines the available operations, the data they accept, and the responses they return.

## 5. What Is a REST API?

REST is a style of designing HTTP APIs around resources.

A resource is something the API manages, such as a job, user, or application.

REST APIs typically use resource-oriented URLs and HTTP methods.

| Method | Purpose | Example |
|---|---|---|
| `GET` | Retrieve data | `GET /api/jobs` |
| `POST` | Create a resource | `POST /api/jobs` |
| `PUT` | Replace a resource | `PUT /api/jobs/123` |
| `PATCH` | Partially update a resource | `PATCH /api/jobs/123` |
| `DELETE` | Delete a resource | `DELETE /api/jobs/123` |

The four basic data operations are called **CRUD**:

- Create
- Read
- Update
- Delete

FastAPI automatically generates interactive API documentation using OpenAPI.

When the backend is running, open:

`http://localhost:8000/docs`

## 6. How a Request Travels Through Role-Craft

Consider a user opening the Jobs page.

1. The browser loads `/jobs` from the Next.js frontend.
2. The page calls `endpoints.jobs()` in `apps/web/src/lib/endpoints.ts`.
3. That function sends a `GET` request to `/api/jobs` on the FastAPI backend.
4. FastAPI matches the request to a route in `apps/api/app/api/jobs.py`.
5. The route obtains the necessary data through the backend's business logic and database layers.
6. FastAPI returns JSON.
7. The frontend receives the JSON and displays the jobs.

The overall flow is:

```text
Browser
   |
   v
Next.js page
   |
   v
Frontend API helper
   |
   | GET /api/jobs
   v
FastAPI route
   |
   v
Service / Repository
   |
   v
Database
   |
   v
JSON response
   |
   v
Next.js displays the jobs
```

The frontend does not communicate directly with PostgreSQL. The backend controls access to the application's data.

## 7. Practice: Build a Notes API

The best way to understand APIs is to build one.

Create a simple Notes resource that allows a user to save, retrieve, update, and delete notes.

### Required endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/notes` | List notes |
| `POST` | `/api/notes` | Create a note |
| `GET` | `/api/notes/{id}` | Retrieve one note |
| `PATCH` | `/api/notes/{id}` | Update a note |
| `DELETE` | `/api/notes/{id}` | Delete a note |

A note could contain:

```json
{
  "id": 1,
  "text": "Learn how REST APIs work"
}
```

### Suggested implementation steps

1. Inspect `apps/api/app/api/health.py` to see a simple route.
2. Examine `apps/api/app/api/router.py` and `apps/api/app/main.py` to understand how routes are registered.
3. Create a Notes route in `apps/api/app/api/notes.py`.
4. Define request and response schemas.
5. Implement the note operations in a service.
6. Register the Notes router.
7. Start the backend and test the endpoints at `http://localhost:8000/docs`.

For an initial exercise, notes can be stored in memory. Later, extend the implementation to use PostgreSQL.

## 8. Suggested Learning Order

1. Understand the frontend, backend, and database.
2. Learn what APIs, HTTP requests, and JSON are.
3. Understand the HTTP methods and CRUD operations.
4. Start the FastAPI backend and explore `/docs`.
5. Read the existing health endpoint.
6. Trace a request from the Next.js frontend to FastAPI.
7. Build the Notes API.
8. Explore services, repositories, database migrations, and background workers.

## Summary

Role-Craft consists of a Next.js frontend and a FastAPI backend. The frontend sends HTTP requests to the backend, which processes them and communicates with the database. REST conventions help organize these interactions around resources and standard HTTP methods. Understanding this structure makes it easier to explore the existing project and implement new features.