# Tentabo PRM Authentication Architecture

## Two-Layer Authentication System

### Overview
Tentabo PRM uses two types of authentication tokens:
1. **Session Tokens (JWT)** - For web application sessions (short-lived)
2. **API Keys** - For programmatic API access (long-lived)

## V1 Authentication Design

### 1. Admin Account (Independent)
- **Storage**: PostgreSQL database
- **Password**: Hashed with bcrypt in DB
- **No LDAP dependency**: Works even if all auth providers fail
- **Purpose**: System administration, emergency access, provider management

```python
class AdminUser(Base):
    __tablename__ = 'admin_users'

    id = Column(UUID, primary_key=True)
    username = Column(String, unique=True)  # 'admin'
    password_hash = Column(String)  # bcrypt hash
    created_at = Column(DateTime)
    last_login = Column(DateTime)
```

### 2. Regular Users (Provider-Based)
- **V1**: LDAP authentication only
- **V2**: Multiple auth providers (LDAP, SSO, OAuth, etc.)
- **Storage**: User records in PostgreSQL after first login
- **Roles**: Assigned by admin in PostgreSQL

```python
class User(Base):
    __tablename__ = 'users'

    id = Column(UUID, primary_key=True)
    provider = Column(String)  # 'ldap', future: 'google', 'saml', etc.
    provider_id = Column(String)  # LDAP uid, OAuth ID, etc.
    email = Column(String)
    full_name = Column(String)

    # Authorization (managed in our DB)
    role = Column(Enum(UserRole))
    is_enabled = Column(Boolean, default=False)
    enabled_by = Column(UUID, ForeignKey('admin_users.id'))
    enabled_at = Column(DateTime)

    created_at = Column(DateTime)
    last_login = Column(DateTime)
```

### 3. API Keys (Personal Access Tokens)
- **Purpose**: Long-lived tokens for API access without storing passwords
- **Storage**: Hashed in PostgreSQL, only shown once at creation
- **Management**: Users can create, name, and revoke their own keys

```python
class APIKey(Base):
    __tablename__ = 'api_keys'

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey('users.id'), nullable=False)
    admin_id = Column(UUID, ForeignKey('admin_users.id'), nullable=True)

    name = Column(String, nullable=False)  # "Mobile App", "Zapier Integration"
    key_hash = Column(String, nullable=False)  # bcrypt hash of the actual key
    key_prefix = Column(String(8), nullable=False)  # "tnt_xxxx" for identification

    last_used_at = Column(DateTime, nullable=True)
    last_used_ip = Column(String(45), nullable=True)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration

    scopes = Column(JSONB, default=list)  # ["read:leads", "write:orders"]
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=func.now())
    revoked_at = Column(DateTime, nullable=True)
    revoked_reason = Column(String, nullable=True)

    # Relationships
    user = relationship("User", back_populates="api_keys")
    admin = relationship("AdminUser", back_populates="api_keys")
```

## Authentication Flows

### Session Authentication (Web App)

#### 1. Web Login (Returns JWT)
```python
# POST /api/v1/auth/login
def login(username: str, password: str):
    # For admin
    if is_admin_username(username):
        admin = db.query(AdminUser).filter_by(username=username).first()
        if admin and bcrypt.verify(password, admin.password_hash):
            return {
                "access_token": create_jwt_token(admin, expires_in="24h"),
                "token_type": "Bearer",
                "expires_in": 86400
            }

    # For regular users (LDAP)
    if ldap_authenticate(username, password):
        user = db.query(User).filter_by(
            provider='ldap',
            provider_id=username
        ).first()

        if user and user.is_enabled:
            return {
                "access_token": create_jwt_token(user, expires_in="24h"),
                "token_type": "Bearer",
                "expires_in": 86400
            }

    raise AuthenticationError("Invalid credentials")
```

#### 2. Using JWT in Web App
```python
# All subsequent requests from web app
GET /api/v1/leads
Headers:
    Authorization: Bearer eyJhbGciOiJIUzI1NiIs...  # JWT token
```

### API Key Authentication (Programmatic Access)

