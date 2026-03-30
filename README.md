# SyncUp — Megajohn's Family Project

**Team members:**
- Adam Kowalczyk
- Tymon Budzowski
- Bartosz Sieradzki
- Oleksandr Shybitskyi
## Overview

SyncUp is a task management web app built with FastAPI and Firestore. Users can register, log in, and manage personal task lists with color-tagged tasks. The app features a clean, modern UI with responsive design and smooth interactions.

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, Uvicorn |
| **Database** | Google Firestore (REST API) with in-memory cache |
| **Auth** | JWT (PyJWT, 24h expiry), Argon2 password hashing (passlib) |
| **Frontend** | Vanilla HTML / CSS / JavaScript |
| **Validation** | Pydantic v2 |

## Project Structure

```
.
├── main.py                    # FastAPI app entry point & route 
├── app/
│   ├── auth.py                # JWT token creation and validation
│   ├── database.py            # Firestore REST API client with 
│   ├── hash.py                # Argon2 password hashing utilities
│   └── models.py              # UserManager, TaskManager, 
├── static/
│   ├── landingpage.html       # Public landing page
│   ├── login.html             # Login form
│   ├── register.html          # Registration form
│   ├── index.html             # Main dashboard (protected)
│   ├── main.css               # Landing/auth page styles
│   ├── loginregister.css      # Shared auth form styles
│   └── indexmain.css          # Dashboard styles
└── requirements.txt
```
## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment** — create a `.env` file:
   ```
   SECRET_KEY=your_jwt_secret
   GOOGLE_APPLICATION_CREDENTIALS=path/to/serviceAccount.json
   ```

3. **Run the server:**
   ```bash
   uvicorn main:app --reload
   ```

4. Open `http://localhost:8000` in your browser.

## API Endpoints

### Auth (public)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/users/register` | Register a new user |
| POST | `/users/login` | Log in, returns JWT token |
| POST | `/users/change-password` | Change password (auth required) |
| DELETE | `/users/me` | Delete account (auth required) |

### Lists (auth required)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/lists` | Get all lists with tasks |
| POST | `/lists` | Create a list |
| PATCH | `/lists/{list_id}` | Rename a list |
| DELETE | `/lists/{list_id}` | Delete a list and its tasks |

### Tasks (auth required)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/lists/{list_id}/tasks` | Create a task in a list |
| PATCH | `/tasks/{task_id}` | Update task name, description, or color tag |
| DELETE | `/tasks/{task_id}` | Delete a task |
| POST | `/tasks/{task_id}/move` | Move task to another list |

Interactive API docs available at `http://localhost:8000/docs`.

## Database Architecture

**Firestore collection:** `syncup`

| Document | Schema | Description |
|----------|--------|-------------|
| `users` | `{ "users": { "username": "hashed_pw", ... } }` | Global user registry |
| `tasks_{username}` | `{ "lists": {...}, "tasks": {...} }` | Per-user lists and tasks |

## Auth Flow

1. **Register** — POST credentials, hash password, save to Firestore
2. **Login** — verify credentials, issue JWT (HS256, 24h expiry)
3. **Protected requests** — `Authorization: Bearer {token}` header
4. **Logout** — clear token from LocalStorage (client-side)

## Features

- User registration, login, logout, password change, account deletion
- Create, rename, and delete task lists
- Add, edit, and delete tasks with optional descriptions and color tags
- Move tasks between lists
- Toast notifications for all user actions
- Responsive grid layout adapting to any screen size
- Data persisted in Firestore per user with in-memory caching
