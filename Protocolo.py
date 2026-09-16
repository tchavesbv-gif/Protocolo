CREATE TABLE IF NOT EXISTS exames (
    id SERIAL PRIMARY KEY,
    protocolo TEXT UNIQUE NOT NULL,
    data_coleta TEXT NOT NULL,
    nome_paciente TEXT NOT NULL,
    tipo_exame TEXT NOT NULL,
    status TEXT NOT NULL,
    data_chegada TEXT,
    data_entrega TEXT,
    recebido_por TEXT,
    data_protocolo TEXT,
    usuario_cadastro TEXT,
    usuario_entrega TEXT
);

CREATE TABLE IF NOT EXISTS logs_sistema (
    id SERIAL PRIMARY KEY,
    data_hora TEXT NOT NULL,
    usuario TEXT NOT NULL,
    acao TEXT NOT NULL,
    detalhes TEXT
);

CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    senha TEXT NOT NULL,
    nome_completo TEXT NOT NULL,
    perfil TEXT NOT NULL
);

INSERT INTO usuarios (username, senha, nome_completo, perfil)
VALUES 
    ('admin', '123', 'Administrador do Sistema', 'admin'),
    ('atendente1', '123', 'Atendente Recepção 1', 'atendente'),
    ('atendente2', '123', 'Atendente Recepção 2', 'atendente')
ON CONFLICT (username) DO NOTHING;
