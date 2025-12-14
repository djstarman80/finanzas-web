import streamlit as st
import pandas as pd
import sqlite3  # ¡Este es parte de Python estándar!
from datetime import datetime, date
from fpdf import FPDF
import os
import io
from pathlib import Path

# Configuración de la página
st.set_page_config(
    page_title="💰 Finanzas - Marcelo & Yenny",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constantes
MESES_NUMERO = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

TARJETAS = ["BROU", "Santander", "OCA", "Otra", "Efectivo", "Transferencia"]
PERSONAS = ["Marcelo", "Yenny"]
CATEGORIAS = ["Compras", "Cargo fijo", "Otros", "Supermercado", "Servicios", 
              "Salidas", "Educación", "Salud", "Transporte", "Regalos"]

# Funciones auxiliares (igual que antes)
def monto_uy_a_float(t):
    """Convierte string de monto uruguayo a float"""
    if t is None or (isinstance(t, float) and pd.isna(t)):
        return 0.0
    if isinstance(t, (int, float)):
        return float(t)
    
    s = str(t).strip()
    s = s.replace("$", "").replace(" ", "")
    
    if not s:
        return 0.0
    
    try:
        return float(s)
    except ValueError:
        pass
    
    tiene_punto = "." in s
    tiene_coma = "," in s
    
    if not tiene_punto and not tiene_coma:
        try:
            return float(s)
        except:
            return 0.0
    
    elif tiene_coma and not tiene_punto:
        try:
            return float(s.replace(",", "."))
        except:
            return 0.0
    
    elif tiene_punto and not tiene_coma:
        partes = s.split(".")
        if len(partes) > 2:
            if len(partes[-1]) == 2:
                enteros = "".join(partes[:-1])
                decimales = partes[-1]
                return float(f"{enteros}.{decimales}")
            else:
                return float("".join(partes))
        else:
            return float(s)
    
    else:
        s_sin_puntos = s.replace(".", "")
        s_final = s_sin_puntos.replace(",", ".")
        try:
            return float(s_final)
        except:
            return 0.0

def float_a_monto_uy(v):
    """Convierte float a formato uruguayo"""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "0,00"
    
    try:
        v = float(v)
        
        if abs(v) < 0.01 and abs(v) > 0:
            return f"{v:.4f}".replace(".", ",")
        
        parte_entera = int(abs(v))
        parte_decimal = round(abs(v) - parte_entera, 2)
        
        parte_entera_str = f"{parte_entera:,}".replace(",", ".")
        decimal_str = f"{parte_decimal:.2f}".split(".")[1]
        
        resultado = f"{parte_entera_str},{decimal_str}"
        
        if v < 0:
            resultado = f"-{resultado}"
        
        return resultado
    except Exception:
        return str(v)

def init_db():
    """Inicializa la base de datos SQLite"""
    conn = sqlite3.connect("finanzas.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Fecha TEXT,
            Monto REAL,
            Categoria TEXT,
            Persona TEXT,
            Descripcion TEXT,
            Tarjeta TEXT,
            CuotasTotales INTEGER,
            CuotasPagadas INTEGER,
            MesesPagados TEXT
        )
    """)
    
    cursor.execute("PRAGMA table_info(gastos)")
    columnas = [col[1] for col in cursor.fetchall()]
    
    if "MesesPagados" not in columnas:
        cursor.execute("ALTER TABLE gastos ADD COLUMN MesesPagados TEXT DEFAULT ''")
        st.success("✓ Columna 'MesesPagados' agregada")
    
    conn.commit()
    conn.close()

def cargar_datos():
    """Carga todos los gastos desde la base de datos"""
    conn = sqlite3.connect("finanzas.db")
    
    try:
        df = pd.read_sql_query("SELECT * FROM gastos", conn)
        
        if not df.empty:
            df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
            if "MesesPagados" not in df.columns:
                df["MesesPagados"] = ""
        else:
            df = pd.DataFrame(columns=[
                "id", "Fecha", "Monto", "Categoria", "Persona", 
                "Descripcion", "Tarjeta", "CuotasTotales", "CuotasPagadas", "MesesPagados"
            ])
    
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        df = pd.DataFrame(columns=[
            "id", "Fecha", "Monto", "Categoria", "Persona", 
            "Descripcion", "Tarjeta", "CuotasTotales", "CuotasPagadas", "MesesPagados"
        ])
    
    finally:
        conn.close()
    
    return df

# ... (el resto de las funciones se mantienen igual que en la versión anterior)

# Inicializar la aplicación
def main():
    # Inicializar base de datos
    init_db()
    
    # Título principal
    st.title("💰 Finanzas - Marcelo & Yenny")
    
    # Cargar datos
    df = cargar_datos()
    
    # Sidebar para formulario y acciones
    with st.sidebar:
        st.header("📝 Gestión de Gastos")
        
        # Formulario de gasto
        with st.form("form_gasto"):
            fecha = st.date_input("Fecha", value=date.today(), format="DD/MM/YYYY")
            
            col_monto = st.columns(2)
            with col_monto[0]:
                monto = st.text_input("Monto ($)", value="0,00")
            with col_monto[1]:
                categoria = st.selectbox("Categoría", CATEGORIAS)
            
            persona = st.selectbox("Persona", PERSONAS)
            descripcion = st.text_input("Descripción")
            tarjeta = st.selectbox("Tarjeta", TARJETAS)
            
            col_cuotas = st.columns(2)
            with col_cuotas[0]:
                cuotas_totales = st.selectbox("Cuotas totales", list(range(1, 13)), index=0)
            with col_cuotas[1]:
                cuotas_pagadas = st.selectbox("Cuotas pagadas", list(range(0, 13)), index=0)
            
            # Botones del formulario
            col_botones = st.columns(2)
            with col_botones[0]:
                agregar_btn = st.form_submit_button("➕ Agregar", type="primary", use_container_width=True)
            with col_botones[1]:
                limpiar_btn = st.form_submit_button("🧹 Limpiar", use_container_width=True)
    
    # Mostrar datos
    st.header("📊 Gastos Registrados")
    
    if df.empty:
        st.info("No hay gastos registrados")
    else:
        # Preparar datos para mostrar
        df_display = df.copy()
        df_display["Fecha"] = df_display["Fecha"].apply(
            lambda x: x.strftime("%d/%m/%Y") if not pd.isna(x) else ""
        )
        df_display["Monto"] = df_display["Monto"].apply(lambda x: f"$ {float_a_monto_uy(x)}")
        df_display["Cuotas"] = df_display.apply(
            lambda row: f"{int(row['CuotasPagadas'] or 0)}/{int(row['CuotasTotales'] or 1)}", 
            axis=1
        )
        
        # Mostrar tabla
        st.dataframe(
            df_display[["id", "Fecha", "Descripcion", "Categoria", "Persona", "Tarjeta", "Monto", "Cuotas"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": "ID",
                "Fecha": "📅 Fecha",
                "Descripcion": "📝 Descripción",
                "Categoria": "🏷️ Categoría",
                "Persona": "👤 Persona",
                "Tarjeta": "💳 Tarjeta",
                "Monto": "💰 Monto",
                "Cuotas": "📅 Cuotas"
            }
        )

if __name__ == "__main__":
    main()