# User Authentication Backend

JWT-based user authentication backend built with FastAPI and PostgreSQL, following SOLID principles and clean architecture patterns.

## Features

### Authentication
- User registration and login
- JWT token authentication (access + refresh tokens)
- Password management (change password, reset password)
- Token refresh mechanism
- Secure password hashing with bcrypt

### Dashboard
- JWT-protected dashboard API
- User-specific dashboard data
- Extensible data structure for future features

### Infrastructure
- PostgreSQL database with connection pooling
- Database migrations with Alembic
- Comprehensive API documentation (Swagger/OpenAPI)
- Clean architecture (API → Service → Repository → Models)
- SOLID principles throughout

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL (Docker recommended)
- pip3 or poetry

### Setup

1. **Start PostgreSQL**
   ```bash
   docker start pg_local
   ```

2. **Install dependencies**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.local .env
   # or create .env with your DATABASE_URL
   ```

4. **Run migrations**
   ```bash
   alembic upgrade head
   ```

5. **Start the application**
   ```bash
   uvicorn app.main:app --reload
   ```

6. **Access API documentation**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
  - Request: `{"email": "user@example.com", "password": "Password123"}`
  - Response: User details (201 Created)
  
- `POST /api/auth/login` - Login and get tokens
  - Request: `{"email": "user@example.com", "password": "Password123"}`
  - Response: `{"access_token": "...", "refresh_token": "...", "token_type": "bearer"}`
  
- `POST /api/auth/change-password` - Change password (🔒 protected)
  - Request: `{"current_password": "Old123", "new_password": "New456"}`
  - Headers: `Authorization: Bearer <access_token>`
  - Response: Success message
  
- `POST /api/auth/reset-password/request` - Request password reset
  - Request: `{"email": "user@example.com"}`
  - Response: Success message with reset token
  
- `POST /api/auth/reset-password/confirm` - Confirm password reset
  - Request: `{"token": "reset_token", "new_password": "NewPass123"}`
  - Response: Success message
  
- `POST /api/auth/refresh` - Refresh access token
  - Request: `{"refresh_token": "..."}`
  - Response: New access token

### Dashboard (🔒 JWT Protected)
- `GET /api/dashboard` - Get user dashboard data
  - Headers: `Authorization: Bearer <access_token>`
  - Response: User dashboard with summary, stats, and activity
  - Example response:
    ```json
    {
      "user_id": 1,
      "email": "user@example.com",
      "dashboard_data": {
        "summary": {
          "total_logins": 0,
          "last_login": null,
          "account_created": "2024-01-15T10:30:00Z"
        },
        "stats": {},
        "recent_activity": []
      },
      "message": "Dashboard data retrieved successfully"
    }
    ```

### Health
- `GET /health` - Health check
  - Response: `{"status": "healthy", "database": "connected"}`

## Database

### PostgreSQL Configuration

**Docker Container:**
```
Host: localhost
Port: 5432
Database: ai_admin
Username: admin
Password: admin123
Connection: postgresql://admin:admin123@localhost:5432/ai_admin
```

### Connection Pooling

The application uses SQLAlchemy's QueuePool for efficient connection management:

- **Pool Size**: 5 (minimum connections maintained)
- **Max Overflow**: 10 (additional connections allowed)
- **Pool Timeout**: 30 seconds (wait time for connection)
- **Pool Recycle**: 1 hour (recycle stale connections)
- **Pool Pre-Ping**: Enabled (verify connections before use)

**Benefits:**
- Reuses connections for better performance
- Detects and removes stale connections automatically
- Handles concurrent requests efficiently
- Limits total connections to database

### Database Models

**Users Table:**
- id (Primary Key)
- email (Unique, Indexed)
- password_hash
- is_active
- created_at
- updated_at

**Password Reset Tokens Table:**
- id (Primary Key)
- user_id (Foreign Key → users.id)
- token (Unique, Indexed)
- expires_at
- created_at
- used

## Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_api_endpoints.py -v

# Run dashboard tests only
pytest tests/test_dashboard_api.py tests/test_dashboard_service.py -v

# Run with verbose output
pytest -v --tb=short
```

### Test Coverage

- **Unit Tests**: Service layer business logic
- **Integration Tests**: API endpoints with database
- **Property-Based Tests**: JWT security properties
- **End-to-End Tests**: Complete user flows

**Test Files:**
- `test_auth_service_integration.py` - Auth service tests
- `test_api_endpoints.py` - Auth API endpoint tests
- `test_dashboard_service.py` - Dashboard service tests (7 tests)
- `test_dashboard_api.py` - Dashboard API tests (9 tests)
- `test_e2e_flows.py` - End-to-end flow tests
- `test_jwt_properties.py` - JWT property-based tests
- `test_exception_handlers.py` - Error handling tests
- `test_health_check.py` - Health check tests

## Project Structure

