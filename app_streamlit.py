import streamlit as st

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
# Utilidades de formato de pesos colombianos
# ----------------------------------------------------------------------
def formatear_pesos(valor: str) -> str:
    solo_digitos = "".join(c for c in str(valor) if c.isdigit())
    if not solo_digitos:
        return ""
    solo_digitos = solo_digitos.lstrip("0") or "0"
    return f"{int(solo_digitos):,}".replace(",", ".")


def campo_moneda(label, campo_key, ayuda="", valor_defecto=0):
    """Campo de dinero para usar DENTRO de un st.form. Dentro de un
    formulario, Streamlit no permite reformatear mientras escribes (no
    hay rerun hasta que se envía el formulario) -así que se formatea
    automáticamente apenas le das clic a 'Guardar esta sección'."""
    if campo_key not in st.session_state:
        st.session_state[campo_key] = formatear_pesos(str(int(valor_defecto))) if valor_defecto else ""
    st.text_input(f"{label} ($)", key=campo_key, placeholder="0", help=ayuda or None)


def valor_numerico(campo_key) -> float:
    """Convierte a número el texto guardado por un campo_moneda."""
    texto = st.session_state.get(campo_key, "")
    solo_digitos = "".join(c for c in str(texto) if c.isdigit())
    return float(solo_digitos) if solo_digitos else 0.0


def reformatear_campos_moneda(campos):
    """Llamar justo después de un st.form_submit_button exitoso, para
    que los campos de dinero de esa sección se vean con puntos de miles."""
    for c in campos:
        if c in st.session_state:
            st.session_state[c] = formatear_pesos(st.session_state[c])


def obtener(campo_key, default=0.0):
    """Para campos que NO son de dinero (checkbox, selectbox, number_input, texto libre)."""
    return st.session_state.get(campo_key, default)


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
# 0. Perfil (checkboxes: no necesitan formulario, un clic ya es una
# interacción completa y no compite con la navegación)
# ----------------------------------------------------------------------
if seccion == "0. Perfil":
    st.write("Cuéntanos brevemente tu situación. Así solo te mostramos las preguntas que te aplican.")
    st.checkbox("Tuve empleo (recibí salario)", key="perfil_empleo", value=True)
    st.checkbox("Tuve honorarios o un negocio propio (trabajo independiente)", key="perfil_honorarios", value=False)
    if not obtener("perfil_empleo", True) and not obtener("perfil_honorarios", False):
        st.warning("Si no tuviste ninguno de los dos, es probable que no necesites declarar renta — revisa la pantalla '9. Topes y Obligación' para confirmarlo.")
    st.caption("Puedes cambiar esto en cualquier momento; los campos de Ingresos y Deducciones se ajustan solos.")

# ----------------------------------------------------------------------
# 1. Datos Personales
# ----------------------------------------------------------------------
elif seccion == "1. Datos Personales":
    st.caption("Estos datos no afectan el cálculo del impuesto; se usarán más adelante para diligenciar tu Formulario 210.")
    with st.form("form_datos_personales"):
        st.text_input("Nombres y apellidos", key="dp_nombre")
        st.selectbox("Tipo de documento", ["Cédula de ciudadanía", "Cédula de extranjería", "Pasaporte", "NIT"], key="dp_tipo_doc")
        st.text_input("Número de documento", key="dp_num_doc")
        st.text_input("Ciudad", key="dp_ciudad")
        st.text_input("Dirección", key="dp_direccion")
        st.text_input("Correo electrónico", key="dp_correo")
        guardado = st.form_submit_button("💾 Guardar esta sección")
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
        guardado = st.form_submit_button("💾 Guardar esta sección")
    if guardado:
        reformatear_campos_moneda(["uvt"])
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
        guardado = st.form_submit_button("💾 Guardar esta sección")
    if guardado:
        reformatear_campos_moneda(["casa", "bancos", "vehiculos"])
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
        guardado = st.form_submit_button("💾 Guardar esta sección")
    if guardado:
        reformatear_campos_moneda(["deudas_bancos", "deudas_terceros"])
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
        campos_esta_seccion = []
        with st.form("form_ingresos"):
            if tiene_empleo:
                campo_moneda("Salarios y prestaciones", "salarios",
                             "Todo lo que recibiste por tu trabajo en el "
                             "año: sueldo, primas, bonos, auxilios (Art. "
                             "103 E.T.). Ponlo completo, sin restar nada "
                             "todavía.")
                campos_esta_seccion.append("salarios")
            if tiene_negocio:
                campo_moneda("Honorarios (Independiente)", "honorarios",
                             "Lo que facturaste en el año trabajando de "
                             "forma independiente —freelance, contratos "
                             "por servicios, negocio propio— (Art. 103 "
                             "E.T.). También va completo; los gastos del "
                             "negocio se restan en la siguiente pantalla, "
                             "Deducciones.")
                campos_esta_seccion.append("honorarios")
            guardado = st.form_submit_button("💾 Guardar esta sección")
        if guardado:
            reformatear_campos_moneda(campos_esta_seccion)
            st.success("Guardado.")

