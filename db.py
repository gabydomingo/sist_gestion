"""db.py
Funciones para crear la base de datos y CRUD.
"""
import sqlite3
import datetime
from typing import List, Dict, Tuple, Optional


DB_NAME = "sangucheria.db"

# --- CREACIÓN DE TABLAS (SIN CAMBIOS) ---
def create_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sanguches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    ingredientes TEXT,
    precio REAL,
    categoria_id INTEGER,
    FOREIGN KEY (categoria_id) REFERENCES categorias(id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS caja_sesiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_apertura TEXT,
    fecha_cierre TEXT,
    monto_inicial REAL,
    total_ventas_netas REAL,
    total_descuentos REAL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    telefono TEXT,
    email TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT,
    total REAL,
    metodo_pago TEXT,
    descuento REAL DEFAULT 0,
    motivo_descuento TEXT,
    sesion_id INTEGER,
    cliente_id INTEGER,
    FOREIGN KEY(sesion_id) REFERENCES caja_sesiones(id),
    FOREIGN KEY(cliente_id) REFERENCES clientes(id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS venta_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id INTEGER,
    sanguche_id INTEGER,
    cantidad INTEGER,
    subtotal REAL,
    FOREIGN KEY(venta_id) REFERENCES ventas(id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS gastos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT,
    producto TEXT,
    cantidad REAL,
    total_gastado REAL,
    metodo_pago TEXT,
    sesion_id INTEGER,
    FOREIGN KEY(sesion_id) REFERENCES caja_sesiones(id)
    )
    """)
    conn.commit()
    conn.close()
    
# ----------------------
# Categorías y Sanguches (Sin cambios)
# ----------------------
def get_categorias() -> List[Tuple[int, str]]:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, nombre FROM categorias ORDER BY nombre ASC")
    rows = cur.fetchall()
    conn.close()
    return rows
def add_categoria(nombre: str) -> None:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO categorias (nombre) VALUES (?)", (nombre,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()
def update_categoria(cat_id: int, nuevo_nombre: str) -> None:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE categorias SET nombre = ? WHERE id = ?", (nuevo_nombre, cat_id))
    conn.commit()
    conn.close()
def delete_categoria(cat_id: int) -> None:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM categorias WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()
def get_sanguches() -> List[Tuple[int, str, str, float, Optional[str]]]:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
    """
    SELECT s.id, s.nombre, s.ingredientes, s.precio, c.nombre
    FROM sanguches s
    LEFT JOIN categorias c ON s.categoria_id = c.id
    ORDER BY s.nombre ASC
    """
    )
    rows = cur.fetchall()
    conn.close()
    return rows
def get_sanguches_simple() -> List[Tuple[int, str, float]]:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, precio FROM sanguches ORDER BY nombre")
    rows = cur.fetchall()
    conn.close()
    return rows
def add_sanguche(nombre: str, ingredientes: str, precio: float, categoria_id: Optional[int]) -> None:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
    "INSERT INTO sanguches (nombre, ingredientes, precio, categoria_id) VALUES (?, ?, ?, ?)",
    (nombre, ingredientes, precio, categoria_id)
    )
    conn.commit()
    conn.close()
def update_sanguche(s_id: int, nombre: str, ingredientes: str, precio: float, categoria_id: Optional[int]) -> None:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
    "UPDATE sanguches SET nombre = ?, ingredientes = ?, precio = ?, categoria_id = ? WHERE id = ?",
    (nombre, ingredientes, precio, categoria_id, s_id)
    )
    conn.commit()
    conn.close()
def delete_sanguche(s_id: int) -> None:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM sanguches WHERE id = ?", (s_id,))
    conn.commit()
    conn.close()
# ----------------------
# Clientes (Sin cambios)
# ----------------------
def add_cliente(nombre: str, telefono: Optional[str], email: Optional[str]) -> int:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO clientes (nombre, telefono, email) VALUES (?, ?, ?)",
        (nombre, telefono, email)
    )
    cliente_id = cur.lastrowid
    conn.commit()
    conn.close()
    return cliente_id
def get_clientes() -> List[Tuple[int, str, Optional[str], Optional[str]]]:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, telefono, email FROM clientes ORDER BY nombre ASC")
    rows = cur.fetchall()
    conn.close()
    return rows
def buscar_clientes_por_nombre(nombre_parcial: str) -> List[Tuple[int, str, Optional[str], Optional[str]]]:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, nombre, telefono, email FROM clientes WHERE nombre LIKE ? ORDER BY nombre ASC",
        (f"%{nombre_parcial}%",)
    )
    rows = cur.fetchall()
    conn.close()
    return rows
def update_cliente(cliente_id: int, nombre: str, telefono: Optional[str], email: Optional[str]):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "UPDATE clientes SET nombre = ?, telefono = ?, email = ? WHERE id = ?",
        (nombre, telefono, email, cliente_id)
    )
    conn.commit()
    conn.close()
def delete_cliente(cliente_id: int):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
    conn.commit()
    conn.close()
# ----------------------
# Ventas (Sin cambios)
# ----------------------
def add_venta(total: float, metodo_pago: str, items: List[Dict], descuento: float, motivo_descuento: Optional[str], sesion_id: int, cliente_id: Optional[int]) -> int:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "INSERT INTO ventas (fecha, total, metodo_pago, descuento, motivo_descuento, sesion_id, cliente_id) VALUES (?, ?, ?, ?, ?, ?, ?)", 
        (fecha, total, metodo_pago, descuento, motivo_descuento, sesion_id, cliente_id)
    )
    venta_id = cur.lastrowid
    for it in items:
        cur.execute(
        "INSERT INTO venta_items (venta_id, sanguche_id, cantidad, subtotal) VALUES (?, ?, ?, ?)",
        (venta_id, it['sanguche_id'], it['cantidad'], it['subtotal'])
        )
    conn.commit()
    conn.close()
    return venta_id
def get_resumen_ventas_por_sesion(sesion_id: int) -> List[Tuple[str, float]]:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
    "SELECT metodo_pago, SUM(total) FROM ventas WHERE sesion_id = ? GROUP BY metodo_pago",
    (sesion_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows
def get_ventas_detalladas_por_sesion(sesion_id: int) -> List[Tuple]:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
    """
    SELECT v.fecha, v.total, v.metodo_pago, v.descuento, v.motivo_descuento, IFNULL(c.nombre, 'Consumidor Final')
    FROM ventas v
    LEFT JOIN clientes c ON v.cliente_id = c.id
    WHERE v.sesion_id = ? 
    ORDER BY v.fecha ASC
    """,
    (sesion_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows
def get_totales_ventas_por_sesion(sesion_id: int) -> Tuple[float, float]:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
    "SELECT SUM(total), SUM(descuento) FROM ventas WHERE sesion_id = ?",
    (sesion_id,)
    )
    row = cur.fetchone()
    total_ventas = row[0] or 0
    total_descuentos = row[1] or 0
    conn.close()
    return (total_ventas, total_descuentos)
# ----------------------
# Gastos (Sin cambios)
# ----------------------
def add_gasto(producto: str, cantidad: float, total_gastado: float, metodo_pago: str, sesion_id: int):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "INSERT INTO gastos (fecha, producto, cantidad, total_gastado, metodo_pago, sesion_id) VALUES (?, ?, ?, ?, ?, ?)",
        (fecha, producto, cantidad, total_gastado, metodo_pago, sesion_id)
    )
    conn.commit()
    conn.close()
def get_gastos_detallados_por_sesion(sesion_id: int) -> List[Tuple[str, str, float, float, str]]:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT fecha, producto, cantidad, total_gastado, metodo_pago FROM gastos WHERE sesion_id = ? ORDER BY fecha ASC",
        (sesion_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows
def get_resumen_gastos_por_sesion(sesion_id: int) -> List[Tuple[str, float]]:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT metodo_pago, SUM(total_gastado) FROM gastos WHERE sesion_id = ? GROUP BY metodo_pago",
        (sesion_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows
def get_total_gastos_por_sesion(sesion_id: int) -> float:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT SUM(total_gastado) FROM gastos WHERE sesion_id = ?",
        (sesion_id,)
    )
    row = cur.fetchone()
    total_gastos = row[0] or 0
    conn.close()
    return total_gastos
# ----------------------
# Caja (Sin cambios)
# ----------------------
def abrir_caja(monto_inicial: float) -> int:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "INSERT INTO caja_sesiones (fecha_apertura, monto_inicial) VALUES (?, ?)",
        (fecha, monto_inicial)
    )
    sesion_id = cur.lastrowid
    conn.commit()
    conn.close()
    return sesion_id
def cerrar_caja(sesion_id: int, total_ventas_netas: float, total_descuentos: float):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        """
        UPDATE caja_sesiones 
        SET fecha_cierre = ?, total_ventas_netas = ?, total_descuentos = ?
        WHERE id = ?
        """,
        (fecha, total_ventas_netas, total_descuentos, sesion_id)
    )
    conn.commit()
    conn.close()
def get_ultima_sesion_abierta() -> Optional[Tuple[int, str, float]]:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, fecha_apertura, monto_inicial FROM caja_sesiones WHERE fecha_cierre IS NULL ORDER BY id DESC LIMIT 1"
    )
    row = cur.fetchone()
    conn.close()
    return row

# ----------------------------------------------------
# --- NUEVAS FUNCIONES PARA REPORTES HISTÓRICOS ---
# ----------------------------------------------------

def get_ventas_detalladas_por_rango(fecha_inicio: str, fecha_fin: str) -> List[Tuple]:
    """Obtiene todas las ventas detalladas de un rango de fechas, incluyendo el nombre del cliente."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
    """
    SELECT v.fecha, v.total, v.metodo_pago, v.descuento, v.motivo_descuento, IFNULL(c.nombre, 'Consumidor Final')
    FROM ventas v
    LEFT JOIN clientes c ON v.cliente_id = c.id
    WHERE v.fecha BETWEEN ? AND ?
    ORDER BY v.fecha ASC
    """,
    (fecha_inicio, fecha_fin)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def get_gastos_detallados_por_rango(fecha_inicio: str, fecha_fin: str) -> List[Tuple]:
    """Obtiene todos los gastos detallados de un rango de fechas."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT fecha, producto, cantidad, total_gastado, metodo_pago FROM gastos WHERE fecha BETWEEN ? AND ? ORDER BY fecha ASC",
        (fecha_inicio, fecha_fin)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def get_totales_ventas_por_rango(fecha_inicio: str, fecha_fin: str) -> Tuple[float, float]:
    """Retorna (total_ventas_netas, total_descuentos) de un rango de fechas."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
    "SELECT SUM(total), SUM(descuento) FROM ventas WHERE fecha BETWEEN ? AND ?",
    (fecha_inicio, fecha_fin)
    )
    row = cur.fetchone()
    total_ventas = row[0] or 0
    total_descuentos = row[1] or 0
    conn.close()
    return (total_ventas, total_descuentos)

def get_total_gastos_por_rango(fecha_inicio: str, fecha_fin: str) -> float:
    """Obtiene el total de gastos de un rango de fechas."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT SUM(total_gastado) FROM gastos WHERE fecha BETWEEN ? AND ?",
        (fecha_inicio, fecha_fin)
    )
    row = cur.fetchone()
    total_gastos = row[0] or 0
    conn.close()
    return total_gastos