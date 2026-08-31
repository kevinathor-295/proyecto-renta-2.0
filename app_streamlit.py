import streamlit as st
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from motor.calculadora import calcular_declaracion, topes_obligacion_declarar
from motor.reglas_2026 import UVT_2026
from modelos.contribuyente import (
    guardar_declaracion, cargar_declaracion,
    CAMPOS_DATOS_PERSONALES, CAMPOS_DECLARACION,
)

st.set_page_config(page_title="Simulador Tributario", page_icon="🧾", layout="wide")

CAMPOS_NO_MONEDA = {"num_dependientes", "num_declaracion"}
CAMPOS_MONEDA_DECLARACION = [c for c in CAMPOS_DECLARACION if c not in CAMPOS_NO_MONEDA]

# ----------------------------------------------------------------------
# Utilidades de Persistencia y Formato
# ----------------------------------------------------------------------
# Streamlit borra los widgets al cambiar de sección. Para evitar que 
# los cálculos den cero, guardamos todo en un diccionario "maestro" persistente.
if "datos" not in st.session_state:
    st.session_state.datos = {
        "perfil_empleo": True,
        "perfil_honorarios": False,
        "num_dependientes": 0,
        "num_declaracion": "Primera vez"
    }

def guardar_todo():
    """Copia el valor de los widgets visibles al diccionario maestro."""
    for k, v in st.session_state.items():
        if k.endswith("_widget"):
            real_k = k.replace("_widget", "")
            st.session_state.datos[real_k] = v

def formatear_pesos(valor) -> str:
    v_str = str(valor).split('.')[0] # Ignorar decimales si llega un float
    solo_digitos = "".join(c for c in v_str if c.isdigit())
    if not solo_digitos:
        return ""
    solo_digitos = solo_digitos.lstrip("0") or "0"
    return f"{int(solo_digitos):,}".replace(",", ".")

def obtener(campo_key, default=0.0):
    """Obtiene el valor del diccionario maestro."""
    return st.session_state.datos.get(campo_key, default)

def valor_numerico(campo_key) -> float:
    """Extrae el valor numérico del diccionario maestro para hacer cálculos."""
    texto = st.session_state.datos.get(campo_key, "")
    solo_digitos = "".join(c for c in str(texto) if c.isdigit())
    return float(solo_digitos) if solo_digitos else 0.0

# ----------------------------------------------------------------------
# Wrappers (Envoltorios) para campos en pantalla
# ----------------------------------------------------------------------
def campo_moneda(label, campo_key, ayuda="", valor_defecto=0):
    w_key = f"{campo_key}_widget"
    if w_key not in st.session_state:
        val = st.session_state.datos.get(campo_key, valor_defecto)
        st.session_state[w_key] = formatear_pesos(val) if val else ""
    else:
        st.session_state[w_key] = formatear_pesos(st.session_state[w_key])
    st.text_input(f"{label} ($)", key=w_key, placeholder="0", help=ayuda or None)

def campo_texto(label, campo_key, ayuda=""):
    w_key = f"{campo_key}_widget"
    if w_key not in st.session_state:
        st.session_state[w_key] = st.session_state.datos.get(campo_key, "")
    st.text_input(label, key=w_key, help=ayuda or None)

def campo_selectbox(label, opciones, campo_key, ayuda=""):
    w_key = f"{campo_key}_widget"
    if w_key not in st.session_state:
        st.session_state[w_key] = st.session_state.datos.get(campo_key, opciones[0])
    st.selectbox(label, opciones, key=w_key, help=ayuda or None)

def campo_numero(label, min_v, max_v, campo_key, ayuda=""):
    w_key = f"{campo_key}_widget"
    if w_key not in st.session_state:
        st.session_state[w_key] = st.session_state.datos.get(campo_key, min_v)
    st.number_input(label, min_value=min_v, max_value=max_v, step=1, key=w_key, help=ayuda or None)

def campo_checkbox(label, campo_key, default=False, ayuda=""):
    w_key = f"{campo_key}_widget"
    if w_key not in st.session_state:
        st.session_state[w_key] = st.session_state.datos.get(campo_key, default)
    st.checkbox(label, key=w_key, help=ayuda or None, on_change=guardar_todo)

