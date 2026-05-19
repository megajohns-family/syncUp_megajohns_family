# SyncUp — Megajohn's Family Project

**Team members:**
- Adam Kowalczyk
- Tymon Budzowski
- Bartosz Sieradzki
- Oleksandr Shybitskyi

## Overview

SyncUp is a real-time collaborative task management web app built with FastAPI and Firestore. Multiple users can work on shared boards simultaneously — changes appear instantly for all connected users via WebSocket. Users can register, log in, create boards, invite teammates, and manage task lists with color-tagged tasks. The app features a clean, modern UI with responsive design and smooth interactions.

**Now online!** [SyncUp](https://syncup.up.railway.app)

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, Uvicorn |
| **Database** | Google Firestore |
| **Auth** | JWT (PyJWT, 24h expiry), Argon2 password hashing (passlib) |
| **Realtime** | WebSocket (FastAPI native) |
| **Frontend** | Vanilla HTML / CSS / JavaScript |
| **Validation** | Pydantic v2 |
| **Hosting** | Railway |

## Project Structure
```
.
├── main.py                    # FastAPI app entry point & routes
├── Procfile                   # Railway deployment config
├── app/
│   ├── auth.py                # JWT token creation and validation
│   ├── database.py            # Firestore client
│   ├── hash.py                # Argon2 password hashing utilities
│   └── models.py              # UserManager, TaskManager
├── static/
│   ├── html/
│   │   ├── landingpage.html   # Public landing page
│   │   ├── login.html         # Login form
│   │   ├── register.html      # Registration form
│   │   ├── boards.html        # Board selection page (protected)
│   │   └── index.html         # Main dashboard (protected)
│   ├── style/
│   │   ├── main.css           # Landing page styles
│   │   ├── loginregister.css  # Shared auth form styles
│   │   └── indexmain.css      # Dashboard styles
│   ├── script/
│   │   ├── login.js           # Login logic
│   │   ├── register.js        # Registration logic
│   │   ├── boards.js          # Board selection logic
│   │   └── index.js           # Dashboard logic
│   └── imgs/
│       └── logo.png           # Website logo
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
   FIREBASE_SERVICE_ACCOUNT={"type":"service_account",...}
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

### Boards (auth required)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/boards` | List all boards for current user |
| POST | `/boards` | Create a new board |
| GET | `/boards/{board_id}/users` | List users on a board |
| POST | `/boards/{board_id}/users` | Add user to a board (owner only) |
| DELETE | `/boards/{board_id}/users/{username}` | Remove user from a board (owner only) |

### Lists (auth required)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/boards/{board_id}/lists` | Get all lists with tasks |
| POST | `/boards/{board_id}/lists` | Create a list |
| PATCH | `/boards/{board_id}/lists/{list_id}` | Rename a list |
| DELETE | `/boards/{board_id}/lists/{list_id}` | Delete a list and its tasks |
| PUT | `/boards/{board_id}/lists/order` | Reorder lists |

### Tasks (auth required)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/boards/{board_id}/lists/{list_id}/tasks` | Create a task |
| PATCH | `/boards/{board_id}/tasks/{task_id}` | Update task name, description, or color tag |
| DELETE | `/boards/{board_id}/tasks/{task_id}` | Delete a task |
| POST | `/boards/{board_id}/tasks/{task_id}/move` | Move task to another list |

### Search (auth required)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/boards/{board_id}/search?q=` | Search tasks by name or description |

### WebSocket
| Path | Description |
|------|-------------|
| `ws://.../ws/{board_id}` | Real-time board updates |

Interactive API docs available at `http://localhost:8000/docs`.

## Database Architecture

**Firestore collections:**

| Collection | Document | Description |
|------------|----------|-------------|
| `boards` | `board_{board_id}` | Board data: lists, tasks, owner, users |
| `users` | `users` | Global user registry |

## Auth Flow

1. **Register** — POST credentials, hash password, save to Firestore
2. **Login** — verify credentials, issue JWT (HS256, 24h expiry)
3. **Protected requests** — `Authorization: Bearer {token}` header
4. **Logout** — clear token from LocalStorage (client-side)

## Features

- User registration, login, logout
- Create and manage multiple boards
- Invite teammates to boards; remove users (owner only)
- Real-time collaboration via WebSocket — changes appear instantly for all connected users
- Toast notifications for all board events (task added, list deleted, user removed, etc.)
- Create, rename, and delete task lists
- Drag-and-drop reordering of lists and tasks
- Add, edit (double-click), and delete tasks with optional descriptions and color tags
- Move tasks between lists via drag-and-drop
- Search tasks by name or description with live results and scroll-to-highlight
- Responsive grid layout adapting to any screen size
- Data persisted in Firestore
