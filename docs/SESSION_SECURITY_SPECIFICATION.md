# Backend Session Security Specification — Passwordless Device-Bound Login

This document specifies the backend implementation details for enforcing a single bound device per username using passwordless authentication. This ensures that only pre-registered usernames can log in, and they are cryptographically locked to the first physical device that activates them.

## 1. Authentication Lifecycle

```
[ Admin (You) ] ──( Add Username )──> [ Create user with bound_device_uuid: null ]
                                                         │
                                                         ▼
[ User (First Login) ] ──( Username + Device UUID )──> [ Save UUID to user record ]
                                                         │
                                                         ▼
[ User (Subsequent) ]  ──( Username + Device UUID )──> [ Check UUID match -> Success ]
                                                         │
                                                         ▼
[ Hacker / Shared ]    ──( Username + New UUID )    ──> [ Mismatch -> Reject (403) ]
```

---

## 2. Storage Schema (`instance/users.json`)

The storage file `instance/users.json` persists the users, their bound device identifiers, and their active session tokens:

```json
{
  "skanda": {
    "bound_device_uuid": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
    "active_token": "current_session_token_here"
  },
  "new_user_unactivated": {
    "bound_device_uuid": null,
    "active_token": null
  }
}
```

---

## 3. API Contract

### 3.1 Device Login
- **Endpoint**: `POST /api/v1/auth/login`
- **Rate Limit**: 10 requests per minute (per IP)
- **Request Payload**:
  ```json
  {
    "username": "skanda",
    "device_uuid": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6"
  }
  ```
- **Login Validation Workflow**:
  1. Check if `username` exists in `users.json`. If not, return **404 Not Found** (*"Username not registered"*).
  2. If the user exists and `bound_device_uuid` is `null`:
     - Save the incoming `device_uuid` to the user's record (Activation step).
  3. If `bound_device_uuid` is not `null` and does not match the incoming `device_uuid`:
     - Return **403 Forbidden** (*"Account bound to another device"*).
  4. Generate a new session token, save it to `active_token`, and return it.

- **Response (Success - HTTP 200)**:
  ```json
  {
    "token": "49d8c3f29b4e10ad5c721b017b2f4a13"
  }
  ```

---

## 4. Request Authentication & Validation

### 4.1 Flask Decorator (`@require_session`)
A custom decorator will inspect the request headers for the `Authorization` header containing the Bearer token:

```python
from functools import wraps
from flask import request
from hora_server.utils.errors import ApiError
from hora_server.auth import verify_token

def require_session(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise ApiError(
                "Missing or invalid Authorization header",
                code="unauthorized",
                status_code=401
            )
            
        token = auth_header.split(" ")[1].strip()
        if not verify_token(token):
            raise ApiError(
                "Session expired or logged in on another device",
                code="session_expired",
                status_code=401
            )
        return f(*args, **kwargs)
    return decorated
```

---

## 5. Flask CLI Command (User Pre-Registration)

To allow pre-registering users without setting a password:

```bash
flask add-user <username>
```
This command will:
1. Load `instance/users.json`.
2. Create the user record:
   ```json
   {
     "bound_device_uuid": null,
     "active_token": null
   }
   ```
3. Save the file back to disk.

To reset a user's device (e.g. if they get a new phone):
```bash
flask reset-device <username>
```
This resets `bound_device_uuid` and `active_token` to `null`, allowing the next login to bind a new device.

To remove a pre-registered user entirely:
```bash
flask remove-user <username>
```
This deletes the user from `users.json`, instantly invalidating their session and stopping all API access.