```
backend/
├── app/
│   ├── api/v1/endpoints/
│   │   ├── auth.py          # Authentication endpoints
│   │   └── dashboard.py     # Dashboard endpoints (NEW)
│   ├── core/
│   │   ├── config.py        # Configuration management
│   │   ├── database.py      # Database connection & pooling
│   │   ├── dependencies.py  # Dependency injection
│   │   ├── exceptions.py    # Custom exceptions
│   │   └── security.py      # JWT & password hashing
│   ├── models/
│   │   └── user.py          # User & PasswordResetToken models
│   ├── repositories/
│   │   ├── user_repository.py              # User data access
│   │   └── password_reset_repository.py    # Reset token data access
│   ├── schemas/
│   │   ├── auth.py          # Auth request/response schemas
│   │   └── dashboard.py     # Dashboard schemas (NEW)
│   ├── services/
│   │   ├── auth_service.py      # Auth business logic
│   │   └── dashboard_service.py # Dashboard business logic (NEW)
│   └── main.py              # Application entry point
├── alembic/                 # Database migrations
│   ├── versions/            # Migration files
│   └── env.py               # Alembic configuration
├── tests/                   # Test files
│   ├── test_auth_service_integration.py
│   ├── test_api_endpoints.py
│   ├── test_dashboard_service.py    # NEW
│   ├── test_dashboard_api.py        # NEW
│   ├── test_e2e_flows.py
│   ├── test_jwt_properties.py
│   ├── test_exception_handlers.py
│   ├── test_health_check.py
│   └── conftest.py          # Test fixtures
├── scripts/
│   └── setup_database.py    # Database verification script
├── .env.local               # Local development config
├── .env.example             # Example configuration
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

### Architecture

The application follows **Clean Architecture** principles with clear separation of concerns:

```
┌─────────────────────────────────────────┐
│         API Layer (FastAPI)              │
│  - HTTP request/response                 │
│  - JWT authentication                    │
│  - OpenAPI documentation                 │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│         Service Layer                    │
│  - Business logic                        │
│  - Data aggregation                      │
│  - Validation                            │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│         Repository Layer                 │
│  - Database operations                   │
│  - Query construction                    │
│  - Transaction management                │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│         Data Layer (Models)              │
│  - SQLAlchemy ORM models                 │
│  - Database schema                       │
└─────────────────────────────────────────┘
```

## Development

### Database Verification

Verify database connection and setup:

```bash
python3 scripts/setup_database.py
```

This script checks:
- Database connectivity
- Connection pool status
- Table existence
- Migration status
- CRUD operations

### Create New Migration

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Check current version
alembic current
```

### Code Formatting

```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Type checking
mypy app/
```

### Development Workflow

1. **Make changes** to code
2. **Create migration** if database schema changed
3. **Write tests** for new functionality
4. **Run tests** to verify
5. **Format code** before committing
6. **Update documentation** as needed

## Security

### Password Security
- **Hashing**: bcrypt with 12 rounds (configurable)
- **Salt**: Unique salt per password (automatic)
- **Requirements**: Minimum 8 characters, letters + numbers
- **Storage**: Never stored in plain text
- **Comparison**: Constant-time comparison to prevent timing attacks

### Token Security
- **Algorithm**: HS256 (HMAC with SHA-256)
- **Secret Key**: Stored in environment variables (256-bit minimum)
- **Access Token**: 30-minute expiration
- **Refresh Token**: 7-day expiration
- **Claims**: user_id, type, exp (expiration), iat (issued at)
- **Validation**: Signature, expiration, and structure verified

### API Security
- **JWT Protection**: All dashboard endpoints require valid JWT
- **HTTPS**: Required in production
- **CORS**: Configurable allowed origins
- **Error Handling**: Sanitized error messages (no sensitive data leakage)
- **Input Validation**: Strict validation using Pydantic schemas

### Database Security
- **Connection Pooling**: Limits concurrent connections
- **SSL**: Supported for production
- **Credentials**: Stored in environment variables
- **Migrations**: Version-controlled schema changes
- **Indexes**: Optimized queries with proper indexing

## Environment Variables

### Required Variables

Create `.env` or `.env.local` file with:

```env
# Application
APP_ENV=development
APP_NAME=DeveloperDocAI
APP_HOST=0.0.0.0
APP_PORT=8000

# Database (PostgreSQL)
DATABASE_URL=postgresql://admin:admin123@localhost:5432/ai_admin

# JWT Configuration
JWT_SECRET_KEY=your-256-bit-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Password Reset
PASSWORD_RESET_TOKEN_EXPIRE_HOURS=1

# Password Hashing
BCRYPT_ROUNDS=12

# Other
SECRET_KEY=your-secret-key
OPENAI_API_KEY=your-openai-key
```

### Configuration Priority

1. `.env.local` (local development - highest priority)
2. `.env` (general configuration)
3. Environment variables (system-level)
4. Default values (in code)

### Generate Secure Keys

