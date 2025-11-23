# Backend FastAPI avec Authentification JWT - PostgreSQL Version
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, date, timedelta
import os
from contextlib import contextmanager
import jwt
from passlib.context import CryptContext
import secrets

# PostgreSQL
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI(title="Biotech Dashboard API", version="2.0.0")

# Configuration JWT
SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_urlsafe(32))
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

# Configuration base de données PostgreSQL
DATABASE_URL = os.environ.get("DATABASE_URL")

@contextmanager
def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()

# ==================== MODÈLES PYDANTIC ====================

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "researcher"

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
    status: str = "available"

class ResourceCreate(ResourceBase):
    pass

class Resource(ResourceBase):
    id: int
    current_stock: float
    updated_at: datetime

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
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("user_id")

    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()

        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        return dict(user)

# ==================== INITIALISATION BASE DE DONNÉES ====================

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()

        # Table des utilisateurs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                assignee TEXT NOT NULL,
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                description TEXT,
                created_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Table des expériences
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                protocol_type TEXT NOT NULL,
                assignee TEXT NOT NULL,
                status TEXT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
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
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                lot_number TEXT NOT NULL,
                initial_stock REAL NOT NULL,
                current_stock REAL NOT NULL,
                unit TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'available',
                created_by INTEGER REFERENCES users(id),
                updated_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Table pour l'historique des utilisations
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

        conn.commit()

        # Créer un utilisateur admin par défaut
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE email = %s", ("admin@biotech.com",))
        if cursor.fetchone()['count'] == 0:
            admin_password = hash_password("admin123")
            cursor.execute("""
                INSERT INTO users (email, password_hash, full_name, role)
                VALUES (%s, %s, %s, %s)
            """, ("admin@biotech.com", admin_password, "Admin User", "admin"))
            conn.commit()
            print("Default admin user created: admin@biotech.com / admin123")

# ==================== ROUTES D'AUTHENTIFICATION ====================

@app.post("/api/auth/register", response_model=Token)
async def register(user_data: UserRegister):
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE email = %s", (user_data.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

        password_hash = hash_password(user_data.password)
        cursor.execute("""
            INSERT INTO users (email, password_hash, full_name, role)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (user_data.email, password_hash, user_data.full_name, user_data.role))
        user_id = cursor.fetchone()['id']
        conn.commit()

        access_token = create_access_token(data={"user_id": user_id})

        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = dict(cursor.fetchone())

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {"id": user['id'], "email": user['email'], "full_name": user['full_name'], "role": user['role']}
        }

@app.post("/api/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (credentials.email,))
        user = cursor.fetchone()

        if not user or not verify_password(credentials.password, user['password_hash']):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

        access_token = create_access_token(data={"user_id": user['id']})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {"id": user['id'], "email": user['email'], "full_name": user['full_name'], "role": user['role']}
        }

@app.get("/api/auth/me", response_model=User)
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user['id'],
        "email": current_user['email'],
        "full_name": current_user['full_name'],
        "role": current_user['role'],
        "created_at": current_user['created_at']
    }

# ==================== ROUTES TASKS ====================

@app.get("/api/tasks", response_model=List[Task])
async def get_tasks(status: Optional[str] = None, priority: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []

        if status:
            query += " AND status = %s"
            params.append(status)
        if priority:
            query += " AND priority = %s"
            params.append(priority)

        query += " ORDER BY end_date ASC"

        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(task) for task in cursor.fetchall()]

@app.post("/api/tasks", response_model=Task)
async def create_task(task: TaskCreate, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (title, assignee, status, priority, start_date, end_date, description, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (task.title, task.assignee, task.status, task.priority, task.start_date, task.end_date, task.description, current_user['id']))
        task_id = cursor.fetchone()['id']
        conn.commit()

        cursor.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
        return dict(cursor.fetchone())

@app.put("/api/tasks/{task_id}", response_model=Task)
async def update_task(task_id: int, task: TaskCreate, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tasks SET title=%s, assignee=%s, status=%s, priority=%s, start_date=%s, end_date=%s, description=%s
            WHERE id=%s
        """, (task.title, task.assignee, task.status, task.priority, task.start_date, task.end_date, task.description, task_id))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")

        cursor.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
        return dict(cursor.fetchone())

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")

        return {"message": "Task deleted successfully"}

# ==================== ROUTES RESOURCES ====================

def calculate_resource_status(current_stock: float, initial_stock: float) -> str:
    if current_stock <= 0:
        return "empty"
    ratio = current_stock / initial_stock if initial_stock > 0 else 0
    if ratio <= 0.1:
        return "critical"
    elif ratio <= 0.25:
        return "low"
    return "available"

@app.get("/api/resources", response_model=List[Resource])
async def get_resources(category: Optional[str] = None, status: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        query = "SELECT * FROM resources WHERE 1=1"
        params = []
        if category:
            query += " AND category = %s"
            params.append(category)
        if status:
            query += " AND status = %s"
            params.append(status)
        query += " ORDER BY name ASC"

        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]

