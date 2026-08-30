"""
Motor de cálculo del Simulador Tributario.

Esta función NO sabe nada de interfaces gráficas (ni CustomTkinter, ni
Streamlit, ni nada). Recibe un diccionario de datos ya parseados (números,
no texto de un campo) y devuelve un diccionario con todos los resultados
intermedios. Así se puede llamar desde cualquier interfaz, probar
automáticamente, o reutilizar en otro proyecto sin arrastrar la interfaz.
"""

from motor.reglas_2026 import REGLAS, UVT_2026


def _valor(nombre_regla):
    return REGLAS[nombre_regla]["valor"]


def calcular_impuesto_tabla_241(renta_liquida_gravable_uvt: float) -> float:
    """Aplica la tabla progresiva del Art. 241 E.T. Devuelve el impuesto en UVT."""
    for piso, techo, base, tarifa in REGLAS["tabla_241"]["tramos"]:
        if renta_liquida_gravable_uvt <= techo:
            return base + max(renta_liquida_gravable_uvt - piso, 0) * tarifa
    return 0.0  # no debería alcanzarse (el último tramo llega hasta infinito)


def topes_obligacion_declarar(uvt: float = None) -> dict:
    """Devuelve, en pesos, los topes que obligan a declarar renta (Art. 592 E.T.)."""
    UVT = uvt if uvt and uvt > 0 else UVT_2026
    t = REGLAS["topes_obligacion_declarar_uvt"]
    return {
        "patrimonio_bruto": t["patrimonio_bruto"] * UVT,
        "ingresos_brutos": t["ingresos_brutos"] * UVT,
        "consumos_tarjeta": t["consumos_tarjeta"] * UVT,
        "compras_consumos": t["compras_consumos"] * UVT,
        "consignaciones": t["consignaciones"] * UVT,
        "impuesto_desde": _valor("tope_inicio_impuesto_uvt") * UVT,
    }


