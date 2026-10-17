# LabSphere — College Lab Management System

**Manage Labs. Track Progress. Build Skills.**

LabSphere is a comprehensive, production-grade College Laboratory Management & Coding Examination Platform built with **Django 6.x**, **Python**, **SQLite3**, **HTML5**, **Vanilla CSS3**, and **Vanilla JavaScript**.

---

## 🌟 Core Features (Phases 1, 2 & 3)

### 1. Dual Role Authentication & Access Control
- **Student Portal:** Register with Full Name, University Roll Number (unique), Batch (`BATCH YYYY-YY`), and Password. Authenticate using Roll Number + Password with batch/name verification.
- **Teacher Portal:** Protected teacher registration requiring a secret administrative code (`TEACHER_REGISTRATION_SECRET`). Authenticate using Teacher ID + Password.
- **Role-Based Access Control:** Strict `@student_required` and `@teacher_required` server-side route guards.

### 2. Teacher Dashboard & Student Performance Management
- **Analytics Overview:** Real-time metrics on Total Students, Active Assessments, Average Scores, and Attendance Rates.
- **Search & Filtering:** Search students across batches by name or roll number; filter by academic batch.
- **Detailed Student Profiles:** Comprehensive performance breakdown per student showing assessment history, question-wise marks, submission timestamps, and attendance records.
- **Assessment Management:** Create, edit, publish/unpublish, archive, and delete coding assessments.
- **Question & Test Case Suite:** Configure problem statements, constraints, input/output formats, time/memory limits, language starter templates, visible sample cases, and confidential private evaluation test cases.
- **Manual Score Override:** Authorized teachers can override awarded scores with mandatory reason logging and audit history.

### 3. Student Dashboard
- **Live Lab Check-In:** Automatic detection of active lab practical sessions for the student's batch with PIN verification.
- **Performance Summary:** Total marks earned, enrolled batch verification, and real-time attendance rate.
- **Assessment Roster:** Dynamic categories for *Available / Live*, *Upcoming*, and *Past Completed* assessments.
- **Submission History:** Table of past coding submissions with verdict badges, marks, and timestamps.

### 4. LeetCode-Style Split IDE Coding Interface
- **Split Workspace:**
  - **Left Panel:** Problem statement, constraints, input/output format, sample cases with copyable test inputs and explanations.
  - **Right Panel:** Full **Monaco Editor** integration (the engine powering Visual Studio Code) with syntax highlighting, language selector, and code reset.
  - **Bottom Panel:** Tabbed console for custom test inputs, standard output, compiler errors, runtime metrics, and evaluation verdict.
- **Three Supported Languages:**
  - **C/C++** (GCC)
  - **Java** (OpenJDK)
  - **Python 3**
- **Autosave Drafts:** Automatically persists code drafts per student, per question, and per language every few seconds; seamlessly restores code on reload.
- **Exam Countdown Timer:** Live countdown with automatic warning when time is running out.

### 5. Isolated Code Execution & Automated Grading Engine
- **Decoupled Sandbox:** Untrusted code execution is kept isolated from the main Django application server.
- **Execution Modes (`EXECUTION_SERVICE_MODE`):**
  - `judge0`: Connects to public/self-hosted Judge0 CE or RapidAPI endpoints.
  - `sandbox`: Isolated local process execution with clean environment, output caps (64 KB), and strict timeouts.
  - `mock`: Fast, deterministic execution engine for test suites and offline demos.
- **Private Test Case Protection:** Private test case inputs and expected outputs are never exposed in client HTML or response JSON.
- **Fair Marks Allocation:** Scores calculated proportionally based on passed test cases and question weights.

### 6. Laboratory Attendance Tracking
- **Session Management:** Teachers schedule practical sessions for specific labs, batches, dates, and time windows with optional 6-digit verification PINs.
- **Server-Side Validation:** Validates student batch, active session status, current server time window, and duplicate prevention.
- **Audit Logs & Manual Corrections:** Teachers can update attendance records with mandatory audit reasons.
- **Downloadable CSV Reports:** Instant export of laboratory attendance rosters.

### 7. Examination Security & Safeguards
- **Browser-Level Safeguards:** Fullscreen assessment mode, automatic tab switch / window blur detection, and event audit logging (`/assessments/api/log-event/`).
- **Audit Log Review:** Teachers can inspect recorded student security events directly on the submission review page.
- *Note:* Hardened laboratory restrictions require institutional kiosk browsers and network firewall allowlisting.

### 8. Light Mode & Dark Mode Theme System
- Complete theme switching across the entire platform (Landing page, Dashboards, Tables, Cards, Modals, and Monaco Editor).
- Monaco Editor theme automatically synchronizes between `vs` (Light Mode) and `vs-dark` (Dark Mode).
- Persists user preference via `localStorage` and respects system `prefers-color-scheme` without page flash (anti-FOUC).

---

## 🚀 Setup & Installation

### 1. Requirements
- Python 3.12+ (Tested on Python 3.14)
- Git

### 2. Setup Virtual Environment
```bash
# Create local virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
```bash
copy .env.example .env
```
Edit `.env` and set:
```ini
DJANGO_SECRET_KEY=your-secure-random-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
TEACHER_REGISTRATION_SECRET=labsphere-teacher-2025
EXECUTION_SERVICE_MODE=sandbox
```

### 4. Database Migrations
```bash
python manage.py migrate
```

### 5. Run the Test Suite
Run all 36 automated test cases covering authentication, lab sessions, attendance check-in, assessment grading, and security logging:
```bash
python manage.py test -v2
```

### 6. Start the Development Server
```bash
python manage.py runserver
```
Visit http://127.0.0.1:8000/ in your browser.

---

## 📁 Project Architecture

```
labsphere/           — Django settings, master URLs, WSGI/ASGI
accounts/            — Authentication app (User, StudentProfile, TeacherProfile, backends, RBAC)
labs/                — Laboratory app (Lab, LabSession, LabAttendance, CSV export)
assessments/         — Examination app (Assessment, Question, TestCase, Submissions, Monaco IDE, Security logs)
  └── services/      — Isolated code execution service (Judge0, Sandboxed runner, Mock executor)
templates/           — Semantic HTML5 templates
  ├── accounts/      — Student & Teacher dashboards
  ├── labs/          — Session list, session form, attendance detail
  └── assessments/   — LeetCode coding IDE, question forms, submissions audit
static/
  ├── css/style.css  — Design tokens, Light & Dark themes, 1300+ lines responsive CSS
  ├── js/main.js     — Form toggling, theme switcher, Monaco synchronization, toasts
  └── images/hero.png— Hero illustration
```
