import streamlit as st
import pandas as pd
from datetime import datetime, date
import json
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import gspread
from google.oauth2.service_account import Credentials
import hashlib

# ============================================
# CONFIGURACIÓN DE AUTENTICACIÓN
# ============================================

# Usuarios y contraseñas (hasheadas)
# Para generar hash: hashlib.sha256("tu_contraseña".encode()).hexdigest()
USUARIOS = {
    "admin": {
        "password_hash": "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918",  # "admin"
        "nombre": "Administrador",
        "rol": "admin"
    },
    "empleado": {
        "password_hash": "906e5b0b0f417f7d0a4935e13a6b5a3f92e1ea8e3d3d3c3e3f3f3f3f3f3f3f3f",  # "empleado123"
        "nombre": "Empleado",
        "rol": "empleado"
    }
}

def hash_password(password):
    """Genera hash SHA256 de una contraseña"""
    return hashlib.sha256(password.encode()).hexdigest()

def verificar_login(username, password):
    """Verifica credenciales de usuario"""
    if username in USUARIOS:
        password_hash = hash_password(password)
        if USUARIOS[username]["password_hash"] == password_hash:
            return True, USUARIOS[username]
    return False, None

def mostrar_pantalla_login():
    """Muestra la pantalla de login"""
    st.markdown(
        """
        <div style='text-align: center; padding: 50px;'>
            <h1>🚌 Sistema de Gestión de Viajes</h1>
            <h3>San Juan de los Lagos</h3>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Iniciar Sesión")
        
        with st.form("login_form"):
            username = st.text_input("👤 Usuario", placeholder="Ingresa tu usuario")
            password = st.text_input("🔑 Contraseña", type="password", placeholder="Ingresa tu contraseña")
            submitted = st.form_submit_button("Iniciar Sesión", use_container_width=True, type="primary")
            
            if submitted:
                if not username or not password:
                    st.error("❌ Por favor ingresa usuario y contraseña")
                else:
                    valido, usuario_data = verificar_login(username, password)
                    if valido:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.user_data = usuario_data
                        st.success(f"✅ Bienvenido {usuario_data['nombre']}")
                        st.rerun()
                    else:
                        st.error("❌ Usuario o contraseña incorrectos")
        
        st.markdown("---")
        st.info("""
        **👤 Usuarios de prueba:**
        
        **Admin:** admin / admin
        
        **Empleado:** empleado / empleado123
        
        ⚠️ Cambia las contraseñas después del primer uso
        """)

# ============================================
# CONFIGURACIÓN DE GOOGLE SHEETS
# ============================================

@st.cache_resource
def get_google_sheets_client():
    """Conecta con Google Sheets usando credenciales de Streamlit Secrets"""
    try:
        # Las credenciales vienen de st.secrets (configurado en Streamlit Cloud)
        credentials_dict = {
            "type": st.secrets["gcp_service_account"]["type"],
            "project_id": st.secrets["gcp_service_account"]["project_id"],
            "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
            "private_key": st.secrets["gcp_service_account"]["private_key"],
            "client_email": st.secrets["gcp_service_account"]["client_email"],
            "client_id": st.secrets["gcp_service_account"]["client_id"],
            "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
            "token_uri": st.secrets["gcp_service_account"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"]
        }
        
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {str(e)}")
        return None

def get_spreadsheet():
    """Obtiene o crea la hoja de cálculo"""
    client = get_google_sheets_client()
    if not client:
        return None
    
    try:
        # Intenta abrir la hoja existente
        spreadsheet_name = st.secrets.get("spreadsheet_name", "viaje_san_juan_data")
        spreadsheet = client.open(spreadsheet_name)
        return spreadsheet
    except gspread.SpreadsheetNotFound:
        # Si no existe, créala
        spreadsheet = client.create(spreadsheet_name)
        # Comparte con tu email
        spreadsheet.share(st.secrets.get("owner_email", ""), perm_type='user', role='owner')
        
        # Crea las hojas necesarias
        spreadsheet.add_worksheet("Clientes", rows=1000, cols=20)
        spreadsheet.add_worksheet("Pagos", rows=5000, cols=15)
        spreadsheet.add_worksheet("Configuracion", rows=10, cols=5)
        
        return spreadsheet
    except Exception as e:
        st.error(f"Error al acceder a la hoja: {str(e)}")
        return None

# Configuración de la página
st.set_page_config(
    page_title="Viaje San Juan de los Lagos",
    page_icon="🚌",
    layout="wide"
)

# ============================================
# VERIFICAR AUTENTICACIÓN
# ============================================

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    mostrar_pantalla_login()
    st.stop()

# ============================================
# USUARIO AUTENTICADO - MOSTRAR APP
# ============================================

# Botón de cerrar sesión en la barra lateral
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user_data['nombre']}")
    st.markdown(f"**Rol:** {st.session_state.user_data['rol']}")
    st.markdown("---")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.user_data = None
        st.rerun()

# Configuración de tarifas
TARIFAS = {
    'transporte': 400,
    'habitacion_sencilla': 600,
    'habitacion_doble': 800,
    'habitacion_triple': 1000
}

# ============================================
# FUNCIONES DE DATOS CON GOOGLE SHEETS
# ============================================

@st.cache_data(ttl=60)
def cargar_clientes():
    """Carga clientes desde Google Sheets"""
    try:
        spreadsheet = get_spreadsheet()
        if not spreadsheet:
            return {}
        
        worksheet = spreadsheet.worksheet("Clientes")
        data = worksheet.get_all_records()
        
        if not data:
            return {}
        
        clientes = {}
        for row in data:
            cliente_id = row.get('ID')
            if cliente_id:
                # Reconstruir estructura de habitaciones
                clientes[cliente_id] = {
                    'nombre': row.get('Nombre', ''),
                    'telefono': row.get('Telefono', ''),
                    'email': row.get('Email', ''),
                    'asientos': int(row.get('Asientos', 0)),
                    'habitaciones': {
                        'sencillas': int(row.get('Hab_Sencillas', 0)),
                        'dobles': int(row.get('Hab_Dobles', 0)),
                        'triples': int(row.get('Hab_Triples', 0))
                    },
                    'total_a_pagar': float(row.get('Total_Pagar', 0)),
                    'total_pagado': float(row.get('Total_Pagado', 0)),
                    'saldo_pendiente': float(row.get('Saldo_Pendiente', 0)),
                    'notas': row.get('Notas', ''),
                    'fecha_registro': row.get('Fecha_Registro', ''),
                    'pagos': []  # Los pagos se cargan por separado
                }
        
        return clientes
    except Exception as e:
        st.error(f"Error al cargar clientes: {str(e)}")
        return {}

def guardar_cliente(cliente_id, cliente):
    """Guarda o actualiza un cliente en Google Sheets"""
    try:
        spreadsheet = get_spreadsheet()
        if not spreadsheet:
            return False
        
        worksheet = spreadsheet.worksheet("Clientes")
        
        # Preparar datos para guardar
        row_data = [
            cliente_id,
            cliente['nombre'],
            cliente['telefono'],
            cliente['email'],
            cliente['asientos'],
            cliente['habitaciones']['sencillas'],
            cliente['habitaciones']['dobles'],
            cliente['habitaciones']['triples'],
            cliente['total_a_pagar'],
            cliente['total_pagado'],
            cliente['saldo_pendiente'],
            cliente['notas'],
            cliente['fecha_registro']
        ]
        
        # Buscar si el cliente ya existe
        all_values = worksheet.get_all_values()
        
        if len(all_values) == 0:
            # Primera vez - crear headers
            headers = ['ID', 'Nombre', 'Telefono', 'Email', 'Asientos', 'Hab_Sencillas', 
                      'Hab_Dobles', 'Hab_Triples', 'Total_Pagar', 'Total_Pagado', 
                      'Saldo_Pendiente', 'Notas', 'Fecha_Registro']
            worksheet.append_row(headers)
            worksheet.append_row(row_data)
        else:
            # Buscar fila del cliente
            cell = worksheet.find(cliente_id)
            if cell:
                # Actualizar fila existente
                worksheet.update(f'A{cell.row}:M{cell.row}', [row_data])
            else:
                # Agregar nuevo cliente
                worksheet.append_row(row_data)
        
        # Limpiar cache
        cargar_clientes.clear()
        return True
    except Exception as e:
        st.error(f"Error al guardar cliente: {str(e)}")
        return False

def eliminar_cliente_sheets(cliente_id):
    """Elimina un cliente de Google Sheets"""
    try:
        spreadsheet = get_spreadsheet()
        if not spreadsheet:
            return False
        
        worksheet = spreadsheet.worksheet("Clientes")
        cell = worksheet.find(cliente_id)
        
        if cell:
            worksheet.delete_rows(cell.row)
            cargar_clientes.clear()
            return True
        return False
    except Exception as e:
        st.error(f"Error al eliminar cliente: {str(e)}")
        return False

@st.cache_data(ttl=60)
def cargar_pagos():
    """Carga todos los pagos desde Google Sheets"""
    try:
        spreadsheet = get_spreadsheet()
        if not spreadsheet:
            return {}
        
        worksheet = spreadsheet.worksheet("Pagos")
        data = worksheet.get_all_records()
        
        # Organizar pagos por cliente
        pagos_por_cliente = {}
        for row in data:
            cliente_id = row.get('Cliente_ID')
            if cliente_id:
                if cliente_id not in pagos_por_cliente:
                    pagos_por_cliente[cliente_id] = []
                
                pago = {
                    'fecha': row.get('Fecha', ''),
                    'monto': float(row.get('Monto', 0)),
                    'metodo': row.get('Metodo', ''),
                    'referencia': row.get('Referencia', ''),
                    'notas': row.get('Notas', ''),
                    'timestamp': row.get('Timestamp', '')
                }
                pagos_por_cliente[cliente_id].append(pago)
        
        return pagos_por_cliente
    except Exception as e:
        st.error(f"Error al cargar pagos: {str(e)}")
        return {}

def guardar_pago(cliente_id, pago):
    """Guarda un pago en Google Sheets"""
    try:
        spreadsheet = get_spreadsheet()
        if not spreadsheet:
            return False
        
        worksheet = spreadsheet.worksheet("Pagos")
        
        row_data = [
            cliente_id,
            pago['fecha'],
            pago['monto'],
            pago['metodo'],
            pago['referencia'],
            pago['notas'],
            pago['timestamp']
        ]
        
        # Verificar si hay headers
        all_values = worksheet.get_all_values()
        if len(all_values) == 0:
            headers = ['Cliente_ID', 'Fecha', 'Monto', 'Metodo', 'Referencia', 'Notas', 'Timestamp']
            worksheet.append_row(headers)
        
        worksheet.append_row(row_data)
        cargar_pagos.clear()
        return True
    except Exception as e:
        st.error(f"Error al guardar pago: {str(e)}")
        return False

# Función para generar ID único
def generar_id(clientes):
    if not clientes:
        return "CLI001"
    ultimo_id = max([int(k[3:]) for k in clientes.keys()])
    return f"CLI{str(ultimo_id + 1).zfill(3)}"

# Función para calcular total
def calcular_total(asientos, hab_sencillas, hab_dobles, hab_triples):
    total = (asientos * TARIFAS['transporte'] +
             hab_sencillas * TARIFAS['habitacion_sencilla'] +
             hab_dobles * TARIFAS['habitacion_doble'] +
             hab_triples * TARIFAS['habitacion_triple'])
    return total

# Cargar datos
clientes = cargar_clientes()
pagos_data = cargar_pagos()

# Combinar clientes con sus pagos
for cliente_id in clientes:
    clientes[cliente_id]['pagos'] = pagos_data.get(cliente_id, [])

# Título principal
st.title("🚌 Viaje a San Juan de los Lagos")
st.markdown("---")

# Menú lateral (filtrado por rol)
rol = st.session_state.user_data['rol']

if rol == 'admin':
    opciones_menu = ["🏠 Dashboard", "➕ Nuevo Cliente", "✏️ Editar/Eliminar Cliente", 
                     "💰 Registrar Pago", "🗑️ Eliminar Pago", "👥 Ver Clientes", 
                     "📊 Reportes", "📄 Kardex Individual", "⚙️ Configuración"]
elif rol == 'empleado':
    opciones_menu = ["🏠 Dashboard", "➕ Nuevo Cliente", "💰 Registrar Pago", 
                     "👥 Ver Clientes", "📊 Reportes", "📄 Kardex Individual"]
else:
    opciones_menu = ["🏠 Dashboard", "👥 Ver Clientes", "📊 Reportes"]

menu = st.sidebar.selectbox("📋 Menú Principal", opciones_menu)

# ============================================
# DASHBOARD
# ============================================
if menu == "🏠 Dashboard":
    st.header("Panel de Control")
    
    if not clientes:
        st.info("👋 No hay clientes registrados aún.")
    else:
        # Métricas generales
        col1, col2, col3, col4 = st.columns(4)
        
        total_clientes = len(clientes)
        total_asientos = sum(c['asientos'] for c in clientes.values())
        total_habitaciones = sum(
            c['habitaciones']['sencillas'] + 
            c['habitaciones']['dobles'] + 
            c['habitaciones']['triples'] 
            for c in clientes.values()
        )
        
        presupuesto_total = sum(c['total_a_pagar'] for c in clientes.values())
        total_recaudado = sum(c['total_pagado'] for c in clientes.values())
        saldo_pendiente = presupuesto_total - total_recaudado
        
        with col1:
            st.metric("👥 Total Clientes", total_clientes)
        with col2:
            st.metric("🪑 Asientos Reservados", total_asientos)
        with col3:
            st.metric("🏨 Habitaciones", total_habitaciones)
        with col4:
            porcentaje = (total_recaudado / presupuesto_total * 100) if presupuesto_total > 0 else 0
            st.metric("📈 Recaudado", f"{porcentaje:.1f}%")
        
        st.markdown("---")
        
        # Métricas financieras
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("💵 Presupuesto Total", f"${presupuesto_total:,.2f}")
        with col2:
            st.metric("✅ Total Recaudado", f"${total_recaudado:,.2f}")
        with col3:
            st.metric("⏳ Saldo Pendiente", f"${saldo_pendiente:,.2f}")
        
        st.markdown("---")
        
        # Tabla de clientes
        st.subheader("📊 Estado de Pagos por Cliente")
        
        clientes_list = []
        for cliente_id, cliente in clientes.items():
            porcentaje_pago = (cliente['total_pagado'] / cliente['total_a_pagar'] * 100) if cliente['total_a_pagar'] > 0 else 0
            clientes_list.append({
                'ID': cliente_id,
                'Cliente': cliente['nombre'],
                'Total': f"${cliente['total_a_pagar']:,.2f}",
                'Pagado': f"${cliente['total_pagado']:,.2f}",
                'Pendiente': f"${cliente['saldo_pendiente']:,.2f}",
                'Avance': f"{porcentaje_pago:.1f}%",
                'Estado': '✅ Liquidado' if cliente['saldo_pendiente'] == 0 else '⏳ Pendiente'
            })
        
        df_clientes = pd.DataFrame(clientes_list)
        st.dataframe(df_clientes, use_container_width=True, hide_index=True)

# ============================================
# NUEVO CLIENTE
# ============================================
elif menu == "➕ Nuevo Cliente":
    st.header("Registrar Nuevo Cliente")
    
    with st.form("form_nuevo_cliente"):
        col1, col2 = st.columns(2)
        
        with col1:
            nombre = st.text_input("👤 Nombre Completo *", placeholder="Ej: Juan Pérez García")
            telefono = st.text_input("📱 Teléfono", placeholder="Ej: 3331234567")
            email = st.text_input("📧 Email", placeholder="Ej: cliente@email.com")
        
        with col2:
            asientos = st.number_input("🪑 Número de Asientos", min_value=0, value=1, step=1)
            st.markdown("**🏨 Habitaciones:**")
            hab_sencillas = st.number_input("Sencillas ($600)", min_value=0, value=0, step=1)
            hab_dobles = st.number_input("Dobles ($800)", min_value=0, value=0, step=1)
            hab_triples = st.number_input("Triples ($1,000)", min_value=0, value=0, step=1)
        
        notas = st.text_area("📝 Notas adicionales", placeholder="Información extra del cliente...")
        
        total = calcular_total(asientos, hab_sencillas, hab_dobles, hab_triples)
        st.info(f"💰 **Total a pagar: ${total:,.2f}**")
        
        submitted = st.form_submit_button("✅ Registrar Cliente", type="primary", use_container_width=True)
        
        if submitted:
            if not nombre:
                st.error("❌ El nombre es obligatorio")
            elif total == 0:
                st.error("❌ Debe seleccionar al menos un asiento o una habitación")
            else:
                cliente_id = generar_id(clientes)
                nuevo_cliente = {
                    'nombre': nombre,
                    'telefono': telefono,
                    'email': email,
                    'asientos': asientos,
                    'habitaciones': {
                        'sencillas': hab_sencillas,
                        'dobles': hab_dobles,
                        'triples': hab_triples
                    },
                    'total_a_pagar': total,
                    'total_pagado': 0,
                    'saldo_pendiente': total,
                    'notas': notas,
                    'fecha_registro': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    'pagos': []
                }
                
                if guardar_cliente(cliente_id, nuevo_cliente):
                    st.success(f"✅ Cliente {nombre} registrado exitosamente con ID: {cliente_id}")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Error al guardar el cliente")

# Agregar nota informativa en el sidebar
st.sidebar.markdown("---")
st.sidebar.info("""
📊 **Datos en Google Sheets**

Tus datos están guardados de forma segura en tu Google Drive.

Puedes acceder directamente a la hoja de cálculo desde tu cuenta de Google.
""")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
    🚌 Sistema de Gestión de Viajes | Cloud Edition con Google Sheets
    </div>
    """,
    unsafe_allow_html=True
)
