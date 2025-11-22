# 🚀 Complete Guide: Biotech Dashboard - Setup, Usage & Deployment

## Table of Contents
1. [Quick Start (Local Development)](#quick-start)
2. [Complete Feature Guide](#complete-feature-guide)
3. [Deployment Options Analysis](#deployment-options)
4. [Recommended Deployment: Render + Vercel](#recommended-deployment)
5. [Alternative Deployments](#alternative-deployments)
6. [Troubleshooting](#troubleshooting)

---

## 🏁 Quick Start (Local Development)

### Prerequisites
- Python 3.8+ installed
- pip installed
- Modern web browser (Chrome, Firefox, Safari, Edge)
- Git (optional but recommended)

### Step 1: Download Files

Create your project structure:
```bash
mkdir biotech-dashboard
cd biotech-dashboard
mkdir backend frontend
```

**Files to download:**
- `backend-auth.py` → Place in `/backend/` folder
- `requirements-full.txt` → Place in `/backend/` folder
- `index.html` → Place in `/frontend/` folder

### Step 2: Install Backend Dependencies

```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements-full.txt
```

### Step 3: Start the Backend

```bash
# Make sure you're in the backend folder
python backend-auth.py
```

✅ **Backend running at:** http://localhost:8000
📚 **API Documentation:** http://localhost:8000/docs

**Default credentials:**
- Email: `admin@biotech.com`
- Password: `admin123`

### Step 4: Start the Frontend

**Option A - Simple Python Server:**
```bash
# Open new terminal, go to frontend folder
cd frontend
python -m http.server 3000
```

**Option B - Using Node.js (if installed):**
```bash
cd frontend
npx serve -p 3000
```

**Option C - Direct file:**
Simply double-click `index.html` (works but API calls require CORS)

✅ **Frontend running at:** http://localhost:3000

### Step 5: Login & Start Using

1. Open http://localhost:3000 in your browser
2. Login with default credentials
3. Start creating tasks, experiments, and resources!

---

## 📖 Complete Feature Guide

### 🔐 Authentication System

#### Register New User
1. Click **"Register"** on login page
2. Fill in:
   - Email
   - Password (minimum 8 characters recommended)
   - Full Name
   - Role (researcher, manager, admin)
3. Click **"Create Account"**
4. You'll be automatically logged in

#### Login
1. Enter email and password
2. Click **"Login"**
3. JWT token is stored in browser (24h validity)

#### Logout
Click **"Logout"** button in top navigation bar

---

### 📊 Dashboard Overview

The main dashboard displays key metrics:

- **Active Tasks** - Total tasks in progress
- **Task Completion** - Percentage of completed tasks
- **Active Experiments** - Running experiments
- **Completed This Week** - Recently finished experiments

**Usage:**
- Metrics update in real-time when you add/modify data
- Click on any section card to jump to that section

---

### ✅ Task Management

#### Create New Task
1. Click **"+ New Task"** button
2. Fill in the form:
   - **Title**: Task name (e.g., "Analyze PCR results")
   - **Assignee**: Person responsible
   - **Status**: Todo / In Progress / Done
   - **Priority**: Low / Medium / High
   - **Deadline**: Due date (use date picker)
   - **Description**: Optional details
3. Click **"Create Task"**

#### Filter Tasks
- **By Status**: Select from dropdown (All, Todo, In Progress, Done)
- **By Priority**: Select from dropdown (All, Low, Medium, High)
- **Search**: Type in search box to filter by title

#### Update Task
1. Click **"Edit"** button on any task
2. Modify fields in the form
3. Click **"Update Task"**

#### Delete Task
1. Click **"Delete"** button on task card
2. Confirm deletion

**Pro Tips:**
- Use High priority for urgent tasks
- Set realistic deadlines
- Update status regularly to track progress

---

### 🧪 Experiment Management

#### Create New Experiment
1. Click **"+ New Experiment"** button
2. Fill in:
   - **Title**: Experiment name
   - **Protocol Type**: Type of protocol (e.g., "PCR", "Western Blot")
   - **Assignee**: Researcher name
   - **Status**: Planning / In Progress / Done
   - **Start Date**: When experiment begins
   - **End Date**: Expected completion
   - **Description**: Methodology details
   - **Results**: Findings (can be updated later)
3. Click **"Create Experiment"**

#### Filter Experiments
- **By Status**: Filter planning/in progress/completed experiments
- **Search**: Find experiments by title or protocol

#### Update Experiment
1. Click **"Edit"** on experiment card
2. Update fields (especially useful for adding results)
3. Save changes

#### Best Practices:
- Document methodology in description
- Update results as soon as available
- Link related tasks using consistent naming

---

### 📦 Resource Management

#### Add New Resource
1. Click **"+ New Resource"** button
2. Fill in:
   - **Name**: Resource name (e.g., "Acetonitrile HPLC")
   - **Category**: Type (Solvents, Reagents, Equipment, etc.)
   - **Stock**: Current quantity (e.g., "250 mL")
   - **Status**: OK / Low / Critical
   - **Unit**: Measurement unit (L, mL, mg, units)
3. Click **"Create Resource"**

#### Monitor Stock Levels
- **Green (OK)**: Sufficient stock
- **Orange (Low)**: Reorder soon
- **Red (Critical)**: Immediate reorder needed

#### Update Stock
1. Click **"Edit"** on resource
2. Update stock quantity and status
3. Save changes

**Inventory Management Tips:**
- Set "Low" threshold at 20-30% of normal stock
- Set "Critical" when immediate reorder needed
- Regular weekly stock checks recommended

---

### 📈 Charts & Analytics

#### View Charts
1. Navigate to **"Analytics"** or **"Charts"** section (if implemented in frontend)
2. Available visualizations:
   - **Task Distribution by Status** (Pie/Doughnut chart)
   - **Task Priority Breakdown** (Bar chart)
   - **Experiments Timeline** (Line chart - last 6 months)

#### Export Chart Data
- Charts automatically update with real-time data
- Can be exported as images (right-click > Save Image)

---

### 💾 Export Features

#### Export Tasks to CSV
1. Go to Tasks section
2. Click **"Export CSV"** button
3. File downloads as `tasks.csv`
4. Open in Excel/Google Sheets

**CSV includes:**
- ID, Title, Assignee, Status, Priority, Deadline, Description

#### Export Experiments to CSV
1. Go to Experiments section
2. Click **"Export CSV"** button
3. File downloads as `experiments.csv`

**CSV includes:**
- ID, Title, Protocol Type, Assignee, Status, Dates, Results

#### Use Cases:
- Monthly reports
- Backup data
- Import into other systems
- Statistical analysis in R/Python

---

## ☁️ Deployment Options Analysis

### Comparison Matrix

| Platform | Backend | Database | Cost | Complexity | Best For |
|----------|---------|----------|------|------------|----------|
| **Render + Vercel** | ✅ | PostgreSQL | Free tier | Low | **RECOMMENDED** |
| Railway | ✅ | PostgreSQL | 500h free | Low | Small teams |
| Heroku | ✅ | PostgreSQL | $7/mo min | Medium | Legacy projects |
| AWS | ✅ | RDS | ~$50/mo | High | Enterprise |
| DigitalOcean | ✅ | Managed DB | $12/mo | Medium | Full control |
| Fly.io | ✅ | PostgreSQL | Free tier | Low | Modern apps |

### ⭐ Recommended: Render + Vercel (FREE)

**Why this combination?**

✅ **Completely FREE** for production use  
✅ **Automatic deployments** from Git  
✅ **Free PostgreSQL database** (no time limit)  
✅ **Free SSL certificates** (HTTPS)  
✅ **Easy setup** (10 minutes)  
✅ **Auto-scaling** included  
✅ **99.9% uptime** SLA  

**Perfect for:**
- Biotech research teams (2-50 users)
- Academic institutions
- Startup biotech companies
- Long-term projects without budget concerns

---

## 🎯 Recommended Deployment: Render + Vercel

### Part 1: Backend on Render.com (FREE)

#### Step 1: Prepare Your Code

```bash
# Initialize Git repository
cd biotech-dashboard
git init
git add .
git commit -m "Initial commit"

# Create GitHub repository and push
git remote add origin https://github.com/YOUR_USERNAME/biotech-dashboard.git
git branch -M main
git push -u origin main
```

#### Step 2: Create Render Account
1. Go to https://render.com
2. Sign up with GitHub
3. Authorize Render to access repositories

#### Step 3: Deploy Backend
1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub repository
3. Configure:
   - **Name**: `biotech-dashboard-api`
   - **Region**: Choose closest to your location
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements-full.txt`
   - **Start Command**: `uvicorn backend-auth:app --host 0.0.0.0 --port $PORT`
4. Click **"Create Web Service"**

⏳ **Wait 2-3 minutes** for deployment

✅ **Your API is live at:** `https://biotech-dashboard-api.onrender.com`

#### Step 4: Add PostgreSQL Database (FREE)
1. In Render dashboard, click **"New +"** → **"PostgreSQL"**
2. Configure:
   - **Name**: `biotech-db`
   - **Database**: `biotech_dashboard`
   - **User**: Auto-generated
   - **Region**: Same as your web service
   - **Plan**: **Free** (0.1 GB, no expiration)
3. Click **"Create Database"**

✅ **Database created with connection URL**

#### Step 5: Connect Database to Backend
1. Go to your Web Service settings
2. Click **"Environment"** tab
3. Add environment variable:
   - **Key**: `DATABASE_URL`
   - **Value**: Copy from PostgreSQL internal connection string
4. Save changes
5. Service will auto-redeploy

#### Step 6: Update Backend for PostgreSQL

Create new file `backend/database.py`:

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./biotech_dashboard.db")

# Render uses postgres:// but SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```

Update `requirements-full.txt`:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic[email]==2.5.0
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
PyJWT==2.8.0
bcrypt==4.1.1
psycopg2-binary==2.9.9
sqlalchemy==2.0.23
```

Push changes:
```bash
git add .
git commit -m "Add PostgreSQL support"
git push
```

🎉 **Render auto-deploys your changes!**

---

### Part 2: Frontend on Vercel (FREE)

#### Step 1: Install Vercel CLI
```bash
npm install -g vercel
```

#### Step 2: Deploy Frontend
```bash
cd frontend
vercel
```

Follow prompts:
- **Set up and deploy?** Yes
- **Which scope?** Your account
- **Link to existing project?** No
- **Project name?** `biotech-dashboard`
- **Directory?** `./` (current directory)
- **Override settings?** No

⏳ **Deployment takes 30 seconds**

✅ **Frontend live at:** `https://biotech-dashboard-xxx.vercel.app`

#### Step 3: Configure API URL
1. Create `frontend/config.js`:

```javascript
const API_URL = 'https://biotech-dashboard-api.onrender.com/api';
```

2. In `index.html`, update API calls to use `API_URL` from config

3. Redeploy:
```bash
vercel --prod
```

#### Step 4: Configure CORS on Backend

In `backend-auth.py`, update CORS:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://biotech-dashboard-xxx.vercel.app",  # Your Vercel URL
        "http://localhost:3000"  # For local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Commit and push:
```bash
git add .
git commit -m "Configure CORS for production"
git push
```

---

### Part 3: Post-Deployment Setup

#### Step 1: Test Your Deployment
1. Visit your Vercel URL
2. Try logging in with default credentials
3. Create a test task
4. Verify data persists

#### Step 2: Create Production Admin Account
1. Go to `https://YOUR-API.onrender.com/docs`
2. Use **POST /api/auth/register** endpoint
3. Create your admin account
4. Delete default admin (optional, for security)

#### Step 3: Custom Domain (Optional)
**Vercel:**
1. Go to Project Settings → Domains
2. Add your domain (e.g., `dashboard.yourbiotech.com`)
3. Update DNS records as instructed

**Render:**
1. Go to Service Settings → Custom Domain
2. Add API subdomain (e.g., `api.yourbiotech.com`)
3. Update DNS records

---

## 🔧 Alternative Deployments

### Option 2: Railway (Alternative to Render)

**Pros:** Even simpler than Render  
**Cons:** Free tier limited to 500 hours/month

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Deploy
cd biotech-dashboard
railway init
railway up

# Add PostgreSQL
railway add postgresql

# Deploy backend
cd backend
railway up
```

---

### Option 3: DigitalOcean App Platform

**Best for:** Teams with budget wanting full control  
**Cost:** ~$12/month for backend + $15/month for database

1. Create DigitalOcean account
2. Go to Apps → Create App
3. Connect GitHub repository
4. Configure build settings
5. Add Managed PostgreSQL Database

---

### Option 4: Self-Hosted (VPS)

**Best for:** Maximum control and customization  
**Cost:** $5-10/month for VPS (DigitalOcean, Linode, Vultr)

```bash
# On your VPS (Ubuntu 22.04)
sudo apt update
sudo apt install python3-pip nginx postgresql

# Clone your repo
git clone https://github.com/YOUR_USERNAME/biotech-dashboard.git
cd biotech-dashboard/backend

# Install dependencies
pip3 install -r requirements-full.txt

# Setup PostgreSQL
sudo -u postgres createdb biotech_dashboard
sudo -u postgres createuser biotech_user

# Run with systemd
sudo nano /etc/systemd/system/biotech-api.service
```

Systemd service file:
```ini
[Unit]
Description=Biotech Dashboard API
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/biotech-dashboard/backend
Environment="PATH=/usr/local/bin"
ExecStart=/usr/local/bin/uvicorn backend-auth:app --host 0.0.0.0 --port 8000

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable biotech-api
sudo systemctl start biotech-api

# Configure Nginx reverse proxy
sudo nano /etc/nginx/sites-available/biotech-dashboard
```

---

## 🐛 Troubleshooting

### Backend Issues

**Problem:** `ImportError: No module named 'fastapi'`  
**Solution:**
```bash
pip install -r requirements-full.txt --force-reinstall
```

**Problem:** Database connection error  
**Solution:**
```bash
# Check DATABASE_URL environment variable
echo $DATABASE_URL

# Verify database exists
psql $DATABASE_URL -c "\dt"
```

**Problem:** CORS error in browser  
**Solution:**
- Check `allow_origins` in `backend-auth.py`
- Ensure frontend URL is in the list
- Restart backend after changes

---

### Frontend Issues

**Problem:** "Failed to fetch" errors  
**Solution:**
- Verify backend is running
- Check API URL in config
- Open browser console for specific error
- Ensure CORS is configured

**Problem:** Login not working  
**Solution:**
- Verify API URL is correct
- Check backend logs for errors
- Ensure JWT secret is consistent
- Clear browser localStorage

**Problem:** Charts not displaying  
**Solution:**
- Check Chart.js is loaded (check browser console)
- Verify chart data API endpoints work
- Inspect network tab for failed requests

---

### Deployment Issues

**Problem:** Render deployment fails  
**Solution:**
- Check build logs in Render dashboard
- Verify `requirements-full.txt` is correct
- Ensure start command is accurate
- Check Python version compatibility

**Problem:** Database connection timeout  
**Solution:**
- Verify database is in same region as web service
- Check internal connection string (not external)
- Ensure web service has DATABASE_URL env var

**Problem:** Vercel deployment 404 errors  
**Solution:**
- Ensure `index.html` is in root of deployment directory
- Check vercel.json configuration
- Verify build settings

---

## 📊 Performance Optimization

### Backend Optimization
```python
# Add caching for dashboard stats
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=128)
def get_cached_stats(timestamp: int):
    # Cache stats for 5 minutes
    return get_dashboard_stats()

@app.get("/api/dashboard/stats")
async def dashboard_stats_cached():
    cache_key = int(datetime.now().timestamp() // 300)
    return get_cached_stats(cache_key)
```

### Database Optimization
```sql
-- Add indexes for faster queries
CREATE INDEX idx_tasks_deadline ON tasks(deadline);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_experiments_dates ON experiments(start_date, end_date);
```

---

## 🔒 Security Best Practices

### Production Checklist
- [ ] Change default admin credentials
- [ ] Use strong JWT secret (environment variable)
- [ ] Enable HTTPS only (disable HTTP)
- [ ] Restrict CORS to specific domains
- [ ] Implement rate limiting
- [ ] Regular database backups
- [ ] Monitor API logs for suspicious activity
- [ ] Use environment variables for secrets
- [ ] Enable API authentication on all routes
- [ ] Set secure password requirements

---

## 📈 Scaling Considerations

### When to upgrade from Free Tier?

**Render Free → Render Starter ($7/mo):**
- More than 100 requests/day
- Need faster response times
- Want zero cold starts

**Vercel Free → Vercel Pro ($20/mo):**
- More than 100GB bandwidth/month
- Need advanced analytics
- Custom domains for multiple projects

**PostgreSQL Free → Paid ($7/mo):**
- Database size > 0.1 GB
- Need automated backups
- Require high availability

---

## 🎓 Next Steps

### Phase 2 Enhancements
- [ ] Real-time notifications (WebSockets)
- [ ] Advanced analytics dashboard
- [ ] PDF report generation
- [ ] Email notifications for deadlines
- [ ] File upload for experiment data
- [ ] Collaborative annotations
- [ ] Gantt chart for project timeline
- [ ] Mobile app (React Native)

### Learning Resources
- FastAPI: https://fastapi.tiangolo.com
- Chart.js: https://www.chartjs.org
- Render Docs: https://render.com/docs
- Vercel Docs: https://vercel.com/docs

---

## 💬 Support

**Common Commands:**

```bash
# View backend logs (Render)
render logs -s biotech-dashboard-api

# View frontend logs (Vercel)
vercel logs

# Restart backend
render restart -s biotech-dashboard-api

# Redeploy frontend
vercel --prod

# Database backup
pg_dump $DATABASE_URL > backup.sql
```

---

**🎉 Congratulations! Your Biotech Dashboard is now production-ready!**

**Recommended deployment:** Render (backend + PostgreSQL) + Vercel (frontend) = **100% FREE**

For questions or issues, refer to the troubleshooting section or check the official documentation of each platform.
