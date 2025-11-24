# Backend FastAPI avec Authentification JWT - Phase 2
# Support PostgreSQL (Neon) + SQLite fallback
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, date, timedelta
from contextlib import contextmanager
import jwt
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

app = FastAPI(title="Biotech Dashboard API", version="2.0.0")

# Configuration JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 heures

# Configuration du hachage de mot de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sécurité Bearer Token
security = HTTPBearer()

# Configuration base de données - PostgreSQL (Neon) ou SQLite fallback
DATABASE_URL = os.getenv("DATABASE_URL")

# Détecter si on utilise PostgreSQL ou SQLite
USE_POSTGRES = DATABASE_URL is not None and DATABASE_URL.startswith(("postgres://", "postgresql://"))

if USE_POSTGRES:
    # PostgreSQL / Neon
    import psycopg2
    from psycopg2.extras import RealDictCursor

    # Neon/Render utilise postgres:// mais psycopg2 préfère postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    @contextmanager
    def get_db():
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        try:
            yield conn
        finally:
            conn.close()

    def get_placeholder():
        return "%s"

    def sql(query: str) -> str:
        """Convertit les ? en %s pour PostgreSQL"""
        return query.replace("?", "%s")

    def get_last_id(cursor, conn):
        """Récupère le dernier ID inséré pour PostgreSQL"""
        cursor.execute("SELECT lastval()")
        return cursor.fetchone()['lastval']

    print("🐘 Using PostgreSQL (Neon)")
else:
    # SQLite fallback pour développement local
    import sqlite3

    DATABASE = os.getenv("SQLITE_DATABASE", "biotech_dashboard.db")

    @contextmanager
    def get_db():
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def get_placeholder():
        return "?"

    def sql(query: str) -> str:
        """Garde les ? pour SQLite"""
        return query

    def get_last_id(cursor, conn):
        """Récupère le dernier ID inséré pour SQLite"""
        return cursor.lastrowid

    print("📁 Using SQLite (local development)")

# ==================== MODÈLES PYDANTIC ====================

# Modèles d'authentification
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "researcher"  # researcher, admin, manager

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class User(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    created_at: datetime

# Modèles existants (Tasks, Experiments, Resources)
class TaskBase(BaseModel):
    title: str
    assignee: str
    status: str
    priority: str
    start_date: date
    end_date: date
    description: Optional[str] = None

class TaskCreate(TaskBase):
    pass

class Task(TaskBase):
    id: int
    created_at: datetime

class ExperimentBase(BaseModel):
    title: str
    protocol_type: str
    assignee: str
    status: str
    start_date: date
    end_date: date
    description: Optional[str] = None
    results: Optional[str] = None

class ExperimentCreate(ExperimentBase):
    pass

class Experiment(ExperimentBase):
    id: int
    created_at: datetime

class ResourceBase(BaseModel):
    name: str
    category: str
    lot_number: str
    initial_stock: float
    unit: str
    status: str = "available"  # available, low, critical, empty

class ResourceCreate(ResourceBase):
    pass

class Resource(ResourceBase):
    id: int
    current_stock: float
    updated_at: datetime

# Modèle pour l'utilisation des ressources
class ResourceUsageCreate(BaseModel):
    quantity_used: float
    purpose: str

class ResourceUsage(BaseModel):
    id: int
    resource_id: int
    quantity_used: float
    purpose: str
    stock_before: float
    stock_after: float
    used_by: int
    used_at: datetime

class RestockRequest(BaseModel):
    quantity: float
    lot_number: Optional[str] = None

# ==================== FONCTIONS UTILITAIRES ====================

def hash_password(password: str) -> str:
    """Hasher un mot de passe"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifier un mot de passe"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Créer un token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str):
    """Décoder un token JWT"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Obtenir l'utilisateur actuel depuis le token"""
    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("user_id")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql("SELECT * FROM users WHERE id = ?"), (user_id,))
        user = cursor.fetchone()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        return dict(user)

