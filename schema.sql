-- Schema da tabela de avaliações. Compatível com qualquer servidor PostgreSQL.

CREATE TABLE IF NOT EXISTS evaluation (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    consultor VARCHAR(255),
    lead VARCHAR(255),
    fase VARCHAR(100),
    nota_final FLOAT NOT NULL,
    classificacao VARCHAR(50) NOT NULL,
    metadata_json TEXT, -- Armazena o JSON completo para auditoria detalhada
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índices para performance em escala
CREATE INDEX IF NOT EXISTS idx_evaluation_session_id ON evaluation(session_id);
CREATE INDEX IF NOT EXISTS idx_evaluation_consultor ON evaluation(consultor);
CREATE INDEX IF NOT EXISTS idx_evaluation_created_at ON evaluation(created_at);

COMMENT ON COLUMN evaluation.metadata_json IS 'Cópia íntegra da avaliação da IA para fins de auditoria e rastreabilidade.';
