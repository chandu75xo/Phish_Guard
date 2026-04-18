<div align="center">

<img src="https://img.shields.io/badge/Python-3.10-3776AB?style=for-the-badge&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/Django-4.2_LTS-092E20?style=for-the-badge&logo=django&logoColor=white" />
<img src="https://img.shields.io/badge/scikit--learn-1.5.1-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white" />
<img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" />
<img src="https://img.shields.io/badge/Deployed_on-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white" />

<br/><br/>

# PhishGuard

### ML-Powered Phishing URL Detection

**An ensemble machine learning web application that instantly detects whether a URL is phishing or legitimate — built with Django 4.2, scikit-learn, and a custom Cyber-Noir design system.**

[Live Demo](https://phishguard.onrender.com) · [Report Bug](https://github.com/your-username/phishguard/issues) · [Request Feature](https://github.com/your-username/phishguard/issues)

</div>

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [ML Models](#ml-models)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [User Roles and Features](#user-roles-and-features)
- [Local Setup](#local-setup)
- [Environment Variables](#environment-variables)
- [Deploying to Render](#deploying-to-render)
- [Deploying to PythonAnywhere](#deploying-to-pythonanywhere)
- [All Routes](#all-routes)
- [Security Notes](#security-notes)
- [Known Limitations](#known-limitations)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

PhishGuard is a full-stack web application that uses an **ensemble of five machine learning classifiers** to detect phishing URLs in real time. Users submit any URL and receive an instant verdict — **Phishing** or **Non Phishing** — backed by per-model accuracy scores.

The project is a complete modern rebuild of an academic system based on the IEEE paper *"Phishing Website Detection using Machine Learning Algorithms"* (Smart Systems and Emerging Technologies, January 2021). All original algorithms are preserved. The new version uses Django 4.2 LTS, clean Pythonic architecture, a professional Cyber-Noir UI, and deploys for free.

**Key highlights:**

- Zero-cost deployment — SQLite, no paid database services required
- Real-time AJAX predictions with animated model progress indicators
- Full admin panel with Chart.js analytics, user management, and styled Excel export
- Secure authentication using Django's built-in hashed password system (PBKDF2)
- Professional design with Oxanium display font and Phosphor Icons throughout

---

## How It Works

```
User submits a URL
        │
        ▼
Django loads Website_urls.csv
(labeled phishing / non-phishing URL dataset)
        │
        ▼
CountVectorizer tokenizes all URL strings
into a sparse token-count feature matrix
        │
        ▼
80 / 20 train-test split (random_state=42)
        │
        ┌──────────────────────────────────────────────┐
        │           Five models trained                │
        │                                              │
        │  Naive Bayes        LinearSVC (SVM)          │
        │  Logistic Reg.      Decision Tree            │
        │  SGD Classifier                              │
        └──────────────────────────────────────────────┘
        │
        ▼
VotingClassifier (hard vote of all 5 models)
        │
        ▼
Input URL vectorized → ensemble predicts → result saved to DB
        │
        ▼
  "Phishing"  or  "Non Phishing"
```

> The model retrains on every prediction request. This keeps the implementation stateless and simple. A production optimisation would be to cache trained models to disk using `joblib`.

---

## ML Models

| Model | Class | Role |
|---|---|---|
| Naive Bayes | `MultinomialNB` | Probabilistic — works well with token counts |
| SVM | `LinearSVC(max_iter=2000)` | Linear boundary — high accuracy on text |
| Logistic Regression | `LogisticRegression(solver='lbfgs')` | Probabilistic linear model |
| Decision Tree | `DecisionTreeClassifier` | Non-linear rule-based |
| SGD Classifier | `SGDClassifier(loss='hinge')` | Gradient descent with SVM-style loss |
| Random Forest | `RandomForestClassifier(n_estimators=100)` | Accuracy tracking only — not in final vote |
| **Voting Ensemble** | `VotingClassifier` | **Hard vote of all 5 above — final prediction** |

**Feature extraction:** `CountVectorizer` on raw URL strings.
**Label encoding:** `Phishing = 0`, `Non Phishing = 1`.
**Train/test split:** 80% / 20%, `random_state=42`.
**Typical accuracy:** 96–99% depending on model.

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Backend framework | Django | 4.2.16 LTS |
| Language | Python | 3.10.x |
| ML library | scikit-learn | 1.5.1 |
| Data processing | pandas | 2.0.3 |
| Numerics | numpy | 1.24.4 |
| NLP | nltk | 3.9.1 |
| Word clouds | wordcloud | 1.9.3 |
| Excel export | openpyxl | 3.1.2 |
| Config management | python-decouple | 3.8 |
| Static files | WhiteNoise | 6.7.0 |
| Production server | gunicorn | 22.0.0 |
| Database | SQLite | built-in |
| Charts | Chart.js | 4.4.1 via CDN |
| Icons | Phosphor Icons | 2.1.1 via CDN |
| Display font | Oxanium | Google Fonts |
| Body font | DM Sans | Google Fonts |

---

## Project Structure

```
phishguard/
│
├── detection_of_phishing_websites/         ← Django project root
│   ├── manage.py
│   ├── Website_urls.csv                    ← Labeled ML training dataset
│   ├── ml_engine.py                        ← All ML logic, clean separation
│   │
│   ├── detection_of_phishing_websites/     ← Django config package
│   │   ├── settings.py                     ← Settings via python-decouple
│   │   ├── urls.py                         ← Root URL routing
│   │   └── wsgi.py
│   │
│   ├── Remote_User/                        ← End-user app
│   │   ├── models.py                       ← UserProfile, URLPrediction, ModelAccuracy
│   │   ├── views.py                        ← Auth, dashboard, predict, history, profile
│   │   ├── forms.py                        ← RegisterForm
│   │   ├── urls.py
│   │   └── migrations/
│   │
│   ├── Service_Provider/                   ← Admin app
│   │   ├── views.py                        ← Dashboard, train, analytics, export
│   │   ├── urls.py
│   │   └── migrations/
│   │
│   └── templates/
│       ├── base.html                       ← Design system (CSS vars, components)
│       ├── landing.html
│       ├── RUser/
│       │   ├── login.html
│       │   ├── register.html
│       │   ├── dashboard.html
│       │   ├── predict.html
│       │   ├── history.html
│       │   └── profile.html
│       └── SProvider/
│           ├── base_admin.html
│           ├── login.html
│           ├── dashboard.html
│           ├── users.html
│           ├── train.html
│           ├── predictions.html
│           └── analytics.html
│
├── requirements.txt
├── Procfile                                ← Render / Railway deploy
├── render.yaml                             ← One-click Render config
├── runtime.txt
├── .env.example
└── .gitignore
```

---

## User Roles and Features

### Remote User

| Feature | Description |
|---|---|
| Register | Create account with username, email, hashed password, optional location |
| Login / Logout | Session-based via Django auth |
| Dashboard | Stats cards, quick URL check widget, recent scan list, threat distribution bar |
| URL Scanner | AJAX prediction with live step-by-step model progress and per-model accuracy bars |
| Scan History | Full history table with filter by All / Phishing / Safe |
| Profile | Edit email and location, view account metadata and activity summary |

### Service Provider (Admin)

| Feature | Description |
|---|---|
| Admin Login | Separate login at `/admin/login/` with credentials `Admin` / `Admin` |
| Dashboard | System-wide stats and latest prediction activity table |
| User Management | View all users with scan counts and phishing/safe breakdown |
| Train Models | AJAX training of all 6 models with live terminal-style log output |
| View Predictions | All URL predictions across all users, filterable |
| Analytics | Chart.js doughnut chart (detection ratio) + bar chart (model accuracy) |
| Export Excel | Styled `.xlsx` download of all predictions with user data |

---

## Local Setup

### Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.10.x (3.9 and 3.11 also work) |
| pip | latest |
| Git | any |

No MySQL, no XAMPP, no Docker needed. SQLite is built into Python.

---

### Step 1 — Clone the Repository

```bash
git clone https://github.com/your-username/PhishGuard.git
cd PhishGuard
```

---

### Step 2 — Create a Virtual Environment

**Windows (PowerShell):**
```powershell
py -3.10 -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3.10 -m venv venv
source venv/bin/activate
```

Your terminal prompt will show `(venv)` confirming it is active.

---

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

All packages have pre-built wheels for Python 3.10. No C++ compiler needed. Takes 2–3 minutes.

---

### Step 4 — Create the .env File

The `.env` file must go **inside** the `detection_of_phishing_websites/` folder — the one that contains `manage.py`.

```bash
cd detection_of_phishing_websites
```

Generate a secure secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Create `.env` and paste your key:

```ini
SECRET_KEY=your-generated-secret-key-here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```

---

### Step 5 — Apply Migrations

```bash
python manage.py migrate
```

Django creates `db.sqlite3` automatically. Every migration should show `OK`.

---

### Step 6 — Run the Server

```bash
python manage.py runserver
```

Open **http://127.0.0.1:8000/**

---

### Step 7 — Quick Smoke Test

1. Go to `http://127.0.0.1:8000/register/` — create a test account
2. Log in and go to **Check URL** at `http://127.0.0.1:8000/predict/`
3. Paste this known phishing URL and click **Analyze URL**:
   ```
   nobell.it/70ffb52d079109dca5664cce6f317373782/login.SkyPe.com/en/cgi-bin/verification/login/index.php
   ```
4. Wait 30–90 seconds for model training — expected result: **Phishing**
5. Test the admin panel at `http://127.0.0.1:8000/admin/login/` with `Admin` / `Admin`

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | Yes | — | Django cryptographic secret. Generate fresh for every environment. |
| `DEBUG` | No | `False` | Set `True` locally only. Never `True` in production. |
| `ALLOWED_HOSTS` | Yes | `127.0.0.1,localhost` | Comma-separated list of allowed hostnames. |

Never commit `.env` to Git. It is already in `.gitignore`.

---

## Deploying to Render

Render is the recommended free deployment platform. Supports Python natively, auto-deploys from GitHub, and has persistent disk for SQLite on paid plans.

### Step 1 — Push to GitHub

```bash
git add .
git commit -m "Initial deployment"
git push origin main
```

### Step 2 — Create Render Account

Sign up at **https://render.com** using your GitHub account.

### Step 3 — Create a New Web Service

1. Dashboard → **New** → **Web Service**
2. Connect your PhishGuard GitHub repository
3. Render auto-detects `render.yaml` — click **Apply**

If not auto-detected, configure manually:

| Field | Value |
|---|---|
| Environment | Python |
| Build Command | `pip install -r requirements.txt && cd detection_of_phishing_websites && python manage.py migrate && python manage.py collectstatic --noinput` |
| Start Command | `cd detection_of_phishing_websites && gunicorn detection_of_phishing_websites.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120` |
| Instance Type | Free |

### Step 4 — Add Environment Variables

In Render dashboard → your service → **Environment** tab:

| Key | Value |
|---|---|
| `SECRET_KEY` | Generate a fresh key — never reuse your local one |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `your-service-name.onrender.com` |
| `PYTHON_VERSION` | `3.10.11` |

### Step 5 — Deploy

Click **Deploy latest commit**. Watch the deploy log. A successful deploy ends with:

```
Your service is live at https://your-service-name.onrender.com
```

### Render Free Tier Notes

The free tier spins the service down after 15 minutes of inactivity. The first request after sleeping takes ~30 seconds to wake. SQLite data resets on each new deploy — upgrade to a Render PostgreSQL database for persistence.

---

## Deploying to PythonAnywhere

### Step 1 — Sign Up and Open Bash

Sign up at **https://www.pythonanywhere.com** (free account) then open a Bash console from the dashboard.

### Step 2 — Clone and Install

```bash
git clone https://github.com/your-username/PhishGuard.git
cd PhishGuard

python3.10 -m venv venv --system-site-packages
source venv/bin/activate

pip install Django==4.2.16 python-decouple==3.8 whitenoise==6.7.0 \
            openpyxl==3.1.2 wordcloud==1.9.3 gunicorn==22.0.0
```

### Step 3 — Create Production .env

```bash
cd ~/PhishGuard/detection_of_phishing_websites
nano .env
```

```ini
SECRET_KEY=your-new-production-secret-key
DEBUG=False
ALLOWED_HOSTS=yourusername.pythonanywhere.com
```

### Step 4 — Migrate and Collect Static

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

### Step 5 — Configure Web Tab

Go to **Web tab** → **Add new web app** → **Manual configuration** → **Python 3.10**.

| Field | Value |
|---|---|
| Source code | `/home/yourusername/PhishGuard/detection_of_phishing_websites` |
| Working directory | `/home/yourusername/PhishGuard/detection_of_phishing_websites` |
| Virtualenv | `/home/yourusername/PhishGuard/venv` |

Edit the WSGI file — delete everything and paste:

```python
import sys, os

path = '/home/yourusername/PhishGuard/detection_of_phishing_websites'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'detection_of_phishing_websites.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

Add static files mapping:

| URL | Directory |
|---|---|
| `/static/` | `/home/yourusername/PhishGuard/detection_of_phishing_websites/staticfiles` |

Click **Reload** → visit `https://yourusername.pythonanywhere.com`.

---

## All Routes

### Public Routes

| Method | URL | Description |
|---|---|---|
| GET | `/` | Landing page with live stats |
| GET | `/login/` | Login page |
| POST | `/login/` | Authenticate user |
| GET | `/register/` | Registration page |
| POST | `/register/` | Create account |
| GET | `/logout/` | Log out |

### Authenticated User Routes

| Method | URL | Description |
|---|---|---|
| GET | `/dashboard/` | Stats overview and quick check |
| GET | `/predict/` | URL scanner page |
| POST | `/predict/` | Run prediction — returns JSON |
| GET | `/history/` | Scan history (supports `?filter=phishing\|safe`) |
| GET | `/profile/` | View profile |
| POST | `/profile/` | Save profile changes |

### Admin Routes (prefix `/admin/`)

| Method | URL | Description |
|---|---|---|
| GET | `/admin/login/` | Admin login page |
| POST | `/admin/login/` | Authenticate admin |
| GET | `/admin/logout/` | Clear admin session |
| GET | `/admin/dashboard/` | System stats overview |
| GET | `/admin/users/` | All registered users |
| GET | `/admin/train/` | Model training page |
| POST | `/admin/train/` | Trigger training — returns JSON |
| GET | `/admin/predictions/` | All predictions (supports `?filter=`) |
| GET | `/admin/analytics/` | Charts and user activity |
| GET | `/admin/export/` | Download `.xlsx` report |

---

## Security Notes

This project is intended for educational and portfolio purposes. Before using in a real production environment, review these items:

| Concern | Current State | Production Fix |
|---|---|---|
| Admin credentials | Hardcoded `Admin`/`Admin` | Move to `.env` and load via `config()` |
| HTTPS enforcement | Not set in Django | Add `SECURE_SSL_REDIRECT = True` behind HTTPS proxy |
| DEBUG mode | Defaults to `False` via decouple | Confirm `DEBUG=False` in production `.env` |
| Model retraining | On every request — slow | Cache with `joblib.dump/load` |
| SQLite concurrency | Single-writer only | Switch to PostgreSQL for multi-user production |
| No rate limiting | Predict endpoint is open | Add Django Ratelimit or similar |
| CSRF protection | Enabled on all POST routes | No action needed |
| Password hashing | Django PBKDF2 (default, secure) | No action needed |

---

## Known Limitations

| Limitation | Detail |
|---|---|
| Slow predictions | Models retrain from scratch on every request (30–120 seconds). Expected for a stateless implementation. |
| SQLite resets on Render free | Ephemeral disk — data lost on each deploy. Upgrade to Render PostgreSQL for persistence. |
| No model caching | Trained model objects are not persisted between requests. |
| Static admin credentials | `Admin`/`Admin` is suitable for demo, not for production. |
| No email verification | Users register without email confirmation. |
| No request throttling | The predict endpoint has no rate limit. |

---

## Contributing

Contributions welcome. To contribute:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit: `git commit -m "Add your feature"`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

Please run `python manage.py check` before submitting — it must pass with 0 issues.

---

## License

Released for educational and research purposes. Based on:

> *"Phishing Website Detection using Machine Learning Algorithms"*
> IEEE Conference on Smart Systems and Emerging Technologies, January 2021

---

<div align="center">
Built with Django · scikit-learn · Phosphor Icons · Oxanium
</div>