# ==================== INITIALISATION BASE DE DONNÉES ====================

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        p = get_placeholder()  # %s pour PostgreSQL, ? pour SQLite

        if USE_POSTGRES:
            # PostgreSQL / Neon - Utilise SERIAL au lieu de AUTOINCREMENT

            # Table des utilisateurs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    full_name VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Table des tâches
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(500) NOT NULL,
                    assignee VARCHAR(255) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    priority VARCHAR(50) NOT NULL,
                    start_date DATE,
                    end_date DATE,
                    deadline DATE,
                    description TEXT,
                    created_by INTEGER REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Table des expériences
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiments (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(500) NOT NULL,
                    protocol_type VARCHAR(255) NOT NULL,
                    assignee VARCHAR(255) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    start_date DATE,
                    end_date DATE,
                    description TEXT,
                    results TEXT,
                    created_by INTEGER REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Table des ressources
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resources (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    lot_number VARCHAR(100) DEFAULT '',
                    initial_stock REAL DEFAULT 0,
                    current_stock REAL DEFAULT 0,
                    unit VARCHAR(50) NOT NULL,
                    status VARCHAR(50) DEFAULT 'available',
                    created_by INTEGER REFERENCES users(id),
                    updated_by INTEGER REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Table historique utilisation ressources
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resource_usage (
                    id SERIAL PRIMARY KEY,
                    resource_id INTEGER NOT NULL REFERENCES resources(id),
                    quantity_used REAL NOT NULL,
                    purpose TEXT NOT NULL,
                    stock_before REAL NOT NULL,
                    stock_after REAL NOT NULL,
                    used_by INTEGER NOT NULL REFERENCES users(id),
                    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

        else:
            # SQLite - Code original

            # Table des utilisateurs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Table des tâches
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    assignee TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    start_date DATE,
                    end_date DATE,
                    deadline DATE,
                    description TEXT,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(id)
                )
            """)

            # Table des expériences
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    protocol_type TEXT NOT NULL,
                    assignee TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_date DATE,
                    end_date DATE,
                    description TEXT,
                    results TEXT,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(id)
                )
            """)

            # Table des ressources
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    lot_number TEXT DEFAULT '',
                    initial_stock REAL DEFAULT 0,
                    current_stock REAL DEFAULT 0,
                    unit TEXT NOT NULL,
                    status TEXT DEFAULT 'available',
                    created_by INTEGER,
                    updated_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(id),
                    FOREIGN KEY (updated_by) REFERENCES users(id)
                )
            """)

            # Table historique utilisation ressources
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resource_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resource_id INTEGER NOT NULL,
                    quantity_used REAL NOT NULL,
                    purpose TEXT NOT NULL,
                    stock_before REAL NOT NULL,
                    stock_after REAL NOT NULL,
                    used_by INTEGER NOT NULL,
                    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (resource_id) REFERENCES resources(id),
                    FOREIGN KEY (used_by) REFERENCES users(id)
                )
            """)

        conn.commit()

        # Créer un utilisateur admin par défaut
        cursor.execute(f"SELECT COUNT(*) as count FROM users WHERE email = {p}", ("admin@biotech.com",))
        result = cursor.fetchone()
        count = result['count'] if isinstance(result, dict) else result[0]

        if count == 0:
            admin_password = hash_password("admin123")
            cursor.execute(f"""
                INSERT INTO users (email, password_hash, full_name, role)
                VALUES ({p}, {p}, {p}, {p})
            """, ("admin@biotech.com", admin_password, "Admin User", "admin"))
            conn.commit()
            print("✅ Default admin user created: admin@biotech.com / admin123")

# ==================== ROUTES D'AUTHENTIFICATION ====================

