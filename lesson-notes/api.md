# What Is an API?

## 1. Definition

An **API (Application Programming Interface)** is a defined way for one program to communicate with another program.

For example, a website can use an API to request information from a backend server.

## 2. The Restaurant Analogy

Think of an API as a waiter in a restaurant:

- **Client:** The customer making a request.
- **API:** The waiter receiving the request.
- **Server:** The kitchen preparing the order.
- **Response:** The food delivered to the customer.

The client does not need to know how the server performs its work. It only needs to know how to make a request and receive a response.

## 3. Requests and Responses

A client sends a request to an API, and the server returns a response.

For example:

```http
GET /jobs
```

This asks the API to return a list of jobs.

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

An **endpoint** identifies an API operation. For example, `GET /jobs` retrieves jobs, while `POST /jobs` creates a job.

## 4. Common HTTP Methods

| Method | Purpose |
|---|---|
| `GET` | Retrieve information |
| `POST` | Create a resource |
| `PUT` | Replace a resource |
| `PATCH` | Partially update a resource |
| `DELETE` | Delete a resource |

These methods allow clients to communicate their intended operations to the server.

## 5. How Next.js and FastAPI Work Together

Next.js can provide the website's user interface, while FastAPI provides the backend API.

```text
User
  |
  v
Next.js frontend
  |
  | HTTP request
  v
FastAPI backend
  |
  v
Database
```

For example, when a user opens the jobs page:

1. Next.js requests the jobs from FastAPI.
2. FastAPI retrieves the jobs from the database.
3. FastAPI returns the data as JSON.
4. Next.js displays the jobs to the user.

## Key Takeaway

An **API defines how one program can request information from another program or ask it to perform a specific task, and receive a response.**