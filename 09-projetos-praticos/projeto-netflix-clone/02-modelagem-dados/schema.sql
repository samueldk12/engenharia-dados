-- ============================================================================
-- NETFLIX CLONE: DATABASE SCHEMA COMPLETO
-- Plataforma de Streaming de Vídeo em Escala
-- ============================================================================

-- Database: PostgreSQL 14+ para metadata e transacional
-- Cassandra: Para viewing_history (time-series, bilhões de eventos)
-- Redis: Para caching e sessions

-- ============================================================================
-- 1. USERS & AUTHENTICATION
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS netflix;
SET search_path TO netflix;

-- Usuários e autenticação
CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200),
    phone VARCHAR(20),
    date_of_birth DATE,
    country_code CHAR(2) NOT NULL,
    language_preference VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    email_verified BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'deleted')),

    -- Compliance
    gdpr_consent BOOLEAN DEFAULT FALSE,
    marketing_consent BOOLEAN DEFAULT FALSE,
    last_login_at TIMESTAMP,
    last_login_ip INET
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status) WHERE status = 'active';
CREATE INDEX idx_users_country ON users(country_code);

-- Profiles (múltiplos perfis por conta)
CREATE TABLE profiles (
    profile_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    profile_name VARCHAR(100) NOT NULL,
    avatar_url VARCHAR(500),
    is_kids BOOLEAN DEFAULT FALSE,
    language VARCHAR(10),
    maturity_level VARCHAR(20) DEFAULT 'all' CHECK (maturity_level IN ('kids', 'teen', 'mature', 'all')),
    autoplay_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, profile_name)
);

CREATE INDEX idx_profiles_user ON profiles(user_id);

-- Sessions
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    profile_id BIGINT REFERENCES profiles(profile_id),
    device_type VARCHAR(50),
    device_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_expires ON sessions(expires_at) WHERE is_active = TRUE;

-- ============================================================================
-- 2. SUBSCRIPTIONS & BILLING
-- ============================================================================

