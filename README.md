# ArthSathi | अर्थसाथी

A multilingual financial guidance web app for underprivileged people in rural India.

## What it does

- Recommends government financial schemes based on user profile
- Supports 13 Indian languages with voice input/output
- Self-learning model that improves with more users
- Works on low connectivity (2G/3G)
- No external APIs — everything built from scratch

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML + CSS + Vanilla JS |
| Voice | Web Speech API (built into browser) |
| Backend | Python + Flask |
| Database | PostgreSQL 16 |
| ML Model | Custom Python (no scikit-learn) |

---

## Prerequisites

Before setup, install these manually:

1. **Python 3.10+** — https://www.python.org/downloads/
   - During install, check ✅ "Add Python to PATH"

2. **PostgreSQL 16** — https://www.postgresql.org/download/windows/
   - Default port: 5432
   - Default password: `postgres`

---

## Setup (Windows)

```bash
# 1. Clone the repo
git clone https://github.com/omkard0212/Major-Project.git
cd Major-Project

# 2. Run setup (installs packages, creates DB, processes dataset)
setup.bat

# 3. Start the app
start.bat
```

App opens at **http://localhost:8080**

---

## Setup (Linux / Mac)

```bash
git clone https://github.com/omkard0212/Major-Project.git
cd Major-Project

chmod +x setup.sh start.sh
./setup.sh
./start.sh
```

---

## Project Structure

```
ArthSathi/
├── frontend/          # HTML/CSS/JS web app
│   ├── index.html     # Screen 1 — Character selection
│   ├── language.html  # Screen 2 — Language selection
│   ├── voice-or-type.html
│   ├── register.html  # Screen 4 — Register/Login
│   ├── onboarding.html# Screen 5 — Personal details
│   ├── goals.html     # Screen 6 — Goals
│   ├── results.html   # Screen 7 — Scheme recommendations
│   ├── css/
│   ├── js/
│   └── lang/          # 13 language JSON files
│
├── backend/           # Flask API
│   ├── app.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── profile.py
│   │   └── schemes.py
│   └── config/
│       ├── database.py
│       └── .env.example
│
├── ml-model/          # Recommendation engine
│   ├── recommender.py       # Main entry point
│   ├── eligibility_engine.py
│   ├── scoring_engine.py
│   ├── learning_layer.py
│   ├── interaction_logger.py
│   ├── parse_schemes.py     # Dataset parser
│   ├── schemes_raw.csv      # Source data (3400 schemes)
│   └── schemes_processed.csv# Processed data
│
├── database/
│   └── schema.sql     # PostgreSQL schema
│
├── setup.bat          # Windows first-time setup
├── start.bat          # Windows start
├── setup.sh           # Linux/Mac setup
├── start.sh           # Linux/Mac start
└── requirements.txt   # Python dependencies
```

---

## Environment Variables

Copy `backend/config/.env.example` to `backend/config/.env` and set:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=arthsathi
DB_USER=postgres
DB_PASSWORD=your_password
SECRET_KEY=any_random_string
```

---

## Supported Languages

Hindi, Marathi, Gujarati, Bengali, Tamil, Telugu, Kannada, Malayalam, Punjabi, Odia, Assamese, Urdu, English

---

## How the ML Model Works

1. **Eligibility Engine** — filters 3400 schemes by age, income, gender, caste, state, occupation
2. **Scoring Engine** — ranks eligible schemes by relevance score
3. **Learning Layer** — boosts schemes chosen by similar users over time
4. **Interaction Logger** — records view/save/apply actions for learning

---

*Built for Bharat 🇮🇳*
