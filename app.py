import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, date

# Configurar página
st.set_page_config(page_title="Finanzas App", layout="wide")
st.title("💰 Finanzas - Marcelo & Yenny")

# ===== CONFIGURACIÓN FÁCIL =====
# Pega tu ID de Google Sheets aquí
GOOGLE_SHEET_ID = "PEGA_AQUI_TU_ID_DE_GOOGLE_SHEETS"

# ===== CONEXIÓN SUPER SIMPLE =====
@st.cache_resource
def conectar_sheets():
    """Conectar a Google Sheets de forma simple"""
    try:
        # Método simple usando credenciales públicas
        gc = gspread.service_account(filename='credenciales.json')
        hoja = gc.open_by_key(GOOGLE_SHEET_ID).sheet1
        st.sidebar.success("✅ Conectado a Google Sheets")
        return hoja
    except Exception as e:
        st.sidebar.warning(f"⚠️ Error: {e}")
        st.sidebar.info("Usando modo local temporal")
        return None

# ===== FUNCIONES PRINCIPALES =====
def cargar_datos():
    """Cargar todos los gastos"""
    hoja = conectar_sheets()
    
    if hoja:
        try:
            # Leer todos los datos
            datos = hoja.get_all_records()
            df = pd.DataFrame(datos)
            
            if not df.empty:
                # Convertir tipos de datos
                df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
                df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce')
                df['CuotasTotales'] = pd.to_numeric(df['CuotasTotales'], errors='coerce').fillna(1).astype(int)
                df['CuotasPagadas'] = pd.to_numeric(df['CuotasPagadas'], errors='coerce').fillna(0).astype(int)
            
            return df
        except:
            return pd.DataFrame()
    else:
        # Modo local si no hay conexión
        return pd.DataFrame()

def guardar_gasto(gasto):
    """Guardar un nuevo gasto"""
    hoja = conectar_sheets()
    
    if hoja:
        try:
            # Preparar la fila
            fila = [
                gasto['Fecha'].strftime('%d/%m/%Y'),
                float(gasto['Monto']),
                gasto['Categoria'],
                gasto['Persona'],
                gasto['Descripcion'],
                gasto['Tarjeta'],
                int(gasto['CuotasTotales']),
                int(gasto['CuotasPagadas']),
                gasto.get('MesesPagados', '')
            ]
            
            # Agregar a Google Sheets
            hoja.append_row(fila)
            return True
        except Exception as e:
            st.error(f"Error al guardar: {e}")
            return False
    return False

def actualizar_gasto(id_gasto, gasto):
    """Actualizar gasto existente"""
    hoja = conectar_sheets()
    
    if hoja:
        try:
            # Buscar fila por ID (asumiendo que ID es el número de fila)
            fila_numero = id_gasto + 1  # +1 porque la fila 1 es el encabezado
            
            datos = [
                gasto['Fecha'].strftime('%d/%m/%Y'),
                float(gasto['Monto']),
                gasto['Categoria'],
                gasto['Persona'],
                gasto['Descripcion'],
                gasto['Tarjeta'],
                int(gasto['CuotasTotales']),
                int(gasto['CuotasPagadas']),
                gasto.get('MesesPagados', '')
            ]
            
            # Actualizar la fila
            for col, valor in enumerate(datos, start=1):
                hoja.update_cell(fila_numero, col, valor)
            
            return True
        except:
            return False
    return False

def eliminar_gasto(id_gasto):
    """Eliminar un gasto"""
    hoja = conectar_sheets()
    
    if hoja:
        try:
            # +2 porque: +1 para encabezado, +1 porque las filas empiezan en 1, no en 0
            hoja.delete_rows(id_gasto + 2)
            return True
        except:
            return False
    return False

# ===== INTERFAZ DE USUARIO =====
# Sidebar - Formulario
with st.sidebar:
    st.header("📝 Nuevo Gasto")
    
    with st.form("form_gasto"):
        fecha = st.date_input("Fecha", value=date.today())
        monto = st.number_input("Monto ($)", min_value=0.0, value=0.0, step=0.01)
        categoria = st.selectbox("Categoría", 
                               ['Compras', 'Supermercado', 'Servicios', 'Salidas', 
                                'Educación', 'Salud', 'Transporte', 'Otros'])
        persona = st.selectbox("Persona", ['Marcelo', 'Yenny'])
        descripcion = st.text_input("Descripción")
        tarjeta = st.selectbox("Tarjeta", ['BROU', 'Santander', 'OCA', 'Efectivo', 'Transferencia'])
        
        col1, col2 = st.columns(2)
        with col1:
            cuotas_totales = st.selectbox("Cuotas", [1, 2, 3, 6, 12], index=0)
        with col2:
            cuotas_pagadas = st.selectbox("Pagadas", list(range(0, 13)), index=0)
        
        submit = st.form_submit_button("💾 Guardar Gasto", type="primary")
        
        if submit:
            gasto = {
                'Fecha': fecha,
                'Monto': monto,
                'Categoria': categoria,
                'Persona': persona,
                'Descripcion': descripcion,
                'Tarjeta': tarjeta,
                'CuotasTotales': cuotas_totales,
                'CuotasPagadas': cuotas_pagadas,
                'MesesPagados': ''
            }
            
            if guardar_gasto(gasto):
                st.success("✅ Gasto guardado en Google Sheets!")
                st.rerun()

