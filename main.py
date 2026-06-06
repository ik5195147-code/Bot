from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import jwt
import os
import json
import shutil
import zipfile
import asyncio
import subprocess
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import aiofiles
from pathlib import Path
from passlib.context import CryptContext
import psutil

# Configuration
SECRET_KEY = "your-secret-key-change-this"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440
BOTS_DIR = "bots"
LOGS_DIR = "logs"
DB_URL = "sqlite:///./bot_panel.db"

# Ensure directories exist
os.makedirs(BOTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# Pydantic Models
class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class BotStatus(BaseModel):
    bot_name: str
    status: str  # running, stopped
    pid: Optional[int] = None

class BotCreate(BaseModel):
    bot_name: str

# FastAPI App
app = FastAPI(title="Bot Hosting Panel", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper Functions
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = None, db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# Running processes dictionary
running_processes: Dict[str, subprocess.Popen] = {}
active_connections: Dict[str, List[WebSocket]] = {}

# Auth Routes
@app.post("/api/register", response_model=Token)
def register(user: UserRegister, db: Session = Depends(get_db)):
    """Register a new user"""
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        id=str(datetime.utcnow().timestamp()),
        username=user.username,
        email=user.email,
        hashed_password=hash_password(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.username},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    """Login user"""
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.username},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/me")
def get_current_user_info(token: str = None, db: Session = Depends(get_db)):
    """Get current user info"""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = get_current_user(token, db)
    return {"username": user.username, "email": user.email}

# Bot Management Routes
@app.post("/api/bots/{bot_name}/start")
async def start_bot(bot_name: str, token: str = None, db: Session = Depends(get_db)):
    """Start a bot"""
    user = get_current_user(token, db)
    
    bot_path = os.path.join(BOTS_DIR, user.username, bot_name)
    main_file = os.path.join(bot_path, "main.py")
    
    if not os.path.exists(main_file):
        raise HTTPException(status_code=404, detail="Bot main.py not found")
    
    if bot_name in running_processes and running_processes[bot_name].poll() is None:
        raise HTTPException(status_code=400, detail="Bot already running")
    
    log_file = os.path.join(LOGS_DIR, f"{bot_name}.log")
    
    try:
        with open(log_file, "a") as lf:
            lf.write(f"\n[{datetime.now()}] Starting bot...\n")
        
        process = subprocess.Popen(
            ["python", main_file],
            cwd=bot_path,
            stdout=open(log_file, "a"),
            stderr=subprocess.STDOUT
        )
        running_processes[bot_name] = process
        
        return {"status": "started", "pid": process.pid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bots/{bot_name}/stop")
async def stop_bot(bot_name: str, token: str = None, db: Session = Depends(get_db)):
    """Stop a bot"""
    user = get_current_user(token, db)
    
    if bot_name not in running_processes:
        raise HTTPException(status_code=404, detail="Bot not running")
    
    process = running_processes[bot_name]
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        
        log_file = os.path.join(LOGS_DIR, f"{bot_name}.log")
        with open(log_file, "a") as lf:
            lf.write(f"[{datetime.now()}] Bot stopped.\n")
    
    del running_processes[bot_name]
    return {"status": "stopped"}

@app.post("/api/bots/{bot_name}/restart")
async def restart_bot(bot_name: str, token: str = None, db: Session = Depends(get_db)):
    """Restart a bot"""
    user = get_current_user(token, db)
    
    # Stop if running
    if bot_name in running_processes:
        await stop_bot(bot_name, token, db)
    
    await asyncio.sleep(1)
    
    # Start again
    return await start_bot(bot_name, token, db)

@app.get("/api/bots/{bot_name}/status")
async def get_bot_status(bot_name: str, token: str = None, db: Session = Depends(get_db)):
    """Get bot status"""
    user = get_current_user(token, db)
    
    if bot_name in running_processes:
        process = running_processes[bot_name]
        if process.poll() is None:
            return {"status": "running", "pid": process.pid}
        else:
            del running_processes[bot_name]
    
    return {"status": "stopped", "pid": None}

# File Management Routes
@app.post("/api/bots/{bot_name}/upload")
async def upload_file(
    bot_name: str,
    file: UploadFile = File(...),
    token: str = None,
    db: Session = Depends(get_db)
):
    """Upload file to bot"""
    user = get_current_user(token, db)
    
    bot_path = os.path.join(BOTS_DIR, user.username, bot_name)
    os.makedirs(bot_path, exist_ok=True)
    
    file_path = os.path.join(bot_path, file.filename)
    
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        return {"filename": file.filename, "status": "uploaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bots/{bot_name}/unzip")
async def unzip_file(
    bot_name: str,
    filename: str,
    token: str = None,
    db: Session = Depends(get_db)
):
    """Unzip file in bot directory"""
    user = get_current_user(token, db)
    
    bot_path = os.path.join(BOTS_DIR, user.username, bot_name)
    file_path = os.path.join(bot_path, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(bot_path)
        
        return {"status": "unzipped", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/bots/{bot_name}/files/{file_path:path}")
async def delete_file(
    bot_name: str,
    file_path: str,
    token: str = None,
    db: Session = Depends(get_db)
):
    """Delete file from bot"""
    user = get_current_user(token, db)
    
    bot_path = os.path.join(BOTS_DIR, user.username, bot_name)
    full_path = os.path.join(bot_path, file_path)
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
        
        return {"status": "deleted", "path": file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bots/{bot_name}/files")
async def list_files(
    bot_name: str,
    token: str = None,
    db: Session = Depends(get_db)
):
    """List files in bot directory"""
    user = get_current_user(token, db)
    
    bot_path = os.path.join(BOTS_DIR, user.username, bot_name)
    
    if not os.path.exists(bot_path):
        return {"files": []}
    
    files = []
    for item in os.listdir(bot_path):
        item_path = os.path.join(bot_path, item)
        files.append({
            "name": item,
            "type": "directory" if os.path.isdir(item_path) else "file",
            "size": os.path.getsize(item_path) if os.path.isfile(item_path) else 0
        })
    
    return {"files": files}

@app.get("/api/bots/{bot_name}/files/{file_path:path}")
async def read_file(
    bot_name: str,
    file_path: str,
    token: str = None,
    db: Session = Depends(get_db)
):
    """Read file content"""
    user = get_current_user(token, db)
    
    bot_path = os.path.join(BOTS_DIR, user.username, bot_name)
    full_path = os.path.join(bot_path, file_path)
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        async with aiofiles.open(full_path, 'r') as f:
            content = await f.read()
        
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/bots/{bot_name}/files/{file_path:path}")
async def edit_file(
    bot_name: str,
    file_path: str,
    content: dict,
    token: str = None,
    db: Session = Depends(get_db)
):
    """Edit file content"""
    user = get_current_user(token, db)
    
    bot_path = os.path.join(BOTS_DIR, user.username, bot_name)
    full_path = os.path.join(bot_path, file_path)
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        async with aiofiles.open(full_path, 'w') as f:
            await f.write(content["content"])
        
        return {"status": "saved", "path": file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket for live logs
@app.websocket("/ws/logs/{bot_name}")
async def websocket_endpoint(websocket: WebSocket, bot_name: str, token: str = None):
    """WebSocket for live logs"""
    try:
        await websocket.accept()
        
        if bot_name not in active_connections:
            active_connections[bot_name] = []
        active_connections[bot_name].append(websocket)
        
        log_file = os.path.join(LOGS_DIR, f"{bot_name}.log")
        
        while True:
            if os.path.exists(log_file):
                async with aiofiles.open(log_file, 'r') as f:
                    logs = await f.read()
                    await websocket.send_text(logs)
            
            await asyncio.sleep(1)
    
    except WebSocketDisconnect:
        if bot_name in active_connections:
            active_connections[bot_name].remove(websocket)

# Static files
@app.get("/")
async def root():
    """Serve index.html"""
    return FileResponse("static/index.html")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
