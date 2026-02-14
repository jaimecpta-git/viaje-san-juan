import streamlit as st
import pandas as pd
from datetime import datetime, date
import json
import os
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# Configuración de la página
st.set_page_config(
    page_title="Viaje San Juan de los Lagos dia Miercoles 01 abril 2026",
    page_icon="🚌",
    layout="wide"
)

# Archivo para guardar datos
DATA_FILE = "viaje_data.json"

# Configuración de tarifas
TARIFAS = {
    'transporte': 400,
    'habitacion_sencilla': 600,
    'habitacion_doble': 800,
    'habitacion_triple': 1000
}

# Inicializar datos
def inicializar_datos():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'clientes': {},
        'configuracion': TARIFAS,
        'fecha_viaje': None
    }

# Guardar datos
def guardar_datos(datos):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)

# Cargar datos
if 'datos' not in st.session_state:
    st.session_state.datos = inicializar_datos()

datos = st.session_state.datos

# Función para generar ID único
def generar_id():
    if not datos['clientes']:
        return "CLI001"
    ultimo_id = max([int(k[3:]) for k in datos['clientes'].keys()])
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
    
    # Estilos
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
    
    # Contenido del documento
    story = []
    
    # Título principal
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
    
    # Construir PDF
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
        df_reservas = pd.DataFrame(reservas)
        df_reservas.to_excel(writer, sheet_name='Reservas y Costos', index=False)
        
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

# Título principal
st.title("🚌 Viaje San Juan de los Lagos dia Miercoles 01 abril 2026")
st.markdown("---")

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
        # Métricas generales
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
        
        # Métricas financieras
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("💵 Presupuesto Total", f"${presupuesto_total:,.2f}")
        with col2:
            st.metric("✅ Total Recaudado", f"${total_recaudado:,.2f}")
        with col3:
            st.metric("⏳ Saldo Pendiente", f"${saldo_pendiente:,.2f}")
        
        st.markdown("---")
        
        # Progreso de pagos
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
        
        # Clientes con saldo pendiente
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
            hab_sencillas = st.number_input("Sencillas ($600)", min_value=0, value=0, step=1)
            hab_dobles = st.number_input("Dobles ($800)", min_value=0, value=0, step=1)
            hab_triples = st.number_input("Triples ($1,000)", min_value=0, value=0, step=1)
        
        notas = st.text_area("📝 Notas adicionales", placeholder="Información extra del cliente...")
        
        # Calcular total
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
                datos['clientes'][cliente_id] = {
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
                guardar_datos(datos)
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
        # Selector de cliente
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
                
                # Calcular nuevo total
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
                        # Actualizar datos
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
                        
                        guardar_datos(datos)
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
                    del datos['clientes'][cliente_id]
                    guardar_datos(datos)
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
        # Selector de cliente
        clientes_opciones = {f"{cid} - {c['nombre']} (Saldo: ${c['saldo_pendiente']:,.2f})": cid 
                            for cid, c in datos['clientes'].items() if c['saldo_pendiente'] > 0}
        
        if not clientes_opciones:
            st.success("🎉 ¡Todos los clientes están liquidados!")
        else:
            cliente_seleccionado = st.selectbox("👤 Seleccionar Cliente", list(clientes_opciones.keys()))
            cliente_id = clientes_opciones[cliente_seleccionado]
            cliente = datos['clientes'][cliente_id]
            
            # Mostrar información del cliente
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💵 Total a Pagar", f"${cliente['total_a_pagar']:,.2f}")
            with col2:
                st.metric("✅ Total Pagado", f"${cliente['total_pagado']:,.2f}")
            with col3:
                st.metric("⏳ Saldo Pendiente", f"${cliente['saldo_pendiente']:,.2f}")
            
            st.markdown("---")
            
            # Formulario de pago
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
                    # Registrar el pago
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
                    
                    guardar_datos(datos)
                    
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
        # Filtrar clientes que tienen pagos
        clientes_con_pagos = {f"{cid} - {c['nombre']}": cid 
                             for cid, c in datos['clientes'].items() if len(c['pagos']) > 0}
        
        if not clientes_con_pagos:
            st.info("ℹ️ No hay pagos registrados para eliminar.")
        else:
            cliente_seleccionado = st.selectbox("👤 Seleccionar Cliente", list(clientes_con_pagos.keys()))
            cliente_id = clientes_con_pagos[cliente_seleccionado]
            cliente = datos['clientes'][cliente_id]
            
            st.subheader(f"Pagos de {cliente['nombre']}")
            
            # Mostrar pagos
            for idx, pago in enumerate(cliente['pagos']):
                with st.expander(f"Pago #{idx+1} - ${pago['monto']:,.2f} - {pago['fecha']}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Fecha:** {pago['fecha']}")
                        st.write(f"**Monto:** ${pago['monto']:,.2f}")
                        st.write(f"**Método:** {pago['metodo']}")
                        st.write(f"**Referencia:** {pago['referencia']}")
                        st.write(f"**Notas:** {pago['notas']}")
                        st.write(f"**Registrado:** {pago['timestamp']}")
                    
                    with col2:
                        if st.button(f"🗑️ Eliminar", key=f"del_pago_{idx}", type="secondary"):
                            # Eliminar pago
                            monto_eliminado = pago['monto']
                            cliente['pagos'].pop(idx)
                            cliente['total_pagado'] -= monto_eliminado
                            cliente['saldo_pendiente'] = cliente['total_a_pagar'] - cliente['total_pagado']
                            
                            guardar_datos(datos)
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
        # Filtros
        col1, col2 = st.columns([3, 1])
        with col1:
            buscar = st.text_input("🔍 Buscar cliente", placeholder="Nombre, ID o teléfono...")
        with col2:
            filtro_estado = st.selectbox("Estado", ["Todos", "Liquidados", "Pendientes"])
        
        # Filtrar clientes
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
        
        # Mostrar clientes
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
                    
                    # Barra de progreso
                    porcentaje = (cliente['total_pagado'] / cliente['total_a_pagar'] * 100) if cliente['total_a_pagar'] > 0 else 0
                    st.progress(porcentaje / 100, text=f"Pagado: {porcentaje:.1f}%")
                
                # Historial de pagos
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
            
            # Preparar datos
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
            
            # Desglose de ingresos
            st.markdown("---")
            st.subheader("💵 Desglose de Ingresos")
            
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
            
            # Exportar a Excel
            st.markdown("---")
            if st.button("📥 Exportar Reporte Completo a Excel"):
                output = BytesIO()
                
                # Crear Excel con múltiples hojas
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # Hoja 1: Clientes
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
                    
                    # Hoja 2: Pagos
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
                                'Timestamp': pago['timestamp']
                            })
                    if pagos_export:
                        pd.DataFrame(pagos_export).to_excel(writer, sheet_name='Pagos', index=False)
                    
                    # Hoja 3: Resumen
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
        # Selector de cliente
        clientes_opciones = {f"{cid} - {c['nombre']}": cid for cid, c in datos['clientes'].items()}
        cliente_seleccionado = st.selectbox("👤 Seleccionar Cliente para Kardex", list(clientes_opciones.keys()))
        cliente_id = clientes_opciones[cliente_seleccionado]
        cliente = datos['clientes'][cliente_id]
        
        # Vista previa del cliente
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("💵 Total a Pagar", f"${cliente['total_a_pagar']:,.2f}")
        with col2:
            st.metric("✅ Total Pagado", f"${cliente['total_pagado']:,.2f}")
        with col3:
            st.metric("⏳ Saldo Pendiente", f"${cliente['saldo_pendiente']:,.2f}")
        
        st.markdown("---")
        
        # Información que se incluirá en el Kardex
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
        
        # Selector de formato
        st.subheader("📥 Generar Kardex")
        
        formato = st.radio(
            "Selecciona el formato a generar:",
            ["📄 Solo PDF", "📊 Solo Excel", "📄📊 PDF y Excel"],
            horizontal=True
        )
        
        col1, col2, col3 = st.columns(3)
        
        # Botones según el formato seleccionado
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
        
        else:  # PDF y Excel
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
        
        # Información adicional
        st.markdown("---")
        st.info("💡 **Tip:** El PDF es ideal para enviar por WhatsApp o email. El Excel te permite editar o imprimir con formato personalizado.")