# Panel principal
st.header("📊 Gastos Registrados")

# Cargar y mostrar datos
df = cargar_datos()

if not df.empty:
    # Mostrar tabla
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Fecha": st.column_config.DatetimeColumn("📅 Fecha", format="DD/MM/YYYY"),
            "Monto": st.column_config.NumberColumn("💰 Monto", format="$%.2f"),
            "Categoría": "🏷️ Categoría",
            "Persona": "👤 Persona",
            "Descripción": "📝 Descripción",
            "Tarjeta": "💳 Tarjeta",
            "CuotasTotales": "📅 Cuotas Totales",
            "CuotasPagadas": "✅ Pagadas"
        }
    )
    
    # Estadísticas
    total = df['Monto'].sum()
    total_registros = len(df)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💵 Total Gastos", f"${total:,.2f}")
    with col2:
        st.metric("📋 Total Registros", total_registros)
    with col3:
        promedio = total / total_registros if total_registros > 0 else 0
        st.metric("📊 Promedio", f"${promedio:,.2f}")
    
    # Gastos por persona
    st.subheader("👥 Distribución por Persona")
    if 'Persona' in df.columns:
        por_persona = df.groupby('Persona')['Monto'].sum()
        
        col_per1, col_per2 = st.columns(2)
        with col_per1:
            if 'Marcelo' in por_persona:
                st.metric("Marcelo", f"${por_persona['Marcelo']:,.2f}")
        with col_per2:
            if 'Yenny' in por_persona:
                st.metric("Yenny", f"${por_persona['Yenny']:,.2f}")
        
        # Gráfico simple
        st.bar_chart(por_persona)
    
else:
    st.info("📭 No hay gastos registrados. ¡Agrega el primero en el formulario!")

# ===== SECCIÓN DE GESTIÓN =====
st.divider()
st.header("⚙️ Gestión de Gastos")

tab1, tab2, tab3 = st.tabs(["📤 Exportar", "✏️ Editar", "🗑️ Eliminar"])

with tab1:
    st.subheader("Exportar Datos")
    
    if not df.empty:
        # Exportar a CSV
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name=f"gastos_{date.today().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        # Exportar a Excel
        excel_buffer = df.to_excel(index=False, engine='openpyxl')
        st.download_button(
            label="📊 Descargar Excel",
            data=excel_buffer,
            file_name=f"gastos_{date.today().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    else:
        st.info("No hay datos para exportar")

with tab2:
    st.subheader("Editar Gasto")
    
    if not df.empty:
        # Selector de gasto a editar
        gasto_ids = list(range(1, len(df) + 1))
        gasto_seleccionado = st.selectbox("Seleccionar gasto por ID", gasto_ids)
        
        if gasto_seleccionado:
            idx = gasto_seleccionado - 1
            gasto_actual = df.iloc[idx]
            
            with st.form("form_editar"):
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    nueva_fecha = st.date_input("Fecha", value=gasto_actual['Fecha'].date())
                    nuevo_monto = st.number_input("Monto", value=float(gasto_actual['Monto']))
                    nueva_categoria = st.text_input("Categoría", value=str(gasto_actual['Categoría']))
                
                with col_f2:
                    nueva_persona = st.selectbox("Persona", ['Marcelo', 'Yenny'], 
                                                index=0 if str(gasto_actual['Persona']) == 'Marcelo' else 1)
                    nueva_desc = st.text_input("Descripción", value=str(gasto_actual['Descripción']))
                    nueva_tarjeta = st.text_input("Tarjeta", value=str(gasto_actual['Tarjeta']))
                
                if st.form_submit_button("💾 Actualizar Gasto"):
                    gasto_actualizado = {
                        'Fecha': nueva_fecha,
                        'Monto': nuevo_monto,
                        'Categoria': nueva_categoria,
                        'Persona': nueva_persona,
                        'Descripcion': nueva_desc,
                        'Tarjeta': nueva_tarjeta,
                        'CuotasTotales': int(gasto_actual['CuotasTotales']),
                        'CuotasPagadas': int(gasto_actual['CuotasPagadas']),
                        'MesesPagados': str(gasto_actual.get('MesesPagados', ''))
                    }
                    
                    if actualizar_gasto(idx, gasto_actualizado):
                        st.success("✅ Gasto actualizado!")
                        st.rerun()
    else:
        st.info("No hay gastos para editar")

with tab3:
    st.subheader("Eliminar Gasto")
    
    if not df.empty:
        gasto_a_eliminar = st.selectbox("Seleccionar gasto a eliminar", 
                                       list(range(1, len(df) + 1)))
        
        if st.button("🗑️ Eliminar Gasto Seleccionado", type="secondary"):
            if eliminar_gasto(gasto_a_eliminar - 1):
                st.success("✅ Gasto eliminado!")
                st.rerun()
    else:
        st.info("No hay gastos para eliminar")

# ===== PIE DE PÁGINA =====
st.divider()
st.caption(f"📅 Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
st.caption("💡 Los datos se guardan automáticamente en Google Sheets")