# ----------------------------------------------------------------------
# Generación del PDF de resultados
# ----------------------------------------------------------------------
def generar_pdf_resultado(r, datos_personales) -> BytesIO:
    """Arma un PDF con el mismo desglose que se muestra en pantalla."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Resumen Tributario Estimado", styles["Title"]))
    story.append(Paragraph("Generado con Declaración Simple — no reemplaza tu declaración oficial", styles["Italic"]))
    story.append(Spacer(1, 0.4 * cm))

    nombre = datos_personales.get("dp_nombre") or "(sin nombre)"
    doc_ident = datos_personales.get("dp_num_doc") or "(sin documento)"
    story.append(Paragraph(f"<b>Contribuyente:</b> {nombre}", styles["Normal"]))
    story.append(Paragraph(f"<b>Documento:</b> {doc_ident}", styles["Normal"]))
    story.append(Paragraph(f"<b>UVT utilizada:</b> $ {r['uvt']:,.0f}", styles["Normal"]))
    story.append(Spacer(1, 0.4 * cm))

    def tabla(titulo, filas):
        story.append(Paragraph(titulo, styles["Heading3"]))
        data = [["Concepto", "Valor"]] + filas
        t = Table(data, colWidths=[11 * cm, 5 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F4F8")]),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.35 * cm))

    p = r["patrimonio"]
    tabla("1. Patrimonio Líquido", [
        ["Activos", f"$ {p['total_activos']:,.0f}"],
        ["Pasivos", f"$ {p['total_pasivos']:,.0f}"],
        ["Patrimonio líquido", f"$ {p['patrimonio_liquido']:,.0f}"],
    ])

    ing = r["ingresos"]
    tabla("2. Depuración de Ingresos", [
        ["Ingresos brutos", f"$ {ing['ingresos_brutos']:,.0f}"],
        ["(-) Aportes salud/pensión", f"$ {ing['incr']:,.0f}"],
        ["(-) Costos y gastos del negocio (Art. 107)", f"$ {ing['costos_gastos_deducibles']:,.0f}"],
        ["= Ingreso neto", f"$ {ing['renta_neta']:,.0f}"],
    ])

    d = r["deducciones"]
    tabla("3. Deducciones y Rentas Exentas (tope 40% / 1.340 UVT)", [
        ["Dependientes, 10% ingreso (Art. 387)", f"$ {d['dependientes_10pct']:,.0f}"],
        ["Medicina prepagada (Art. 387)", f"$ {d['prepagada_deducible']:,.0f}"],
        ["Intereses de vivienda (Art. 119)", f"$ {d['intereses_deducibles']:,.0f}"],
        ["50% del 4x1000 (Art. 115)", f"$ {d['gmf_deducible']:,.0f}"],
        ["1% facturas electrónicas (Art. 336-5)", f"$ {d['facturas_deducible']:,.0f}"],
        ["AFC + pensión voluntaria (Art. 126-1/126-4)", f"$ {d['afc_pension_aceptado']:,.0f}"],
        ["25% renta exenta laboral (Art. 206-10)", f"$ {d['exenta_25']:,.0f}"],
        ["Aceptado (tras tope del 40%/1.340 UVT)", f"$ {d['aceptado']:,.0f}"],
        ["Deducción adicional dependientes, 72 UVT c/u (fuera del tope)", f"$ {d['dependientes_extra_72uvt']:,.0f}"],
    ])

    story.append(Paragraph(f"<b>Renta Líquida Gravable: $ {r['renta_liquida_gravable']:,.0f}</b>", styles["Heading2"]))
    story.append(Spacer(1, 0.3 * cm))

    imp = r["impuesto"]
    tabla("5. Impuesto de Renta (Art. 241 E.T.)", [
        ["Impuesto calculado", f"$ {imp['impuesto_pesos']:,.0f}"],
        ["Descuento por donaciones (Art. 257)", f"$ {imp['descuento_donaciones']:,.0f}"],
        ["Impuesto neto de renta", f"$ {imp['impuesto_neto_final']:,.0f}"],
    ])

    a = r["anticipo"]
    tabla("6. Anticipo y Retenciones (Art. 807 E.T.)", [
        ["Retenciones en la fuente", f"$ {a['retenciones']:,.0f}"],
        ["Anticipo pagado el año anterior", f"$ {a['anticipo_anterior']:,.0f}"],
        ["Anticipo calculado para el próximo año", f"$ {a['anticipo_a_pagar']:,.0f}"],
    ])

    etiqueta_total = "TOTAL ESTIMADO A PAGAR" if r["total_a_pagar"] >= 0 else "TOTAL ESTIMADO A FAVOR"
    story.append(Paragraph(f"<b>{etiqueta_total}: $ {abs(r['total_a_pagar']):,.0f}</b>", styles["Heading1"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "Cálculo estimado con fines educativos, basado en el Estatuto Tributario vigente. "
        "No reemplaza tu declaración oficial ni el software autorizado por la DIAN.",
        styles["Italic"],
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer


# ----------------------------------------------------------------------
# Navegación
# ----------------------------------------------------------------------
SECCIONES = [
    "0. Perfil", "1. Datos Personales", "2. Configuración", "3. Activos", "4. Pasivos",
    "5. Ingresos", "6. Deducciones", "7. Rentas Exentas",
    "8. Anticipo y Retenciones", "9. Topes y Obligación", "10. Resultados",
]

st.sidebar.title("📋 Declaración Simple")
seccion = st.sidebar.radio("Ir a:", SECCIONES, label_visibility="collapsed")
st.title(seccion)

# ----------------------------------------------------------------------
# 0. Perfil
# ----------------------------------------------------------------------
if seccion == "0. Perfil":
    st.write("Cuéntanos brevemente tu situación. Así solo te mostramos las preguntas que te aplican.")
    campo_checkbox("Tuve empleo (recibí salario)", "perfil_empleo", default=True)
    campo_checkbox("Tuve honorarios o un negocio propio (trabajo independiente)", "perfil_honorarios", default=False)
    
    if not obtener("perfil_empleo", True) and not obtener("perfil_honorarios", False):
        st.warning("Si no tuviste ninguno de los dos, es probable que no necesites declarar renta — revisa la pantalla '9. Topes y Obligación' para confirmarlo.")
    st.caption("Puedes cambiar esto en cualquier momento; los campos de Ingresos y Deducciones se ajustan solos.")

# ----------------------------------------------------------------------
# 1. Datos Personales
# ----------------------------------------------------------------------
elif seccion == "1. Datos Personales":
    st.caption("Estos datos no afectan el cálculo del impuesto; se usarán más adelante para diligenciar tu Formulario 210.")
    with st.form("form_datos_personales"):
        campo_texto("Nombres y apellidos", "dp_nombre")
        campo_selectbox("Tipo de documento", ["Cédula de ciudadanía", "Cédula de extranjería", "Pasaporte", "NIT"], "dp_tipo_doc")
        campo_texto("Número de documento", "dp_num_doc")
        campo_texto("Ciudad", "dp_ciudad")
        campo_texto("Dirección", "dp_direccion")
        campo_texto("Correo electrónico", "dp_correo")
        guardado = st.form_submit_button("💾 Guardar esta sección", on_click=guardar_todo)
    if guardado:
        st.success("Guardado.")

# ----------------------------------------------------------------------
# 2. Configuración
# ----------------------------------------------------------------------
elif seccion == "2. Configuración":
    st.caption("Ajusta acá el valor de la UVT del año que quieras simular.")
    with st.form("form_configuracion"):
        campo_moneda(
            "Valor de la UVT", "uvt",
            ayuda="La UVT es una medida que usa la DIAN para no tener que "
            "escribir cifras en pesos en cada ley (Art. 868 E.T.). Sube cada "
            "año con el IPC. Para 2026 vale $52.374 (Resolución DIAN 000238 "
            "de 2025). Si dejas el campo vacío, se usa ese valor.",
            valor_defecto=UVT_2026,
        )
        guardado = st.form_submit_button("💾 Guardar esta sección", on_click=guardar_todo)
    if guardado:
        st.success("Guardado.")

# ----------------------------------------------------------------------
# 3. Activos
# ----------------------------------------------------------------------
elif seccion == "3. Activos":
    st.subheader("Tus Activos (Lo que tienes)")
    with st.form("form_activos"):
        campo_moneda("Casas, aptos o lotes", "casa",
                     "Lo que te costó tu casa, apto o lote cuando lo "
                     "compraste (o el avalúo catastral, si es mayor) — Art. "
                     "267 E.T. No restes nada todavía; las deudas van en la "
                     "pantalla de Pasivos.")
        campo_moneda("Dinero en bancos", "bancos",
                     "Lo que tenías en tus cuentas de ahorro, corriente o "
                     "CDT, exactamente el 31 de diciembre (Art. 261 E.T.). "
                     "No es lo que ganaste en el año, es lo que había "
                     "guardado ese día.")
        campo_moneda("Carros o motos", "vehiculos",
                     "El valor de compra de tus vehículos, sin restar el "
                     "desgaste (Art. 267 E.T.). Es el precio de cuando lo "
                     "compraste, no lo que vale hoy.")
        guardado = st.form_submit_button("💾 Guardar esta sección", on_click=guardar_todo)
    if guardado:
        st.success("Guardado.")

# ----------------------------------------------------------------------
# 4. Pasivos
# ----------------------------------------------------------------------
elif seccion == "4. Pasivos":
    st.subheader("Tus Pasivos (Lo que debes)")
    with st.form("form_pasivos"):
        campo_moneda("Deudas con bancos", "deudas_bancos",
                     "Lo que te falta por pagar de tus créditos con bancos, "
                     "al 31 de diciembre (Art. 283 E.T.). Solo lo que aún "
                     "debes.")
        campo_moneda("Deudas con terceros", "deudas_terceros",
                     "Deudas con personas o empresas que no son un banco. "
                     "Para que cuenten necesitas un papel que las respalde "
                     "—pagaré, contrato, etc.— (Art. 770 E.T.). Sin eso la "
                     "DIAN no las reconoce.")
        guardado = st.form_submit_button("💾 Guardar esta sección", on_click=guardar_todo)
    if guardado:
        st.success("Guardado.")

# ----------------------------------------------------------------------
# 5. Ingresos
# ----------------------------------------------------------------------
elif seccion == "5. Ingresos":
    st.subheader("Tus Ingresos del Año")
    tiene_empleo = obtener("perfil_empleo", True)
    tiene_negocio = obtener("perfil_honorarios", False)

    if not tiene_empleo and not tiene_negocio:
        st.info("Ve a la pantalla '0. Perfil' y marca si tuviste empleo o negocio propio, para ver los campos correspondientes aquí.")
    else:
        with st.form("form_ingresos"):
            if tiene_empleo:
                campo_moneda("Salarios y prestaciones", "salarios",
                             "Todo lo que recibiste por tu trabajo en el "
                             "año: sueldo, primas, bonos, auxilios (Art. "
                             "103 E.T.). Ponlo completo, sin restar nada "
                             "todavía.")
            if tiene_negocio:
                campo_moneda("Honorarios (Independiente)", "honorarios",
                             "Lo que facturaste en el año trabajando de "
                             "forma independiente —freelance, contratos "
                             "por servicios, negocio propio— (Art. 103 "
                             "E.T.). También va completo; los gastos del "
                             "negocio se restan en la siguiente pantalla, "
                             "Deducciones.")
            guardado = st.form_submit_button("💾 Guardar esta sección", on_click=guardar_todo)
        if guardado:
            st.success("Guardado.")

# ----------------------------------------------------------------------
# 6. Deducciones
# ----------------------------------------------------------------------
elif seccion == "6. Deducciones":
    st.subheader("Deducciones (Bajan tu impuesto)")
    st.caption("Con la cantidad de dependientes que escribas, el simulador ya "
               "calcula automáticamente los DOS beneficios que existen por eso.")
    with st.form("form_deducciones"):
        campo_moneda("Salud y Pensión obligatoria", "salud_pension",
                     "Lo que pagaste en el año, de forma obligatoria, a "
                     "salud y pensión. La ley no lo cuenta como ingreso "
                     "tuyo, así que se resta de tu base antes de calcular "
                     "el impuesto (Art. 55 y 56 E.T.).")
        
        campo_numero("Cantidad de dependientes (0 a 4)", 0, 4, "num_dependientes",
                     ayuda="Cuántas personas dependen de ti económicamente —hijos, "
                     "pareja, papás, etc.—, hasta 4. Con este número el simulador "
                     "calcula dos beneficios: el 10% de tus ingresos laborales, "
                     "tope 384 UVT al año (Art. 387 E.T.), y además 72 UVT fijas "
                     "por cada uno, hasta 4 (Art. 387, adicionado por la Ley 2277 "
                     "de 2022). No necesitas guardar facturas para esto.")
        
        campo_moneda("Medicina prepagada", "prepagada",
                     "Lo que pagaste en el año por medicina prepagada o "
                     "pólizas de salud, para ti o tu familia. Puedes "
                     "descontar hasta 192 UVT al año (Art. 387 E.T.); si "
                     "pagaste más, el simulador solo toma el tope.")
        campo_moneda("Intereses de vivienda", "intereses",
                     "Los intereses que pagaste en el año por tu crédito "
                     "hipotecario o leasing de vivienda (Art. 119 E.T.). "
                     "El tope es 1.200 UVT al año.")
        campo_moneda("4x1000 pagado (GMF)", "gmf",
                     "Es el 4x1000 que te cobra el banco por movimientos y "
                     "retiros. Puedes descontar la mitad de lo que pagaste "
                     "en el año (Art. 115 E.T.), con el certificado del "
                     "banco. Escribe el total pagado; el simulador calcula "
                     "el 50%.")
        campo_moneda("Compras con factura electrónica", "compras_facturadas",
                     "Suma tus compras del año que tengan factura "
                     "electrónica, personales o del negocio (Art. 336, "
                     "numeral 5, E.T.). Puedes descontar el 1% de ese "
                     "total, hasta 240 UVT al año.")
        if obtener("perfil_honorarios", False):
            campo_moneda("Costos y gastos del negocio", "costos_gastos",
                         "Los gastos necesarios para generar tus "
                         "honorarios: arriendo del local, insumos, "
                         "servicios, empleados, etc. (Art. 107 E.T.). Se "
                         "restan directamente de tus honorarios, SIN el "
                         "tope del 40%. Nota: si usas este campo, ese "
                         "ingreso ya no puede tomar además la exención del "
                         "25% del Art. 206 —el simulador aplica ese 25% "
                         "solo a tus salarios—.")
        guardado = st.form_submit_button("💾 Guardar esta sección", on_click=guardar_todo)
    if guardado:
        st.success("Guardado.")

# ----------------------------------------------------------------------
# 7. Rentas Exentas
# ----------------------------------------------------------------------
elif seccion == "7. Rentas Exentas":
    st.subheader("Rentas Exentas y Beneficios")
    with st.form("form_exentas"):
        campo_moneda("Aportes Cuentas AFC", "afc",
                     "Ahorros en una cuenta AFC (Ahorro para el Fomento a "
                     "la Construcción). Si los dejas quietos varios años, "
                     "no pagan impuesto (Art. 126-4 E.T.). Junto con tus "
                     "pensiones voluntarias, el tope conjunto es 30% de "
                     "tus ingresos o 3.800 UVT, lo que sea menor.")
        campo_moneda("Pensiones voluntarias", "pensiones_vol",
                     "Aportes extra que hiciste a tu fondo de pensión, "
                     "además de los obligatorios. También quedan libres de "
                     "impuesto (Art. 126-1 E.T.), con el mismo tope "
                     "conjunto que las cuentas AFC.")
        campo_moneda("Donaciones (descuento tributario)", "donaciones",
                     "Donaciones a fundaciones o entidades sin ánimo de "
                     "lucro autorizadas por la DIAN. A diferencia de los "
                     "otros campos, esto no baja tu renta gravable: te "
                     "devuelve el 25% de lo donado directamente del "
                     "impuesto ya calculado (Art. 257 E.T.), hasta el 25% "
                     "de ese impuesto.")
        guardado = st.form_submit_button("💾 Guardar esta sección", on_click=guardar_todo)
    if guardado:
        st.success("Guardado.")

# ----------------------------------------------------------------------
# 8. Anticipo y Retenciones
# ----------------------------------------------------------------------
elif seccion == "8. Anticipo y Retenciones":
    st.caption("Cuando declaras, además de pagar el impuesto del año que "
               "declaras, adelantas parte del impuesto del año siguiente "
               "(Art. 807 E.T.).")
    with st.form("form_anticipo"):
        campo_moneda("Retenciones en la fuente del año", "retenciones",
                     "Suma de las retenciones que te hicieron en el año "
                     "—las que salen en tus certificados de ingresos o de "
                     "honorarios—. Ese dinero ya se lo diste a la DIAN por "
                     "adelantado, así que se resta de lo que debas pagar "
                     "(Art. 807 E.T.).")
        campo_moneda("Anticipo pagado el año anterior", "anticipo_anterior",
                     "El anticipo de renta que pagaste en tu declaración "
                     "del año pasado. Como ya lo pagaste, se resta del "
                     "total de este año (Art. 807 E.T.).")
        campo_moneda("Impuesto neto de renta año anterior", "impuesto_anio_anterior",
                     "Opcional: el impuesto que liquidaste el año pasado, "
                     "si ya habías declarado antes. Si lo llenas, el "
                     "simulador usa el promedio de los dos últimos años "
                     "cuando eso te convenga más (Art. 807 E.T.).")
        
        campo_selectbox(
            "N.º de veces que declaras (con esta)",
            ["Primera vez", "Segunda vez", "Tercera vez o más"],
            "num_declaracion",
            ayuda="Marca si esta es tu primera, segunda o tercera "
            "declaración en adelante. El porcentaje de tu anticipo "
            "depende de eso: 25%, 50% o 75% (Art. 807 E.T.)."
        )
        guardado = st.form_submit_button("💾 Guardar esta sección", on_click=guardar_todo)
    if guardado:
        st.success("Guardado.")

# ----------------------------------------------------------------------
# 9. Topes y Obligación
# ----------------------------------------------------------------------
elif seccion == "9. Topes y Obligación":
    uvt_actual = valor_numerico("uvt") or UVT_2026
    topes = topes_obligacion_declarar(uvt_actual)
    st.caption(f"Calculado con la UVT configurada: $ {uvt_actual:,.0f}")

    st.markdown("### ¿Debo presentar declaración de renta? (Art. 592 E.T.)")
    st.write("Debes declarar si, durante el año, cumples **al menos uno** de estos 5 topes:")
    st.markdown(f"""
