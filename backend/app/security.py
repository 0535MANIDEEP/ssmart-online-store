import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from dotenv import load_dotenv

# -------------------------------------------------
# Load .env (project root /backend/.env)
# -------------------------------------------------
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(dotenv_path=env_path)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# -------------------------------------------------
# Password hashing
# -------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# -------------------------------------------------
# Simple in‑memory user store (populated from .env)
# -------------------------------------------------
class User(BaseModel):
    username: str
    hashed_password: str
    role: str   # "admin", "staff", etc.

def load_users() -> dict[str, User]:
    users_raw = os.getenv("USERS", "")
    users: dict[str, User] = {}
    for line in users_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        username, hpw, role = line.split("|")
        users[username] = User(username=username, hashed_password=hpw, role=role)
    return users

_users_cache = load_users()

def authenticate_user(username: str, password: str) -> Optional[User]:
    user = _users_cache.get(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

# -------------------------------------------------
# JWT token handling
# -------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=role)
    except JWTError:
        raise credentials_exception
    user = _users_cache.get(token_data.username)
    if user is None:
        raise credentials_exception
    return user

def require_role(required_role: str):
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires '{required_role}' role",
            )
        return current_user
    return role_checker