CREATE TABLE subscription_plans (
    plan_id SERIAL PRIMARY KEY,
    plan_name VARCHAR(100) NOT NULL,
    description TEXT,
    price_usd DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    billing_cycle VARCHAR(20) DEFAULT 'monthly' CHECK (billing_cycle IN ('monthly', 'yearly')),
    max_streams INT DEFAULT 1,
    video_quality VARCHAR(20) DEFAULT 'HD' CHECK (video_quality IN ('SD', 'HD', 'UHD')),
    max_profiles INT DEFAULT 1,
    download_enabled BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO subscription_plans (plan_name, price_usd, max_streams, video_quality, max_profiles, download_enabled) VALUES
('Basic', 9.99, 1, 'SD', 1, FALSE),
('Standard', 15.99, 2, 'HD', 2, TRUE),
('Premium', 19.99, 4, 'UHD', 4, TRUE);

CREATE TABLE subscriptions (
    subscription_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    plan_id INT NOT NULL REFERENCES subscription_plans(plan_id),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('trial', 'active', 'paused', 'cancelled', 'expired')),
    start_date DATE NOT NULL DEFAULT CURRENT_DATE,
    end_date DATE,
    next_billing_date DATE,
    auto_renew BOOLEAN DEFAULT TRUE,
    payment_method VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_billing ON subscriptions(next_billing_date) WHERE status = 'active';

CREATE TABLE payments (
    payment_id BIGSERIAL PRIMARY KEY,
    subscription_id BIGINT NOT NULL REFERENCES subscriptions(subscription_id),
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    payment_method VARCHAR(50) NOT NULL,
    transaction_id VARCHAR(200) UNIQUE,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed', 'refunded')),
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

CREATE INDEX idx_payments_subscription ON payments(subscription_id);
CREATE INDEX idx_payments_user ON payments(user_id);
CREATE INDEX idx_payments_status ON payments(status);

-- ============================================================================
-- 3. CONTENT CATALOG
-- ============================================================================

-- Content types: movie, series, documentary, etc
CREATE TABLE content (
    content_id BIGSERIAL PRIMARY KEY,
    content_type VARCHAR(20) NOT NULL CHECK (content_type IN ('movie', 'series', 'documentary', 'special')),
    title VARCHAR(500) NOT NULL,
    original_title VARCHAR(500),
    description TEXT,
    synopsis TEXT,
    release_year INT,
    runtime_minutes INT, -- Para movies
    total_seasons INT, -- Para series
    total_episodes INT, -- Para series
    original_language VARCHAR(10),
    country_of_origin VARCHAR(50),

    -- Classificação
    maturity_rating VARCHAR(10), -- G, PG, PG-13, R, NC-17, TV-Y, TV-PG, TV-14, TV-MA
    content_warning TEXT,

    -- Metadata
    director TEXT[], -- Array de diretores
    cast TEXT[], -- Array de atores principais
    genres TEXT[] NOT NULL, -- ['Action', 'Drama', 'Sci-Fi']
    tags TEXT[], -- ['award-winning', 'oscar-winner', 'trending']

    -- Media
    thumbnail_url VARCHAR(500),
    poster_url VARCHAR(500),
    backdrop_url VARCHAR(500),
    trailer_url VARCHAR(500),

    -- Status
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    is_original BOOLEAN DEFAULT FALSE, -- Netflix Original?

    -- Dates
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_content_type ON content(content_type);
CREATE INDEX idx_content_status ON content(status) WHERE status = 'published';
CREATE INDEX idx_content_genres ON content USING GIN(genres);
CREATE INDEX idx_content_release ON content(release_year DESC);
CREATE INDEX idx_content_original ON content(is_original) WHERE is_original = TRUE;

-- Temporadas (para séries)
CREATE TABLE seasons (
    season_id BIGSERIAL PRIMARY KEY,
    content_id BIGINT NOT NULL REFERENCES content(content_id) ON DELETE CASCADE,
    season_number INT NOT NULL,
    title VARCHAR(500),
    description TEXT,
    release_year INT,
    episode_count INT,
    thumbnail_url VARCHAR(500),

    UNIQUE(content_id, season_number)
);

CREATE INDEX idx_seasons_content ON seasons(content_id);

-- Episódios
CREATE TABLE episodes (
    episode_id BIGSERIAL PRIMARY KEY,
    season_id BIGINT NOT NULL REFERENCES seasons(season_id) ON DELETE CASCADE,
    content_id BIGINT NOT NULL REFERENCES content(content_id) ON DELETE CASCADE,
    episode_number INT NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    runtime_minutes INT NOT NULL,
    thumbnail_url VARCHAR(500),

    -- Video assets
    video_url_sd VARCHAR(500),
    video_url_hd VARCHAR(500),
    video_url_uhd VARCHAR(500),

    published_at TIMESTAMP,

    UNIQUE(season_id, episode_number)
);

CREATE INDEX idx_episodes_season ON episodes(season_id);
CREATE INDEX idx_episodes_content ON episodes(content_id);

-- Video assets (diferentes resoluções e bitrates)
CREATE TABLE video_assets (
    asset_id BIGSERIAL PRIMARY KEY,
    content_id BIGINT REFERENCES content(content_id) ON DELETE CASCADE,
    episode_id BIGINT REFERENCES episodes(episode_id) ON DELETE CASCADE,

    -- Video specs
    resolution VARCHAR(10) NOT NULL, -- '360p', '480p', '720p', '1080p', '4K'
    bitrate_kbps INT NOT NULL,
    codec VARCHAR(20) NOT NULL, -- 'h264', 'h265', 'vp9', 'av1'
    container VARCHAR(10) NOT NULL, -- 'mp4', 'webm'

    -- Storage
    storage_path VARCHAR(1000) NOT NULL, -- S3/GCS path
    file_size_bytes BIGINT,
    duration_seconds INT,

    -- HLS/DASH
    manifest_url VARCHAR(500), -- .m3u8 or .mpd

    -- Status
    encoding_status VARCHAR(20) DEFAULT 'pending' CHECK (encoding_status IN ('pending', 'processing', 'completed', 'failed')),
    quality_score DECIMAL(5,2), -- VMAF score

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CHECK (
        (content_id IS NOT NULL AND episode_id IS NULL) OR
        (content_id IS NULL AND episode_id IS NOT NULL)
    )
);

CREATE INDEX idx_assets_content ON video_assets(content_id);
CREATE INDEX idx_assets_episode ON video_assets(episode_id);
CREATE INDEX idx_assets_resolution ON video_assets(resolution);

-- Subtitles
CREATE TABLE subtitles (
    subtitle_id BIGSERIAL PRIMARY KEY,
    content_id BIGINT REFERENCES content(content_id) ON DELETE CASCADE,
    episode_id BIGINT REFERENCES episodes(episode_id) ON DELETE CASCADE,
    language VARCHAR(10) NOT NULL,
    subtitle_type VARCHAR(20) DEFAULT 'caption' CHECK (subtitle_type IN ('caption', 'subtitle', 'sdh')),
    storage_path VARCHAR(1000) NOT NULL, -- .vtt, .srt file

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(content_id, episode_id, language, subtitle_type)
);

-- ============================================================================
-- 4. VIEWING HISTORY & ANALYTICS
-- ============================================================================

-- Para PostgreSQL (recente, hot data - últimos 30 dias)
CREATE TABLE viewing_history_hot (
    view_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    profile_id BIGINT NOT NULL REFERENCES profiles(profile_id),
    content_id BIGINT REFERENCES content(content_id),
    episode_id BIGINT REFERENCES episodes(episode_id),

    -- Playback info
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    watch_duration_seconds INT, -- Tempo real assistido
    progress_seconds INT, -- Posição atual no vídeo
    completed BOOLEAN DEFAULT FALSE,

    -- Device & Network
    device_type VARCHAR(50),
    device_id VARCHAR(100),
    ip_address INET,
    country_code CHAR(2),
    city VARCHAR(100),

    -- Quality metrics
    avg_bitrate_kbps INT,
    resolution_watched VARCHAR(10),
    buffering_events INT DEFAULT 0,
    buffering_time_seconds INT DEFAULT 0,

    -- Session
    session_id UUID REFERENCES sessions(session_id)
) PARTITION BY RANGE (started_at);

-- Particionamento por mês
CREATE TABLE viewing_history_hot_2024_01 PARTITION OF viewing_history_hot
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE viewing_history_hot_2024_02 PARTITION OF viewing_history_hot
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Índices nas partições
CREATE INDEX idx_viewing_hot_user_2024_01 ON viewing_history_hot_2024_01(user_id);
CREATE INDEX idx_viewing_hot_profile_2024_01 ON viewing_history_hot_2024_01(profile_id);
CREATE INDEX idx_viewing_hot_content_2024_01 ON viewing_history_hot_2024_01(content_id);
CREATE INDEX idx_viewing_hot_started_2024_01 ON viewing_history_hot_2024_01(started_at);

-- Continue Watching (última posição por conteúdo)
CREATE TABLE continue_watching (
    continue_watch_id BIGSERIAL PRIMARY KEY,
    profile_id BIGINT NOT NULL REFERENCES profiles(profile_id),
    content_id BIGINT REFERENCES content(content_id),
    episode_id BIGINT REFERENCES episodes(episode_id),
    progress_seconds INT NOT NULL,
    total_seconds INT NOT NULL,
    last_watched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(profile_id, content_id, episode_id)
);

CREATE INDEX idx_continue_profile ON continue_watching(profile_id, last_watched_at DESC);

-- ============================================================================
-- 5. RECOMMENDATIONS
-- ============================================================================

CREATE TABLE recommendations (
    recommendation_id BIGSERIAL PRIMARY KEY,
    profile_id BIGINT NOT NULL REFERENCES profiles(profile_id),
    content_id BIGINT NOT NULL REFERENCES content(content_id),

    -- Recommendation metadata
    algorithm VARCHAR(50) NOT NULL, -- 'collaborative', 'content-based', 'trending', 'personalized'
    score DECIMAL(5,4) NOT NULL, -- 0.0 to 1.0
    reason TEXT, -- "Because you watched X"
    position INT, -- Position in recommendation list

    -- Context
    context VARCHAR(50), -- 'homepage', 'genre-page', 'search'
    genre_context VARCHAR(50),

    -- Tracking
    generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,

    -- User interaction
    shown_at TIMESTAMP,
    clicked_at TIMESTAMP,
    watched_at TIMESTAMP
);

CREATE INDEX idx_recommendations_profile ON recommendations(profile_id, expires_at);
CREATE INDEX idx_recommendations_content ON recommendations(content_id);

-- My List (favoritos do usuário)
CREATE TABLE my_list (
    my_list_id BIGSERIAL PRIMARY KEY,
    profile_id BIGINT NOT NULL REFERENCES profiles(profile_id),
    content_id BIGINT NOT NULL REFERENCES content(content_id),
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(profile_id, content_id)
);

CREATE INDEX idx_mylist_profile ON my_list(profile_id, added_at DESC);

-- Ratings (curtir/não curtir)
CREATE TABLE ratings (
    rating_id BIGSERIAL PRIMARY KEY,
    profile_id BIGINT NOT NULL REFERENCES profiles(profile_id),
    content_id BIGINT NOT NULL REFERENCES content(content_id),
    rating_type VARCHAR(20) NOT NULL CHECK (rating_type IN ('like', 'dislike')),
    rated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(profile_id, content_id)
);

CREATE INDEX idx_ratings_profile ON ratings(profile_id);
CREATE INDEX idx_ratings_content ON ratings(content_id, rating_type);

-- ============================================================================
-- 6. SEARCH & DISCOVERY
-- ============================================================================

-- Search history
CREATE TABLE search_history (
    search_id BIGSERIAL PRIMARY KEY,
    profile_id BIGINT NOT NULL REFERENCES profiles(profile_id),
    query TEXT NOT NULL,
    results_count INT,
    clicked_content_id BIGINT REFERENCES content(content_id),
    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_search_profile ON search_history(profile_id, searched_at DESC);
CREATE INDEX idx_search_query ON search_history USING gin(to_tsvector('english', query));

-- Trending content (cached aggregations)
CREATE TABLE trending_content (
    trending_id BIGSERIAL PRIMARY KEY,
    content_id BIGINT NOT NULL REFERENCES content(content_id),
    country_code CHAR(2) DEFAULT 'GLOBAL',

    -- Metrics (últimas 24h)
    view_count BIGINT DEFAULT 0,
    unique_viewers BIGINT DEFAULT 0,
    avg_watch_time_seconds INT,
    completion_rate DECIMAL(5,2),

    -- Ranking
    rank INT,
    previous_rank INT,

    -- Window
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(content_id, country_code, window_start)
);

CREATE INDEX idx_trending_country ON trending_content(country_code, rank);

-- ============================================================================
-- 7. ANALYTICS AGGREGATIONS (Pre-computed)
-- ============================================================================

-- Daily content metrics
CREATE TABLE content_metrics_daily (
    metric_id BIGSERIAL PRIMARY KEY,
    content_id BIGINT NOT NULL REFERENCES content(content_id),
    metric_date DATE NOT NULL,

    -- View metrics
    total_views BIGINT DEFAULT 0,
    unique_viewers BIGINT DEFAULT 0,
    total_watch_time_seconds BIGINT DEFAULT 0,
    avg_watch_time_seconds INT,

    -- Engagement
    completion_rate DECIMAL(5,2),
    like_count INT DEFAULT 0,
    dislike_count INT DEFAULT 0,
    added_to_list_count INT DEFAULT 0,

    -- Quality
    avg_buffering_events DECIMAL(5,2),
    avg_video_quality VARCHAR(10),

    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(content_id, metric_date)
);

CREATE INDEX idx_content_metrics_date ON content_metrics_daily(metric_date DESC);
CREATE INDEX idx_content_metrics_content ON content_metrics_daily(content_id);

-- User engagement metrics
CREATE TABLE user_metrics_daily (
    metric_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    metric_date DATE NOT NULL,

    -- Activity
    sessions_count INT DEFAULT 0,
    total_watch_time_seconds BIGINT DEFAULT 0,
    content_watched_count INT DEFAULT 0,
    unique_titles_watched INT DEFAULT 0,

    -- Engagement
    searches_count INT DEFAULT 0,
    ratings_given INT DEFAULT 0,
    list_additions INT DEFAULT 0,

    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, metric_date)
);

CREATE INDEX idx_user_metrics_date ON user_metrics_daily(metric_date DESC);

-- ============================================================================
-- 8. NOTIFICATIONS & MESSAGING
-- ============================================================================

CREATE TABLE notifications (
    notification_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    notification_type VARCHAR(50) NOT NULL, -- 'new_content', 'recommendation', 'billing', 'system'
    title VARCHAR(200) NOT NULL,
    message TEXT,
    content_id BIGINT REFERENCES content(content_id),

    -- Delivery
    is_read BOOLEAN DEFAULT FALSE,
    is_sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP,
    read_at TIMESTAMP,

    -- Channels
    push_notification BOOLEAN DEFAULT FALSE,
    email BOOLEAN DEFAULT FALSE,
    in_app BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE INDEX idx_notifications_user ON notifications(user_id, is_read, created_at DESC);

-- ============================================================================
-- 9. A/B TESTING
-- ============================================================================

CREATE TABLE experiments (
    experiment_id SERIAL PRIMARY KEY,
    experiment_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    hypothesis TEXT,

    -- Configuration
    start_date DATE NOT NULL,
    end_date DATE,
    traffic_allocation DECIMAL(3,2) DEFAULT 0.10, -- % of users

    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'running', 'paused', 'completed')),

    -- Results
    winner_variant VARCHAR(50),
    confidence_level DECIMAL(5,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE experiment_variants (
    variant_id SERIAL PRIMARY KEY,
    experiment_id INT NOT NULL REFERENCES experiments(experiment_id),
    variant_name VARCHAR(50) NOT NULL,
    description TEXT,
    configuration JSONB,
    traffic_allocation DECIMAL(3,2), -- % within experiment

    UNIQUE(experiment_id, variant_name)
);

CREATE TABLE experiment_assignments (
    assignment_id BIGSERIAL PRIMARY KEY,
    experiment_id INT NOT NULL REFERENCES experiments(experiment_id),
    variant_id INT NOT NULL REFERENCES experiment_variants(variant_id),
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(experiment_id, user_id)
);

-- ============================================================================
-- 10. AUDIT & COMPLIANCE
-- ============================================================================

CREATE TABLE audit_logs (
    log_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id BIGINT,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_action ON audit_logs(action, created_at DESC);

-- ============================================================================
-- VIEWS & MATERIALIZED VIEWS
-- ============================================================================

-- Popular content (última semana)
CREATE MATERIALIZED VIEW mv_popular_content AS
SELECT
    c.content_id,
    c.title,
    c.content_type,
    COUNT(DISTINCT vh.profile_id) as unique_viewers,
    COUNT(*) as total_views,
    AVG(vh.watch_duration_seconds) as avg_watch_time,
    SUM(CASE WHEN vh.completed THEN 1 ELSE 0 END)::DECIMAL / COUNT(*) * 100 as completion_rate
FROM content c
JOIN viewing_history_hot vh ON c.content_id = vh.content_id
WHERE vh.started_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY c.content_id, c.title, c.content_type
HAVING COUNT(*) >= 100
ORDER BY unique_viewers DESC;

CREATE UNIQUE INDEX idx_mv_popular_content ON mv_popular_content(content_id);

-- User engagement summary
CREATE MATERIALIZED VIEW mv_user_engagement AS
SELECT
    u.user_id,
    u.email,
    s.status as subscription_status,
    COUNT(DISTINCT DATE(vh.started_at)) as days_active_30d,
    COUNT(DISTINCT vh.content_id) as unique_content_watched_30d,
    SUM(vh.watch_duration_seconds) / 3600 as total_hours_30d,
    MAX(vh.started_at) as last_activity_at
FROM users u
LEFT JOIN subscriptions s ON u.user_id = s.user_id AND s.status = 'active'
LEFT JOIN viewing_history_hot vh ON u.user_id = vh.user_id
    AND vh.started_at >= CURRENT_DATE - INTERVAL '30 days'
WHERE u.status = 'active'
GROUP BY u.user_id, u.email, s.status;

-- ============================================================================
-- SAMPLE QUERIES
-- ============================================================================

-- Query 1: Top 10 most watched content esta semana
/*
SELECT
    c.title,
    c.content_type,
    COUNT(DISTINCT vh.profile_id) as unique_viewers,
    COUNT(*) as total_views,
    AVG(vh.watch_duration_seconds / 60.0) as avg_watch_minutes
FROM content c
JOIN viewing_history_hot vh ON c.content_id = vh.content_id
WHERE vh.started_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY c.content_id, c.title, c.content_type
ORDER BY unique_viewers DESC
LIMIT 10;
*/

-- Query 2: Retenção de usuários (cohort analysis)
/*
WITH user_cohorts AS (
    SELECT
        user_id,
        DATE_TRUNC('month', created_at) as cohort_month
    FROM users
),
user_activity AS (
    SELECT DISTINCT
        user_id,
        DATE_TRUNC('month', started_at) as activity_month
    FROM viewing_history_hot
)
SELECT
    uc.cohort_month,
    ua.activity_month,
    EXTRACT(MONTH FROM AGE(ua.activity_month, uc.cohort_month)) as months_since_signup,
    COUNT(DISTINCT ua.user_id) as active_users
FROM user_cohorts uc
LEFT JOIN user_activity ua ON uc.user_id = ua.user_id
WHERE uc.cohort_month >= '2024-01-01'
GROUP BY uc.cohort_month, ua.activity_month
ORDER BY uc.cohort_month, ua.activity_month;
*/

-- Query 3: Recomendações personalizadas (collaborative filtering simplificado)
/*
WITH user_watched AS (
    SELECT DISTINCT content_id
    FROM viewing_history_hot
    WHERE profile_id = :profile_id
),
similar_users AS (
    SELECT
        vh.profile_id,
        COUNT(*) as common_content
    FROM viewing_history_hot vh
    WHERE vh.content_id IN (SELECT content_id FROM user_watched)
      AND vh.profile_id != :profile_id
    GROUP BY vh.profile_id
    ORDER BY common_content DESC
    LIMIT 50
),
recommendations AS (
    SELECT
        c.content_id,
        c.title,
        COUNT(*) as recommendation_score
    FROM viewing_history_hot vh
    JOIN content c ON vh.content_id = c.content_id
    WHERE vh.profile_id IN (SELECT profile_id FROM similar_users)
      AND c.content_id NOT IN (SELECT content_id FROM user_watched)
    GROUP BY c.content_id, c.title
    ORDER BY recommendation_score DESC
    LIMIT 20
)
SELECT * FROM recommendations;
*/

-- ============================================================================
-- TRIGGERS & FUNCTIONS
-- ============================================================================

-- Function para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Aplicar trigger em tabelas relevantes
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_content_updated_at BEFORE UPDATE ON content
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- REFRESH MATERIALIZED VIEWS (via cron/scheduler)
-- ============================================================================

-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_popular_content;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_user_engagement;