1. Patrimonio bruto (sin restar deudas) al 31 de diciembre: **$ {topes['patrimonio_bruto']:,.0f}**
2. Ingresos brutos totales del año: **$ {topes['ingresos_brutos']:,.0f}**
3. Consumos con tarjeta de crédito: **$ {topes['consumos_tarjeta']:,.0f}**
4. Compras y consumos totales (cualquier medio de pago): **$ {topes['compras_consumos']:,.0f}**
5. Consignaciones bancarias, depósitos o inversiones: **$ {topes['consignaciones']:,.0f}**
""")
    st.info("Además: si fuiste responsable del IVA en algún momento del año, debes declarar sin importar los topes anteriores. Basta con cumplir UNO SOLO de los 5 puntos.")

    st.markdown("### ¿Debo pagar impuesto de renta? (Art. 241 E.T.)")
    st.write(f"Estar obligado a declarar no significa que debas pagar. Solo se genera impuesto cuando tu Renta Líquida Gravable supera **$ {topes['impuesto_desde']:,.0f}**.")
    st.write("Por debajo de ese monto la tabla del Art. 241 da $0 de impuesto, aunque igual tengas que presentar la declaración si superaste algún tope de arriba.")

# ----------------------------------------------------------------------
# 10. Resultados
# ----------------------------------------------------------------------
elif seccion == "10. Resultados":
    st.caption("Antes de calcular, asegúrate de haber dado clic en 'Guardar esta sección' en cada pantalla donde ingresaste datos.")
    if st.button("Generar Cálculo", type="primary"):
        datos = {c: valor_numerico(c) for c in CAMPOS_MONEDA_DECLARACION}
        datos["num_dependientes"] = obtener("num_dependientes", 0)
        datos["num_declaracion"] = obtener("num_declaracion", "Primera vez")
        st.session_state["ultimo_resultado"] = calcular_declaracion(datos, uvt=valor_numerico("uvt") or UVT_2026)

    resultado = st.session_state.get("ultimo_resultado")

    if not resultado:
        st.info("Haz clic en 'Generar Cálculo' para procesar los datos.")
    else:
        r = resultado
        st.caption(f"UVT utilizada en este cálculo: $ {r['uvt']:,.0f}")

        st.subheader("1. Patrimonio Líquido")
        c1, c2, c3 = st.columns(3)
        c1.metric("Activos", f"$ {r['patrimonio']['total_activos']:,.0f}")
        c2.metric("Pasivos", f"$ {r['patrimonio']['total_pasivos']:,.0f}")
        c3.metric("Patrimonio líquido", f"$ {r['patrimonio']['patrimonio_liquido']:,.0f}")
        with st.expander("¿De dónde salió este valor?"):
            p = r["patrimonio"]
            st.markdown(f"""
