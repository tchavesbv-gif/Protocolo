def init_db():
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS exames (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        )
    """)
  
  # Garante compatibilidade caso o banco antigo já exista sem essas colunas
  cursor.execute("PRAGMA table_info(exames)")
  colunas_existentes = [col[1] for col in cursor.fetchall()]
  
  if "usuario_cadastro" not in colunas_existentes:
    cursor.execute("ALTER TABLE exames ADD COLUMN usuario_cadastro TEXT")
  if "usuario_entrega" not in colunas_existentes:
    cursor.execute("ALTER TABLE exames ADD COLUMN usuario_entrega TEXT")
  if "data_protocolo" not in colunas_existentes:
    cursor.execute("ALTER TABLE exames ADD COLUMN data_protocolo TEXT")

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs_sistema (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT NOT NULL,
            usuario TEXT NOT NULL,
            acao TEXT NOT NULL,
            detalhes TEXT
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            nome_completo TEXT NOT NULL,
            perfil TEXT NOT NULL
        )
    """)

  cursor.execute("SELECT COUNT(*) FROM usuarios")
  if cursor.fetchone()[0] == 0:
    usuarios_iniciais = [
        ("admin", "123", "Administrador do Sistema", "admin"),
        ("atendente1", "123", "Atendente Recepção 1", "atendente"),
        ("atendente2", "123", "Atendente Recepção 2", "atendente")
    ]
    cursor.executemany("""
            INSERT INTO usuarios (username, senha, nome_completo, perfil)
            VALUES (?, ?, ?, ?)
        """, usuarios_iniciais)

  conn.commit()
  conn.close()
