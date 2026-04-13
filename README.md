# 🛡️ PhishGuard — Phishing URL Detection

> A modern, full-stack ML web application built with Django 4.2 and SQLite that detects phishing URLs using an ensemble of 5 machine learning models. Free to deploy anywhere.

![Python](https://img.shields.io/badge/Python-3.10-blue) ![Django](https://img.shields.io/badge/Django-4.2-green) ![scikit--learn](https://img.shields.io/badge/scikit--learn-1.5.1-orange) ![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey)

---

## ✨ What's New (vs Legacy Version)

| Feature | Legacy | PhishGuard |
|---|---|---|
| Django version | 3.0.14 | **4.2.16 LTS** |
| URL routing | `url()` deprecated | `path()` modern |
| Authentication | Plain text passwords | **Django auth (hashed)** |
| Database | MySQL (paid) | **SQLite (free, zero config)** |
| Frontend | Inline CSS, Flash SWF | **Cyber-Noir design system** |
| Prediction UI | Full page reload | **Live AJAX — no reloads** |
| Static files | Manual | **WhiteNoise (auto-served)** |
| ML code | Mixed into views | **Extracted to `ml_engine.py`** |
| Excel export | `xlwt` (.xls) | **openpyxl (.xlsx)** |
| Deployment | XAMPP only | **Render / PythonAnywhere free** |
| User dashboard | None | **Stats, charts, history** |
| Admin panel | Basic | **Sidebar, analytics, Chart.js** |

---

## 🤖 ML Models (All Original Algorithms Preserved)

| Model | Library | Role |
|---|---|---|
| Naive Bayes | `MultinomialNB` | Fast probabilistic |
| SVM | `LinearSVC` | Linear classification |
| Logistic Regression | `LogisticRegression` | Probabilistic |
| Decision Tree | `DecisionTreeClassifier` | Non-linear |
| SGD Classifier | `SGDClassifier` | Gradient descent |
| Random Forest | `RandomForestClassifier` | Accuracy tracking |
| **Voting Ensemble** | `VotingClassifier` | **Final prediction** |

Feature extraction: `CountVectorizer` on raw URL strings. Train/test split: 80/20.

---

## 📁 Project Structure

```
PhishGuard/
├── detection_of_phishing_websites/     ← Django project root
│   ├── manage.py
│   ├── Website_urls.csv                ← ML training dataset
│   ├── ml_engine.py                    ← All ML logic (clean separation)
│   ├── db.sqlite3                      ← Auto-created on first run
│   │
│   ├── detection_of_phishing_websites/ ← Django config package
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   │
│   ├── Remote_User/                    ← End-user app
│   │   ├── models.py                   ← UserProfile, URLPrediction, ModelAccuracy
│   │   ├── views.py                    ← Login, Register, Dashboard, Predict, History
│   │   ├── forms.py
│   │   └── urls.py
│   │
│   ├── Service_Provider/               ← Admin app
│   │   ├── views.py                    ← Admin dashboard, train, analytics, export
│   │   └── urls.py
│   │
│   └── templates/
│       ├── base.html                   ← Full design system
│       ├── landing.html
│       ├── RUser/                      ← User-facing pages
│       │   ├── login.html
│       │   ├── register.html
│       │   ├── dashboard.html
│       │   ├── predict.html
│       │   ├── history.html
│       │   └── profile.html
│       └── SProvider/                  ← Admin pages
│           ├── base_admin.html         ← Sidebar layout
│           ├── login.html
│           ├── dashboard.html
│           ├── users.html
│           ├── train.html
│           ├── predictions.html
│           └── analytics.html
│
├── requirements.txt
├── Procfile                            ← Render/Railway deploy
├── render.yaml                         ← One-click Render deploy
├── runtime.txt
├── .env.example
└── .gitignore
```

---

## 🚀 Local Setup

### Prerequisites
- Python 3.10 (recommended) or 3.9/3.11
- Git

### Step 1 — Clone

```bash
git clone https://github.com/<your-username>/Detection_of_Phishing_Websites.git
cd Detection_of_Phishing_Websites
```

### Step 2 — Create Virtual Environment

```bash
# Windows
py -3.10 -m venv venv
venv\Scripts\activate

# macOS / Linux
python3.10 -m venv venv
source venv/bin/activate
```

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Create .env File

Create `.env` inside the `detection_of_phishing_websites/` folder (next to `manage.py`):

```ini
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```

Generate a secret key:
```bash
cd detection_of_phishing_websites
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Step 5 — Run Migrations

```bash
cd detection_of_phishing_websites
python manage.py migrate
```

### Step 6 — Run the Server

```bash
python manage.py runserver
```

Visit: **http://127.0.0.1:8000/**

---

## 👥 User Roles

### Remote User (End User)
| Action | URL |
|---|---|
| Home / Landing | http://127.0.0.1:8000/ |
| Register | http://127.0.0.1:8000/register/ |
| Login | http://127.0.0.1:8000/login/ |
| Dashboard | http://127.0.0.1:8000/dashboard/ |
| Check URL | http://127.0.0.1:8000/predict/ |
| History | http://127.0.0.1:8000/history/ |
| Profile | http://127.0.0.1:8000/profile/ |

### Service Provider (Admin)
| Action | URL |
|---|---|
| Admin Login | http://127.0.0.1:8000/admin/login/ |
| Dashboard | http://127.0.0.1:8000/admin/dashboard/ |
| Users | http://127.0.0.1:8000/admin/users/ |
| Train Models | http://127.0.0.1:8000/admin/train/ |
| Predictions | http://127.0.0.1:8000/admin/predictions/ |
| Analytics | http://127.0.0.1:8000/admin/analytics/ |
| Export Excel | http://127.0.0.1:8000/admin/export/ |

Admin credentials: **Username:** `Admin` | **Password:** `Admin`

---

## ☁️ Free Deployment (Render)

1. Push your code to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` — click **Deploy**
5. Add environment variable `SECRET_KEY` in the Render dashboard

Your app will be live at `https://phishguard.onrender.com` (or your chosen name).

> **Note:** Render free tier spins down after 15 mins of inactivity. First request after sleep takes ~30 seconds to wake up.

---

## 📄 License

Educational and research purposes. Not intended for production security use without further hardening.