- Casas, aptos o lotes + Dinero en bancos + Carros/motos = **Activos: $ {p['total_activos']:,.0f}** (Art. 267 y 261 E.T.)
- Deudas con bancos + Deudas con terceros = **Pasivos: $ {p['total_pasivos']:,.0f}** (Art. 283 y 770 E.T.)
- Activos − Pasivos = **Patrimonio líquido: $ {p['patrimonio_liquido']:,.0f}**
""")

        st.subheader("2. Depuración de Ingresos")
        ing = r["ingresos"]
        st.markdown(f"""
| Concepto | Valor |
|---|---:|
| Ingresos brutos | $ {ing['ingresos_brutos']:,.0f} |
| (–) Aportes salud/pensión | $ {ing['incr']:,.0f} |
| (–) Costos y gastos del negocio (Art. 107) | $ {ing['costos_gastos_deducibles']:,.0f} |
| **= Ingreso neto** | **$ {ing['renta_neta']:,.0f}** |
""")

        st.subheader("3. Deducciones y Rentas Exentas (tope 40% / 1.340 UVT)")
        d = r["deducciones"]
        st.markdown(f"""
| Concepto | Valor |
|---|---:|
| Dependientes, 10% ingreso (Art. 387) | $ {d['dependientes_10pct']:,.0f} |
| Medicina prepagada (Art. 387) | $ {d['prepagada_deducible']:,.0f} |
| Intereses de vivienda (Art. 119) | $ {d['intereses_deducibles']:,.0f} |
| 50% del 4x1000 (Art. 115) | $ {d['gmf_deducible']:,.0f} |
| 1% facturas electrónicas (Art. 336-5) | $ {d['facturas_deducible']:,.0f} |
| AFC + pensión voluntaria (Art. 126-1/126-4) | $ {d['afc_pension_aceptado']:,.0f} |
| 25% renta exenta laboral (Art. 206-10) | $ {d['exenta_25']:,.0f} |
| Solicitado | $ {d['solicitado']:,.0f} |
| Tope máximo | $ {d['tope_maximo']:,.0f} |
| **Aceptado** | **$ {d['aceptado']:,.0f}** |
""")
        st.info(f"Deducción adicional por dependientes (72 UVT c/u, fuera del tope anterior): **$ {d['dependientes_extra_72uvt']:,.0f}**")

        st.subheader("Renta Líquida Gravable")
        st.metric("", f"$ {r['renta_liquida_gravable']:,.0f}")
        with st.expander("¿De dónde salió este valor?"):
            st.markdown(f"""
