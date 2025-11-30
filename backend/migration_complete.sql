-- MIGRATION COMPLÈTE POUR LA BASE DE DONNÉES POSTGRESQL
-- À exécuter dans la console Neon SQL Editor

-- ==================== ÉTAPE 1: CRÉER LES TABLES DE HIÉRARCHIE ====================

-- Table Projects
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'active',
    start_date DATE,
    end_date DATE,
    manager VARCHAR(255),
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table Sub-projects
CREATE TABLE IF NOT EXISTS sub_projects (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'active',
    start_date DATE,
    end_date DATE,
    lead VARCHAR(255),
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table Categories
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    sub_project_id INTEGER NOT NULL REFERENCES sub_projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    color VARCHAR(7) DEFAULT '#3b82f6',
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==================== ÉTAPE 2: AJOUTER category_id À experiments ====================

ALTER TABLE experiments ADD COLUMN IF NOT EXISTS category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL;

-- ==================== ÉTAPE 3: AJOUTER LES 11 NOUVEAUX CHAMPS ====================

ALTER TABLE experiments ADD COLUMN IF NOT EXISTS priority VARCHAR(50) DEFAULT 'medium';
ALTER TABLE experiments ADD COLUMN IF NOT EXISTS tags TEXT;
ALTER TABLE experiments ADD COLUMN IF NOT EXISTS experiment_number VARCHAR(100);
ALTER TABLE experiments ADD COLUMN IF NOT EXISTS hypothesis TEXT;
ALTER TABLE experiments ADD COLUMN IF NOT EXISTS objectives TEXT;
ALTER TABLE experiments ADD COLUMN IF NOT EXISTS observations TEXT;
ALTER TABLE experiments ADD COLUMN IF NOT EXISTS conclusion TEXT;
ALTER TABLE experiments ADD COLUMN IF NOT EXISTS success_status VARCHAR(50);
ALTER TABLE experiments ADD COLUMN IF NOT EXISTS next_steps TEXT;
ALTER TABLE experiments ADD COLUMN IF NOT EXISTS files_link VARCHAR(500);
ALTER TABLE experiments ADD COLUMN IF NOT EXISTS cost DECIMAL(10, 2);

-- ==================== VÉRIFICATION ====================

-- Vérifier que toutes les tables existent
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('projects', 'sub_projects', 'categories', 'experiments')
ORDER BY table_name;

-- Vérifier les colonnes de la table experiments
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'experiments'
ORDER BY ordinal_position;
