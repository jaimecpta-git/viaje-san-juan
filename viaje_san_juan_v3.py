import streamlit as st
import pandas as pd
from datetime import datetime, date
import json
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import gspread
from google.oauth2.service_account import Credentials

# Configuración de la página
st.set_page_config(
    page_title="Viaje San Juan de los Lagos dia Miercoles 01 abril 2026",
    page_icon="🚌",
    layout="wide"
)

# Configuración de tarifas
TARIFAS = {
    'transporte': 400,
    'habitacion_sencilla': 900,
    'habitacion_doble': 1150,
    'habitacion_triple': 1300
}

# ============================================
# CONEXIÓN A GOOGLE SHEETS
# ============================================
@st.cache_resource
def conectar_google_sheets():
    """Conecta a Google Sheets usando las credenciales de Streamlit Secrets."""
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    client = gspread.authorize(creds)
    return client

def obtener_hojas():
    """Obtiene las hojas de clientes y pagos."""
    client = conectar_google_sheets()
    spreadsheet = client.open("viaje_san_juan_data")
    hoja_clientes = spreadsheet.worksheet("clientes")
    hoja_pagos = spreadsheet.worksheet("pagos")
    return hoja_clientes, hoja_pagos

# ============================================
# FUNCIONES DE LECTURA/ESCRITURA EN GOOGLE SHEETS
# ============================================
def cargar_datos_sheets():
    """Carga todos los datos desde Google Sheets y los convierte al formato interno."""
    try:
        hoja_clientes, hoja_pagos = obtener_hojas()
        
        # Leer clientes
        registros_clientes = hoja_clientes.get_all_records()
        
        # Leer pagos
        registros_pagos = hoja_pagos.get_all_records()
        
        # Construir estructura de datos interna
        clientes = {}
        for row in registros_clientes:
            cid = str(row['cliente_id'])
            clientes[cid] = {
                'nombre': str(row.get('nombre', '')),
                'telefono': str(row.get('telefono', '')),
                'email': str(row.get('email', '')),
                'asientos': int(row.get('asientos', 0)),
                'habitaciones': {
                    'sencillas': int(row.get('hab_sencillas', 0)),
                    'dobles': int(row.get('hab_dobles', 0)),
                    'triples': int(row.get('hab_triples', 0)),
                },
                'total_a_pagar': float(row.get('total_a_pagar', 0)),
                'total_pagado': float(row.get('total_pagado', 0)),
                'saldo_pendiente': float(row.get('saldo_pendiente', 0)),
                'notas': str(row.get('notas', '')),
                'fecha_registro': str(row.get('fecha_registro', '')),
                'pagos': []
            }
        
        # Asignar pagos a cada cliente
        for pago_row in registros_pagos:
            cid = str(pago_row['cliente_id'])
            if cid in clientes:
                clientes[cid]['pagos'].append({
                    'fecha': str(pago_row.get('fecha', '')),
                    'monto': float(pago_row.get('monto', 0)),
                    'metodo': str(pago_row.get('metodo', '')),
                    'referencia': str(pago_row.get('referencia', '')),
                    'notas': str(pago_row.get('notas', '')),
                    'timestamp': str(pago_row.get('timestamp', ''))
                })
        
        return {'clientes': clientes, 'configuracion': TARIFAS, 'fecha_viaje': None}
    
    except Exception as e:
        st.error(f"❌ Error al conectar con Google Sheets: {e}")
        return {'clientes': {}, 'configuracion': TARIFAS, 'fecha_viaje': None}

