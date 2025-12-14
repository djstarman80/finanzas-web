import streamlit as st
import pandas as pd
import sqlite3
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

# Funciones auxiliares (manteniendo las originales)
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

def guardar_gasto(gasto):
    """Guarda un nuevo gasto en la base de datos"""
    conn = sqlite3.connect("finanzas.db")
    cursor = conn.cursor()
    
    # Aplicar regla del día 5
    fecha_gasto = gasto["Fecha"]
    dia_gasto = fecha_gasto.day
    
    if dia_gasto >= 5:
        primer_mes_pago = fecha_gasto.replace(day=1) + pd.DateOffset(months=1)
        cuotas_pagadas = gasto["CuotasPagadas"]
        
        if cuotas_pagadas > 0:
            meses_pagados = []
            for i in range(cuotas_pagadas):
                mes_pagado = primer_mes_pago + pd.DateOffset(months=i)
                meses_pagados.append(mes_pagado.strftime("%Y-%m"))
            gasto["MesesPagados"] = ",".join(meses_pagados)
        else:
            gasto["MesesPagados"] = ""
    else:
        gasto["MesesPagados"] = ""
    
    cursor.execute("""
        INSERT INTO gastos (Fecha, Monto, Categoria, Persona, Descripcion, 
                           Tarjeta, CuotasTotales, CuotasPagadas, MesesPagados)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        gasto["Fecha"].strftime("%d/%m/%Y"), 
        gasto["Monto"], 
        gasto["Categoria"], 
        gasto["Persona"],
        gasto["Descripcion"], 
        gasto["Tarjeta"], 
        gasto["CuotasTotales"], 
        gasto["CuotasPagadas"], 
        gasto.get("MesesPagados", "")
    ))
    
    conn.commit()
    conn.close()
    return cursor.lastrowid

def actualizar_gasto(id_gasto, gasto):
    """Actualiza un gasto existente"""
    conn = sqlite3.connect("finanzas.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT MesesPagados FROM gastos WHERE id=?", (id_gasto,))
    resultado = cursor.fetchone()
    meses_pagados_existentes = resultado[0] if resultado else ""
    
    # Aplicar regla del día 5
    fecha_gasto = gasto["Fecha"]
    dia_gasto = fecha_gasto.day
    
    if dia_gasto >= 5:
        primer_mes_pago = fecha_gasto.replace(day=1) + pd.DateOffset(months=1)
        
        if meses_pagados_existentes:
            meses_lista = [m.strip() for m in meses_pagados_existentes.split(",") if m.strip()]
            nuevos_meses = []
            for i, _ in enumerate(meses_lista):
                mes_recalculado = primer_mes_pago + pd.DateOffset(months=i)
                nuevos_meses.append(mes_recalculado.strftime("%Y-%m"))
            gasto["MesesPagados"] = ",".join(nuevos_meses)
        else:
            gasto["MesesPagados"] = ""
    else:
        gasto["MesesPagados"] = meses_pagados_existentes
    
    cursor.execute("""
        UPDATE gastos SET Fecha=?, Monto=?, Categoria=?, Persona=?, 
                         Descripcion=?, Tarjeta=?, CuotasTotales=?, 
                         CuotasPagadas=?, MesesPagados=? WHERE id=?
    """, (
        gasto["Fecha"].strftime("%d/%m/%Y"), 
        gasto["Monto"], 
        gasto["Categoria"], 
        gasto["Persona"],
        gasto["Descripcion"], 
        gasto["Tarjeta"], 
        gasto["CuotasTotales"], 
        gasto["CuotasPagadas"], 
        gasto.get("MesesPagados", ""), 
        id_gasto
    ))
    
    conn.commit()
    conn.close()

def eliminar_gasto(id_gasto):
    """Elimina un gasto por ID"""
    conn = sqlite3.connect("finanzas.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM gastos WHERE id=?", (id_gasto,))
    conn.commit()
    conn.close()

def obtener_meses_pagos_pendientes(df):
    """Calcula los pagos futuros pendientes"""
    if df.empty:
        return {}
    
    hoy = datetime.today()
    mes_actual = pd.Timestamp(year=hoy.year, month=hoy.month, day=1)
    meses_pagos = {}
    
    for _, fila in df.iterrows():
        try:
            monto = monto_uy_a_float(fila["Monto"])
            tarjeta = fila["Tarjeta"]
            persona = fila["Persona"]
            fecha_gasto = fila["Fecha"]
            
            if pd.isna(fecha_gasto):
                continue
            
            cuotas_totales = int(fila["CuotasTotales"] or 1)
            cuotas_pagadas = int(fila["CuotasPagadas"] or 0)
            
            if cuotas_pagadas >= cuotas_totales:
                continue
            
            meses_pagados_str = fila.get("MesesPagados", "")
            meses_pagados = []
            
            if meses_pagados_str and str(meses_pagados_str).strip():
                meses_str = str(meses_pagados_str)
                meses_str = meses_str.replace(" ", "").replace("'", "").replace('"', '')
                if meses_str.lower() != "nan" and meses_str:
                    meses_pagados = [m.strip() for m in meses_str.split(",") if m.strip()]
            
            # Regla del día 5
            dia_gasto = fecha_gasto.day
            primer_mes = pd.Timestamp(year=fecha_gasto.year, month=fecha_gasto.month, day=1)
            
            if dia_gasto >= 5:
                primer_mes = primer_mes + pd.DateOffset(months=1)
            
            for i in range(cuotas_totales):
                mes_cuota = primer_mes + pd.DateOffset(months=i)
                mes_cuota_clave = mes_cuota.strftime("%Y-%m")
                
                cuota_ya_pagada = mes_cuota_clave in meses_pagados
                
                if not cuota_ya_pagada and mes_cuota >= mes_actual:
                    if mes_cuota_clave not in meses_pagos:
                        mes_nombre = MESES_NUMERO[mes_cuota.month]
                        meses_pagos[mes_cuota_clave] = {
                            'mes_nombre': mes_nombre,
                            'año': mes_cuota.year,
                            'tarjetas': {},
                            'personas': {}
                        }
                    
                    if tarjeta not in meses_pagos[mes_cuota_clave]['tarjetas']:
                        meses_pagos[mes_cuota_clave]['tarjetas'][tarjeta] = {
                            'total': 0,
                            'cantidad': 0
                        }
                    
                    meses_pagos[mes_cuota_clave]['tarjetas'][tarjeta]['total'] += monto
                    meses_pagos[mes_cuota_clave]['tarjetas'][tarjeta]['cantidad'] += 1
                    
                    if persona not in meses_pagos[mes_cuota_clave]['personas']:
                        meses_pagos[mes_cuota_clave]['personas'][persona] = {
                            'total': 0,
                            'cantidad': 0
                        }
                    
                    meses_pagos[mes_cuota_clave]['personas'][persona]['total'] += monto
                    meses_pagos[mes_cuota_clave]['personas'][persona]['cantidad'] += 1
                    
        except Exception as e:
            continue
    
    return meses_pagos

def exportar_pdf(df_filtrado):
    """Exporta los datos a PDF"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    
    hoy = datetime.today()
    pdf.cell(0, 10, "REPORTE DE GASTOS", 0, 1, "C")
    
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 8, f"Generado: {hoy.strftime('%d/%m/%Y %H:%M')}", 0, 1, "C")
    
    pdf.ln(10)
    
    total = df_filtrado["Monto"].sum()
    registros = len(df_filtrado)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Total: $ {float_a_monto_uy(total)}", 0, 1)
    pdf.cell(0, 10, f"Registros: {registros}", 0, 1)
    
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(200, 200, 200)
    
    columnas = ["Fecha", "Descripción", "Categoría", "Persona", "Tarjeta", "Monto"]
    anchos = [25, 60, 25, 20, 20, 20]
    
    for i, col in enumerate(columnas):
        pdf.cell(anchos[i], 10, col, 1, 0, "C", True)
    pdf.ln()
    
    pdf.set_font("Arial", "", 9)
    for _, fila in df_filtrado.iterrows():
        fecha_str = fila["Fecha"].strftime("%d/%m/%Y") if not pd.isna(fila["Fecha"]) else ""
        pdf.cell(anchos[0], 8, fecha_str, 1, 0, "C")
        
        desc = str(fila["Descripcion"])
        if len(desc) > 40:
            desc = desc[:37] + "..."
        pdf.cell(anchos[1], 8, desc, 1, 0, "L")
        
        pdf.cell(anchos[2], 8, str(fila["Categoria"]), 1, 0, "C")
        pdf.cell(anchos[3], 8, str(fila["Persona"]), 1, 0, "C")
        pdf.cell(anchos[4], 8, str(fila["Tarjeta"]), 1, 0, "C")
        pdf.cell(anchos[5], 8, f"$ {float_a_monto_uy(fila['Monto'])}", 1, 0, "R")
        pdf.ln()
    
    return pdf

