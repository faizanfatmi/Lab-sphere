# LabSphere — College Lab Management System

**Manage Labs. Track Progress. Build Skills.**

LabSphere is a professional College Lab Management System. This is Phase 1: Landing page and authentication foundation.

## Setup

1. **Install Python 3.13+**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   copy .env.example .env
   ```
   Edit `.env` and set:
   - `DJANGO_SECRET_KEY` — a secure random key
   - `TEACHER_REGISTRATION_SECRET` — the code teachers need to register

4. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Run the development server:**
   ```bash
   python manage.py runserver
   ```

6. **Open in browser:** http://127.0.0.1:8000/

## Testing

```bash
python manage.py test accounts -v2
```

## Authentication

### Student
- Register with: Full Name, Roll Number, Batch (format: `BATCH YYYY-YY`, e.g. `BATCH 2025-29`), Password
- Login with: Name, Batch, Roll Number, Password

### Teacher
- Register with: Teacher ID, Full Name, Password, Registration Code
- Login with: Name, Teacher ID, Password
- Registration requires a secret code configured in `.env`

## Database

Uses SQLite for local development. The database file `db.sqlite3` is created automatically on first migration.

## Project Structure

```
labsphere/     — Django project settings
accounts/      — Authentication app (models, views, forms, backends)
templates/     — HTML templates
static/        — CSS, JavaScript, images
```