@app.post("/api/auth/register", response_model=Token)
async def register(user_data: UserRegister):
    """Enregistrer un nouvel utilisateur"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Vérifier si l'email existe déjà
        cursor.execute(sql("SELECT id FROM users WHERE email = ?"), (user_data.email,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Créer l'utilisateur
        password_hashed = hash_password(user_data.password)
        cursor.execute(sql("""
            INSERT INTO users (email, password_hash, full_name, role)
            VALUES (?, ?, ?, ?)
        """), (user_data.email, password_hashed, user_data.full_name, user_data.role))
        conn.commit()

        user_id = get_last_id(cursor, conn)

        # Créer le token
        access_token = create_access_token(data={"user_id": user_id})

        cursor.execute(sql("SELECT * FROM users WHERE id = ?"), (user_id,))
        user = dict(cursor.fetchone())

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user['id'],
                "email": user['email'],
                "full_name": user['full_name'],
                "role": user['role']
            }
        }

@app.post("/api/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    """Connexion utilisateur"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql("SELECT * FROM users WHERE email = ?"), (credentials.email,))
        user = cursor.fetchone()

        if not user or not verify_password(credentials.password, user['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        # Créer le token
        access_token = create_access_token(data={"user_id": user['id']})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user['id'],
                "email": user['email'],
                "full_name": user['full_name'],
                "role": user['role']
            }
        }

@app.get("/api/auth/me", response_model=User)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Obtenir l'utilisateur actuel"""
    return {
        "id": current_user['id'],
        "email": current_user['email'],
        "full_name": current_user['full_name'],
        "role": current_user['role'],
        "created_at": current_user['created_at']
    }

# ==================== ROUTES TASKS (Protégées) ====================

@app.get("/api/tasks", response_model=List[Task])
async def get_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Récupérer toutes les tâches"""
    with get_db() as conn:
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)
        if priority:
            query += " AND priority = ?"
            params.append(priority)

        query += " ORDER BY end_date ASC"

        cursor = conn.cursor()
        cursor.execute(sql(query), params)
        tasks = cursor.fetchall()

        return [dict(task) for task in tasks]

@app.post("/api/tasks", response_model=Task)
async def create_task(task: TaskCreate, current_user: dict = Depends(get_current_user)):
    """Créer une nouvelle tâche"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql("""
            INSERT INTO tasks (title, assignee, status, priority, start_date, end_date, description, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """), (task.title, task.assignee, task.status, task.priority,
              task.start_date, task.end_date, task.description, current_user['id']))
        conn.commit()

        task_id = get_last_id(cursor, conn)
        cursor.execute(sql("SELECT * FROM tasks WHERE id = ?"), (task_id,))
        return dict(cursor.fetchone())

@app.put("/api/tasks/{task_id}", response_model=Task)
async def update_task(
    task_id: int,
    task: TaskCreate,
    current_user: dict = Depends(get_current_user)
):
    """Mettre à jour une tâche"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql("""
            UPDATE tasks
            SET title=?, assignee=?, status=?, priority=?, start_date=?, end_date=?, description=?
            WHERE id=?
        """), (task.title, task.assignee, task.status, task.priority,
              task.start_date, task.end_date, task.description, task_id))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")

        cursor.execute(sql("SELECT * FROM tasks WHERE id = ?"), (task_id,))
        return dict(cursor.fetchone())

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int, current_user: dict = Depends(get_current_user)):
    """Supprimer une tâche"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql("DELETE FROM tasks WHERE id = ?"), (task_id,))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")

        return {"message": "Task deleted successfully"}

# ==================== ROUTES EXPERIMENTS (Protégées) ====================