# ============================================
# CONFIGURACIÓN
# ============================================
elif menu == "⚙️ Configuración":
    st.header("Configuración del Sistema")
    
    with st.form("form_config"):
        st.subheader("💵 Tarifas")
        
        col1, col2 = st.columns(2)
        
        with col1:
            tarifa_transporte = st.number_input(
                "Transporte por persona", 
                value=float(TARIFAS['transporte']),
                min_value=0.0,
                step=50.0
            )
            tarifa_sencilla = st.number_input(
                "Habitación Sencilla", 
                value=float(TARIFAS['habitacion_sencilla']),
                min_value=0.0,
                step=50.0
            )
        
        with col2:
            tarifa_doble = st.number_input(
                "Habitación Doble", 
                value=float(TARIFAS['habitacion_doble']),
                min_value=0.0,
                step=50.0
            )
            tarifa_triple = st.number_input(
                "Habitación Triple", 
                value=float(TARIFAS['habitacion_triple']),
                min_value=0.0,
                step=50.0
            )
        
        st.markdown("---")
        st.subheader("📅 Información del Viaje")
        
        fecha_viaje = st.date_input("Fecha del Viaje", value=date.today())
        
        submitted_config = st.form_submit_button("💾 Guardar Configuración", type="primary")
        
        if submitted_config:
            TARIFAS['transporte'] = tarifa_transporte
            TARIFAS['habitacion_sencilla'] = tarifa_sencilla
            TARIFAS['habitacion_doble'] = tarifa_doble
            TARIFAS['habitacion_triple'] = tarifa_triple
            
            datos['configuracion'] = TARIFAS
            datos['fecha_viaje'] = fecha_viaje.strftime("%d/%m/%Y")
            
            guardar_datos(datos)
            st.success("✅ Configuración guardada exitosamente")
    
    st.markdown("---")
    st.subheader("🗑️ Zona de Peligro")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Reiniciar Datos", type="secondary", use_container_width=True):
            if st.checkbox("⚠️ Confirmo que quiero borrar TODOS los datos"):
                datos['clientes'] = {}
                guardar_datos(datos)
                st.success("✅ Datos reiniciados")
                st.rerun()
    
    with col2:
        if st.button("📥 Respaldar Datos", use_container_width=True):
            backup_filename = f"backup_viaje_{datetime.now().strftime('%d-%m-%Y_%H%M%S')}.json"
            with open(backup_filename, 'w', encoding='utf-8') as f:
                json.dump(datos, f, indent=2, ensure_ascii=False)
            
            with open(backup_filename, 'rb') as f:
                st.download_button(
                    label="⬇️ Descargar Respaldo",
                    data=f,
                    file_name=backup_filename,
                    mime="application/json"
                )

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
    🚌 Sistema de Gestión de Viajes | Desarrollado para viaje a Viaje San Juan de los Lagos dia Miercoles 01 abril 2026
    </div>
    """,
    unsafe_allow_html=True
)
