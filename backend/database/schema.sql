-- PostgreSQL Database Schema for Sattva Streamer
-- Generated from production database: 2025-12-04
-- Database version: PostgreSQL 15.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';
SET default_table_access_method = heap;

-- ============================================================================
-- TABLE: users
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.users (
    id uuid NOT NULL PRIMARY KEY,
    google_id character varying,
    email character varying,
    full_name character varying,
    profile_picture_url character varying,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone,
    hashed_password character varying,
    email_verified boolean DEFAULT false,
    role character varying DEFAULT 'user'::character varying NOT NULL,
    status character varying DEFAULT 'pending'::character varying NOT NULL,
    telegram_id bigint,
    telegram_username character varying(255),
    CONSTRAINT uq_users_telegram_id UNIQUE (telegram_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON public.users USING btree (email);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_id ON public.users USING btree (google_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_telegram_id ON public.users USING btree (telegram_id);

COMMENT ON TABLE public.users IS 'Пользователи системы';
COMMENT ON COLUMN public.users.role IS 'Роль: user, admin';
COMMENT ON COLUMN public.users.status IS 'Статус: pending, approved, rejected';

-- ============================================================================
-- TABLE: telegram_accounts
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.telegram_accounts (
    id uuid NOT NULL PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES public.users(id),
    phone character varying NOT NULL,
    encrypted_session character varying NOT NULL,
    tg_user_id bigint,
    first_name character varying,
    username character varying,
    photo_url character varying,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone
);

COMMENT ON TABLE public.telegram_accounts IS 'Telegram аккаунты пользователей';
COMMENT ON COLUMN public.telegram_accounts.encrypted_session IS 'Зашифрованная Pyrogram session string';

-- ============================================================================
-- TABLE: channels
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.channels (
    id uuid NOT NULL PRIMARY KEY,
    account_id uuid NOT NULL REFERENCES public.telegram_accounts(id),
    chat_id bigint NOT NULL,
    name character varying NOT NULL,
    status character varying,
    ffmpeg_args character varying,
    video_quality character varying,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone
);

COMMENT ON TABLE public.channels IS 'Telegram каналы/группы для стриминга';
COMMENT ON COLUMN public.channels.chat_id IS 'Telegram chat ID канала';
COMMENT ON COLUMN public.channels.status IS 'Статус: stopped, running, error';

-- ============================================================================
-- TABLE: playlist_items
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.playlist_items (
    id uuid NOT NULL PRIMARY KEY,
    channel_id uuid REFERENCES public.channels(id),
    url character varying NOT NULL,
    title character varying,
    type character varying,
    "position" integer,
    created_by uuid REFERENCES public.users(id),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    status character varying(20) DEFAULT 'pending'::character varying,
    duration integer
);

COMMENT ON TABLE public.playlist_items IS 'Элементы плейлиста канала';
COMMENT ON COLUMN public.playlist_items.type IS 'Тип: video, audio, youtube, stream';
COMMENT ON COLUMN public.playlist_items.status IS 'Статус: pending, playing, played, error';
COMMENT ON COLUMN public.playlist_items.duration IS 'Длительность в секундах';

-- ============================================================================
-- TABLE: alembic_version (Alembic migrations tracking)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.alembic_version (
    version_num character varying(32) NOT NULL PRIMARY KEY
);

COMMENT ON TABLE public.alembic_version IS 'Версии Alembic миграций';