@app.get("/api/experiments", response_model=List[Experiment])
async def get_experiments(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Récupérer toutes les expériences"""
    with get_db() as conn:
        query = "SELECT * FROM experiments WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY start_date DESC"

        cursor = conn.cursor()
        cursor.execute(sql(query), params)
        experiments = cursor.fetchall()

        return [dict(exp) for exp in experiments]

@app.post("/api/experiments", response_model=Experiment)
async def create_experiment(experiment: ExperimentCreate, current_user: dict = Depends(get_current_user)):
    """Créer une nouvelle expérience"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql("""
            INSERT INTO experiments (title, protocol_type, assignee, status, start_date, end_date, description, results, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """), (experiment.title, experiment.protocol_type, experiment.assignee, experiment.status,
              experiment.start_date, experiment.end_date, experiment.description, experiment.results, current_user['id']))
        conn.commit()

        exp_id = get_last_id(cursor, conn)
        cursor.execute(sql("SELECT * FROM experiments WHERE id = ?"), (exp_id,))
        return dict(cursor.fetchone())

@app.put("/api/experiments/{experiment_id}", response_model=Experiment)
async def update_experiment(
    experiment_id: int,
    experiment: ExperimentCreate,
    current_user: dict = Depends(get_current_user)
):
    """Mettre à jour une expérience"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql("""
            UPDATE experiments
            SET title=?, protocol_type=?, assignee=?, status=?, start_date=?, end_date=?, description=?, results=?
            WHERE id=?
        """), (experiment.title, experiment.protocol_type, experiment.assignee, experiment.status,
              experiment.start_date, experiment.end_date, experiment.description, experiment.results, experiment_id))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Experiment not found")

        cursor.execute(sql("SELECT * FROM experiments WHERE id = ?"), (experiment_id,))
        return dict(cursor.fetchone())

@app.delete("/api/experiments/{experiment_id}")
async def delete_experiment(experiment_id: int, current_user: dict = Depends(get_current_user)):
    """Supprimer une expérience"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql("DELETE FROM experiments WHERE id = ?"), (experiment_id,))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Experiment not found")

        return {"message": "Experiment deleted successfully"}

# ==================== ROUTES RESOURCES (Gestion de Stock) ====================

def calculate_resource_status(current_stock: float, initial_stock: float) -> str:
    """Calculer le statut d'une ressource basé sur le stock"""
    if current_stock <= 0:
        return "empty"
    ratio = current_stock / initial_stock if initial_stock > 0 else 0
    if ratio <= 0.1:
        return "critical"
    elif ratio <= 0.25:
        return "low"
    return "available"

@app.get("/api/resources", response_model=List[Resource])
async def get_resources(
    category: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Récupérer toutes les ressources"""
    with get_db() as conn:
        query = "SELECT * FROM resources WHERE 1=1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY name ASC"

        cursor = conn.cursor()
        cursor.execute(sql(query), params)
        resources = cursor.fetchall()

        return [dict(r) for r in resources]

@app.get("/api/resources/{resource_id}", response_model=Resource)
async def get_resource(resource_id: int, current_user: dict = Depends(get_current_user)):
    """Récupérer une ressource par ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql("SELECT * FROM resources WHERE id = ?"), (resource_id,))
        resource = cursor.fetchone()

        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")

        return dict(resource)

@app.post("/api/resources", response_model=Resource)
async def create_resource(resource: ResourceCreate, current_user: dict = Depends(get_current_user)):
    """Créer une nouvelle ressource (composé, réactif, etc.)"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Le stock actuel = stock initial au départ
        current_stock = resource.initial_stock
        res_status = calculate_resource_status(current_stock, resource.initial_stock)

        cursor.execute(sql("""
            INSERT INTO resources (name, category, lot_number, initial_stock, current_stock, unit, status, created_by, updated_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """), (resource.name, resource.category, resource.lot_number, resource.initial_stock,
              current_stock, resource.unit, res_status, current_user['id'], current_user['id']))
        conn.commit()

        new_resource_id = get_last_id(cursor, conn)
        cursor.execute(sql("SELECT * FROM resources WHERE id = ?"), (new_resource_id,))
        return dict(cursor.fetchone())

@app.put("/api/resources/{resource_id}", response_model=Resource)
async def update_resource(
    resource_id: int,
    resource: ResourceCreate,
    current_user: dict = Depends(get_current_user)
):
    """Mettre à jour une ressource"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Récupérer la ressource existante
        cursor.execute(sql("SELECT * FROM resources WHERE id = ?"), (resource_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Resource not found")

        # Si le stock initial change, ajuster le stock actuel proportionnellement
        if resource.initial_stock != existing['initial_stock']:
            ratio = existing['current_stock'] / existing['initial_stock'] if existing['initial_stock'] > 0 else 1
            new_current_stock = resource.initial_stock * ratio
        else:
            new_current_stock = existing['current_stock']

        res_status = calculate_resource_status(new_current_stock, resource.initial_stock)

        cursor.execute(sql("""
            UPDATE resources
            SET name=?, category=?, lot_number=?, initial_stock=?, current_stock=?, unit=?, status=?, updated_by=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """), (resource.name, resource.category, resource.lot_number, resource.initial_stock,
              new_current_stock, resource.unit, res_status, current_user['id'], resource_id))
        conn.commit()

        cursor.execute(sql("SELECT * FROM resources WHERE id = ?"), (resource_id,))
        return dict(cursor.fetchone())

@app.delete("/api/resources/{resource_id}")
async def delete_resource(resource_id: int, current_user: dict = Depends(get_current_user)):
    """Supprimer une ressource"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql("DELETE FROM resources WHERE id = ?"), (resource_id,))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Resource not found")

        return {"message": "Resource deleted successfully"}

# ==================== ROUTES UTILISATION RESSOURCES ====================

@app.post("/api/resources/{resource_id}/usage", response_model=ResourceUsage)
async def record_resource_usage(
    resource_id: int,
    usage: ResourceUsageCreate,
    current_user: dict = Depends(get_current_user)
):
    """Enregistrer une utilisation de ressource et mettre à jour le stock"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Récupérer la ressource
        cursor.execute(sql("SELECT * FROM resources WHERE id = ?"), (resource_id,))
        resource = cursor.fetchone()

        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")

        stock_before = resource['current_stock']

        # Vérifier qu'il y a assez de stock
        if usage.quantity_used > stock_before:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuffisant. Disponible: {stock_before} {resource['unit']}, Demandé: {usage.quantity_used} {resource['unit']}"
            )

        stock_after = stock_before - usage.quantity_used
        new_status = calculate_resource_status(stock_after, resource['initial_stock'])

        # Enregistrer l'utilisation
        cursor.execute(sql("""
            INSERT INTO resource_usage (resource_id, quantity_used, purpose, stock_before, stock_after, used_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """), (resource_id, usage.quantity_used, usage.purpose, stock_before, stock_after, current_user['id']))

        # Mettre à jour le stock de la ressource
        cursor.execute(sql("""
            UPDATE resources
            SET current_stock = ?, status = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """), (stock_after, new_status, current_user['id'], resource_id))

        conn.commit()

        usage_id = get_last_id(cursor, conn)
        cursor.execute(sql("SELECT * FROM resource_usage WHERE id = ?"), (usage_id,))
        return dict(cursor.fetchone())

@app.get("/api/resources/{resource_id}/usage", response_model=List[ResourceUsage])
async def get_resource_usage_history(
    resource_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Récupérer l'historique des utilisations d'une ressource"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Vérifier que la ressource existe
        cursor.execute(sql("SELECT id FROM resources WHERE id = ?"), (resource_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Resource not found")

        cursor.execute(sql("""
            SELECT ru.*, u.full_name as user_name
            FROM resource_usage ru
            LEFT JOIN users u ON ru.used_by = u.id
            WHERE ru.resource_id = ?
            ORDER BY ru.used_at DESC
        """), (resource_id,))

        return [dict(row) for row in cursor.fetchall()]

@app.post("/api/resources/{resource_id}/restock", response_model=Resource)
async def restock_resource(
    resource_id: int,
    restock: RestockRequest,
    current_user: dict = Depends(get_current_user)
):
    """Réapprovisionner une ressource"""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute(sql("SELECT * FROM resources WHERE id = ?"), (resource_id,))
        resource = cursor.fetchone()

        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")

        new_stock = resource['current_stock'] + restock.quantity
        new_initial = resource['initial_stock'] + restock.quantity
        new_lot = restock.lot_number if restock.lot_number else resource['lot_number']
        new_status = calculate_resource_status(new_stock, new_initial)

        cursor.execute(sql("""
            UPDATE resources
            SET current_stock = ?, initial_stock = ?, lot_number = ?, status = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """), (new_stock, new_initial, new_lot, new_status, current_user['id'], resource_id))
        conn.commit()

        cursor.execute(sql("SELECT * FROM resources WHERE id = ?"), (resource_id,))
        return dict(cursor.fetchone())

# ==================== ROUTES POUR GRAPHIQUES ====================

@app.get("/api/charts/task-distribution")
async def get_task_distribution(current_user: dict = Depends(get_current_user)):
    """Distribution des tâches par statut"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM tasks
            GROUP BY status
        """)
        results = cursor.fetchall()
        
        return {
            "labels": [row['status'] for row in results],
            "data": [row['count'] for row in results]
        }

@app.get("/api/charts/task-priority")
async def get_task_priority(current_user: dict = Depends(get_current_user)):
    """Distribution des tâches par priorité"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT priority, COUNT(*) as count
            FROM tasks
            GROUP BY priority
        """)
        results = cursor.fetchall()
        
        return {
            "labels": [row['priority'] for row in results],
            "data": [row['count'] for row in results]
        }

@app.get("/api/charts/experiments-timeline")
async def get_experiments_timeline(current_user: dict = Depends(get_current_user)):
    """Timeline des expériences par mois"""
    with get_db() as conn:
        cursor = conn.cursor()

        if USE_POSTGRES:
            # PostgreSQL syntax
            cursor.execute("""
                SELECT TO_CHAR(start_date, 'YYYY-MM') as month, COUNT(*) as count
                FROM experiments
                WHERE start_date >= CURRENT_DATE - INTERVAL '6 months'
                GROUP BY TO_CHAR(start_date, 'YYYY-MM')
                ORDER BY month
            """)
        else:
            # SQLite syntax
            cursor.execute("""
                SELECT strftime('%Y-%m', start_date) as month, COUNT(*) as count
                FROM experiments
                WHERE start_date >= date('now', '-6 months')
                GROUP BY month
                ORDER BY month
            """)

        results = cursor.fetchall()

        return {
            "labels": [row['month'] for row in results],
            "data": [row['count'] for row in results]
        }

@app.get("/api/charts/tasks-gantt")
async def get_tasks_gantt(current_user: dict = Depends(get_current_user)):
    """Données pour diagramme de Gantt des tâches"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, assignee, status, priority, start_date, end_date, description
            FROM tasks
            ORDER BY start_date ASC
        """)
        tasks = cursor.fetchall()

        gantt_data = []
        for task in tasks:
            # Calculer le pourcentage de progression basé sur le statut
            status = task['status']
            if status == 'done':
                progress = 100
            elif status == 'progress':
                progress = 50
            elif status == 'review':
                progress = 75
            else:  # todo, pending
                progress = 0

            # Couleur basée sur la priorité
            priority = task['priority']
            if priority == 'high':
                color = '#ef4444'  # rouge
            elif priority == 'medium':
                color = '#f59e0b'  # orange
            else:  # low
                color = '#22c55e'  # vert

            gantt_data.append({
                "id": task['id'],
                "title": task['title'],
                "assignee": task['assignee'],
                "status": status,
                "priority": priority,
                "start_date": task['start_date'],
                "end_date": task['end_date'],
                "progress": progress,
                "color": color,
                "description": task['description'] or ""
            })

        return {
            "tasks": gantt_data,
            "total": len(gantt_data)
        }

# ==================== ROUTES POUR EXPORT ====================

@app.get("/api/export/tasks/csv")
async def export_tasks_csv(current_user: dict = Depends(get_current_user)):
    """Exporter les tâches en CSV"""
    from fastapi.responses import StreamingResponse
    import io
    import csv
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks ORDER BY end_date")
        tasks = cursor.fetchall()

        # Créer le CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Headers
        writer.writerow(['ID', 'Title', 'Assignee', 'Status', 'Priority', 'Start Date', 'End Date', 'Description'])

        # Data
        for task in tasks:
            writer.writerow([
                task['id'], task['title'], task['assignee'],
                task['status'], task['priority'], task['start_date'], task['end_date'],
                task['description'] or ''
            ])
        
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=tasks.csv"}
        )

@app.get("/api/export/experiments/csv")
async def export_experiments_csv(current_user: dict = Depends(get_current_user)):
    """Exporter les expériences en CSV"""
    from fastapi.responses import StreamingResponse
    import io
    import csv
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM experiments ORDER BY start_date DESC")
        experiments = cursor.fetchall()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['ID', 'Title', 'Protocol Type', 'Assignee', 'Status', 
                        'Start Date', 'End Date', 'Results'])
        
        for exp in experiments:
            writer.writerow([
                exp['id'], exp['title'], exp['protocol_type'], 
                exp['assignee'], exp['status'], exp['start_date'],
                exp['end_date'], exp['results'] or ''
            ])
        
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=experiments.csv"}
        )

