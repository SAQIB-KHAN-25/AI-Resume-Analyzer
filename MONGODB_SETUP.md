# MongoDB Setup Guide

## Connection Details

**MongoDB Server:** Asterinfinity MongoDB Server  
**Connection String:** Set via environment variable `MONGODB_URL` in your local `.env` file (do not commit credentials).  
**Database Name:** `ai_resume_analyzer`

## Collections

The application uses the following MongoDB collections:

1. **users** - User accounts and authentication
2. **resumes** - Uploaded resume data and extracted information
3. **job_descriptions** - Job descriptions and requirements
4. **analysis_results** - Resume analysis results and recommendations

## Installation Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

New packages installed:
- `motor==3.3.2` - Async MongoDB driver for FastAPI
- `pymongo==4.6.1` - MongoDB driver
- `passlib==1.7.4` - Password hashing
- `bcrypt==4.1.2` - Password encryption

### 2. Database Configuration

The database configuration is located in `backend/database.py`:
- Automatic connection on server startup
- Connection pooling configured (min: 1, max: 10)
- Automatic reconnection on failure

### 3. Start the Backend Server

```bash
cd backend
uvicorn main:app --reload
```

You should see:
```
✓ Connected to MongoDB successfully!
✓ Database: ai_resume_analyzer
✓ Application startup complete
```

## API Endpoints

### Authentication
- **POST** `/api/auth/register` - Register new user
- **POST** `/api/auth/login` - Login user
- **GET** `/api/auth/users/{user_id}` - Get user by ID

### Resume Analysis
- **POST** `/api/upload_resume` - Upload and parse resume
- **POST** `/api/upload_jd` - Process job description

## Frontend Integration

The frontend is already configured to connect to the backend authentication API:
- Sign In page connects to `/api/auth/login`
- Sign Up page connects to `/api/auth/register`
- User data stored in localStorage after successful authentication

## Testing the Connection

1. Start the backend server
2. Visit `http://localhost:8000/docs` for API documentation
3. Test the `/health` endpoint to verify server is running
4. Create a new user account via Sign Up page
5. Login with the created account

## Security Notes

- Passwords are hashed using bcrypt
- Connection uses TLS/SSL encryption
- User sessions use JWT bearer tokens
- Store all secrets (`MONGODB_URL`, `JWT_SECRET_KEY`) only in environment files excluded from git

## Troubleshooting

If connection fails:
1. Check internet connectivity
2. Verify MongoDB cluster is accessible
3. Check firewall settings
4. Review server logs for detailed error messages
