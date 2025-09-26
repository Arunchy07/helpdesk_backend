# 🛠️ Helpdesk & Ticket Management System (Django + DRF + Celery)

A **Django + Django REST Framework (DRF)** based backend API for a simple Helpdesk & Ticket Management System.  
This project demonstrates **authentication, ticket management, escalation alerts with Celery, and API documentation**.  

---

## 🚀 Features

### 🔐 Authentication & User Management
- User registration, login, logout, profile update, delete account.
- Roles:
  - **User** → Raise tickets, view own tickets.  
  - **Agent** → Assigned tickets, update status, resolve.  
  - **Admin** → Full access (manage users, tickets, escalations).  

### 🎫 Ticket Management
- Users:
  - Create a ticket → title, description, priority (`low/medium/high`), status (`open/in-progress/resolved/closed`).
  - View own tickets.  
- Agents:
  - View assigned tickets.
  - Update status, add comments/updates.  
- Admins:
  - View all tickets.
  - Assign/reassign tickets to agents.
  - Delete tickets.  

### ⏰ Escalation & Alerts (Celery)
- Escalates tickets if not updated/resolved in defined timeframe:
  - High → **1 hr**, Medium → **4 hrs**, Low → **24 hrs**.
- Escalation flow:
  - Status auto-updated to **escalated**.
  - Email alert sent to **Admin + Ticket Creator** (using console/email backend for demo).
- Powered by **Celery + Redis** for async processing.

### 🔎 Search & Filtering
- Search tickets by → `title`, `status`, `priority`, `assigned_to`.
- Search users with computed field:  
  `nameEmail = "FirstName LastName - Email"`

### 🔐 Permissions & Security
- **Users** → Only own tickets.  
- **Agents** → Only assigned tickets.  
- **Admins** → Full access.  
- Enforced using **DRF permissions**.

### 📑 Documentation
- Auto-generated API docs with **Swagger / OpenAPI** via `drf-spectacular` (or drf-yasg).
- Clear request/response examples for each endpoint.

---

## 📦 Bonus Features
- Ticket comments (thread of updates per ticket).  
- Reporting endpoint → Number of tickets opened, resolved, escalated in last 7 days.  

---

## 🛠️ Tech Stack
- **Django** (Backend framework)  
- **Django REST Framework (DRF)** (API development)  
- **Celery + Redis** (Async task queue, escalations & alerts)  
- **SQLite / PostgreSQL** (Database)  
- **Swagger / drf-spectacular** (API Documentation)  

---

## ⚙️ Setup Instructions

### 1️⃣ Clone Repository
```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
```

### 2️⃣ Create Virtual Environment & Install Dependencies
```bash
python -m venv venv
source venv/bin/activate   # On Linux/Mac
venv\Scripts\activate      # On Windows

pip install -r requirements.txt
```

### 3️⃣ Run Migrations
```bash
python manage.py migrate
```

### 4️⃣ Create Superuser
```bash
python manage.py createsuperuser
```

### 5️⃣ Start Server
```bash
python manage.py runserver
```

### 6️⃣ Start Celery Worker
In a separate terminal:
```bash
celery -A <project_name> worker -l info
```

### 7️⃣ Start Celery Beat (for periodic tasks)
```bash
celery -A <project_name> beat -l info
```

---

## 📖 API Documentation
After running server, visit:  
👉 [http://127.0.0.1:8000/api/schema/swagger/](http://127.0.0.1:8000/api/schema/swagger/) (Swagger UI)  
👉 [http://127.0.0.1:8000/api/schema/redoc/](http://127.0.0.1:8000/api/schema/redoc/) (ReDoc)  

---

## 📊 Example Endpoints

### 🔐 Auth
- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `POST /api/auth/logout/`

### 🎫 Tickets
- `POST /api/tickets/` → Create ticket  
- `GET /api/tickets/` → List own tickets  
- `PATCH /api/tickets/{id}/` → Update ticket  
- `DELETE /api/tickets/{id}/` → Delete ticket (Admin only)  

### 🔍 Search
- `GET /api/tickets/?status=open&priority=high`  
- `GET /api/users/?search=john`  

---

## 📌 Reporting (Bonus)
Example:  
```http
GET /api/reports/last7days/
```
Response:
```json
{
  "opened": 12,
  "resolved": 8,
  "escalated": 3
}
```

---

## 📬 Contact
**Author:** Arun Singh  
**Email:** chyarun727@gmail.com  
---
