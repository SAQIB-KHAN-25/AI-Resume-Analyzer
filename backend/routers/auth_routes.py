"""
Authentication Routes for User Registration and Login
"""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from ..database import (
    get_database,
    get_users_collection,
    get_password_resets_collection,
)
from ..models.db_models import UserModel
from ..services.email_service import send_otp_email, is_email_configured
from ..utils.rate_limit import RateLimiter
from bson import ObjectId
from jose import JWTError, jwt
import os
import secrets
import uuid

router = APIRouter()


# ---------- Rate limiters ----------
# All limiters can be disabled globally via env RATE_LIMIT_DISABLED=true.
# Auth endpoints are the primary abuse target (credential stuffing, OTP spam,
# account enumeration) so limits are deliberately conservative. Scoping is by
# client IP; pairing with per-email caps would require a body-caching
# middleware and is deferred until there is a concrete abuse signal.
login_limiter = RateLimiter(max_requests=10, window_seconds=60, scope="auth:login")
register_limiter = RateLimiter(max_requests=5, window_seconds=60, scope="auth:register")
forgot_password_limiter = RateLimiter(
    max_requests=5, window_seconds=300, scope="auth:forgot-password"
)
verify_otp_limiter = RateLimiter(
    max_requests=10, window_seconds=60, scope="auth:verify-otp"
)
reset_password_limiter = RateLimiter(
    max_requests=5, window_seconds=60, scope="auth:reset-password"
)
change_password_limiter = RateLimiter(
    max_requests=5, window_seconds=60, scope="auth:change-password"
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRES_MINUTES = int(os.getenv("JWT_EXPIRES_MINUTES", "60"))

INVALID_CREDENTIALS_MESSAGE = "Invalid email or password"

# In-memory demo auth fallback when MongoDB is unavailable.
DEMO_USERS_BY_ID: dict[str, dict] = {}
DEMO_USER_ID_BY_EMAIL: dict[str, str] = {}

if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is not set. Configure it in your environment before starting the backend.")


class UserRegistration(BaseModel):
    """User registration request"""
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    """User response"""
    id: str
    full_name: str
    email: str
    profile_pic: str | None = None
    created_at: datetime
    is_active: bool


class UserProfileUpdate(BaseModel):
    """User profile update request"""
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    profile_pic: str | None = None


class AuthResponse(BaseModel):
    """Authentication response payload"""
    message: str
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str) -> str:
    """Create a signed JWT access token for the authenticated user."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_EXPIRES_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def validate_password_strength(password: str) -> None:
    """Validate a baseline password policy for account security."""
    has_upper = any(ch.isupper() for ch in password)
    has_lower = any(ch.islower() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    has_special = any(not ch.isalnum() for ch in password)

    if not (has_upper and has_lower and has_digit and has_special):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must include uppercase, lowercase, number, and special character."
        )


def _get_users_collection_safe():
    """Return Mongo users collection or None when DB is unavailable."""
    if get_database() is None:
        return None
    return get_users_collection()


def _format_user_response(user: dict) -> UserResponse:
    """Normalize DB or demo user records into a consistent API response."""
    raw_id = user.get("_id")
    user_id = str(raw_id)
    return UserResponse(
        id=user_id,
        full_name=user["full_name"],
        email=user["email"],
        profile_pic=user.get("profile_pic"),
        created_at=user["created_at"],
        is_active=user.get("is_active", True)
    )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """Resolve the currently authenticated user from bearer JWT token."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    users_collection = _get_users_collection_safe()
    if users_collection is None:
        user = DEMO_USERS_BY_ID.get(user_id)
    else:
        try:
            user = await users_collection.find_one({"_id": ObjectId(user_id)})
        except Exception:
            user = None

    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return user


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(register_limiter)],
)
async def register_user(user_data: UserRegistration):
    """
    Register a new user
    """
    validate_password_strength(user_data.password)

    users_collection = _get_users_collection_safe()
    if users_collection is None:
        if user_data.email in DEMO_USER_ID_BY_EMAIL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        user_id = str(uuid.uuid4())
        created_user = {
            "_id": user_id,
            "full_name": user_data.full_name,
            "email": user_data.email,
            "password_hash": hash_password(user_data.password),
            "profile_pic": None,
            "created_at": datetime.now(timezone.utc),
            "is_active": True,
            "updated_at": datetime.now(timezone.utc),
        }
        DEMO_USERS_BY_ID[user_id] = created_user
        DEMO_USER_ID_BY_EMAIL[user_data.email] = user_id
        created_user_response = _format_user_response(created_user)
    else:
        existing_user = await users_collection.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        user = UserModel(
            full_name=user_data.full_name,
            email=user_data.email,
            password_hash=hash_password(user_data.password)
        )

        result = await users_collection.insert_one(user.model_dump(by_alias=True, exclude={"id"}))
        created_user = await users_collection.find_one({"_id": result.inserted_id})
        created_user_response = _format_user_response(created_user)

    return AuthResponse(
        message="Registration successful",
        access_token=create_access_token(created_user_response.id),
        user=created_user_response
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    dependencies=[Depends(login_limiter)],
)
async def login_user(credentials: UserLogin):
    """
    Login user and return user info
    """
    users_collection = _get_users_collection_safe()
    if users_collection is None:
        demo_user_id = DEMO_USER_ID_BY_EMAIL.get(credentials.email)
        user = DEMO_USERS_BY_ID.get(demo_user_id) if demo_user_id else None
    else:
        user = await users_collection.find_one({"email": credentials.email})

    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS_MESSAGE
        )
    
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been disabled. Please contact support."
        )
    
    user_response = _format_user_response(user)

    return AuthResponse(
        message="Login successful",
        access_token=create_access_token(user_response.id),
        user=user_response
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, current_user=Depends(get_current_user)):
    """
    Get user by ID
    """
    if str(current_user["_id"]) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user"
        )

    users_collection = _get_users_collection_safe()
    if users_collection is None:
        user = DEMO_USERS_BY_ID.get(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return _format_user_response(user)

    try:
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return _format_user_response(user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user ID: {str(e)}"
        )


@router.put("/users/{user_id}")
async def update_user_profile(user_id: str, profile_data: UserProfileUpdate, current_user=Depends(get_current_user)):
    """
    Update user profile details (name, email, profile picture).
    """
    if str(current_user["_id"]) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )

    users_collection = _get_users_collection_safe()
    if users_collection is None:
        existing_user = DEMO_USERS_BY_ID.get(user_id)
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        if profile_data.email != existing_user.get("email"):
            duplicate_id = DEMO_USER_ID_BY_EMAIL.get(profile_data.email)
            if duplicate_id and duplicate_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered with another account"
                )
            old_email = existing_user.get("email")
            if old_email in DEMO_USER_ID_BY_EMAIL:
                del DEMO_USER_ID_BY_EMAIL[old_email]
            DEMO_USER_ID_BY_EMAIL[profile_data.email] = user_id

        existing_user["full_name"] = profile_data.full_name.strip()
        existing_user["email"] = profile_data.email
        existing_user["profile_pic"] = profile_data.profile_pic
        existing_user["updated_at"] = datetime.now(timezone.utc)

        return {
            "message": "Profile updated successfully",
            "user": _format_user_response(existing_user)
        }

    try:
        object_id = ObjectId(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user ID: {str(e)}"
        )

    existing_user = await users_collection.find_one({"_id": object_id})
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if profile_data.email != existing_user.get("email"):
        duplicate_user = await users_collection.find_one({"email": profile_data.email})
        if duplicate_user and str(duplicate_user.get("_id")) != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered with another account"
            )

    await users_collection.update_one(
        {"_id": object_id},
        {
            "$set": {
                "full_name": profile_data.full_name.strip(),
                "email": profile_data.email,
                "profile_pic": profile_data.profile_pic,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )

    updated_user = await users_collection.find_one({"_id": object_id})

    return {
        "message": "Profile updated successfully",
        "user": _format_user_response(updated_user)
    }


# ============================================================================
# Change Password (authenticated)
# ============================================================================

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


@router.post("/change-password", dependencies=[Depends(change_password_limiter)])
async def change_password(payload: ChangePasswordRequest, current_user=Depends(get_current_user)):
    """
    Change the signed-in user's password.
    Requires the current password to match before allowing update.
    """
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=400,
            detail="New password must be different from the current password",
        )

    # Verify the current password against the stored hash
    stored_hash = current_user.get("password_hash") if isinstance(current_user, dict) else None
    if not stored_hash or not verify_password(payload.current_password, stored_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Enforce password strength on the new password
    validate_password_strength(payload.new_password)

    new_hash = hash_password(payload.new_password)

    users_collection = _get_users_collection_safe()
    user_id = current_user.get("_id") if isinstance(current_user, dict) else None

    if users_collection is None:
        # Demo-mode in-memory store
        uid = str(user_id) if user_id else None
        record = DEMO_USERS_BY_ID.get(uid) if uid else None
        if not record:
            raise HTTPException(status_code=404, detail="User not found")
        record["password_hash"] = new_hash
        record["updated_at"] = datetime.now(timezone.utc)
    else:
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")
        result = await users_collection.update_one(
            {"_id": user_id},
            {"$set": {"password_hash": new_hash, "updated_at": datetime.now(timezone.utc)}},
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")

    return {"message": "Password changed successfully"}


# ============================================================================
# Forgot Password — OTP Flow
# ============================================================================

OTP_TTL_MINUTES = int(os.getenv("OTP_TTL_MINUTES", "10"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
OTP_RESEND_COOLDOWN_SECONDS = int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "60"))
RESET_TOKEN_TTL_MINUTES = int(os.getenv("RESET_TOKEN_TTL_MINUTES", "10"))

# In-memory store used when MongoDB is unavailable (demo mode)
DEMO_PASSWORD_RESETS: dict[str, dict] = {}


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=4, max_length=10)


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str = Field(min_length=8, max_length=128)


def _generate_otp() -> str:
    """Generate a 6-digit numeric OTP."""
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_otp(otp: str) -> str:
    return pwd_context.hash(otp)


def _verify_otp(plain_otp: str, hashed_otp: str) -> bool:
    try:
        return pwd_context.verify(plain_otp, hashed_otp)
    except Exception:
        return False


async def _find_user_by_email(email: str):
    users_collection = _get_users_collection_safe()
    if users_collection is None:
        demo_user_id = DEMO_USER_ID_BY_EMAIL.get(email)
        return DEMO_USERS_BY_ID.get(demo_user_id) if demo_user_id else None
    return await users_collection.find_one({"email": email})


async def _store_password_reset(email: str, record: dict) -> None:
    coll = get_password_resets_collection()
    if coll is None:
        DEMO_PASSWORD_RESETS[email] = record
        return
    await coll.replace_one({"email": email}, {"email": email, **record}, upsert=True)


async def _get_password_reset(email: str):
    coll = get_password_resets_collection()
    if coll is None:
        return DEMO_PASSWORD_RESETS.get(email)
    return await coll.find_one({"email": email})


async def _delete_password_reset(email: str) -> None:
    coll = get_password_resets_collection()
    if coll is None:
        DEMO_PASSWORD_RESETS.pop(email, None)
        return
    await coll.delete_one({"email": email})


def _create_reset_token(email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": email,
        "purpose": "password_reset",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def _decode_reset_token(token: str) -> str:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=400, detail="Reset link expired or invalid")
    if payload.get("purpose") != "password_reset":
        raise HTTPException(status_code=400, detail="Invalid reset token")
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=400, detail="Invalid reset token")
    return email


@router.post("/forgot-password", dependencies=[Depends(forgot_password_limiter)])
async def forgot_password(payload: ForgotPasswordRequest):
    """
    Initiate a password reset by emailing a one-time code to the registered address.
    Always returns 200 with whether the email is registered (per app config).
    """
    email = payload.email.lower().strip()
    user = await _find_user_by_email(email)

    if not user:
        # Per project preference, reveal that the email is not registered.
        return {
            "email_registered": False,
            "message": "No account found with that email.",
        }

    # Resend cooldown check
    existing = await _get_password_reset(email)
    now = datetime.now(timezone.utc)
    if existing:
        last_sent = existing.get("last_sent_at")
        if last_sent:
            if last_sent.tzinfo is None:
                last_sent = last_sent.replace(tzinfo=timezone.utc)
            elapsed = (now - last_sent).total_seconds()
            if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
                remaining = int(OTP_RESEND_COOLDOWN_SECONDS - elapsed)
                raise HTTPException(
                    status_code=429,
                    detail=f"Please wait {remaining}s before requesting another code.",
                )

    otp = _generate_otp()
    expires_at = now + timedelta(minutes=OTP_TTL_MINUTES)

    await _store_password_reset(email, {
        "otp_hash": _hash_otp(otp),
        "expires_at": expires_at,
        "attempts": 0,
        "max_attempts": OTP_MAX_ATTEMPTS,
        "last_sent_at": now,
        "verified": False,
    })

    sent_ok = send_otp_email(email, otp, ttl_minutes=OTP_TTL_MINUTES)

    return {
        "email_registered": True,
        "message": "If an account exists for this email, a verification code has been sent.",
        "expires_in_minutes": OTP_TTL_MINUTES,
        "resend_cooldown_seconds": OTP_RESEND_COOLDOWN_SECONDS,
        "delivered": sent_ok,
        "email_configured": is_email_configured(),
    }


@router.post("/verify-otp", dependencies=[Depends(verify_otp_limiter)])
async def verify_otp(payload: VerifyOtpRequest):
    """Verify the OTP and return a short-lived reset token if valid."""
    email = payload.email.lower().strip()
    otp = payload.otp.strip()

    record = await _get_password_reset(email)
    if not record:
        raise HTTPException(status_code=400, detail="No active reset request. Please request a new code.")

    expires_at = record.get("expires_at")
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if not expires_at or datetime.now(timezone.utc) > expires_at:
        await _delete_password_reset(email)
        raise HTTPException(status_code=400, detail="The code has expired. Please request a new one.")

    attempts = int(record.get("attempts", 0))
    max_attempts = int(record.get("max_attempts", OTP_MAX_ATTEMPTS))
    if attempts >= max_attempts:
        await _delete_password_reset(email)
        raise HTTPException(status_code=429, detail="Too many incorrect attempts. Please request a new code.")

    if not _verify_otp(otp, record.get("otp_hash", "")):
        # Increment attempt counter
        new_attempts = attempts + 1
        coll = get_password_resets_collection()
        if coll is None:
            if email in DEMO_PASSWORD_RESETS:
                DEMO_PASSWORD_RESETS[email]["attempts"] = new_attempts
        else:
            await coll.update_one({"email": email}, {"$set": {"attempts": new_attempts}})
        remaining = max(0, max_attempts - new_attempts)
        raise HTTPException(
            status_code=400,
            detail=f"Incorrect code. {remaining} attempt{'s' if remaining != 1 else ''} remaining.",
        )

    # Mark as verified
    coll = get_password_resets_collection()
    if coll is None:
        DEMO_PASSWORD_RESETS[email]["verified"] = True
    else:
        await coll.update_one({"email": email}, {"$set": {"verified": True}})

    return {
        "verified": True,
        "reset_token": _create_reset_token(email),
        "expires_in_minutes": RESET_TOKEN_TTL_MINUTES,
    }


@router.post("/reset-password", dependencies=[Depends(reset_password_limiter)])
async def reset_password(payload: ResetPasswordRequest):
    """Reset the user's password using a verified reset token."""
    email = _decode_reset_token(payload.reset_token)

    record = await _get_password_reset(email)
    if not record or not record.get("verified"):
        raise HTTPException(status_code=400, detail="Reset session not verified. Please verify the OTP again.")

    validate_password_strength(payload.new_password)

    new_hash = hash_password(payload.new_password)

    users_collection = _get_users_collection_safe()
    if users_collection is None:
        user_id = DEMO_USER_ID_BY_EMAIL.get(email)
        user = DEMO_USERS_BY_ID.get(user_id) if user_id else None
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user["password_hash"] = new_hash
        user["updated_at"] = datetime.now(timezone.utc)
    else:
        result = await users_collection.update_one(
            {"email": email},
            {"$set": {"password_hash": new_hash, "updated_at": datetime.now(timezone.utc)}},
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")

    await _delete_password_reset(email)

    return {"message": "Password reset successful. You can now sign in with your new password."}
