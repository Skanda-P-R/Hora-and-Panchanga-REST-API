# Backend Session Security Specification — Google Sign-In & Email Whitelist Authentication

This document specifies the backend implementation details for enforcing pre-approved access using **Google Sign-In** (OAuth 2.0 / Jetpack Credential Manager) and **Email Whitelisting**. Traditional passwords, custom username registration, and strict single-device UUID locks are replaced by verified Google identity authentication and admin-managed email authorization.

---

## 1. Authentication Lifecycle

```
[ Admin (You) ] ──( Pre-register Email )──> [ Add email to Whitelist in users.json ]
                                                          │
                                                          ▼
[ Mobile App ]  ──( User taps Google Sign-In )──> [ Obtains Google ID Token (JWT) ]
                                                          │
                                                          ▼
[ Mobile App ]  ──( Send ID Token to Backend ) ──> [ POST /api/v1/auth/google-login ]
                                                          │
                                                          ▼
[ Backend ]     ──( Verify Google ID Token )  ──> [ Verify Signature, Exp, & Web Client ID ]
                                                          │
                                                          ▼
[ Backend ]     ──( Check Verified Email )    ──> [ Email in Whitelist? ]
                                                    ├── YES ──> [ Issue Session Token (200 OK) ]
                                                    └── NO  ──> [ Reject Access (403 Forbidden) ]
```

---

## 2. Storage Schema (`instance/users.json`)

The storage file `instance/users.json` persists authorized user email addresses, their verified Google metadata, and active session tokens.

```json
{
  "skanda@gmail.com": {
    "google_sub": "109876543210987654321",
    "email": "skanda@gmail.com",
    "name": "Skanda",
    "picture": "https://lh3.googleusercontent.com/a/...",
    "created_at": "2026-07-26T12:00:00Z",
    "last_login": "2026-07-26T12:38:00Z",
    "active_tokens": [
      "session_token_1",
      "session_token_2"
    ]
  },
  "allowed_friend@gmail.com": {
    "google_sub": null,
    "email": "allowed_friend@gmail.com",
    "name": null,
    "picture": null,
    "created_at": "2026-07-26T12:00:00Z",
    "last_login": null,
    "active_tokens": []
  }
}
```

### Key Changes from Legacy Spec:
- **Email as Primary Identifier**: Replaces arbitrary `username`.
- **Google Subject ID (`google_sub`)**: Immutable Google user ID populated on first login.
- **Device UUID Lock Removed**: Users can log in from multiple devices using their pre-approved Google account without being restricted to a single hardware UUID.
- **Multiple Active Tokens**: `active_tokens` list allows seamless simultaneous usage across multiple authorized personal devices.

---

## 3. API Contract

### 3.1 Google Sign-In Verification
- **Endpoint**: `POST /api/v1/auth/google-login`
- **Rate Limit**: 10 requests per minute (per IP)
- **Request Payload**:
  ```json
  {
    "idToken": "eyJhbGciOiJSUzI1NiIs...",
    "device_uuid": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6"
  }
  ```
  *(Note: `device_uuid` is optional and tracked solely for session metadata/logging, not for restricting device access).*

- **Backend Login Validation Workflow**:
  1. Parse incoming `idToken`. If missing or blank, return **400 Bad Request** (*"Google ID Token is required"*).
  2. Verify `idToken` using Google OAuth verification libraries (`google-auth-library` or `google.oauth2.id_token`):
     - Confirm token signature using Google's public certificates.
     - Validate audience (`aud`) matches the server's **Google Web Client ID**.
     - Validate issuer (`iss`) is `https://accounts.google.com` or `accounts.google.com`.
     - Confirm token has not expired (`exp`).
  3. Extract verified claims: `email`, `sub` (Google Subject ID), `name`, and `picture`.
  4. Normalize email address (lowercase). Check if `email` exists in `instance/users.json` whitelist.
     - If email is **NOT** present: Return **403 Forbidden** (*"Email address not authorized. Contact administrator for access."*).
  5. Update user record:
     - Record `google_sub`, `name`, `picture`, and `last_login` timestamp.
  6. Generate a cryptographically secure session token, append to `active_tokens`, save `users.json`, and return success.

