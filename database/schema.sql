-- ================================================================
-- ArthSathi Database Schema
-- PostgreSQL 16
-- ================================================================

-- ── TABLE 1: users ───────────────────────────────────────────
-- Stores login credentials and app preferences
CREATE TABLE IF NOT EXISTS users (
    user_id           SERIAL PRIMARY KEY,
    name              VARCHAR(100) NOT NULL,
    phone             VARCHAR(15)  UNIQUE NOT NULL,
    email             VARCHAR(150) UNIQUE,
    password_hash     VARCHAR(255) NOT NULL,
    preferred_language VARCHAR(30) NOT NULL DEFAULT 'hindi',
    input_mode        VARCHAR(10)  NOT NULL DEFAULT 'text'
                      CHECK (input_mode IN ('text', 'voice')),
    created_at        TIMESTAMP    NOT NULL DEFAULT NOW(),
    last_login        TIMESTAMP
);

-- ── TABLE 2: user_profiles ───────────────────────────────────
-- Stores personal and financial details of each user
CREATE TABLE IF NOT EXISTS user_profiles (
    profile_id        SERIAL PRIMARY KEY,
    user_id           INT          NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    age               SMALLINT     CHECK (age > 0 AND age < 120),
    gender            VARCHAR(10)  CHECK (gender IN ('male', 'female', 'other')),
    caste             VARCHAR(20)  CHECK (caste IN ('SC', 'ST', 'OBC', 'General', 'Brahmin', 'Minority', 'Other')),
    state             VARCHAR(60),
    district          VARCHAR(60),
    occupation        VARCHAR(30),
    annual_income     INTEGER      CHECK (annual_income >= 0),
    family_size       SMALLINT     CHECK (family_size > 0),
    land_owned_acres  DECIMAL(6,2) DEFAULT 0,
    has_bank_account  BOOLEAN      DEFAULT FALSE,
    is_bpl            BOOLEAN      DEFAULT FALSE,
    is_pwd            BOOLEAN      DEFAULT FALSE,
    is_widow          BOOLEAN      DEFAULT FALSE,
    updated_at        TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ── TABLE 3: user_goals ──────────────────────────────────────
-- Each user can have multiple goals
-- goal_category maps to scheme categories in our ML model
CREATE TABLE IF NOT EXISTS user_goals (
    goal_id           SERIAL PRIMARY KEY,
    user_id           INT          NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    goal_category     VARCHAR(50)  NOT NULL
                      CHECK (goal_category IN (
                          'education',
                          'health',
                          'farming',
                          'business',
                          'housing',
                          'insurance',
                          'employment',
                          'women_empowerment',
                          'social_welfare',
                          'other'
                      )),
    goal_description  TEXT,        -- user's own words in their language
    created_at        TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ── TABLE 4: scheme_recommendations ─────────────────────────
-- Records every time the model recommends a scheme to a user
CREATE TABLE IF NOT EXISTS scheme_recommendations (
    recommendation_id SERIAL PRIMARY KEY,
    user_id           INT          NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    scheme_slug       VARCHAR(100) NOT NULL,
    scheme_name       TEXT         NOT NULL,
    score             DECIMAL(6,2),
    rank              SMALLINT,
    recommended_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ── TABLE 5: user_interactions ───────────────────────────────
-- Records what a user does with each recommended scheme
-- This feeds directly into the self-learning model
CREATE TABLE IF NOT EXISTS user_interactions (
    interaction_id    SERIAL PRIMARY KEY,
    user_id           INT          NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    scheme_slug       VARCHAR(100) NOT NULL,
    scheme_name       TEXT         NOT NULL,
    action            VARCHAR(10)  NOT NULL
                      CHECK (action IN ('view', 'select', 'apply')),
    action_weight     SMALLINT     NOT NULL,
    score_given       DECIMAL(6,2),
    interacted_at     TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ── INDEXES for fast lookups ─────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id     ON user_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_goals_user_id        ON user_goals(user_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_user_id   ON scheme_recommendations(user_id);
CREATE INDEX IF NOT EXISTS idx_interactions_user_id      ON user_interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_interactions_scheme_slug  ON user_interactions(scheme_slug);

-- ================================================================
-- Done
-- ================================================================