#### 1. Creating API Keys
```python
# POST /api/v1/users/me/api-keys (requires JWT auth)
def create_api_key(
    current_user: User,
    name: str,
    expires_in_days: Optional[int] = None,
    scopes: List[str] = ["read", "write"]
):
    # Generate cryptographically secure random key
    raw_key = f"tnt_{secrets.token_urlsafe(32)}"

    # Store only the hash
    api_key = APIKey(
        user_id=current_user.id,
        name=name,
        key_hash=bcrypt.hash(raw_key),
        key_prefix=raw_key[:8],  # Store prefix for identification
        expires_at=datetime.utcnow() + timedelta(days=expires_in_days) if expires_in_days else None,
        scopes=scopes
    )
    db.add(api_key)
    db.commit()

    # Return the raw key only once
    return {
        "api_key": raw_key,
        "name": name,
        "expires_at": api_key.expires_at,
        "message": "Save this key securely - it won't be shown again"
    }
```

#### 2. Using API Keys
```python
# For all API requests from external applications
GET /api/v1/leads
Headers:
    Authorization: Bearer tnt_8f3e2a5b9c7d1e4f6a8b3c5d7e9f1a3b5c7d9e1f

# Backend validation
def validate_api_key(token: str):
    # Find potential keys by prefix
    prefix = token[:8]
    potential_keys = db.query(APIKey).filter(
        APIKey.key_prefix == prefix,
        APIKey.is_active == True
    ).all()

    for key in potential_keys:
        if bcrypt.verify(token, key.key_hash):
            # Update last used
            key.last_used_at = datetime.utcnow()
            key.last_used_ip = request.client.host
            db.commit()

            # Check expiration
            if key.expires_at and key.expires_at < datetime.utcnow():
                raise AuthenticationError("API key expired")

            return key.user  # or key.admin

    raise AuthenticationError("Invalid API key")
```

#### 3. Managing API Keys
```python
# GET /api/v1/users/me/api-keys (list all keys)
def list_api_keys(current_user: User):
    keys = db.query(APIKey).filter(
        APIKey.user_id == current_user.id,
        APIKey.is_active == True
    ).all()

    return [{
        "id": key.id,
        "name": key.name,
        "prefix": key.key_prefix,
        "last_used_at": key.last_used_at,
        "expires_at": key.expires_at,
        "scopes": key.scopes
    } for key in keys]

# DELETE /api/v1/users/me/api-keys/{key_id} (revoke a key)
def revoke_api_key(current_user: User, key_id: UUID, reason: str):
    key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()

    if key:
        key.is_active = False
        key.revoked_at = datetime.utcnow()
        key.revoked_reason = reason
        db.commit()
```

## Benefits of This Architecture

### Security Advantages
1. **No Password Storage**: Applications never store user passwords
2. **Granular Revocation**: Can revoke specific keys without changing password
3. **Audit Trail**: Track which key performed which action
4. **Scope Control**: Limit what each key can access
5. **Separate Concerns**: Web sessions separate from API access

### Use Cases

#### When to Use JWT (Session Tokens)
- Web browser sessions
- Mobile app sessions with user interaction
- Short-term access (hours to days)
- When user can re-authenticate easily

#### When to Use API Keys
- CI/CD pipelines
- Automated scripts
- Third-party integrations (Zapier, etc.)
- Mobile/desktop apps that need persistent access
- IoT devices
- Backup services
- Monitoring tools

### Example Scenarios

```python
# Scenario 1: Web Dashboard
# User logs in with username/password → Gets JWT → Uses for session

# Scenario 2: Mobile App
# User logs in once → Creates API key "My Phone" → App stores key securely

# Scenario 3: Automation Script
# Admin creates API key "Nightly Report Script" → Script uses key indefinitely

# Scenario 4: Partner Integration
# Partner creates API key "ERP Sync" with read-only scope → Limited access
```

## LDAP Service Account Credentials

**Purpose**: Application uses this account to query LDAP (not for user auth)

- **Server**: ldaps://auth.fr.oxileo.net:6366
- **Bind DN**: cn=view,dc=oxileo,dc=net
- **Password**: QsL7OWWfWHcuMqfjcOLYwgBjX0V6gE
- **Base DN**: dc=oxileo,dc=net

**Storage**: Environment variables or encrypted in DB `provider_configs` table

## Implementation Checklist

- [ ] Add `api_keys` table to database schema
- [ ] Create API key generation endpoint
- [ ] Implement dual authentication middleware (JWT or API key)
- [ ] Add API key management UI in web app
- [ ] Document API key scopes and permissions
- [ ] Set up audit logging for API key usage
- [ ] Create rate limiting per API key
- [ ] Add API key rotation recommendations