# ----------------------------------------------------------------------
# 6. Deducciones
# ----------------------------------------------------------------------
elif seccion == "6. Deducciones":
    st.subheader("Deducciones (Bajan tu impuesto)")
    st.caption("Con la cantidad de dependientes que escribas, el simulador ya "
               "calcula automáticamente los DOS beneficios que existen por eso.")
    campos_esta_seccion = ["salud_pension", "prepagada", "intereses", "gmf", "compras_facturadas"]
    with st.form("form_deducciones"):
        campo_moneda("Salud y Pensión obligatoria", "salud_pension",
                     "Lo que pagaste en el año, de forma obligatoria, a "
                     "salud y pensión. La ley no lo cuenta como ingreso "
                     "tuyo, así que se resta de tu base antes de calcular "
                     "el impuesto (Art. 55 y 56 E.T.).")
        st.number_input(
            "Cantidad de dependientes (0 a 4)", key="num_dependientes",
            min_value=0, max_value=4, step=1,
            help="Cuántas personas dependen de ti económicamente —hijos, "
            "pareja, papás, etc.—, hasta 4. Con este número el simulador "
            "calcula dos beneficios: el 10% de tus ingresos laborales, "
            "tope 384 UVT al año (Art. 387 E.T.), y además 72 UVT fijas "
            "por cada uno, hasta 4 (Art. 387, adicionado por la Ley 2277 "
            "de 2022). No necesitas guardar facturas para esto.",
        )
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
            campos_esta_seccion.append("costos_gastos")
        guardado = st.form_submit_button("💾 Guardar esta sección")
    if guardado:
        reformatear_campos_moneda(campos_esta_seccion)
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
        guardado = st.form_submit_button("💾 Guardar esta sección")
    if guardado:
        reformatear_campos_moneda(["afc", "pensiones_vol", "donaciones"])
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
        st.selectbox(
            "N.º de veces que declaras (con esta)",
            ["Primera vez", "Segunda vez", "Tercera vez o más"],
            key="num_declaracion",
            help="Marca si esta es tu primera, segunda o tercera "
            "declaración en adelante. El porcentaje de tu anticipo "
            "depende de eso: 25%, 50% o 75% (Art. 807 E.T.).",
        )
        guardado = st.form_submit_button("💾 Guardar esta sección")
    if guardado:
        reformatear_campos_moneda(["retenciones", "anticipo_anterior", "impuesto_anio_anterior"])
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
        st.session_state["ultimo_resultado"] = calcular_declaracion(datos, uvt=valor_numerico("uvt"))

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

        st.caption("Cálculo estimado con fines educativos, basado en el Estatuto Tributario vigente. "
                   "No reemplaza tu declaración oficial ni el software autorizado por la DIAN.")

        st.divider()
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
