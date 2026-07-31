# Backend Session Security Specification — Device UUID Authentication

This document specifies the backend implementation details for authentication using **Device UUID Authentication** with **Device Token Persistence** in `instance/users.json`.

---

## 1. Authentication Lifecycle

```
[ Mobile / Web App ] ──( Send device_uuid )──> [ POST /api/v1/auth/login ]
                                                         │
                                                         ▼
[ Backend ]          ──( Check device_uuid ) ──> [ Store/Update in users.json ]
                                                         │
                                                         ▼
[ Backend ]          ──( Generate Auth Token )─> [ Set active_token = token ]
                                                       [ Returns Token (200 OK) ]
```

---

## 2. Storage Schema (`instance/users.json`)

The storage file `instance/users.json` persists registered devices and their active authentication tokens.

```json
{
  "device-uuid-phone-a": {
    "device_uuid": "device-uuid-phone-a",
    "active_token": "49d8c3f29b4e10ad5c721b017b2f4a13...",
    "created_at": "2026-07-26T12:00:00Z",
    "last_login": "2026-07-31T15:30:00Z"
  }
}
```

### Key Security & Session Features:
- **Device-Based Registration**: Each device authenticates using its unique `device_uuid`.
- **Token Management**: Re-logging in on the **same device** updates that device's active token.
- **Explicit Logout Endpoint**: `POST /api/v1/auth/logout` revokes the calling device's session token instantly and deletes its device entry from `users.json`.
- **CLI Monitoring**: `flask list-users` reports the total number of active users.

---

## 3. API Contract

### 3.1 Device Login
- **Endpoint**: `POST /api/v1/auth/login`
- **Rate Limit**: 10 requests per minute (per IP)
- **Request Payload**:
  ```json
  {
    "device_uuid": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6"
  }
  ```

- **Backend Login Validation Workflow**:
  1. Parse incoming `device_uuid`. If missing or blank, return **400 Bad Request** (*"device_uuid is required"*).
  2. Generate a new 64-character hex authentication token (`secrets.token_hex(32)`).
  3. Update/create the device record in `instance/users.json` keyed by `device_uuid`.
  4. Return the generated token and `device_uuid`.

- **Response (Success - HTTP 200)**:
  ```json
  {
    "token": "49d8c3f29b4e10ad5c721b017b2f4a13...",
    "device_uuid": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6"
  }
  ```

- **Error Responses**:
  - `400 Bad Request`: `{"error": "device_uuid is required", "code": "missing_parameter"}`

### 3.2 Session Logout & Token Revocation
- **Endpoint**: `POST /api/v1/auth/logout`
- **HTTP Method**: `POST`
- **Request Headers**:
  ```http
  Authorization: Bearer <session-token-to-revoke>
  ```
- **Request Payload**: None (or empty JSON object `{}`).
- **Backend Workflow**: Extracts the active session token from the `Authorization: Bearer` header, deletes the matching device entry from `instance/users.json`, and invalidates subsequent requests using that token.
- **Response (Success - HTTP 200)**:
  ```json
  {
    "status": "logged_out"
  }
  ```

---

## 4. Request Authentication & Validation

### 4.1 Flask Decorator (`@require_session`)
Incoming REST API requests require a valid session token passed via standard Bearer authorization header.

---

## 5. Flask CLI Command

### 5.1 List Active Users Count
```bash
flask list-users
```
Outputs the total number of active users:
```text
Total active users: 2
```