def calcular_declaracion(datos: dict, uvt: float = None) -> dict:
    """
    datos: diccionario con estas llaves (todas opcionales, por defecto 0):
        casa, bancos, vehiculos, deudas_bancos, deudas_terceros,
        salarios, honorarios, salud_pension, num_dependientes,
        prepagada, intereses, gmf, compras_facturadas, costos_gastos,
        afc, pensiones_vol, donaciones,
        retenciones, anticipo_anterior, impuesto_anio_anterior,
        num_declaracion ("Primera vez" | "Segunda vez" | "Tercera vez o más")

    uvt: valor de la UVT a usar; si es None o 0, usa la UVT 2026 por defecto.

    Devuelve un diccionario con TODOS los resultados intermedios, listo
    para que cualquier interfaz los muestre como quiera.
    """
    g = lambda k, d=0: datos.get(k, d) or d
    UVT = uvt if uvt and uvt > 0 else UVT_2026

    # --- Patrimonio ---
    casa, bancos, vehiculos = g("casa"), g("bancos"), g("vehiculos")
    deudas_bancos, deudas_terceros = g("deudas_bancos"), g("deudas_terceros")
    total_activos = casa + bancos + vehiculos
    total_pasivos = deudas_bancos + deudas_terceros
    patrimonio_liquido = total_activos - total_pasivos

    # --- Depuración de ingresos: brutos -> INCR -> costos (Art. 107) -> neto ---
    salarios, honorarios = g("salarios"), g("honorarios")
    salud_pension = g("salud_pension")
    costos_gastos = g("costos_gastos")

    ingresos_brutos = salarios + honorarios
    incr = salud_pension  # simplificación: aportes obligatorios salud/pensión
    costos_gastos_deducibles = min(costos_gastos, honorarios) if honorarios > 0 else 0
    renta_neta = max(ingresos_brutos - incr - costos_gastos_deducibles, 0)

    # --- Deducciones y rentas exentas sujetas al tope 40% / 1.340 UVT ---
    num_dep_val = min(max(int(g("num_dependientes")), 0), int(_valor("tope_dependientes_72uvt_max")))
    dependientes_10pct = (
        min(salarios * 0.10, _valor("tope_dependientes_10pct_mensual_uvt") * 12 * UVT)
        if num_dep_val > 0 else 0
    )
    prepagada_deducible = min(g("prepagada"), _valor("tope_prepagada_mensual_uvt") * 12 * UVT)
    intereses_deducibles = min(g("intereses"), _valor("tope_intereses_vivienda_anual_uvt") * UVT)
    gmf_deducible = g("gmf") * _valor("porcentaje_gmf_deducible")
    facturas_deducible = min(
        g("compras_facturadas") * _valor("porcentaje_facturas_electronicas"),
        _valor("tope_facturas_electronicas_anual_uvt") * UVT,
    )

    tope_afc_pension = min(
        ingresos_brutos * _valor("tope_afc_pension_ingreso_pct"),
        _valor("tope_afc_pension_anual_uvt") * UVT,
    )
    afc_pension_aceptado = min(g("afc") + g("pensiones_vol"), tope_afc_pension)

    # Base del 25% (Art. 206-10): salarios menos INCR proporcional, menos
    # deducciones Art. 387 y demás rentas exentas -- SIN restar la deducción
    # de 72 UVT ni el 1% de facturas electrónicas.
    incr_salarios = incr * (salarios / ingresos_brutos) if ingresos_brutos > 0 else 0
    base_25 = max(
        salarios - incr_salarios - dependientes_10pct - prepagada_deducible
        - intereses_deducibles - afc_pension_aceptado,
        0,
    )
    exenta_25 = min(base_25 * _valor("porcentaje_exenta_laboral"), _valor("tope_exenta_laboral_anual_uvt") * UVT)

    total_deducciones = dependientes_10pct + prepagada_deducible + intereses_deducibles + gmf_deducible + facturas_deducible
    total_exentas = afc_pension_aceptado + exenta_25
    suma_deducciones_exentas = total_deducciones + total_exentas

    tope_maximo = min(renta_neta * _valor("tope_general_deducciones_pct"), _valor("tope_general_deducciones_anual_uvt") * UVT)
    deduccion_exenta_aceptada = min(suma_deducciones_exentas, tope_maximo)

    # --- Deducción adicional por dependientes (72 UVT c/u, fuera del tope anterior) ---
    deduccion_dependientes_extra = num_dep_val * _valor("dependientes_72uvt_valor") * UVT

    # --- Renta Líquida Gravable ---
    renta_liquida_gravable = max(renta_neta - deduccion_exenta_aceptada - deduccion_dependientes_extra, 0)

    # --- Impuesto (tabla Art. 241) ---
    rlg_uvt = renta_liquida_gravable / UVT
    impuesto_uvt = calcular_impuesto_tabla_241(rlg_uvt)
    impuesto_pesos = impuesto_uvt * UVT

    # --- Descuento tributario por donaciones (Art. 257) ---
    donaciones = g("donaciones")
    descuento_donaciones = min(
        donaciones * _valor("porcentaje_descuento_donaciones"),
        impuesto_pesos * _valor("tope_descuento_donaciones_pct_impuesto"),
    )
    impuesto_neto_final = max(impuesto_pesos - descuento_donaciones, 0)

    # --- Anticipo de renta y retenciones (Art. 807) ---
    retenciones = g("retenciones")
    anticipo_anterior = g("anticipo_anterior")
    impuesto_anio_anterior = g("impuesto_anio_anterior")
    num_decl_texto = datos.get("num_declaracion") or "Primera vez"
    porcentaje_anticipo = REGLAS["anticipo_porcentajes"]["valores"].get(num_decl_texto, 0.25)

    if num_decl_texto != "Primera vez" and impuesto_anio_anterior > 0:
        base_promedio = (impuesto_neto_final + impuesto_anio_anterior) / 2
        base_anticipo = min(impuesto_neto_final, base_promedio)
    else:
        base_anticipo = impuesto_neto_final

    anticipo_bruto = base_anticipo * porcentaje_anticipo
    anticipo_a_pagar = max(anticipo_bruto - retenciones, 0)
    saldo_impuesto_actual = impuesto_neto_final - retenciones - anticipo_anterior
    total_a_pagar = saldo_impuesto_actual + anticipo_a_pagar

    return {
        "uvt": UVT,
        "patrimonio": {
            "total_activos": total_activos,
            "total_pasivos": total_pasivos,
            "patrimonio_liquido": patrimonio_liquido,
        },
        "ingresos": {
            "ingresos_brutos": ingresos_brutos,
            "incr": incr,
            "costos_gastos_deducibles": costos_gastos_deducibles,
            "renta_neta": renta_neta,
        },
        "deducciones": {
            "dependientes_10pct": dependientes_10pct,
            "prepagada_deducible": prepagada_deducible,
            "intereses_deducibles": intereses_deducibles,
            "gmf_deducible": gmf_deducible,
            "facturas_deducible": facturas_deducible,
            "afc_pension_aceptado": afc_pension_aceptado,
            "exenta_25": exenta_25,
            "solicitado": suma_deducciones_exentas,
            "tope_maximo": tope_maximo,
            "aceptado": deduccion_exenta_aceptada,
            "dependientes_extra_72uvt": deduccion_dependientes_extra,
        },
        "renta_liquida_gravable": renta_liquida_gravable,
        "impuesto": {
            "impuesto_pesos": impuesto_pesos,
            "descuento_donaciones": descuento_donaciones,
            "impuesto_neto_final": impuesto_neto_final,
        },
        "anticipo": {
            "porcentaje_anticipo": porcentaje_anticipo,
            "retenciones": retenciones,
            "anticipo_anterior": anticipo_anterior,
            "saldo_impuesto_actual": saldo_impuesto_actual,
            "anticipo_a_pagar": anticipo_a_pagar,
        },
        "total_a_pagar": total_a_pagar,
    }