- **Response (Success - HTTP 200)**:
  ```json
  {
    "token": "49d8c3f29b4e10ad5c721b017b2f4a13",
    "user": {
      "email": "skanda@gmail.com",
      "name": "Skanda",
      "picture": "https://lh3.googleusercontent.com/a/..."
    }
  }
  ```

- **Error Responses**:
  - `400 Bad Request`: `{"error": "idToken is required", "code": "missing_parameter"}`
  - `401 Unauthorized`: `{"error": "Invalid or expired Google ID Token", "code": "invalid_google_token"}`
  - `403 Forbidden`: `{"error": "Email address not pre-approved", "code": "email_not_authorized"}`

---

## 4. Request Authentication & Validation

### 4.1 Flask Decorator (`@require_session`)
Incoming REST API requests require a valid session token passed via standard Bearer authorization header:

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
                "Session expired or invalid",
                code="session_expired",
                status_code=401
            )
        return f(*args, **kwargs)
    return decorated
```

---

## 5. Flask CLI Commands (Admin Pre-Registration & Management)

Administrators (you) pre-approve email addresses via CLI commands on the server:

### 5.1 Add Allowed Email
```bash
flask add-user <email>
```
*Example*: `flask add-user skanda@gmail.com`
- Adds the email address to `instance/users.json` with empty Google profile data (`google_sub: null`).
- Enables the account for Google login.

### 5.2 Remove Allowed Email
```bash
flask remove-user <email>
```
- Removes the email address from `users.json`.
- Instantly invalidates all active session tokens associated with that email and denies subsequent logins.

### 5.3 List Pre-Approved Users
```bash
flask list-users
```
- Lists all pre-approved emails, whether they have completed initial Google Sign-In, and their active session count.


## 6. Google Cloud Console Setup Instructions

To enable Google Sign-In authentication, complete the following setup in [Google Cloud Console](https://console.cloud.google.com/):

### 6.1 OAuth Consent Screen Setup
1. Navigate to **APIs & Services** > **OAuth consent screen**.
2. Select **External** (or **Internal** for Google Workspace organizations).
3. Provide mandatory details: App Name (e.g. `Hora Server`), User Support Email, and Developer Contact Information.
4. Save and proceed to the dashboard.

### 6.2 Web Application Client ID (Server Client ID)
1. Navigate to **APIs & Services** > **Credentials**.
2. Click **Create Credentials** > **OAuth client ID**.
3. Choose **Web application** as the application type.
4. Name the credential (e.g. `Hora Server Backend Web Client`).
5. Copy the generated **Client ID** (e.g. `1234567890-abcdef.apps.googleusercontent.com`).
6. Configure `GOOGLE_WEB_CLIENT_ID` in your backend server configuration ([hora_server/config.py](file:///g:/Skanda%20Files/Github%20Repos/Hora-and-Panchanga-REST-API/hora_server/config.py)) or `.env` file.

### 6.3 Android Client ID (Mobile App)
1. Under **Credentials**, click **Create Credentials** > **OAuth client ID**.
2. Choose **Android** as the application type.
3. Enter your Android application package name (e.g. `com.hora.companion`).
4. Enter your SHA-1 certificate fingerprint:
   - For debug key: run `./gradlew signingReport` in the Android project.
   - For release key: run `keytool -list -v -keystore "path/to/release-key.jks" -alias "your-alias"` (using Android Studio's bundled JDK `keytool.exe` at `C:\Program Files\Android\Android Studio\jbr\bin\keytool.exe`).
5. In your Android app Kotlin code, pass the **Web Application Client ID** as the `serverClientId` parameter to `GetGoogleIdOption`.