```bash
# Generate JWT secret key
openssl rand -hex 32

# Generate general secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## License

MIT


## SOLID Principles

The codebase follows SOLID principles for maintainability and extensibility:

### Single Responsibility Principle (SRP)
- Each class has one clear responsibility
- Services handle business logic only
- Repositories handle data access only
- Endpoints handle HTTP concerns only

### Open/Closed Principle (OCP)
- Open for extension (new features)
- Closed for modification (existing code)
- Easy to add new endpoints without changing existing code

### Liskov Substitution Principle (LSP)
- Services can be replaced with different implementations
- Mock implementations used in tests
- Interface contracts maintained

### Interface Segregation Principle (ISP)
- Minimal, focused interfaces
- Clients only depend on methods they use
- No forced dependencies on unused methods

### Dependency Inversion Principle (DIP)
- Depends on abstractions (protocols/interfaces)
- High-level modules don't depend on low-level modules
- Dependency injection throughout

## API Usage Examples

### Complete Authentication Flow

```bash
# 1. Register a new user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"SecurePass123"}'

# Response: {"id":1,"email":"user@example.com","created_at":"...","is_active":true}

# 2. Login to get tokens
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"SecurePass123"}'

# Response: {"access_token":"eyJ...","refresh_token":"eyJ...","token_type":"bearer"}

# 3. Access dashboard (use access_token from step 2)
curl -X GET http://localhost:8000/api/dashboard \
  -H "Authorization: Bearer eyJ..."

# Response: {"user_id":1,"email":"user@example.com","dashboard_data":{...}}

# 4. Change password
curl -X POST http://localhost:8000/api/auth/change-password \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ..." \
  -d '{"current_password":"SecurePass123","new_password":"NewPass456"}'

# 5. Refresh access token
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"eyJ..."}'
```

### Using Python

```python
import requests

BASE_URL = "http://localhost:8000"

# Register
response = requests.post(
    f"{BASE_URL}/api/auth/register",
    json={"email": "user@example.com", "password": "SecurePass123"}
)
print(f"Registered: {response.json()}")

# Login
response = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={"email": "user@example.com", "password": "SecurePass123"}
)
tokens = response.json()
access_token = tokens["access_token"]

# Get dashboard
response = requests.get(
    f"{BASE_URL}/api/dashboard",
    headers={"Authorization": f"Bearer {access_token}"}
)
dashboard = response.json()
print(f"Dashboard: {dashboard}")
```

## Troubleshooting

### Database Connection Issues

**Problem**: Can't connect to PostgreSQL

**Solution**:
```bash
# Check if PostgreSQL is running
docker ps | grep pg_local

# Start PostgreSQL
docker start pg_local

# Check logs
docker logs pg_local

# Verify connection
docker exec -it pg_local psql -U admin -d ai_admin
```

### Migration Issues

**Problem**: Tables not found

**Solution**:
```bash
# Check migration status
alembic current

# Run migrations
alembic upgrade head

# If issues persist, check DATABASE_URL in .env
```

### Test Failures

**Problem**: Tests failing with database errors

**Solution**:
```bash
# Clean test databases
rm -f test*.db

# Run tests in isolation
pytest tests/test_dashboard_api.py -v

# Check database setup in conftest.py
```

### JWT Token Issues

**Problem**: Token validation failing

**Solution**:
- Verify JWT_SECRET_KEY is set in .env
- Check token hasn't expired (30 min for access tokens)
- Ensure Bearer prefix in Authorization header
- Verify token format: `Authorization: Bearer <token>`

## Performance Considerations

### Connection Pooling
- Reuses database connections
- Reduces connection overhead
- Handles concurrent requests efficiently
- Configurable pool size based on load

### Caching (Future)
- Add Redis for session caching
- Cache dashboard data for performance
- Implement cache invalidation strategy

### Scaling (Future)
- Horizontal scaling with load balancer
- Read replicas for database
- Separate auth and dashboard services
- Implement rate limiting

## Contributing

### Code Style
- Follow PEP 8 style guide
- Use type hints
- Write docstrings for all functions
- Keep functions small and focused

### Testing
- Write tests for all new features
- Maintain test coverage above 90%
- Include unit and integration tests
- Test edge cases and error scenarios

### Documentation
- Update README for new features
- Add inline code comments
- Document API changes in Swagger
- Keep examples up to date

## Future Enhancements

### Planned Features
- [ ] Email verification on registration
- [ ] Two-factor authentication (2FA)
- [ ] OAuth integration (Google, GitHub)
- [ ] Session management
- [ ] Role-based access control (RBAC)
- [ ] Audit logging
- [ ] Rate limiting
- [ ] Real-time dashboard updates
- [ ] Dashboard customization
- [ ] Activity tracking

### Dashboard Extensions
- [ ] Real login statistics
- [ ] User activity timeline
- [ ] Analytics and insights
- [ ] Customizable widgets
- [ ] Export functionality

## Support

### Documentation
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc (ReDoc)
- **Database Setup**: See `DATABASE_SETUP.md`
- **Dashboard Guide**: See `DASHBOARD_IMPLEMENTATION_SUMMARY.md`

### Resources
- FastAPI Documentation: https://fastapi.tiangolo.com/
- SQLAlchemy Documentation: https://docs.sqlalchemy.org/
- Alembic Documentation: https://alembic.sqlalchemy.org/
- PostgreSQL Documentation: https://www.postgresql.org/docs/

## License

MIT