@app.get("/api/resources/{resource_id}", response_model=Resource)
async def get_resource(resource_id: int, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM resources WHERE id = %s", (resource_id,))
        resource = cursor.fetchone()
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")
        return dict(resource)

@app.post("/api/resources", response_model=Resource)
async def create_resource(resource: ResourceCreate, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        current_stock = resource.initial_stock
        res_status = calculate_resource_status(current_stock, resource.initial_stock)

        cursor.execute("""
            INSERT INTO resources (name, category, lot_number, initial_stock, current_stock, unit, status, created_by, updated_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (resource.name, resource.category, resource.lot_number, resource.initial_stock, current_stock, resource.unit, res_status, current_user['id'], current_user['id']))
        resource_id = cursor.fetchone()['id']
        conn.commit()

        cursor.execute("SELECT * FROM resources WHERE id = %s", (resource_id,))
        return dict(cursor.fetchone())

@app.put("/api/resources/{resource_id}", response_model=Resource)
async def update_resource(resource_id: int, resource: ResourceCreate, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM resources WHERE id = %s", (resource_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Resource not found")

        if resource.initial_stock != existing['initial_stock']:
            ratio = existing['current_stock'] / existing['initial_stock'] if existing['initial_stock'] > 0 else 1
            new_current_stock = resource.initial_stock * ratio
        else:
            new_current_stock = existing['current_stock']

        res_status = calculate_resource_status(new_current_stock, resource.initial_stock)

        cursor.execute("""
            UPDATE resources SET name=%s, category=%s, lot_number=%s, initial_stock=%s, current_stock=%s, unit=%s, status=%s, updated_by=%s, updated_at=CURRENT_TIMESTAMP
            WHERE id=%s
        """, (resource.name, resource.category, resource.lot_number, resource.initial_stock, new_current_stock, resource.unit, res_status, current_user['id'], resource_id))
        conn.commit()

        cursor.execute("SELECT * FROM resources WHERE id = %s", (resource_id,))
        return dict(cursor.fetchone())

@app.delete("/api/resources/{resource_id}")
async def delete_resource(resource_id: int, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM resources WHERE id = %s", (resource_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Resource not found")
        return {"message": "Resource deleted successfully"}

# ==================== ROUTES UTILISATION RESSOURCES ====================

@app.post("/api/resources/{resource_id}/usage", response_model=ResourceUsage)
async def record_resource_usage(resource_id: int, usage: ResourceUsageCreate, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM resources WHERE id = %s", (resource_id,))
        resource = cursor.fetchone()

        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")

        stock_before = resource['current_stock']
        if usage.quantity_used > stock_before:
            raise HTTPException(status_code=400, detail=f"Stock insuffisant. Disponible: {stock_before} {resource['unit']}")

        stock_after = stock_before - usage.quantity_used
        new_status = calculate_resource_status(stock_after, resource['initial_stock'])

        cursor.execute("""
            INSERT INTO resource_usage (resource_id, quantity_used, purpose, stock_before, stock_after, used_by)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (resource_id, usage.quantity_used, usage.purpose, stock_before, stock_after, current_user['id']))
        usage_id = cursor.fetchone()['id']

        cursor.execute("""
            UPDATE resources SET current_stock = %s, status = %s, updated_by = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s
        """, (stock_after, new_status, current_user['id'], resource_id))
        conn.commit()

        cursor.execute("SELECT * FROM resource_usage WHERE id = %s", (usage_id,))
        return dict(cursor.fetchone())

@app.get("/api/resources/{resource_id}/usage", response_model=List[ResourceUsage])
async def get_resource_usage_history(resource_id: int, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM resources WHERE id = %s", (resource_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Resource not found")

        cursor.execute("""
            SELECT ru.*, u.full_name as user_name FROM resource_usage ru
            LEFT JOIN users u ON ru.used_by = u.id WHERE ru.resource_id = %s ORDER BY ru.used_at DESC
        """, (resource_id,))
        return [dict(row) for row in cursor.fetchall()]

@app.post("/api/resources/{resource_id}/restock", response_model=Resource)
async def restock_resource(resource_id: int, restock: RestockRequest, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM resources WHERE id = %s", (resource_id,))
        resource = cursor.fetchone()

        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")

        new_stock = resource['current_stock'] + restock.quantity
        new_initial = resource['initial_stock'] + restock.quantity
        new_lot = restock.lot_number if restock.lot_number else resource['lot_number']
        new_status = calculate_resource_status(new_stock, new_initial)

        cursor.execute("""
            UPDATE resources SET current_stock = %s, initial_stock = %s, lot_number = %s, status = %s, updated_by = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s
        """, (new_stock, new_initial, new_lot, new_status, current_user['id'], resource_id))
        conn.commit()

        cursor.execute("SELECT * FROM resources WHERE id = %s", (resource_id,))
        return dict(cursor.fetchone())

# ==================== ROUTES GRAPHIQUES ====================

@app.get("/api/charts/task-distribution")
async def get_task_distribution(current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, COUNT(*) as count FROM tasks GROUP BY status")
        results = cursor.fetchall()
        return {"labels": [row['status'] for row in results], "data": [row['count'] for row in results]}

@app.get("/api/charts/task-priority")
async def get_task_priority(current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT priority, COUNT(*) as count FROM tasks GROUP BY priority")
        results = cursor.fetchall()
        return {"labels": [row['priority'] for row in results], "data": [row['count'] for row in results]}

@app.get("/api/charts/experiments-timeline")
async def get_experiments_timeline(current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT to_char(start_date, 'YYYY-MM') as month, COUNT(*) as count
            FROM experiments WHERE start_date >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY month ORDER BY month
        """)
        results = cursor.fetchall()
        return {"labels": [row['month'] for row in results], "data": [row['count'] for row in results]}

@app.get("/api/charts/tasks-gantt")
async def get_tasks_gantt(current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, assignee, status, priority, start_date, end_date, description FROM tasks ORDER BY start_date ASC")
        tasks = cursor.fetchall()

        gantt_data = []
        for task in tasks:
            task_status = task['status']
            progress = 100 if task_status == 'done' else 75 if task_status == 'review' else 50 if task_status == 'progress' else 0
            priority = task['priority']
            color = '#ef4444' if priority == 'high' else '#f59e0b' if priority == 'medium' else '#22c55e'

            gantt_data.append({
                "id": task['id'], "title": task['title'], "assignee": task['assignee'],
                "status": task_status, "priority": priority,
                "start_date": str(task['start_date']), "end_date": str(task['end_date']),
                "progress": progress, "color": color, "description": task['description'] or ""
            })

        return {"tasks": gantt_data, "total": len(gantt_data)}

# ==================== EXPORT CSV ====================

@app.get("/api/export/tasks/csv")
async def export_tasks_csv(current_user: dict = Depends(get_current_user)):
    from fastapi.responses import StreamingResponse
    import io, csv

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks ORDER BY end_date")
        tasks = cursor.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Title', 'Assignee', 'Status', 'Priority', 'Start Date', 'End Date', 'Description'])
        for task in tasks:
            writer.writerow([task['id'], task['title'], task['assignee'], task['status'], task['priority'], task['start_date'], task['end_date'], task['description'] or ''])
        output.seek(0)

        return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=tasks.csv"})

@app.get("/api/export/experiments/csv")
async def export_experiments_csv(current_user: dict = Depends(get_current_user)):
    from fastapi.responses import StreamingResponse
    import io, csv

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM experiments ORDER BY start_date DESC")
        experiments = cursor.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Title', 'Protocol Type', 'Assignee', 'Status', 'Start Date', 'End Date', 'Results'])
        for exp in experiments:
            writer.writerow([exp['id'], exp['title'], exp['protocol_type'], exp['assignee'], exp['status'], exp['start_date'], exp['end_date'], exp['results'] or ''])
        output.seek(0)

        return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=experiments.csv"})

# ==================== DASHBOARD STATS ====================

@app.get("/api/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM tasks")
        total_tasks = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as done FROM tasks WHERE status = 'done'")
        done_tasks = cursor.fetchone()['done']

        cursor.execute("SELECT COUNT(*) as active FROM experiments WHERE status = 'progress'")
        active_experiments = cursor.fetchone()['active']

        cursor.execute("SELECT COUNT(*) as completed FROM experiments WHERE status = 'done' AND start_date >= CURRENT_DATE - INTERVAL '7 days'")
        completed_experiments_7d = cursor.fetchone()['completed']

        cursor.execute("SELECT COUNT(*) as today FROM tasks WHERE end_date = CURRENT_DATE AND status != 'done'")
        due_today = cursor.fetchone()['today']

        cursor.execute("SELECT COUNT(*) as week FROM tasks WHERE end_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days' AND status != 'done'")
        due_this_week = cursor.fetchone()['week']

        cursor.execute("SELECT COUNT(*) as overdue FROM tasks WHERE end_date < CURRENT_DATE AND status != 'done'")
        overdue = cursor.fetchone()['overdue']

        cursor.execute("SELECT COUNT(*) as critical FROM resources WHERE status = 'critical'")
        critical_resources = cursor.fetchone()['critical']

        return {
            "tasks": {"total": total_tasks, "done": done_tasks, "progress": int((done_tasks / total_tasks * 100) if total_tasks > 0 else 0)},
            "experiments": {"active": active_experiments, "completed_7d": completed_experiments_7d},
            "deadlines": {"today": due_today, "week": due_this_week, "overdue": overdue},
            "resources": {"critical": critical_resources}
        }

# ==================== ROUTE RACINE ====================

@app.get("/")
async def root():
    return {"message": "Biotech Dashboard API with PostgreSQL", "version": "2.1.0", "status": "running"}

# ==================== DÉMARRAGE ====================

@app.on_event("startup")
async def startup_event():
    init_db()
    print("PostgreSQL Database initialized")
    print("Default credentials: admin@biotech.com / admin123")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
