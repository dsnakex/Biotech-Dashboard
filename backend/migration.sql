-- Migration SQL pour ajouter les nouvelles colonnes à la table experiments
-- À exécuter dans la console Neon ou via Render Shell

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

-- Vérifier les colonnes ajoutées
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'experiments'
ORDER BY ordinal_position;
