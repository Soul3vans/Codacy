import re
from docx import Document

def limpiar_texto(texto):
    texto = re.sub(r"\s+", " ", texto)
    texto = re.sub(r"\f|\n|Página \d+", "", texto)
    return texto.strip()

def procesar_tabla_docx(path):
    doc = Document(path)
    tablas_cuestionario = []
    componente_actual = None
    bloque_actual = None
    dentro_tabla_cuestionario = False

    for tabla in doc.tables:
        for fila in tabla.rows:
            celdas = [cell.text.strip() for cell in fila.cells]
            if not any(celdas):
                continue

            # Detectar encabezado de tabla
            if any("ASPECTOS A VERIFICAR" in c for c in celdas) and "NO." in celdas[0]:
                dentro_tabla_cuestionario = True
                continue
            if not dentro_tabla_cuestionario:
                continue

            # Detectar componente si al menos 3 celdas tienen el mismo valor no vacío
            if len(set([c for c in celdas if c])) == 1 and len(celdas) >= 3:
                componente_actual = {
                    "componente": limpiar_texto(celdas[0]),
                    "bloques": []
                }
                tablas_cuestionario.append(componente_actual)
                bloque_actual = None
                continue

            no = limpiar_texto(celdas[0]) if len(celdas) > 0 else ""
            aspecto = limpiar_texto(celdas[1]) if len(celdas) > 1 else ""

            if "Elaborado por" in no or "Aprobado por el jefe" in no:
                continue

            if not no and aspecto.endswith(":"):
                bloque_actual = {
                    "encabezado": aspecto,
                    "preguntas": []
                }
                if componente_actual:
                    componente_actual["bloques"].append(bloque_actual)
                continue

            if no.strip(". ").isdigit():
                numero = int(no.strip(". "))
                texto = aspecto
                if bloque_actual:
                    bloque_actual["preguntas"].append({"numero_pregunta": numero, "texto": texto})
                elif componente_actual:
                    bloque_actual = {"encabezado": "Preguntas sin encabezado", "preguntas": []}
                    bloque_actual["preguntas"].append({"numero_pregunta": numero, "texto": texto})
                    componente_actual["bloques"].append(bloque_actual)
                continue

            match_embebido = re.match(r"^(\d{1,3})\.\s+(.*)", aspecto)
            if match_embebido:
                numero = int(match_embebido.group(1))
                texto = match_embebido.group(2).strip()
                if bloque_actual:
                    bloque_actual["preguntas"].append({"numero_pregunta": numero, "texto": texto})
                elif componente_actual:
                    bloque_actual = {"encabezado": "Preguntas sin encabezado", "preguntas": []}
                    bloque_actual["preguntas"].append({"numero_pregunta": numero, "texto": texto})
                    componente_actual["bloques"].append(bloque_actual)
                continue

            if re.match(r"^[a-z0-9]\)", aspecto) and bloque_actual and bloque_actual.get("preguntas"):
                inciso = aspecto
                base = bloque_actual["preguntas"][-1]["numero_pregunta"]
                literal = aspecto[0]
                subnumero = f"{base}.{ord(literal)-ord('a')+1}" if literal.isalpha() else f"{base}.{literal}"
                bloque_actual["preguntas"].append({"numero_pregunta": float(subnumero), "texto": inciso})

    return {"tablas_cuestionario": tablas_cuestionario}
