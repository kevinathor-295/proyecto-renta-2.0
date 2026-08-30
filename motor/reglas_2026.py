"""
Reglas y topes del Estatuto Tributario (E.T.) aplicables al año gravable 2026.

Cada regla tiene su artículo, una descripción en palabras simples y (cuando
aplica) su fuente normativa. La idea es que cuando la ley cambie -o cuando
quieras simular otro año- solo tengas que copiar este archivo a
reglas_2027.py y ajustar los valores, sin tocar el motor de cálculo.
"""

UVT_2026 = 52374  # Resolución DIAN 000238 del 15 de diciembre de 2025

REGLAS = {
    "uvt_defecto": {
        "valor": UVT_2026,
        "articulo": "Art. 868 E.T.",
        "descripcion": "Valor de la Unidad de Valor Tributario para 2026.",
        "fuente": "Resolución DIAN 000238 de 2025",
    },
    "tope_dependientes_10pct_mensual_uvt": {
        "valor": 32,
        "articulo": "Art. 387 E.T., inciso 2",
        "descripcion": "Tope mensual (UVT) de la deducción del 10% de ingresos laborales por tener dependientes.",
    },
    "tope_dependientes_72uvt_max": {
        "valor": 4,
        "articulo": "Art. 387 E.T., inciso 3 (Ley 2277 de 2022)",
        "descripcion": "Número máximo de dependientes que dan la deducción adicional de 72 UVT c/u.",
    },
    "dependientes_72uvt_valor": {
        "valor": 72,
        "articulo": "Art. 387 E.T., inciso 3 (Ley 2277 de 2022)",
        "descripcion": "UVT deducibles por cada dependiente (deducción adicional, fuera del tope del 40%).",
    },
    "tope_prepagada_mensual_uvt": {
        "valor": 16,
        "articulo": "Art. 387 E.T.",
        "descripcion": "Tope mensual (UVT) de la deducción por medicina prepagada.",
    },
    "tope_intereses_vivienda_anual_uvt": {
        "valor": 1200,
        "articulo": "Art. 119 E.T.",
        "descripcion": "Tope anual (UVT) de la deducción por intereses de vivienda.",
    },
    "porcentaje_gmf_deducible": {
        "valor": 0.5,
        "articulo": "Art. 115 E.T.",
        "descripcion": "Porcentaje deducible del 4x1000 (GMF).",
    },
    "tope_facturas_electronicas_anual_uvt": {
        "valor": 240,
        "articulo": "Art. 336 num. 5 E.T. (Ley 2277 de 2022)",
        "descripcion": "Tope anual (UVT) de la deducción del 1% de compras con factura electrónica.",
    },
    "porcentaje_facturas_electronicas": {
        "valor": 0.01,
        "articulo": "Art. 336 num. 5 E.T.",
        "descripcion": "Porcentaje deducible de las compras con factura electrónica.",
    },
    "tope_afc_pension_ingreso_pct": {
        "valor": 0.30,
        "articulo": "Art. 126-1 y 126-4 E.T.",
        "descripcion": "Porcentaje máximo de los ingresos que pueden ser AFC + pensión voluntaria.",
    },
    "tope_afc_pension_anual_uvt": {
        "valor": 3800,
        "articulo": "Art. 126-1 y 126-4 E.T.",
        "descripcion": "Tope anual (UVT) conjunto de AFC + pensión voluntaria.",
    },
    "porcentaje_exenta_laboral": {
        "valor": 0.25,
        "articulo": "Art. 206 num. 10 E.T.",
        "descripcion": "Porcentaje de renta exenta sobre pagos laborales netos.",
    },
    "tope_exenta_laboral_anual_uvt": {
        "valor": 790,
        "articulo": "Art. 206 num. 10 E.T. (tope modificado por Ley 2277 de 2022)",
        "descripcion": "Tope anual (UVT) de la renta exenta laboral del 25%.",
    },
    "tope_general_deducciones_pct": {
        "valor": 0.40,
        "articulo": "Art. 336 num. 3 E.T.",
        "descripcion": "Porcentaje máximo del ingreso neto que pueden sumar deducciones + rentas exentas.",
    },
    "tope_general_deducciones_anual_uvt": {
        "valor": 1340,
        "articulo": "Art. 336 num. 3 E.T. (Ley 2277 de 2022)",
        "descripcion": "Tope anual (UVT) conjunto de deducciones y rentas exentas.",
    },
    "porcentaje_descuento_donaciones": {
        "valor": 0.25,
        "articulo": "Art. 257 E.T.",
        "descripcion": "Porcentaje de la donación que se toma como descuento tributario.",
    },
    "tope_descuento_donaciones_pct_impuesto": {
        "valor": 0.25,
        "articulo": "Art. 257 E.T.",
        "descripcion": "Tope del descuento por donaciones como % del impuesto de renta.",
    },
    "tope_inicio_impuesto_uvt": {
        "valor": 1090,
        "articulo": "Art. 241 E.T.",
        "descripcion": "A partir de cuántas UVT de renta líquida gravable empieza a generarse impuesto.",
    },
    "tabla_241": {
        "articulo": "Art. 241 E.T.",
        "descripcion": "Tabla progresiva del impuesto de renta para personas naturales, en UVT.",
        # (piso_uvt, techo_uvt, impuesto_base_uvt, tarifa_marginal)
        "tramos": [
            (0, 1090, 0, 0.00),
            (1090, 1700, 0, 0.19),
            (1700, 4100, 116, 0.28),
            (4100, 8670, 788, 0.33),
            (8670, 18970, 2296, 0.35),
            (18970, 31000, 5901, 0.37),
            (31000, float("inf"), 10352, 0.39),
        ],
    },
    "anticipo_porcentajes": {
        "articulo": "Art. 807 E.T.",
        "descripcion": "Porcentaje del anticipo de renta según cuántas veces ha declarado el contribuyente.",
        "valores": {
            "Primera vez": 0.25,
            "Segunda vez": 0.50,
            "Tercera vez o más": 0.75,
        },
    },
    "topes_obligacion_declarar_uvt": {
        "articulo": "Art. 592 E.T. y su decreto reglamentario",
        "descripcion": "Topes (UVT) que obligan a presentar declaración de renta (basta con superar uno).",
        "patrimonio_bruto": 4500,
        "ingresos_brutos": 1400,
        "consumos_tarjeta": 1400,
        "compras_consumos": 1400,
        "consignaciones": 1400,
    },
}
