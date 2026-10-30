"""
db.py
------
Tudo relacionado a salvar e consultar dados no banco (SQLite).
SQLite é um banco de dados que fica em um único arquivo (mercado.db) no
próprio computador - não precisa instalar nem configurar servidor nenhum.
"""

import sqlite3
from datetime import date

CAMINHO_BANCO = "mercado.db"


def conectar():
    """Abre uma conexão com o banco de dados."""
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def criar_tabelas():
    """Cria as tabelas do banco caso ainda não existam. Chamado uma vez ao iniciar o app."""
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mercados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cnpj TEXT UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS compras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mercado_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            url_nota TEXT,
            FOREIGN KEY (mercado_id) REFERENCES mercados (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            compra_id INTEGER NOT NULL,
            produto TEXT NOT NULL,
            preco REAL NOT NULL,
            quantidade REAL DEFAULT 1,
            FOREIGN KEY (compra_id) REFERENCES compras (id)
        )
    """)

    conexao.commit()
    conexao.close()


def obter_ou_criar_mercado(nome, cnpj=None):
    """Procura um mercado pelo nome/cnpj; se não existir, cria. Retorna o id do mercado."""
    conexao = conectar()
    cursor = conexao.cursor()

    if cnpj:
        cursor.execute("SELECT id FROM mercados WHERE cnpj = ?", (cnpj,))
        resultado = cursor.fetchone()
        if resultado:
            conexao.close()
            return resultado[0]

    cursor.execute(
        "INSERT INTO mercados (nome, cnpj) VALUES (?, ?)", (nome, cnpj)
    )
    conexao.commit()
    novo_id = cursor.lastrowid
    conexao.close()
    return novo_id


def salvar_compra(nome_mercado, itens, url_nota=None, cnpj=None):
    """
    Salva uma compra completa.
    itens: lista de dicionários no formato {"produto": str, "preco": float, "quantidade": float}
    Retorna o id da compra criada.
    """
    mercado_id = obter_ou_criar_mercado(nome_mercado, cnpj)

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        "INSERT INTO compras (mercado_id, data, url_nota) VALUES (?, ?, ?)",
        (mercado_id, date.today().isoformat(), url_nota),
    )
    compra_id = cursor.lastrowid

    for item in itens:
        cursor.execute(
            "INSERT INTO itens (compra_id, produto, preco, quantidade) VALUES (?, ?, ?, ?)",
            (compra_id, item["produto"], item["preco"], item.get("quantidade", 1)),
        )

    conexao.commit()
    conexao.close()
    return compra_id


def listar_compras():
    """Retorna todas as compras, mais recentes primeiro, com o nome do mercado."""
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("""
        SELECT compras.id, mercados.nome, compras.data
        FROM compras
        JOIN mercados ON mercados.id = compras.mercado_id
        ORDER BY compras.data DESC, compras.id DESC
    """)
    resultado = cursor.fetchall()
    conexao.close()
    return resultado


def listar_itens_da_compra(compra_id):
    """Retorna os itens (produto, preco, quantidade) de uma compra específica."""
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT produto, preco, quantidade FROM itens WHERE compra_id = ?",
        (compra_id,),
    )
    resultado = cursor.fetchall()
    conexao.close()
    return resultado


def menor_preco_por_produto(termo_busca):
    """
    Busca o menor preço já registrado para produtos cujo nome contém o termo buscado,
    junto com o mercado e a data em que esse preço foi visto.
    """
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("""
        SELECT itens.produto, itens.preco, mercados.nome, compras.data
        FROM itens
        JOIN compras ON compras.id = itens.compra_id
        JOIN mercados ON mercados.id = compras.mercado_id
        WHERE itens.produto LIKE ?
        ORDER BY itens.preco ASC
    """, (f"%{termo_busca}%",))
    resultado = cursor.fetchall()
    conexao.close()
    return resultado


def contar_streak_dias():
    """
    Conta quantos dias consecutivos (incluindo hoje ou ontem) o usuário registrou
    pelo menos uma compra. Usado para o "streak" de motivação.
    """
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT DISTINCT data FROM compras ORDER BY data DESC")
    datas = [row[0] for row in cursor.fetchall()]
    conexao.close()

    if not datas:
        return 0

    from datetime import datetime, timedelta

    datas_convertidas = [datetime.strptime(d, "%Y-%m-%d").date() for d in datas]
    hoje = date.today()

    # streak só conta se o registro mais recente foi hoje ou ontem
    if datas_convertidas[0] < hoje - timedelta(days=1):
        return 0

    streak = 1
    for i in range(len(datas_convertidas) - 1):
        diferenca = (datas_convertidas[i] - datas_convertidas[i + 1]).days
        if diferenca == 1:
            streak += 1
        else:
            break

    return streak