- Ingreso neto: **$ {ing['renta_neta']:,.0f}**
- Menos deducciones y rentas exentas aceptadas (tope 40%/1.340 UVT): **− $ {d['aceptado']:,.0f}**
- Menos deducción adicional por dependientes, 72 UVT c/u (Art. 387, fuera del tope): **− $ {d['dependientes_extra_72uvt']:,.0f}**
- = **Renta Líquida Gravable: $ {r['renta_liquida_gravable']:,.0f}**
""")

        st.subheader("5. Impuesto de Renta (Art. 241 E.T.)")
        imp = r["impuesto"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Impuesto calculado", f"$ {imp['impuesto_pesos']:,.0f}")
        c2.metric("Descuento donaciones (Art. 257)", f"- $ {imp['descuento_donaciones']:,.0f}")
        c3.metric("Impuesto neto de renta", f"$ {imp['impuesto_neto_final']:,.0f}")

        st.subheader("6. Anticipo y Retenciones (Art. 807 E.T.)")
        a = r["anticipo"]
        etiqueta_saldo = "Saldo a pagar del año" if a["saldo_impuesto_actual"] >= 0 else "Saldo A FAVOR del año"
        st.write(f"- Retenciones en la fuente: **- $ {a['retenciones']:,.0f}**")
        st.write(f"- Anticipo pagado el año anterior: **- $ {a['anticipo_anterior']:,.0f}**")
        st.write(f"- {etiqueta_saldo}: **$ {abs(a['saldo_impuesto_actual']):,.0f}**")
        st.write(f"- Anticipo calculado para el próximo año ({int(a['porcentaje_anticipo'] * 100)}%): **$ {a['anticipo_a_pagar']:,.0f}**")

        etiqueta_total = "TOTAL ESTIMADO A PAGAR" if r["total_a_pagar"] >= 0 else "TOTAL ESTIMADO A FAVOR"
        st.success(f"### {etiqueta_total}: $ {abs(r['total_a_pagar']):,.0f}")
        with st.expander("¿De dónde salió este valor?"):
            st.markdown(f"""
