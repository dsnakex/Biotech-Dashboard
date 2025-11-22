# Backend FastAPI avec Authentification JWT - Phase 2
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, date, timedelta
import sqlite3
from contextlib import contextmanager
import jwt
from passlib.context import CryptContext
import secrets

app = FastAPI(title="Biotech Dashboard API", version="2.0.0")

# Configuration JWT
SECRET_KEY = secrets.token_urlsafe(32)  # En production, utiliser une variable d'environnement
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 heures

# Configuration du hachage de mot de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "https://biotech-dashboard-my492taps-pascal-daos-projects.vercel.app",
    "http://localhost:3000"
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sécurité Bearer Token
security = HTTPBearer()

# Configuration base de données
DATABASE = "biotech_dashboard.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

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
    deadline: date
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
    stock: str
    status: str
    unit: Optional[str] = None

class ResourceCreate(ResourceBase):
    pass

class Resource(ResourceBase):
    id: int
    updated_at: datetime

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
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
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
                deadline DATE NOT NULL,
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
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
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
                stock TEXT NOT NULL,
                status TEXT NOT NULL,
                unit TEXT,
                updated_by INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (updated_by) REFERENCES users(id)
            )
        """)
        
        conn.commit()
        
        # Créer un utilisateur admin par défaut
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE email = ?", ("admin@biotech.com",))
        if cursor.fetchone()['count'] == 0:
            admin_password = hash_password("admin123")
            cursor.execute("""
                INSERT INTO users (email, password_hash, full_name, role)
                VALUES (?, ?, ?, ?)
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
        cursor.execute("SELECT id FROM users WHERE email = ?", (user_data.email,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Créer l'utilisateur
        password_hash = hash_password(user_data.password)
        cursor.execute("""
            INSERT INTO users (email, password_hash, full_name, role)
            VALUES (?, ?, ?, ?)
        """, (user_data.email, password_hash, user_data.full_name, user_data.role))
        conn.commit()
        
        user_id = cursor.lastrowid
        
        # Créer le token
        access_token = create_access_token(data={"user_id": user_id})
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
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
        cursor.execute("SELECT * FROM users WHERE email = ?", (credentials.email,))
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
        
        query += " ORDER BY deadline ASC"
        
        cursor = conn.cursor()
        cursor.execute(query, params)
        tasks = cursor.fetchall()
        
        return [dict(task) for task in tasks]

@app.post("/api/tasks", response_model=Task)
async def create_task(task: TaskCreate, current_user: dict = Depends(get_current_user)):
    """Créer une nouvelle tâche"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (title, assignee, status, priority, deadline, description, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (task.title, task.assignee, task.status, task.priority, 
              task.deadline, task.description, current_user['id']))
        conn.commit()
        
        task_id = cursor.lastrowid
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
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
        cursor.execute("""
            UPDATE tasks 
            SET title=?, assignee=?, status=?, priority=?, deadline=?, description=?
            WHERE id=?
        """, (task.title, task.assignee, task.status, task.priority, 
              task.deadline, task.description, task_id))
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")
        
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        return dict(cursor.fetchone())

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int, current_user: dict = Depends(get_current_user)):
    """Supprimer une tâche"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {"message": "Task deleted successfully"}

# [Les routes experiments et resources suivent le même pattern...]
# Je les ai omises pour la brièveté, mais elles sont identiques avec Depends(get_current_user)

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

# ==================== ROUTES POUR EXPORT ====================

@app.get("/api/export/tasks/csv")
async def export_tasks_csv(current_user: dict = Depends(get_current_user)):
    """Exporter les tâches en CSV"""
    from fastapi.responses import StreamingResponse
    import io
    import csv
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks ORDER BY deadline")
        tasks = cursor.fetchall()
        
        # Créer le CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow(['ID', 'Title', 'Assignee', 'Status', 'Priority', 'Deadline', 'Description'])
        
        # Data
        for task in tasks:
            writer.writerow([
                task['id'], task['title'], task['assignee'], 
                task['status'], task['priority'], task['deadline'],
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
        
        cursor.execute("""
            SELECT COUNT(*) as completed 
            FROM experiments 
            WHERE status = 'done' AND start_date >= date('now', '-7 days')
        """)
        completed_experiments_7d = cursor.fetchone()['completed']
        
        # Échéances
        cursor.execute("""
            SELECT COUNT(*) as today 
            FROM tasks 
            WHERE deadline = date('now') AND status != 'done'
        """)
        due_today = cursor.fetchone()['today']
        
        cursor.execute("""
            SELECT COUNT(*) as week 
            FROM tasks 
            WHERE deadline BETWEEN date('now') AND date('now', '+7 days') 
            AND status != 'done'
        """)
        due_this_week = cursor.fetchone()['week']
        
        cursor.execute("""
            SELECT COUNT(*) as overdue 
            FROM tasks 
            WHERE deadline < date('now') AND status != 'done'
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