def guardar_cliente_sheets(cliente_id, cliente):
    """Guarda o actualiza un cliente en Google Sheets."""
    hoja_clientes, _ = obtener_hojas()
    
    fila = [
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
    try:
        celda = hoja_clientes.find(cliente_id, in_column=1)
        # Actualizar fila existente
        rango = f"A{celda.row}:M{celda.row}"
        hoja_clientes.update(rango, [fila])
    except Exception:
        # Agregar nueva fila
        hoja_clientes.append_row(fila)

def eliminar_cliente_sheets(cliente_id):
    """Elimina un cliente y sus pagos de Google Sheets."""
    hoja_clientes, hoja_pagos = obtener_hojas()
    
    # Eliminar de hoja clientes
    try:
        celda = hoja_clientes.find(cliente_id, in_column=1)
        hoja_clientes.delete_rows(celda.row)
    except Exception:
        pass
    
    # Eliminar pagos del cliente
    try:
        registros_pagos = hoja_pagos.get_all_records()
        filas_a_eliminar = []
        for idx, pago in enumerate(registros_pagos, start=2):  # start=2 porque fila 1 son encabezados
            if str(pago['cliente_id']) == cliente_id:
                filas_a_eliminar.append(idx)
        
        # Eliminar de abajo hacia arriba para no alterar los índices
        for fila in sorted(filas_a_eliminar, reverse=True):
            hoja_pagos.delete_rows(fila)
    except Exception:
        pass

def agregar_pago_sheets(cliente_id, pago):
    """Agrega un pago a Google Sheets."""
    _, hoja_pagos = obtener_hojas()
    
    fila = [
        cliente_id,
        pago['fecha'],
        pago['monto'],
        pago['metodo'],
        pago['referencia'],
        pago['notas'],
        pago.get('timestamp', '')
    ]
    
    hoja_pagos.append_row(fila)

def eliminar_pago_sheets(cliente_id, indice_pago):
    """Elimina un pago específico de Google Sheets."""
    _, hoja_pagos = obtener_hojas()
    
    registros_pagos = hoja_pagos.get_all_records()
    contador = 0
    for idx, pago in enumerate(registros_pagos, start=2):
        if str(pago['cliente_id']) == cliente_id:
            if contador == indice_pago:
                hoja_pagos.delete_rows(idx)
                return
            contador += 1

def actualizar_totales_cliente(cliente_id, total_pagado, saldo_pendiente):
    """Actualiza solo los totales de pago de un cliente."""
    hoja_clientes, _ = obtener_hojas()
    
    try:
        celda = hoja_clientes.find(cliente_id, in_column=1)
        # Columnas J (total_pagado) y K (saldo_pendiente) = columnas 10 y 11
        hoja_clientes.update_cell(celda.row, 10, total_pagado)
        hoja_clientes.update_cell(celda.row, 11, saldo_pendiente)
    except Exception:
        pass

# ============================================
# INICIALIZAR DATOS
# ============================================
def recargar_datos():
    """Recarga datos desde Google Sheets al session_state."""
    st.session_state.datos = cargar_datos_sheets()

if 'datos' not in st.session_state:
    recargar_datos()

datos = st.session_state.datos

# Función para generar ID único
def generar_id():
    if not datos['clientes']:
        return "CLI001"
    ids_numericos = []
    for k in datos['clientes'].keys():
        try:
            ids_numericos.append(int(k[3:]))
        except ValueError:
            continue
    if not ids_numericos:
        return "CLI001"
    ultimo_id = max(ids_numericos)
    return f"CLI{str(ultimo_id + 1).zfill(3)}"

# Función para calcular total
def calcular_total(asientos, hab_sencillas, hab_dobles, hab_triples):
    total = (asientos * TARIFAS['transporte'] +
             hab_sencillas * TARIFAS['habitacion_sencilla'] +
             hab_dobles * TARIFAS['habitacion_doble'] +
             hab_triples * TARIFAS['habitacion_triple'])
    return total

# Función para generar PDF de kardex
def generar_kardex_pdf(cliente_id, cliente):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitulo_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c5aa0'),
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )
    
    normal_style = styles['Normal']
    
    story = []
    
    titulo = Paragraph("🚌 KARDEX DE CLIENTE", titulo_style)
    story.append(titulo)
    story.append(Spacer(1, 0.2*inch))
    
    subtitulo = Paragraph(f"Viaje San Juan de los Lagos dia Miercoles 01 abril 2026", subtitulo_style)
    story.append(subtitulo)
    story.append(Spacer(1, 0.1*inch))
    
    fecha_generacion = Paragraph(f"<i>Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</i>", normal_style)
    story.append(fecha_generacion)
    story.append(Spacer(1, 0.3*inch))
    
    # SECCIÓN 1: INFORMACIÓN GENERAL
    story.append(Paragraph("📋 INFORMACIÓN GENERAL", subtitulo_style))
    story.append(Spacer(1, 0.1*inch))
    
    info_data = [
        ['Campo', 'Información'],
        ['ID Cliente:', cliente_id],
        ['Nombre:', cliente['nombre']],
        ['Teléfono:', cliente['telefono']],
        ['Email:', cliente['email']],
        ['Fecha de Registro:', cliente['fecha_registro']]
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 0.3*inch))
    
    # SECCIÓN 2: RESERVAS Y COSTOS
    story.append(Paragraph("🎫 RESERVAS Y COSTOS", subtitulo_style))
    story.append(Spacer(1, 0.1*inch))
    
    reservas_data = [
        ['Concepto', 'Cantidad', 'Precio Unitario', 'Subtotal'],
        ['Asientos de Transporte', 
         str(cliente['asientos']), 
         f"${TARIFAS['transporte']:,.2f}", 
         f"${cliente['asientos'] * TARIFAS['transporte']:,.2f}"],
        ['Habitaciones Sencillas', 
         str(cliente['habitaciones']['sencillas']), 
         f"${TARIFAS['habitacion_sencilla']:,.2f}", 
         f"${cliente['habitaciones']['sencillas'] * TARIFAS['habitacion_sencilla']:,.2f}"],
        ['Habitaciones Dobles', 
         str(cliente['habitaciones']['dobles']), 
         f"${TARIFAS['habitacion_doble']:,.2f}", 
         f"${cliente['habitaciones']['dobles'] * TARIFAS['habitacion_doble']:,.2f}"],
        ['Habitaciones Triples', 
         str(cliente['habitaciones']['triples']), 
         f"${TARIFAS['habitacion_triple']:,.2f}", 
         f"${cliente['habitaciones']['triples'] * TARIFAS['habitacion_triple']:,.2f}"]
    ]
    
    reservas_table = Table(reservas_data, colWidths=[2.5*inch, 1*inch, 1.5*inch, 1.5*inch])
    reservas_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    
    story.append(reservas_table)
    story.append(Spacer(1, 0.3*inch))
    
    # SECCIÓN 3: ESTADO DE CUENTA
    story.append(Paragraph("💰 ESTADO DE CUENTA", subtitulo_style))
    story.append(Spacer(1, 0.1*inch))
    
    porcentaje_pagado = (cliente['total_pagado']/cliente['total_a_pagar']*100) if cliente['total_a_pagar'] > 0 else 0
    porcentaje_pendiente = (cliente['saldo_pendiente']/cliente['total_a_pagar']*100) if cliente['total_a_pagar'] > 0 else 0
    
    cuenta_data = [
        ['Concepto', 'Monto', 'Porcentaje'],
        ['Total a Pagar', f"${cliente['total_a_pagar']:,.2f}", '100%'],
        ['Total Pagado', f"${cliente['total_pagado']:,.2f}", f"{porcentaje_pagado:.1f}%"],
        ['Saldo Pendiente', f"${cliente['saldo_pendiente']:,.2f}", f"{porcentaje_pendiente:.1f}%"]
    ]
    
    cuenta_table = Table(cuenta_data, colWidths=[2.5*inch, 2*inch, 1.5*inch])
    cuenta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (0, 1), colors.lightblue),
        ('BACKGROUND', (0, 2), (0, 2), colors.lightgreen),
        ('BACKGROUND', (0, 3), (0, 3), colors.lightyellow),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    
    story.append(cuenta_table)
    story.append(Spacer(1, 0.3*inch))
    
    # SECCIÓN 4: HISTORIAL DE PAGOS
    if cliente['pagos']:
        story.append(Paragraph("📜 HISTORIAL DE PAGOS", subtitulo_style))
        story.append(Spacer(1, 0.1*inch))
        
        pagos_data = [['No.', 'Fecha', 'Monto', 'Método', 'Referencia', 'Saldo Restante']]
        
        saldo_acumulado = cliente['total_a_pagar']
        for i, pago in enumerate(cliente['pagos'], 1):
            saldo_acumulado -= pago['monto']
            pagos_data.append([
                str(i),
                pago['fecha'],
                f"${pago['monto']:,.2f}",
                pago['metodo'],
                pago['referencia'] or '-',
                f"${saldo_acumulado:,.2f}"
            ])
        
        pagos_table = Table(pagos_data, colWidths=[0.4*inch, 1*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch])
        pagos_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        story.append(pagos_table)
        story.append(Spacer(1, 0.2*inch))
    
    # Notas del cliente
    if cliente.get('notas'):
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph("📝 NOTAS DEL CLIENTE", subtitulo_style))
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph(cliente['notas'], normal_style))
    
    # Footer
    story.append(Spacer(1, 0.5*inch))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    story.append(Paragraph("_______________________________________________", footer_style))
    story.append(Paragraph("Sistema de Gestión de Viajes - Viaje San Juan de los Lagos dia Miercoles 01 abril 2026 ", footer_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# Función para generar Kardex de cliente en Excel
def generar_kardex_cliente(cliente_id, cliente):
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Hoja 1: Información General
        info_general = {
            'Campo': ['ID Cliente', 'Nombre', 'Teléfono', 'Email', 'Fecha de Registro'],
            'Valor': [
                cliente_id,
                cliente['nombre'],
                cliente['telefono'],
                cliente['email'],
                cliente['fecha_registro']
            ]
        }
        pd.DataFrame(info_general).to_excel(writer, sheet_name='Información General', index=False)
        
        # Hoja 2: Resumen de Reservas
        reservas = {
            'Concepto': ['Asientos de Transporte', 'Habitaciones Sencillas', 'Habitaciones Dobles', 'Habitaciones Triples'],
            'Cantidad': [
                cliente['asientos'],
                cliente['habitaciones']['sencillas'],
                cliente['habitaciones']['dobles'],
                cliente['habitaciones']['triples']
            ],
            'Precio Unitario': [
                f"${TARIFAS['transporte']:,.2f}",
                f"${TARIFAS['habitacion_sencilla']:,.2f}",
                f"${TARIFAS['habitacion_doble']:,.2f}",
                f"${TARIFAS['habitacion_triple']:,.2f}"
            ],
            'Subtotal': [
                f"${cliente['asientos'] * TARIFAS['transporte']:,.2f}",
                f"${cliente['habitaciones']['sencillas'] * TARIFAS['habitacion_sencilla']:,.2f}",
                f"${cliente['habitaciones']['dobles'] * TARIFAS['habitacion_doble']:,.2f}",
                f"${cliente['habitaciones']['triples'] * TARIFAS['habitacion_triple']:,.2f}"
            ]
        }
        pd.DataFrame(reservas).to_excel(writer, sheet_name='Reservas y Costos', index=False)
        
        # Hoja 3: Estado de Cuenta
        estado_cuenta = {
            'Concepto': ['Total a Pagar', 'Total Pagado', 'Saldo Pendiente'],
            'Monto': [
                f"${cliente['total_a_pagar']:,.2f}",
                f"${cliente['total_pagado']:,.2f}",
                f"${cliente['saldo_pendiente']:,.2f}"
            ],
            'Porcentaje': [
                '100%',
                f"{(cliente['total_pagado']/cliente['total_a_pagar']*100):.1f}%" if cliente['total_a_pagar'] > 0 else '0%',
                f"{(cliente['saldo_pendiente']/cliente['total_a_pagar']*100):.1f}%" if cliente['total_a_pagar'] > 0 else '0%'
            ]
        }
        pd.DataFrame(estado_cuenta).to_excel(writer, sheet_name='Estado de Cuenta', index=False)
        
        # Hoja 4: Historial de Pagos
        if cliente['pagos']:
            pagos_detalle = []
            saldo_acumulado = cliente['total_a_pagar']
            
            for i, pago in enumerate(cliente['pagos'], 1):
                saldo_acumulado -= pago['monto']
                pagos_detalle.append({
                    'No.': i,
                    'Fecha': pago['fecha'],
                    'Monto Pagado': f"${pago['monto']:,.2f}",
                    'Método': pago['metodo'],
                    'Referencia': pago['referencia'],
                    'Saldo Restante': f"${saldo_acumulado:,.2f}",
                    'Notas': pago['notas']
                })
            
            pd.DataFrame(pagos_detalle).to_excel(writer, sheet_name='Historial de Pagos', index=False)
        
        # Hoja 5: Notas del Cliente
        if cliente.get('notas'):
            notas_df = pd.DataFrame({
                'Notas del Cliente': [cliente['notas']]
            })
            notas_df.to_excel(writer, sheet_name='Notas', index=False)
    
    output.seek(0)
    return output

# ============================================
# INTERFAZ PRINCIPAL
# ============================================

# Título principal
st.title("🚌 Viaje San Juan de los Lagos dia Miercoles 01 abril 2026")
st.markdown("---")

# Botón para recargar datos desde Google Sheets
with st.sidebar:
    if st.button("🔄 Recargar datos", use_container_width=True):
        recargar_datos()
        st.success("✅ Datos actualizados")
        st.rerun()

# Menú lateral
menu = st.sidebar.selectbox(
    "📋 Menú Principal",
    ["🏠 Dashboard", "➕ Nuevo Cliente", "✏️ Editar/Eliminar Cliente", "💰 Registrar Pago", 
     "🗑️ Eliminar Pago", "👥 Ver Clientes", "📊 Reportes", "📄 Kardex Individual", "⚙️ Configuración"]
)

# ============================================
# DASHBOARD
# ============================================
if menu == "🏠 Dashboard":
    st.header("Panel de Control")
    
    if not datos['clientes']:
        st.info("👋 No hay clientes registrados aún. Comienza agregando uno en 'Nuevo Cliente'")
    else:
        col1, col2, col3, col4 = st.columns(4)
        
        total_clientes = len(datos['clientes'])
        total_asientos = sum(c['asientos'] for c in datos['clientes'].values())
        total_habitaciones = sum(
            c['habitaciones']['sencillas'] + 
            c['habitaciones']['dobles'] + 
            c['habitaciones']['triples'] 
            for c in datos['clientes'].values()
        )
        
        presupuesto_total = sum(c['total_a_pagar'] for c in datos['clientes'].values())
        total_recaudado = sum(c['total_pagado'] for c in datos['clientes'].values())
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
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("💵 Presupuesto Total", f"${presupuesto_total:,.2f}")
        with col2:
            st.metric("✅ Total Recaudado", f"${total_recaudado:,.2f}")
        with col3:
            st.metric("⏳ Saldo Pendiente", f"${saldo_pendiente:,.2f}")
        
        st.markdown("---")
        
        st.subheader("📊 Estado de Pagos por Cliente")
        
        clientes_list = []
        for cliente_id, cliente in datos['clientes'].items():
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
        
        st.markdown("---")
        st.subheader("⚠️ Clientes con Saldo Pendiente")
        
        pendientes = [c for c in clientes_list if '⏳' in c['Estado']]
        if pendientes:
            df_pendientes = pd.DataFrame(pendientes)
            st.dataframe(df_pendientes, use_container_width=True, hide_index=True)
        else:
            st.success("🎉 ¡Todos los clientes están liquidados!")

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
            asientos = st.number_input("🪑 Número de Asientos ($400)", min_value=0, value=1, step=1)
            st.markdown("**🏨 Habitaciones:**")
            hab_sencillas = st.number_input("Sencillas ($900)", min_value=0, value=0, step=1)
            hab_dobles = st.number_input("Dobles ($1,150)", min_value=0, value=0, step=1)
            hab_triples = st.number_input("Triples ($1,300)", min_value=0, value=0, step=1)
        
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
                cliente_id = generar_id()
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
                    'pagos': [],
                    'notas': notas,
                    'fecha_registro': datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                }
                
                # Guardar en Google Sheets
                with st.spinner("Guardando en Google Sheets..."):
                    guardar_cliente_sheets(cliente_id, nuevo_cliente)
                    datos['clientes'][cliente_id] = nuevo_cliente
                
                st.success(f"✅ Cliente {nombre} registrado exitosamente con ID: {cliente_id}")
                st.balloons()

# ============================================
# EDITAR/ELIMINAR CLIENTE
# ============================================
elif menu == "✏️ Editar/Eliminar Cliente":
    st.header("Editar o Eliminar Cliente")
    
    if not datos['clientes']:
        st.warning("⚠️ No hay clientes registrados.")
    else:
        clientes_opciones = {f"{cid} - {c['nombre']}": cid for cid, c in datos['clientes'].items()}
        cliente_seleccionado = st.selectbox("👤 Seleccionar Cliente", list(clientes_opciones.keys()))
        cliente_id = clientes_opciones[cliente_seleccionado]
        cliente = datos['clientes'][cliente_id]
        
        tab1, tab2 = st.tabs(["✏️ Editar Datos", "🗑️ Eliminar Cliente"])
        
        with tab1:
            st.subheader("Editar Información del Cliente")
            
            with st.form("form_editar_cliente"):
                col1, col2 = st.columns(2)
                
                with col1:
                    nuevo_nombre = st.text_input("👤 Nombre Completo", value=cliente['nombre'])
                    nuevo_telefono = st.text_input("📱 Teléfono", value=cliente['telefono'])
                    nuevo_email = st.text_input("📧 Email", value=cliente['email'])
                
                with col2:
                    nuevos_asientos = st.number_input("🪑 Número de Asientos", min_value=0, value=cliente['asientos'], step=1)
                    st.markdown("**🏨 Habitaciones:**")
                    nuevas_sencillas = st.number_input("Sencillas", min_value=0, value=cliente['habitaciones']['sencillas'], step=1)
                    nuevas_dobles = st.number_input("Dobles", min_value=0, value=cliente['habitaciones']['dobles'], step=1)
                    nuevas_triples = st.number_input("Triples", min_value=0, value=cliente['habitaciones']['triples'], step=1)
                
                nuevas_notas = st.text_area("📝 Notas", value=cliente.get('notas', ''))
                
                nuevo_total = calcular_total(nuevos_asientos, nuevas_sencillas, nuevas_dobles, nuevas_triples)
                st.info(f"💰 **Nuevo total a pagar: ${nuevo_total:,.2f}**")
                
                if nuevo_total != cliente['total_a_pagar']:
                    st.warning(f"⚠️ El total cambió de ${cliente['total_a_pagar']:,.2f} a ${nuevo_total:,.2f}")
                
                submitted_editar = st.form_submit_button("💾 Guardar Cambios", type="primary", use_container_width=True)
                
                if submitted_editar:
                    if not nuevo_nombre:
                        st.error("❌ El nombre es obligatorio")
                    elif nuevo_total == 0:
                        st.error("❌ Debe seleccionar al menos un asiento o una habitación")
                    else:
                        datos['clientes'][cliente_id]['nombre'] = nuevo_nombre
                        datos['clientes'][cliente_id]['telefono'] = nuevo_telefono
                        datos['clientes'][cliente_id]['email'] = nuevo_email
                        datos['clientes'][cliente_id]['asientos'] = nuevos_asientos
                        datos['clientes'][cliente_id]['habitaciones']['sencillas'] = nuevas_sencillas
                        datos['clientes'][cliente_id]['habitaciones']['dobles'] = nuevas_dobles
                        datos['clientes'][cliente_id]['habitaciones']['triples'] = nuevas_triples
                        datos['clientes'][cliente_id]['total_a_pagar'] = nuevo_total
                        datos['clientes'][cliente_id]['saldo_pendiente'] = nuevo_total - cliente['total_pagado']
                        datos['clientes'][cliente_id]['notas'] = nuevas_notas
                        
                        with st.spinner("Actualizando en Google Sheets..."):
                            guardar_cliente_sheets(cliente_id, datos['clientes'][cliente_id])
                        
                        st.success(f"✅ Cliente {nuevo_nombre} actualizado exitosamente")
                        st.rerun()
        
        with tab2:
            st.subheader("⚠️ Eliminar Cliente")
            
            st.warning(f"**¿Estás seguro de eliminar al cliente {cliente['nombre']}?**")
            st.write(f"- ID: {cliente_id}")
            st.write(f"- Total pagado: ${cliente['total_pagado']:,.2f}")
            st.write(f"- Saldo pendiente: ${cliente['saldo_pendiente']:,.2f}")
            st.write(f"- Pagos registrados: {len(cliente['pagos'])}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                confirmar = st.checkbox("✅ Sí, confirmo que quiero eliminar este cliente")
            
            with col2:
                if st.button("🗑️ ELIMINAR CLIENTE", type="secondary", disabled=not confirmar, use_container_width=True):
                    with st.spinner("Eliminando de Google Sheets..."):
                        eliminar_cliente_sheets(cliente_id)
                        del datos['clientes'][cliente_id]
                    st.success(f"✅ Cliente eliminado exitosamente")
                    st.rerun()

# ============================================
# REGISTRAR PAGO
# ============================================
elif menu == "💰 Registrar Pago":
    st.header("Registrar Pago/Abono")
    
    if not datos['clientes']:
        st.warning("⚠️ No hay clientes registrados. Primero agrega un cliente.")
    else:
        clientes_opciones = {f"{cid} - {c['nombre']} (Saldo: ${c['saldo_pendiente']:,.2f})": cid 
                            for cid, c in datos['clientes'].items() if c['saldo_pendiente'] > 0}
        
        if not clientes_opciones:
            st.success("🎉 ¡Todos los clientes están liquidados!")
        else:
            cliente_seleccionado = st.selectbox("👤 Seleccionar Cliente", list(clientes_opciones.keys()))
            cliente_id = clientes_opciones[cliente_seleccionado]
            cliente = datos['clientes'][cliente_id]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💵 Total a Pagar", f"${cliente['total_a_pagar']:,.2f}")
            with col2:
                st.metric("✅ Total Pagado", f"${cliente['total_pagado']:,.2f}")
            with col3:
                st.metric("⏳ Saldo Pendiente", f"${cliente['saldo_pendiente']:,.2f}")
            
            st.markdown("---")
            
            with st.form("form_pago"):
                col1, col2 = st.columns(2)
                
                with col1:
                    monto = st.number_input(
                        "💰 Monto del Pago", 
                        min_value=0.01, 
                        max_value=float(cliente['saldo_pendiente']),
                        value=float(cliente['saldo_pendiente']),
                        step=50.0
                    )
                    fecha_pago = st.date_input("📅 Fecha del Pago", value=date.today())
                
                with col2:
                    metodo_pago = st.selectbox(
                        "💳 Método de Pago",
                        ["Efectivo", "Transferencia", "Tarjeta Débito", "Tarjeta Crédito", "Depósito"]
                    )
                    referencia = st.text_input("🔢 Referencia/Folio", placeholder="Opcional")
                
                notas_pago = st.text_area("📝 Notas del pago", placeholder="Información adicional...")
                
                submitted_pago = st.form_submit_button("💾 Registrar Pago", type="primary", use_container_width=True)
                
                if submitted_pago:
                    pago = {
                        'fecha': fecha_pago.strftime("%d/%m/%Y"),
                        'monto': monto,
                        'metodo': metodo_pago,
                        'referencia': referencia,
                        'notas': notas_pago,
                        'timestamp': datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    }
                    
                    cliente['pagos'].append(pago)
                    cliente['total_pagado'] += monto
                    cliente['saldo_pendiente'] = cliente['total_a_pagar'] - cliente['total_pagado']
                    
                    with st.spinner("Guardando pago en Google Sheets..."):
                        agregar_pago_sheets(cliente_id, pago)
                        actualizar_totales_cliente(cliente_id, cliente['total_pagado'], cliente['saldo_pendiente'])
                    
                    st.success(f"✅ Pago de ${monto:,.2f} registrado exitosamente")
                    
                    if cliente['saldo_pendiente'] == 0:
                        st.balloons()
                        st.success(f"🎉 ¡{cliente['nombre']} ha liquidado completamente su viaje!")
                    else:
                        st.info(f"Saldo pendiente: ${cliente['saldo_pendiente']:,.2f}")
                    
                    st.rerun()

# ============================================
# ELIMINAR PAGO
# ============================================
elif menu == "🗑️ Eliminar Pago":
    st.header("Eliminar Pago Registrado")
    
    if not datos['clientes']:
        st.warning("⚠️ No hay clientes registrados.")
    else:
        clientes_con_pagos = {f"{cid} - {c['nombre']}": cid 
                             for cid, c in datos['clientes'].items() if len(c['pagos']) > 0}
        
        if not clientes_con_pagos:
            st.info("ℹ️ No hay pagos registrados para eliminar.")
        else:
            cliente_seleccionado = st.selectbox("👤 Seleccionar Cliente", list(clientes_con_pagos.keys()))
            cliente_id = clientes_con_pagos[cliente_seleccionado]
            cliente = datos['clientes'][cliente_id]
            
            st.subheader(f"Pagos de {cliente['nombre']}")
            
            for idx, pago in enumerate(cliente['pagos']):
                with st.expander(f"Pago #{idx+1} - ${pago['monto']:,.2f} - {pago['fecha']}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Fecha:** {pago['fecha']}")
                        st.write(f"**Monto:** ${pago['monto']:,.2f}")
                        st.write(f"**Método:** {pago['metodo']}")
                        st.write(f"**Referencia:** {pago['referencia']}")
                        st.write(f"**Notas:** {pago['notas']}")
                        if pago.get('timestamp'):
                            st.write(f"**Registrado:** {pago['timestamp']}")
                    
                    with col2:
                        if st.button(f"🗑️ Eliminar", key=f"del_pago_{idx}", type="secondary"):
                            monto_eliminado = pago['monto']
                            
                            with st.spinner("Eliminando pago de Google Sheets..."):
                                eliminar_pago_sheets(cliente_id, idx)
                            
                            cliente['pagos'].pop(idx)
                            cliente['total_pagado'] -= monto_eliminado
                            cliente['saldo_pendiente'] = cliente['total_a_pagar'] - cliente['total_pagado']
                            
                            with st.spinner("Actualizando totales..."):
                                actualizar_totales_cliente(cliente_id, cliente['total_pagado'], cliente['saldo_pendiente'])
                            
                            st.success(f"✅ Pago de ${monto_eliminado:,.2f} eliminado")
                            st.rerun()

# ============================================
# VER CLIENTES
# ============================================
elif menu == "👥 Ver Clientes":
    st.header("Lista de Clientes")
    
    if not datos['clientes']:
        st.info("👋 No hay clientes registrados aún.")
    else:
        col1, col2 = st.columns([3, 1])
        with col1:
            buscar = st.text_input("🔍 Buscar cliente", placeholder="Nombre, ID o teléfono...")
        with col2:
            filtro_estado = st.selectbox("Estado", ["Todos", "Liquidados", "Pendientes"])
        
        clientes_filtrados = datos['clientes'].copy()
        
        if buscar:
            clientes_filtrados = {
                k: v for k, v in clientes_filtrados.items()
                if buscar.lower() in v['nombre'].lower() or 
                   buscar.lower() in k.lower() or
                   buscar in v['telefono']
            }
        
        if filtro_estado == "Liquidados":
            clientes_filtrados = {k: v for k, v in clientes_filtrados.items() if v['saldo_pendiente'] == 0}
        elif filtro_estado == "Pendientes":
            clientes_filtrados = {k: v for k, v in clientes_filtrados.items() if v['saldo_pendiente'] > 0}
        
        st.markdown("---")
        
        for cliente_id, cliente in clientes_filtrados.items():
            with st.expander(f"**{cliente['nombre']}** - ID: {cliente_id} | Saldo: ${cliente['saldo_pendiente']:,.2f}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 📋 Información General")
                    st.write(f"**ID:** {cliente_id}")
                    st.write(f"**Nombre:** {cliente['nombre']}")
                    st.write(f"**Teléfono:** {cliente['telefono']}")
                    st.write(f"**Email:** {cliente['email']}")
                    st.write(f"**Fecha de registro:** {cliente['fecha_registro']}")
                    if cliente['notas']:
                        st.write(f"**Notas:** {cliente['notas']}")
                    
                    st.markdown("### 🪑 Reservas")
                    st.write(f"**Asientos:** {cliente['asientos']}")
                    st.write(f"**Habitaciones Sencillas:** {cliente['habitaciones']['sencillas']}")
                    st.write(f"**Habitaciones Dobles:** {cliente['habitaciones']['dobles']}")
                    st.write(f"**Habitaciones Triples:** {cliente['habitaciones']['triples']}")
                
                with col2:
                    st.markdown("### 💰 Estado Financiero")
                    st.metric("Total a Pagar", f"${cliente['total_a_pagar']:,.2f}")
                    st.metric("Total Pagado", f"${cliente['total_pagado']:,.2f}")
                    st.metric("Saldo Pendiente", f"${cliente['saldo_pendiente']:,.2f}")
                    
                    porcentaje = (cliente['total_pagado'] / cliente['total_a_pagar'] * 100) if cliente['total_a_pagar'] > 0 else 0
                    st.progress(porcentaje / 100, text=f"Pagado: {porcentaje:.1f}%")
                
                if cliente['pagos']:
                    st.markdown("### 📜 Historial de Pagos")
                    df_pagos = pd.DataFrame(cliente['pagos'])
                    df_pagos['monto'] = df_pagos['monto'].apply(lambda x: f"${x:,.2f}")
                    st.dataframe(df_pagos[['fecha', 'monto', 'metodo', 'referencia', 'notas']], 
                               use_container_width=True, hide_index=True)
                else:
                    st.info("Sin pagos registrados aún")

# ============================================
# REPORTES
# ============================================
elif menu == "📊 Reportes":
    st.header("Reportes y Estadísticas")
    
    if not datos['clientes']:
        st.info("👋 No hay datos para generar reportes.")
    else:
        tab1, tab2, tab3 = st.tabs(["📈 Resumen General", "💰 Financiero", "🎫 Ocupación"])
        
        with tab1:
            st.subheader("Resumen General del Viaje")
            
            total_clientes = len(datos['clientes'])
            total_asientos = sum(c['asientos'] for c in datos['clientes'].values())
            total_hab_sencillas = sum(c['habitaciones']['sencillas'] for c in datos['clientes'].values())
            total_hab_dobles = sum(c['habitaciones']['dobles'] for c in datos['clientes'].values())
            total_hab_triples = sum(c['habitaciones']['triples'] for c in datos['clientes'].values())
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("👥 Total Clientes", total_clientes)
                st.metric("🪑 Total Asientos", total_asientos)
            with col2:
                st.metric("🏨 Hab. Sencillas", total_hab_sencillas)
                st.metric("🏨 Hab. Dobles", total_hab_dobles)
            with col3:
                st.metric("🏨 Hab. Triples", total_hab_triples)
                total_habs = total_hab_sencillas + total_hab_dobles + total_hab_triples
                st.metric("🏨 Total Habitaciones", total_habs)
        
        with tab2:
            st.subheader("Reporte Financiero")
            
            presupuesto_total = sum(c['total_a_pagar'] for c in datos['clientes'].values())
            total_recaudado = sum(c['total_pagado'] for c in datos['clientes'].values())
            saldo_pendiente = presupuesto_total - total_recaudado
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💵 Presupuesto Total", f"${presupuesto_total:,.2f}")
            with col2:
                st.metric("✅ Total Recaudado", f"${total_recaudado:,.2f}")
            with col3:
                st.metric("⏳ Saldo Pendiente", f"${saldo_pendiente:,.2f}")
            
            st.markdown("---")
            st.subheader("💵 Desglose de Ingresos")
            
            total_asientos = sum(c['asientos'] for c in datos['clientes'].values())
            total_hab_sencillas = sum(c['habitaciones']['sencillas'] for c in datos['clientes'].values())
            total_hab_dobles = sum(c['habitaciones']['dobles'] for c in datos['clientes'].values())
            total_hab_triples = sum(c['habitaciones']['triples'] for c in datos['clientes'].values())
            
            ingresos_transporte = total_asientos * TARIFAS['transporte']
            ingresos_sencillas = total_hab_sencillas * TARIFAS['habitacion_sencilla']
            ingresos_dobles = total_hab_dobles * TARIFAS['habitacion_doble']
            ingresos_triples = total_hab_triples * TARIFAS['habitacion_triple']
            
            df_ingresos = pd.DataFrame({
                'Concepto': ['Transporte', 'Habitaciones Sencillas', 'Habitaciones Dobles', 'Habitaciones Triples', 'TOTAL'],
                'Cantidad': [total_asientos, total_hab_sencillas, total_hab_dobles, total_hab_triples, '-'],
                'Tarifa': [f"${TARIFAS['transporte']:,.2f}", 
                          f"${TARIFAS['habitacion_sencilla']:,.2f}",
                          f"${TARIFAS['habitacion_doble']:,.2f}",
                          f"${TARIFAS['habitacion_triple']:,.2f}",
                          '-'],
                'Total': [f"${ingresos_transporte:,.2f}",
                         f"${ingresos_sencillas:,.2f}",
                         f"${ingresos_dobles:,.2f}",
                         f"${ingresos_triples:,.2f}",
                         f"${presupuesto_total:,.2f}"]
            })
            
            st.dataframe(df_ingresos, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            if st.button("📥 Exportar Reporte Completo a Excel"):
                output = BytesIO()
                
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    clientes_export = []
                    for cid, c in datos['clientes'].items():
                        clientes_export.append({
                            'ID': cid,
                            'Nombre': c['nombre'],
                            'Teléfono': c['telefono'],
                            'Email': c['email'],
                            'Asientos': c['asientos'],
                            'Hab. Sencillas': c['habitaciones']['sencillas'],
                            'Hab. Dobles': c['habitaciones']['dobles'],
                            'Hab. Triples': c['habitaciones']['triples'],
                            'Total a Pagar': c['total_a_pagar'],
                            'Total Pagado': c['total_pagado'],
                            'Saldo Pendiente': c['saldo_pendiente'],
                            'Fecha Registro': c['fecha_registro']
                        })
                    pd.DataFrame(clientes_export).to_excel(writer, sheet_name='Clientes', index=False)
                    
                    pagos_export = []
                    for cid, c in datos['clientes'].items():
                        for pago in c['pagos']:
                            pagos_export.append({
                                'Cliente ID': cid,
                                'Cliente': c['nombre'],
                                'Fecha': pago['fecha'],
                                'Monto': pago['monto'],
                                'Método': pago['metodo'],
                                'Referencia': pago['referencia'],
                                'Notas': pago['notas'],
                                'Timestamp': pago.get('timestamp', '')
                            })
                    if pagos_export:
                        pd.DataFrame(pagos_export).to_excel(writer, sheet_name='Pagos', index=False)
                    
                    df_ingresos.to_excel(writer, sheet_name='Resumen Financiero', index=False)
                
                output.seek(0)
                
                st.download_button(
                    label="⬇️ Descargar Reporte Excel",
                    data=output,
                    file_name=f"reporte_viaje_san_juan_{datetime.now().strftime('%d-%m-%Y')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.success("✅ Reporte generado exitosamente")
        
        with tab3:
            st.subheader("🎫 Ocupación y Disponibilidad")
            
            st.info("📌 Esta sección te permitirá establecer capacidades máximas y ver disponibilidad")
            
            total_asientos = sum(c['asientos'] for c in datos['clientes'].values())
            total_hab_sencillas = sum(c['habitaciones']['sencillas'] for c in datos['clientes'].values())
            total_hab_dobles = sum(c['habitaciones']['dobles'] for c in datos['clientes'].values())
            total_hab_triples = sum(c['habitaciones']['triples'] for c in datos['clientes'].values())
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 🚌 Transporte")
                capacidad_bus = st.number_input("Capacidad del autobús", value=50, min_value=1)
                ocupados = total_asientos
                disponibles = capacidad_bus - ocupados
                st.metric("Asientos Ocupados", ocupados)
                st.metric("Asientos Disponibles", disponibles)
                st.progress(ocupados / capacidad_bus if capacidad_bus > 0 else 0, 
                          text=f"Ocupación: {(ocupados/capacidad_bus*100):.1f}%")
            
            with col2:
                st.markdown("### 🏨 Habitaciones")
                st.write(f"**Sencillas:** {total_hab_sencillas}")
                st.write(f"**Dobles:** {total_hab_dobles}")
                st.write(f"**Triples:** {total_hab_triples}")
                st.write(f"**Total:** {total_hab_sencillas + total_hab_dobles + total_hab_triples}")

# ============================================
# KARDEX INDIVIDUAL
# ============================================
elif menu == "📄 Kardex Individual":
    st.header("Kardex Individual por Cliente")
    st.write("Genera un reporte completo en Excel con toda la información de un cliente específico")
    
    if not datos['clientes']:
        st.warning("⚠️ No hay clientes registrados.")
    else:
        clientes_opciones = {f"{cid} - {c['nombre']}": cid for cid, c in datos['clientes'].items()}
        cliente_seleccionado = st.selectbox("👤 Seleccionar Cliente para Kardex", list(clientes_opciones.keys()))
        cliente_id = clientes_opciones[cliente_seleccionado]
        cliente = datos['clientes'][cliente_id]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("💵 Total a Pagar", f"${cliente['total_a_pagar']:,.2f}")
        with col2:
            st.metric("✅ Total Pagado", f"${cliente['total_pagado']:,.2f}")
        with col3:
            st.metric("⏳ Saldo Pendiente", f"${cliente['saldo_pendiente']:,.2f}")
        
        st.markdown("---")
        
        st.subheader("📋 Contenido del Kardex")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**✅ El Kardex incluye:**")
            st.write("• Información general del cliente")
            st.write("• Detalle de reservas (asientos y habitaciones)")
            st.write("• Costos por concepto")
            st.write("• Estado de cuenta completo")
            st.write("• Historial de pagos con saldo acumulado")
            st.write("• Notas del cliente")
        
        with col2:
            st.markdown("**📄 Formatos disponibles:**")
            st.write("🔹 **PDF** - Un documento profesional para compartir")
            st.write("🔹 **Excel** - 5 hojas con datos para editar")
            st.write("🔹 **Ambos** - Genera PDF y Excel al mismo tiempo")
        
        st.markdown("---")
        
        st.subheader("📥 Generar Kardex")
        
        formato = st.radio(
            "Selecciona el formato a generar:",
            ["📄 Solo PDF", "📊 Solo Excel", "📄📊 PDF y Excel"],
            horizontal=True
        )
        
        col1, col2, col3 = st.columns(3)
        
        if formato == "📄 Solo PDF":
            with col2:
                if st.button("📥 Generar PDF", type="primary", use_container_width=True):
                    with st.spinner("Generando PDF..."):
                        kardex_pdf = generar_kardex_pdf(cliente_id, cliente)
                        
                        st.download_button(
                            label="⬇️ Descargar Kardex PDF",
                            data=kardex_pdf,
                            file_name=f"kardex_{cliente_id}_{cliente['nombre'].replace(' ', '_')}_{datetime.now().strftime('%d-%m-%Y')}.pdf",
                            mime="application/pdf"
                        )
                        st.success(f"✅ Kardex PDF de {cliente['nombre']} generado exitosamente")
        
        elif formato == "📊 Solo Excel":
            with col2:
                if st.button("📥 Generar Excel", type="primary", use_container_width=True):
                    with st.spinner("Generando Excel..."):
                        kardex_excel = generar_kardex_cliente(cliente_id, cliente)
                        
                        st.download_button(
                            label="⬇️ Descargar Kardex Excel",
                            data=kardex_excel,
                            file_name=f"kardex_{cliente_id}_{cliente['nombre'].replace(' ', '_')}_{datetime.now().strftime('%d-%m-%Y')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        st.success(f"✅ Kardex Excel de {cliente['nombre']} generado exitosamente")
        
        else:
            with col2:
                if st.button("📥 Generar Ambos Formatos", type="primary", use_container_width=True):
                    with st.spinner("Generando PDF y Excel..."):
                        kardex_pdf = generar_kardex_pdf(cliente_id, cliente)
                        kardex_excel = generar_kardex_cliente(cliente_id, cliente)
                        
                        col_a, col_b = st.columns(2)
                        
                        with col_a:
                            st.download_button(
                                label="⬇️ Descargar PDF",
                                data=kardex_pdf,
                                file_name=f"kardex_{cliente_id}_{cliente['nombre'].replace(' ', '_')}_{datetime.now().strftime('%d-%m-%Y')}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                        
                        with col_b:
                            st.download_button(
                                label="⬇️ Descargar Excel",
                                data=kardex_excel,
                                file_name=f"kardex_{cliente_id}_{cliente['nombre'].replace(' ', '_')}_{datetime.now().strftime('%d-%m-%Y')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                        
                        st.success(f"✅ Kardex de {cliente['nombre']} generado en ambos formatos exitosamente")
        
        st.markdown("---")
        st.info("💡 **Tip:** El PDF es ideal para enviar por WhatsApp o email. El Excel te permite editar o imprimir con formato personalizado.")

# ============================================
# CONFIGURACIÓN
# ============================================
elif menu == "⚙️ Configuración":
    st.header("Configuración del Sistema")
    
    st.info("💡 Las tarifas se configuran directamente en el código. Para cambiarlas, modifica los valores en la sección TARIFAS del archivo.")
    
    st.subheader("📋 Tarifas Actuales")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Transporte por persona:** ${TARIFAS['transporte']:,.2f}")
        st.write(f"**Habitación Sencilla:** ${TARIFAS['habitacion_sencilla']:,.2f}")
    with col2:
        st.write(f"**Habitación Doble:** ${TARIFAS['habitacion_doble']:,.2f}")
        st.write(f"**Habitación Triple:** ${TARIFAS['habitacion_triple']:,.2f}")
    
    st.markdown("---")
    st.subheader("🔗 Estado de Conexión")
    
    try:
        client = conectar_google_sheets()
        spreadsheet = client.open("viaje_san_juan_data")
        st.success(f"✅ Conectado a Google Sheets: **{spreadsheet.title}**")
        st.write(f"📄 URL: {spreadsheet.url}")
        
        hojas = spreadsheet.worksheets()
        for hoja in hojas:
            st.write(f"  - Hoja: **{hoja.title}** ({hoja.row_count} filas)")
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
    
    st.markdown("---")
    st.subheader("📥 Respaldar Datos")
    
    if st.button("📥 Descargar Respaldo JSON", use_container_width=True):
        backup_data = json.dumps(datos, indent=2, ensure_ascii=False)
        st.download_button(
            label="⬇️ Descargar Respaldo",
            data=backup_data,
            file_name=f"backup_viaje_{datetime.now().strftime('%d-%m-%Y_%H%M%S')}.json",
            mime="application/json"
        )

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
    🚌 Sistema de Gestión de Viajes | Desarrollado para viaje a Viaje San Juan de los Lagos dia Miercoles 01 abril 2026
    <br><small>📡 Conectado a Google Sheets</small>
    </div>
    """,
    unsafe_allow_html=True
)
