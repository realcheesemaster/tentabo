# Tentabo PRM Authentication System

Complete authentication system implementation for Tentabo Partner Relationship Management.

## Features

- **Dual Authentication**: Admin (database) and LDAP user authentication
- **JWT Tokens**: Short-lived bearer tokens for web applications (24h expiration)
- **API Keys**: Long-lived tokens for programmatic access
- **Secure Password Hashing**: bcrypt for all password storage
- **LDAP Integration**: Seamless authentication against Oxiadmin LDAP
- **FastAPI Integration**: Full async/await support with dependency injection
- **Comprehensive Middleware**: Authentication, security headers, request logging
- **Health Checks**: Database and LDAP connectivity monitoring

## Quick Start

### 1. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the environment template:

```bash
cp .env.auth .env
```

Edit `.env` and set your configuration (or use defaults for development).

### 3. Create Admin Account

```bash
python3 setup_admin.py
```

Or non-interactively:

```bash
python3 setup_admin.py --username admin --email admin@tentabo.local --password "YourPassword"
```

### 4. Start the Server

```bash
./run_server.sh
```

Or manually:

```bash
source venv/bin/activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Test the System

```bash
python3 test_auth.py
```

## API Documentation

Once the server is running, visit:

- **Interactive Docs**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI JSON**: http://localhost:8000/api/openapi.json

## Authentication Endpoints

### Login
```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 86400,
  "user_type": "admin"
}
```

### Get Current User Info
```bash
GET /api/v1/auth/me
Authorization: Bearer <token>
```

### Refresh Token
```bash
POST /api/v1/auth/refresh
Authorization: Bearer <token>
```

### Create API Key
```bash
POST /api/v1/users/me/api-keys
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "name": "My API Key",
  "description": "For automated scripts",
  "scopes": ["read", "write"]
}
```

Response:
```json
{
  "api_key": "tnt_xxxxxxxxxxxx",
  "id": "uuid",
  "name": "My API Key",
  "prefix": "tnt_xxxx",
  "scopes": ["read", "write"],
  "message": "Save this key securely - it won't be shown again"
}
```

### List API Keys
```bash
GET /api/v1/users/me/api-keys
Authorization: Bearer <token>
```

### Revoke API Key
```bash
DELETE /api/v1/users/me/api-keys/{key_id}
Authorization: Bearer <token>
```

## Using Authentication

### JWT Token (Web Applications)

```python
import requests

# Login
response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"username": "admin", "password": "admin123"}
)
token = response.json()["access_token"]

# Use token
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(
    "http://localhost:8000/api/v1/auth/me",
    headers=headers
)
```

### API Key (Programmatic Access)

```python
import requests

# Use API key
api_key = "tnt_xxxxxxxxxxxx"
headers = {"Authorization": f"Bearer {api_key}"}

response = requests.get(
    "http://localhost:8000/api/v1/auth/me",
    headers=headers
)
```

## Architecture

### Authentication Flow

1. **Admin Authentication**:
   - Username checked against `admin_users` table
   - Password verified with bcrypt
   - JWT token issued on success

2. **LDAP Authentication**:
   - User searched in LDAP directory
   - Password verified via LDAP bind
   - User synced to database
   - Admin must enable user before access granted
   - JWT token issued on success

3. **Token Validation**:
   - JWT tokens validated via signature and expiration
   - API keys validated via database lookup and bcrypt comparison
   - Both methods return User or AdminUser object

### Security Features

- **No Password Storage**: LDAP users never have passwords stored
- **Bcrypt Hashing**: All stored passwords use bcrypt with salt
- **Constant-Time Comparison**: Prevents timing attacks
- **Token Expiration**: JWT tokens expire after 24 hours
- **API Key Tracking**: Last used timestamp, IP, and usage count
- **Scope Control**: API keys support granular permissions
- **Audit Logging**: All authentication attempts logged
- **Rate Limiting**: Protection against brute force attacks
- **Security Headers**: HSTS, XSS protection, frame denial

## Files Created

### Core Modules
- `/home/francois/tentabo/app/auth/security.py` - Core security functions
- `/home/francois/tentabo/app/auth/ldap_auth.py` - LDAP authentication
- `/home/francois/tentabo/app/auth/dependencies.py` - FastAPI dependencies
- `/home/francois/tentabo/app/core/config.py` - Configuration management

### API Endpoints
- `/home/francois/tentabo/app/api/v1/auth.py` - Authentication endpoints

### Middleware
- `/home/francois/tentabo/app/middleware/authentication.py` - Auth middleware

### Application
- `/home/francois/tentabo/app/main.py` - Main FastAPI application

### Scripts
- `/home/francois/tentabo/setup_admin.py` - Admin account management
- `/home/francois/tentabo/test_auth.py` - Comprehensive test suite
- `/home/francois/tentabo/run_server.sh` - Server startup script

### Configuration
- `/home/francois/tentabo/.env.auth` - Environment template
- `/home/francois/tentabo/requirements.txt` - Python dependencies (updated)

## Testing

The test suite verifies:

1. Health checks (API, database, LDAP)
2. Admin login with database credentials
3. JWT token validation
4. User info retrieval
5. Token refresh
6. API key creation
7. API key listing
8. API key authentication
9. Invalid token handling
10. LDAP user login (if configured)

Run tests:
```bash
python3 test_auth.py
```

## Troubleshooting

### Database Connection Issues

Check database connectivity:
```bash
curl http://localhost:8000/health/db
```

### LDAP Connection Issues

Check LDAP connectivity:
```bash
curl http://localhost:8000/health/ldap
```

### Admin Login Fails

Reset admin password:
```bash
python3 setup_admin.py --username admin --password "newpassword" --update
```

### LDAP User Cannot Login

1. Check LDAP connection: `curl http://localhost:8000/health/ldap`
2. Verify user exists in LDAP
3. Check if user is enabled in database (admin must enable after first login)

## Security Considerations

### Production Deployment

1. **Change Default Secrets**:
   - Generate new JWT secret: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
   - Update `.env` with generated secret

2. **Use HTTPS**:
   - All authentication tokens must be transmitted over HTTPS
   - Set `session_cookie_secure=true` in production

3. **Environment Variables**:
   - Never commit `.env` file to version control
   - Use secure secret management (AWS Secrets Manager, HashiCorp Vault, etc.)

4. **Rate Limiting**:
   - Enable rate limiting in production
   - Adjust limits based on your traffic patterns

5. **Audit Logging**:
   - Review authentication logs regularly
   - Set up alerting for suspicious activity

## Next Steps

1. **Implement Protected Routes**: Add authentication to business logic endpoints
2. **User Management UI**: Build admin interface for enabling/disabling users
3. **Role-Based Access Control**: Implement fine-grained permissions
4. **OAuth2 Providers**: Add Google, Microsoft, etc. authentication
5. **Multi-Factor Authentication**: Add 2FA support
6. **Session Management**: Implement session revocation and management

## Support

For issues or questions, refer to:
- Main documentation: `/home/francois/tentabo/tentabo-prm-reference.md`
- Architecture docs: `/home/francois/tentabo/auth_architecture.md`
- Database schema: `/home/francois/tentabo/DATABASE_SCHEMA.md`
