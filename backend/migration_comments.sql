-- Migration pour ajouter le système de commentaires

-- Table des commentaires (peut être utilisée pour tasks, experiments, projects, etc.)
CREATE TABLE IF NOT EXISTS comments (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,  -- 'task', 'experiment', 'project', etc.
    entity_id INTEGER NOT NULL,         -- ID de l'entité commentée
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_comments_entity ON comments(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_comments_user ON comments(user_id);

-- Vérification
SELECT * FROM comments LIMIT 1;