# =============================================
# INTERFAZ DE STREAMLIT
# =============================================

# Inicializar base de datos
init_db()

# Título principal
st.title("💰 Finanzas - Marcelo & Yenny")

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
        
        # Para edición
        if 'gasto_editar' in st.session_state:
            st.info(f"Editando gasto #{st.session_state.gasto_editar['id']}")
            actualizar_btn = st.form_submit_button("🔄 Actualizar", type="secondary", use_container_width=True)
    
    st.divider()
    
    # Acciones rápidas
    st.header("⚡ Acciones")
    
    if st.button("📊 Exportar Excel", use_container_width=True):
        df = cargar_datos()
        if not df.empty:
            hoy = datetime.today()
            nombre_archivo = f"gastos_{hoy.strftime('%Y%m%d_%H%M')}.xlsx"
            
            df_export = df.copy()
            df_export["Fecha"] = df_export["Fecha"].apply(lambda x: x.strftime("%d/%m/%Y") if not pd.isna(x) else "")
            df_export["Monto"] = df_export["Monto"].apply(float_a_monto_uy)
            
            with pd.ExcelWriter(nombre_archivo, engine='openpyxl') as writer:
                df_export.to_excel(writer, sheet_name='Datos', index=False)
            
            with open(nombre_archivo, "rb") as f:
                st.download_button(
                    label="📥 Descargar Excel",
                    data=f,
                    file_name=nombre_archivo,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
    
    if st.button("📄 Exportar PDF", use_container_width=True):
        df = cargar_datos()
        if not df.empty:
            pdf = exportar_pdf(df)
            pdf_output = pdf.output(dest='S').encode('latin1')
            
            st.download_button(
                label="📥 Descargar PDF",
                data=pdf_output,
                file_name=f"gastos_{datetime.today().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
    
    if st.button("✅ Marcar pagos del mes", use_container_width=True, type="secondary"):
        hoy = datetime.today()
        if hoy.day == 10:
            st.success("¡Es día 10! Marcando pagos automáticamente...")
            # Aquí iría la lógica para marcar pagos
        else:
            st.warning(f"Para marcado automático, debe ser día 10. Hoy es día {hoy.day}")
    
    st.divider()
    
    # Información regla 5/10
    st.header("📅 Regla 5/10")
    st.info("""
    **Regla del día 5:**
    • Compras día 1-4 → Pago mismo mes
    • Compras día 5+ → Pago próximo mes
    
    **Regla del día 10:**
    • Marcado automático de pagos
    """)

# Contenido principal
tab1, tab2 = st.tabs(["📋 Gastos", "⏰ Pagos Futuros"])

# Cargar datos
df = cargar_datos()

with tab1:
    # Filtros
    st.header("🔍 Filtros")
    
    col_filtros = st.columns(4)
    with col_filtros[0]:
        filtro_persona = st.selectbox("Persona", ["Todos"] + PERSONAS, key="filtro_persona")
    with col_filtros[1]:
        filtro_tarjeta = st.selectbox("Tarjeta", ["Todos"] + TARJETAS, key="filtro_tarjeta")
    with col_filtros[2]:
        hoy = datetime.today()
        meses_opciones = ["Todos"] + [f"{MESES_NUMERO[i]}/{hoy.year}" for i in range(1, 13)]
        filtro_mes = st.selectbox("Mes", meses_opciones, key="filtro_mes")
    with col_filtros[3]:
        filtro_categoria = st.selectbox("Categoría", ["Todos"] + CATEGORIAS, key="filtro_categoria")
    
    # Aplicar filtros
    df_filtrado = df.copy()
    
    if filtro_persona != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Persona"] == filtro_persona]
    
    if filtro_tarjeta != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Tarjeta"] == filtro_tarjeta]
    
    if filtro_mes != "Todos":
        try:
            mes_str, año_str = filtro_mes.split("/")
            mes = list(MESES_NUMERO.keys())[list(MESES_NUMERO.values()).index(mes_str)]
            año = int(año_str)
            df_filtrado = df_filtrado[
                (df_filtrado["Fecha"].dt.year == año) & 
                (df_filtrado["Fecha"].dt.month == mes)
            ]
        except:
            pass
    
    if filtro_categoria != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Categoria"] == filtro_categoria]
    
    # Mostrar tabla
    st.header("📊 Gastos Registrados")
    
    if df_filtrado.empty:
        st.info("No hay gastos registrados con los filtros actuales")
    else:
        # Preparar datos para mostrar
        df_display = df_filtrado.copy()
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
            df_display[["Fecha", "Descripcion", "Categoria", "Persona", "Tarjeta", "Monto", "Cuotas"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Fecha": "📅 Fecha",
                "Descripcion": "📝 Descripción",
                "Categoria": "🏷️ Categoría",
                "Persona": "👤 Persona",
                "Tarjeta": "💳 Tarjeta",
                "Monto": "💰 Monto",
                "Cuotas": "📅 Cuotas"
            }
        )
        
        # Estadísticas
        total_gastos = df_filtrado["Monto"].sum()
        total_registros = len(df_filtrado)
        
        col_stats = st.columns(3)
        with col_stats[0]:
            st.metric("Total Gastos", f"$ {float_a_monto_uy(total_gastos)}")
        with col_stats[1]:
            st.metric("Total Registros", total_registros)
        with col_stats[2]:
            if total_registros > 0:
                promedio = total_gastos / total_registros
                st.metric("Promedio", f"$ {float_a_monto_uy(promedio)}")
        
        # Botones de acción para filas seleccionadas
        st.subheader("Acciones")
        
        col_acciones = st.columns(3)
        with col_acciones[0]:
            gasto_id = st.number_input("ID del gasto para editar/eliminar", min_value=1, step=1)
        
        with col_acciones[1]:
            if st.button("✏️ Editar", use_container_width=True) and gasto_id:
                # Buscar gasto por ID
                gasto = df_filtrado[df_filtrado["id"] == gasto_id]
                if not gasto.empty:
                    gasto = gasto.iloc[0]
                    st.session_state.gasto_editar = {
                        "id": int(gasto["id"]),
                        "fecha": gasto["Fecha"].date() if not pd.isna(gasto["Fecha"]) else date.today(),
                        "monto": float_a_monto_uy(gasto["Monto"]),
                        "categoria": gasto["Categoria"],
                        "persona": gasto["Persona"],
                        "descripcion": gasto["Descripcion"],
                        "tarjeta": gasto["Tarjeta"],
                        "cuotas_totales": int(gasto["CuotasTotales"] or 1),
                        "cuotas_pagadas": int(gasto["CuotasPagadas"] or 0)
                    }
                    st.rerun()
                else:
                    st.error(f"No se encontró gasto con ID {gasto_id}")
        
        with col_acciones[2]:
            if st.button("🗑️ Eliminar", type="secondary", use_container_width=True) and gasto_id:
                if st.checkbox(f"¿Confirmar eliminación del gasto #{gasto_id}?"):
                    eliminar_gasto(gasto_id)
                    st.success(f"Gasto #{gasto_id} eliminado")
                    st.rerun()

with tab2:
    st.header("⏰ Pagos Futuros")
    
    # Calcular pagos pendientes
    meses_pagos = obtener_meses_pagos_pendientes(df)
    
    if not meses_pagos:
        st.success("✅ No hay pagos futuros pendientes")
    else:
        meses_ordenados = sorted(meses_pagos.keys())
        
        # Mostrar resumen por mes
        for mes_clave in meses_ordenados:
            mes_info = meses_pagos[mes_clave]
            
            with st.expander(f"{mes_info['mes_nombre']} {mes_info['año']}", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("💳 Por Tarjeta")
                    for tarjeta, datos in mes_info['tarjetas'].items():
                        st.write(f"**{tarjeta}:** ${float_a_monto_uy(datos['total'])} ({datos['cantidad']} items)")
                
                with col2:
                    st.subheader("👤 Por Persona")
                    for persona, datos in mes_info['personas'].items():
                        st.write(f"**{persona}:** ${float_a_monto_uy(datos['total'])} ({datos['cantidad']} items)")
                
                # Total del mes
                total_mes = sum(datos['total'] for datos in mes_info['tarjetas'].values())
                st.metric(f"Total {mes_info['mes_nombre']}", f"$ {float_a_monto_uy(total_mes)}")
        
        # Resumen general
        st.divider()
        st.subheader("📊 Resumen General")
        
        total_general = 0
        totales_tarjetas = {"BROU": 0.0, "Santander": 0.0, "OCA": 0.0}
        totales_personas = {"Marcelo": 0.0, "Yenny": 0.0}
        
        for mes_clave in meses_ordenados:
            mes_info = meses_pagos[mes_clave]
            for tarjeta, datos in mes_info['tarjetas'].items():
                if tarjeta in totales_tarjetas:
                    totales_tarjetas[tarjeta] += datos['total']
                total_general += datos['total']
            
            for persona, datos in mes_info['personas'].items():
                if persona in totales_personas:
                    totales_personas[persona] += datos['total']
        
        col_resumen = st.columns(3)
        with col_resumen[0]:
            st.metric("Total General", f"$ {float_a_monto_uy(total_general)}")
            st.metric("Meses con pagos", len(meses_ordenados))
        
        with col_resumen[1]:
            st.write("**Por Tarjeta:**")
            for tarjeta, total in totales_tarjetas.items():
                if total > 0:
                    st.write(f"{tarjeta}: ${float_a_monto_uy(total)}")
        
        with col_resumen[2]:
            st.write("**Por Persona:**")
            for persona, total in totales_personas.items():
                if total > 0:
                    porcentaje = (total / total_general * 100) if total_general > 0 else 0
                    st.write(f"{persona}: ${float_a_monto_uy(total)} ({porcentaje:.1f}%)")

# Lógica para agregar/actualizar gastos
if 'gasto_editar' in st.session_state and 'actualizar_btn' in locals():
    if actualizar_btn:
        try:
            gasto_data = {
                "Fecha": pd.Timestamp(st.session_state.gasto_editar["fecha"]),
                "Monto": monto_uy_a_float(monto),
                "Categoria": categoria,
                "Persona": persona,
                "Descripcion": descripcion,
                "Tarjeta": tarjeta,
                "CuotasTotales": cuotas_totales,
                "CuotasPagadas": cuotas_pagadas
            }
            
            actualizar_gasto(st.session_state.gasto_editar["id"], gasto_data)
            st.success(f"Gasto #{st.session_state.gasto_editar['id']} actualizado")
            del st.session_state.gasto_editar
            st.rerun()
            
        except Exception as e:
            st.error(f"Error al actualizar: {e}")

elif agregar_btn:
    try:
        gasto_data = {
            "Fecha": pd.Timestamp(fecha),
            "Monto": monto_uy_a_float(monto),
            "Categoria": categoria,
            "Persona": persona,
            "Descripcion": descripcion,
            "Tarjeta": tarjeta,
            "CuotasTotales": cuotas_totales,
            "CuotasPagadas": cuotas_pagadas
        }
        
        nuevo_id = guardar_gasto(gasto_data)
        st.success(f"Gasto #{nuevo_id} agregado correctamente")
        st.rerun()
        
    except Exception as e:
        st.error(f"Error al agregar: {e}")

# Verificación día 10 para marcado automático
hoy = datetime.today()
if hoy.day == 10:
    st.sidebar.info(f"¡Es día 10 de {MESES_NUMERO[hoy.month]}! ¿Marcar pagos automáticamente?")
    
    if st.sidebar.button("✅ Marcar automáticamente", use_container_width=True):
        st.sidebar.success("Marcando pagos... (funcionalidad en desarrollo)")