- Impuesto neto de renta (Art. 241 E.T., ya con descuento por donaciones): **$ {imp['impuesto_neto_final']:,.0f}**
- Menos retenciones en la fuente del año: **− $ {a['retenciones']:,.0f}**
- Menos anticipo pagado el año anterior: **− $ {a['anticipo_anterior']:,.0f}**
- = {etiqueta_saldo}: **$ {abs(a['saldo_impuesto_actual']):,.0f}**
- Más anticipo calculado para el próximo año (Art. 807 E.T., {int(a['porcentaje_anticipo'] * 100)}%): **+ $ {a['anticipo_a_pagar']:,.0f}**
- = **{etiqueta_total}: $ {abs(r['total_a_pagar']):,.0f}**
""")

        st.caption("Cálculo estimado con fines educativos, basado en el Estatuto Tributario vigente. "
                   "No reemplaza tu declaración oficial ni el software autorizado por la DIAN.")

        st.divider()
        pdf_buffer = generar_pdf_resultado(r, {c: obtener(c) for c in CAMPOS_DATOS_PERSONALES})
        st.download_button(
            "📄 Descargar resultado en PDF", data=pdf_buffer,
            file_name="resumen_tributario.pdf", mime="application/pdf",
        )
        if st.button("💾 Guardar esta declaración"):
            doc = obtener("dp_num_doc", "")
            if doc:
                datos_guardar = {c: obtener(c) for c in CAMPOS_DATOS_PERSONALES}
                datos_guardar.update({c: valor_numerico(c) for c in CAMPOS_MONEDA_DECLARACION})
                datos_guardar["num_dependientes"] = obtener("num_dependientes", 0)
                datos_guardar["num_declaracion"] = obtener("num_declaracion", "Primera vez")
                guardar_declaracion(doc, 2026, datos_guardar)
                st.success("Declaración guardada.")
            else:
                st.warning("Primero escribe tu número de documento en la sección 'Datos Personales'.")