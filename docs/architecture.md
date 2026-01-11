# CherryPi Architecture

CherryPi is a full-stack application that enables control of 433MHz RF outlets through a web interface. Designed for home automation enthusiasts, it runs on a Raspberry Pi and provides a mobile-friendly UI for controlling RF-enabled power outlets. The system uses loosely-coupled microservices communicating via Redis pub/sub.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User Devices                                   │
│                    (Browser / Mobile / QR Scanner)                          │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Frontend                                        │
│                         React Single Page App                               │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │ REST API
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Backend                                         │
│                          FastAPI Server                                      │
└───────────┬─────────────────────┼─────────────────────┬─────────────────────┘
            │                     │                     │
            ▼                     ▼                     ▼
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│   Auth Service    │  │      Redis        │  │   RF Controller   │
│  (JWT, Users DB)  │◄─┤  (Message Bus)    │──┤  (TX/RX/Config)   │
└───────────────────┘  └───────────────────┘  └─────────┬─────────┘
                                                        │
                                                        ▼
                                              ┌───────────────────┐
                                              │   GPIO Hardware   │
                                              │  (433MHz TX/RX)   │
                                              └───────────────────┘
```

---

## Core Concepts

| Concept | Description |
|---------|-------------|
| **Switch** | A controllable RF outlet with a name, ON code, OFF code, and protocol |
| **RF Code** | A numeric signal (e.g., `12345678`) transmitted at 433MHz to control outlets |
| **Protocol** | The encoding scheme for RF signals (protocol 1-5, pulse length) |
| **User** | An authenticated identity with a role (admin, user, guest) |
| **Magic Code** | A time-limited QR code for passwordless authentication |
| **Sniffing** | Capturing RF codes from existing remotes to learn new devices |

---

## Data Flow

### Primary Flow: Controlling a Switch

```
User clicks "ON"
       │
       ▼
┌─────────────┐    POST /api/secure/outlet     ┌─────────────┐
│  Frontend   │ ──────────────────────────────►│   Backend   │
└─────────────┘                                └──────┬──────┘
                                                      │
                   1. Verify JWT via Redis            │
                   ◄──────────────────────────────────┤
┌─────────────┐    auth:requests / responses   ┌─────┴─────┐
│Auth Service │ ◄─────────────────────────────►│   Redis   │
└─────────────┘                                └─────┬─────┘
                                                     │
                   2. Publish rf_commands            │
                   ──────────────────────────────────┤
                                                     ▼
┌─────────────┐    rf_commands                 ┌───────────┐
│RF Controller│ ◄──────────────────────────────│   Redis   │
└──────┬──────┘                                └───────────┘
       │
       ▼
┌─────────────┐
│ GPIO TX Pin │ ────► 433MHz Signal ────► [Outlet turns ON]
└─────────────┘
```

### Secondary Flow: Learning a New Switch

```
User clicks "Scan Code" → Backend publishes to sniffer_commands
       │
       ▼
┌─────────────┐                                ┌─────────────┐
│  Sniffer    │  Listens on GPIO RX pin...     │   Remote    │
│  Service    │ ◄──────────────────────────────│   Button    │
└──────┬──────┘                                └─────────────┘
       │
       │  Captured code published to sniffer_results
       ▼
┌─────────────┐    Response                    ┌─────────────┐
│  Frontend   │ ◄──────────────────────────────│   Backend   │
└─────────────┘    {code: 12345678}            └─────────────┘
```

### Authentication Flow

```
Login form → Backend → Redis auth:requests → Auth Service
                                                   │
                                   Decrypt user DB │
                                   Verify password │
                                   Generate JWT    │
                                                   ▼
Frontend ◄── JWT token ◄── Backend ◄── Redis auth:responses
```

---

## API Surface

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/auth/login` | Username/password login |
| POST | `/api/auth/magic` | Magic code login |
| GET | `/api/auth/verify` | Validate JWT token |
| GET | `/api/secure/switches` | List all switches |
| POST | `/api/secure/switches` | Create/update switch |
| DELETE | `/api/secure/switches/{id}` | Delete switch |
| POST | `/api/secure/outlet` | Send ON/OFF command |
| POST | `/api/sniffer/start` | Begin RF capture |
| GET | `/api/sniffer/result` | Get captured code |

All `/api/secure/*` endpoints require a valid JWT token.

---

## Key Modules

| Module | Location | Responsibility |
|--------|----------|----------------|
| **Frontend** | `src/frontend/` | React SPA with responsive UI, auth state, switch control |
| **Backend** | `src/backend/` | FastAPI gateway, JWT middleware, Redis pub/sub bridge |
| **Auth Service** | `src/auth_service/` | User DB (encrypted), JWT issuance, RBAC, Magic QR codes |
| **RF Controller** | `src/RFController/` | GPIO TX/RX, RF signal encoding, config persistence |

### RF Controller Sub-modules

| File | Purpose |
|------|---------|
| `redis_listener.py` | Subscribes to `rf_commands`, triggers transmissions |
| `config_listener.py` | Manages switch configuration in `config.json` |
| `sniffer_service.py` | Captures RF codes from physical remotes |
| `codesend.py` | Low-level RF transmission via GPIO |

---

## UI Components

| Component | File | Purpose |
|-----------|------|---------|
| App | `App.js` | Main layout, tab navigation, auth state |
| Login | `Login.js` | Password and Magic Code login forms |
| EditSwitches | `EditSwitches.js` | Switch configuration CRUD interface |
| AddSwitchWizard | `AddSwitchWizard.js` | Guided flow for adding new switches |

---

## Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Loose Coupling** | Services communicate only via Redis pub/sub |
| **Single Responsibility** | Each service has one focused purpose |
| **Security by Design** | Auth Service never network-exposed; Backend is PEP, Auth is PDP |
| **Stateless Backend** | All auth state in JWT tokens, validated per-request |

---

## Setup

For installation and running instructions, see [README.md](../README.md).