# ==================== STATISTIQUES DASHBOARD ====================

@app.get("/api/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    """Statistiques pour le dashboard"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Stats des tâches
        cursor.execute("SELECT COUNT(*) as total FROM tasks")
        total_tasks = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as done FROM tasks WHERE status = 'done'")
        done_tasks = cursor.fetchone()['done']

        # Stats des expériences
        cursor.execute("SELECT COUNT(*) as active FROM experiments WHERE status = 'progress'")
        active_experiments = cursor.fetchone()['active']

        if USE_POSTGRES:
            cursor.execute("""
                SELECT COUNT(*) as completed
                FROM experiments
                WHERE status = 'done' AND start_date >= CURRENT_DATE - INTERVAL '7 days'
            """)
        else:
            cursor.execute("""
                SELECT COUNT(*) as completed
                FROM experiments
                WHERE status = 'done' AND start_date >= date('now', '-7 days')
            """)
        completed_experiments_7d = cursor.fetchone()['completed']

        # Échéances (utiliser end_date au lieu de deadline)
        if USE_POSTGRES:
            cursor.execute("""
                SELECT COUNT(*) as today
                FROM tasks
                WHERE end_date = CURRENT_DATE AND status != 'done'
            """)
        else:
            cursor.execute("""
                SELECT COUNT(*) as today
                FROM tasks
                WHERE end_date = date('now') AND status != 'done'
            """)
        due_today = cursor.fetchone()['today']

        if USE_POSTGRES:
            cursor.execute("""
                SELECT COUNT(*) as week
                FROM tasks
                WHERE end_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
                AND status != 'done'
            """)
        else:
            cursor.execute("""
                SELECT COUNT(*) as week
                FROM tasks
                WHERE end_date BETWEEN date('now') AND date('now', '+7 days')
                AND status != 'done'
            """)
        due_this_week = cursor.fetchone()['week']

        if USE_POSTGRES:
            cursor.execute("""
                SELECT COUNT(*) as overdue
                FROM tasks
                WHERE end_date < CURRENT_DATE AND status != 'done'
            """)
        else:
            cursor.execute("""
                SELECT COUNT(*) as overdue
                FROM tasks
                WHERE end_date < date('now') AND status != 'done'
            """)
        overdue = cursor.fetchone()['overdue']

        # Ressources critiques
        cursor.execute("SELECT COUNT(*) as critical FROM resources WHERE status = 'critical'")
        critical_resources = cursor.fetchone()['critical']

        return {
            "tasks": {
                "total": total_tasks,
                "done": done_tasks,
                "progress": int((done_tasks / total_tasks * 100) if total_tasks > 0 else 0)
            },
            "experiments": {
                "active": active_experiments,
                "completed_7d": completed_experiments_7d
            },
            "deadlines": {
                "today": due_today,
                "week": due_this_week,
                "overdue": overdue
            },
            "resources": {
                "critical": critical_resources
            }
        }

# ==================== ROUTE RACINE ====================

@app.get("/")
async def root():
    return {
        "message": "Biotech Dashboard API with Authentication",
        "version": "2.0.0",
        "status": "running",
        "features": ["JWT Auth", "Charts API", "CSV Export"]
    }

# ==================== DÉMARRAGE ====================

@app.on_event("startup")
async def startup_event():
    init_db()
    print("✅ Database initialized")
    print("🔐 Authentication enabled")
    print("🚀 API started on http://localhost:8000")
    print("📚 Documentation: http://localhost:8000/docs")
    print("\n🔑 Default credentials:")
    print("   Email: admin@biotech.com")
    print("   Password: admin123")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
