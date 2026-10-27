import os
import re
import json
from typing import List, Dict, Tuple, Optional, Set


# ==============================================================================
# 0. GESTOR DE ESCENARIOS CON NOMBRE Y PERSISTENCIA EN DISCO (JSON)
# ==============================================================================
try:
    DIRECTORIO_BASE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    DIRECTORIO_BASE = os.getcwd()

ARCHIVO_ESCENARIOS = os.path.join(DIRECTORIO_BASE, "escenarios_tableaux.json")

ESCENARIOS_PREDETERMINADOS: Dict[str, List[str]] = {
    "Caso del Video (2 cerradas, 1 abierta)": [
        "Si es de día, entonces voy a trabajar",
        "Si llueve, entonces no voy a trabajar",
        "Es de día",
    ],
    "Caso Estudio y Libro (4 cerradas, 1 abierta)": [
        "Estudio si y solo si tengo el libro",
        "Si tengo el libro y leo entonces apruebo",
        "Estudio o leo",
        "No apruebo",
        "No tengo el libro",
    ],
    "Caso Inconsistente (Todas cerradas)": [
        "Si es de día, entonces voy a trabajar",
        "Si llueve, entonces no voy a trabajar",
        "Es de día y llueve",
    ],
}


class GestorEscenarios:
    """
    Administra el guardado y carga de escenarios con nombre personalizado
    y recuerda siempre cuál fue el último escenario visto al cerrar el programa.
    """

    @staticmethod
    def _cargar_archivo() -> dict:
        if os.path.exists(ARCHIVO_ESCENARIOS):
            try:
                with open(ARCHIVO_ESCENARIOS, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                if isinstance(datos, dict) and "escenarios" in datos:
                    return datos
            except (OSError, json.JSONDecodeError):
                pass

        # Estructura inicial si el archivo aún no existe
        nombre_inicial = "Caso del Video (2 cerradas, 1 abierta)"
        datos_iniciales = {
            "ultimo_nombre": nombre_inicial,
            "ultimas_reglas": list(ESCENARIOS_PREDETERMINADOS[nombre_inicial]),
            "escenarios": dict(ESCENARIOS_PREDETERMINADOS),
        }
        GestorEscenarios._guardar_archivo(datos_iniciales)
        return datos_iniciales

    @staticmethod
    def _guardar_archivo(datos: dict) -> None:
        try:
            with open(ARCHIVO_ESCENARIOS, "w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"  [Aviso] No se pudo guardar en disco: {e}")

    @classmethod
    def obtener_ultimo_escenario(cls) -> Tuple[str, List[str]]:
        """Devuelve (nombre_escenario, lista_de_reglas) del último escenario visto."""
        datos = cls._cargar_archivo()
        nombre = datos.get("ultimo_nombre", "Escenario sin título")
        reglas = datos.get("ultimas_reglas", [])
        if not reglas:
            nombre = "Caso del Video (2 cerradas, 1 abierta)"
            reglas = list(ESCENARIOS_PREDETERMINADOS[nombre])
        return nombre, reglas

    @classmethod
    def registrar_ultimo_visto(cls, nombre: str, reglas: List[str]) -> None:
        """Actualiza cuál fue el último escenario visualizado sin obligar a guardarlo en el catálogo."""
        datos = cls._cargar_archivo()
        datos["ultimo_nombre"] = nombre
        datos["ultimas_reglas"] = list(reglas)
        cls._guardar_archivo(datos)

    @classmethod
    def guardar_escenario_con_nombre(cls, nombre: str, reglas: List[str]) -> None:
        """Guarda un escenario bajo el nombre elegido por el usuario y lo marca como último visto."""
        nombre_limpio = nombre.strip()
        if not nombre_limpio:
            return
        datos = cls._cargar_archivo()
        datos["escenarios"][nombre_limpio] = list(reglas)
        datos["ultimo_nombre"] = nombre_limpio
        datos["ultimas_reglas"] = list(reglas)
        cls._guardar_archivo(datos)

    @classmethod
    def listar_escenarios(cls) -> List[Tuple[str, List[str]]]:
        """Devuelve una lista de tuplas (nombre, reglas) con todos los escenarios guardados."""
        datos = cls._cargar_archivo()
        return list(datos.get("escenarios", {}).items())

    @classmethod
    def cargar_escenario_por_nombre(cls, nombre: str) -> Optional[List[str]]:
        """Busca un escenario por su nombre, lo marca como último visto y devuelve sus reglas."""
        datos = cls._cargar_archivo()
        escenarios = datos.get("escenarios", {})
        if nombre in escenarios:
            reglas = list(escenarios[nombre])
            datos["ultimo_nombre"] = nombre
            datos["ultimas_reglas"] = reglas
            cls._guardar_archivo(datos)
            return reglas
        return None

    @classmethod
    def eliminar_escenario(cls, nombre: str) -> bool:
        """Elimina un escenario guardado por su nombre."""
        datos = cls._cargar_archivo()
        escenarios = datos.get("escenarios", {})
        if nombre in escenarios:
            del escenarios[nombre]
            cls._guardar_archivo(datos)
            return True
        return False


# ==============================================================================
# 1. ÁRBOL DE SINTAXIS ABSTRACTA (AST) PARA FÓRMULAS LÓGICAS
# ==============================================================================
class Formula:
    """Clase base para todas las fórmulas bien formadas (FBF)."""
    def es_literal(self) -> bool:
        return False


class Atomo(Formula):
    def __init__(self, letra: str):
        self.letra = letra

    def es_literal(self) -> bool:
        return True

    def __str__(self) -> str:
        return self.letra

    def __repr__(self) -> str:
        return self.letra

    def __eq__(self, other) -> bool:
        return isinstance(other, Atomo) and self.letra == other.letra

    def __hash__(self) -> int:
        return hash(("ATOMO", self.letra))


class Negacion(Formula):
    def __init__(self, operando: Formula):
        self.operando = operando

    def es_literal(self) -> bool:
        return isinstance(self.operando, Atomo)

    def __str__(self) -> str:
        if isinstance(self.operando, (Atomo, Negacion)):
            return f"¬{self.operando}"
        return f"¬({self.operando})"

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other) -> bool:
        return isinstance(other, Negacion) and self.operando == other.operando

    def __hash__(self) -> int:
        return hash(("¬", self.operando))


class Binaria(Formula):
    def __init__(self, op: str, izq: Formula, der: Formula):
        self.op = op
        self.izq = izq
        self.der = der

    def es_literal(self) -> bool:
        return False

    def __str__(self) -> str:
        izq_str = f"({self.izq})" if isinstance(self.izq, Binaria) else str(self.izq)
        der_str = f"({self.der})" if isinstance(self.der, Binaria) else str(self.der)
        return f"{izq_str} {self.op} {der_str}"

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, Binaria)
            and self.op == other.op
            and self.izq == other.izq
            and self.der == other.der
        )

    def __hash__(self) -> int:
        return hash((self.op, self.izq, self.der))


# ==============================================================================
# 2. ANALIZADOR DE LENGUAJE NATURAL (ESPAÑOL) A LÓGICA PROPOSICIONAL
# ==============================================================================
class AnalizadorLenguajeNatural:
    """
    Convierte reglas en español a fórmulas bien formadas (FBF),
    reutilizando átomos idénticos y detectando negaciones y los 5 conectivos.
    """
    PREFIJOS_NEGACION_COMPUESTA = (
        "no es cierto que ",
        "no ocurre que ",
        "es falso que ",
        "no se cumple que ",
        "no pasa que ",
    )

    def __init__(self):
        self.significado_a_letra: Dict[str, str] = {}
        self.letra_a_significado: Dict[str, str] = {}
        self.pool_letras = [chr(c) for c in range(ord("p"), ord("z") + 1)] + [
            chr(c) for c in range(ord("a"), ord("o") + 1)
        ]
        self.indice_letra = 0

    @staticmethod
    def _limpiar_texto(texto: str) -> str:
        t = texto.strip().lower()
        t = re.sub(r"^[«»\"'¡!¿?\.,;:\s]+|[«»\"'¡!¿?\.,;:\s]+$", "", t)
        t = re.sub(r"\s+", " ", t)
        return t

    @staticmethod
    def _tiene_parentesis_externos(texto: str) -> bool:
        if not (texto.startswith("(") and texto.endswith(")")):
            return False
        profundidad = 0
        for i, ch in enumerate(texto):
            if ch == "(":
                profundidad += 1
            elif ch == ")":
                profundidad -= 1
                if profundidad == 0 and i < len(texto) - 1:
                    return False
        return profundidad == 0

    @staticmethod
    def _dividir_nivel_cero(texto: str, patron: str) -> Optional[Tuple[str, str]]:
        """Divide el texto por una expresión regular solo si está fuera de paréntesis."""
        for match in re.finditer(patron, texto):
            inicio = match.start()
            profundidad = texto[:inicio].count("(") - texto[:inicio].count(")")
            if profundidad == 0:
                izq = texto[: match.start()].strip()
                der = texto[match.end() :].strip()
                if izq and der:
                    return izq, der
        return None

    def _obtener_o_crear_atomo(self, frase: str) -> Atomo:
        frase_limpia = self._limpiar_texto(frase)
        if frase_limpia not in self.significado_a_letra:
            if self.indice_letra < len(self.pool_letras):
                letra = self.pool_letras[self.indice_letra]
            else:
                letra = f"p{self.indice_letra}"
            self.indice_letra += 1
            self.significado_a_letra[frase_limpia] = letra
            self.letra_a_significado[letra] = frase_limpia
        return Atomo(self.significado_a_letra[frase_limpia])

    def parsear(self, oracion: str) -> Formula:
        s = self._limpiar_texto(oracion)

        while self._tiene_parentesis_externos(s):
            s = self._limpiar_texto(s[1:-1])

        # 1. Negación explícita de una oración compuesta: "no es cierto que ...", "no (...)"
        for prefijo in self.PREFIJOS_NEGACION_COMPUESTA:
            if s.startswith(prefijo):
                return Negacion(self.parsear(s[len(prefijo) :]))

        if s.startswith("no (") and self._tiene_parentesis_externos(s[3:].strip()):
            return Negacion(self.parsear(s[3:].strip()[1:-1]))

        # 2. Bicondicional: "... si y solo si ..."
        div_iff = self._dividir_nivel_cero(s, r",?\s+si\s+y\s+s[oó]lo\s+si\s+")
        if div_iff:
            izq, der = div_iff
            return Binaria("↔", self.parsear(izq), self.parsear(der))

        # 3. Condicional: "si ... entonces ..."
        if s.startswith("si "):
            cuerpo = s[3:].strip()
            div_imp = self._dividir_nivel_cero(cuerpo, r"(?:,\s*|\s+)entonces\s+")
            if div_imp:
                antecedente, consecuente = div_imp
                return Binaria("→", self.parsear(antecedente), self.parsear(consecuente))

        # 4. Disyunción: "... o ..."
        div_or = self._dividir_nivel_cero(s, r",?\s+o\s+")
        if div_or:
            izq, der = div_or
            return Binaria("∨", self.parsear(izq), self.parsear(der))

        # 5. Conjunción: "... y ..."
        div_and = self._dividir_nivel_cero(s, r",?\s+y\s+")
        if div_and:
            izq, der = div_and
            return Binaria("∧", self.parsear(izq), self.parsear(der))

        # 6. Negación al inicio de proposición ("no voy a trabajar", "no no llueve")
        if s == "no" or s.startswith("no "):
            resto = s[3:].strip()
            if resto:
                return Negacion(self.parsear(resto))

        # 7. Negación interna antes del verbo ("el tren no llega" -> ¬("el tren llega"))
        if " no " in s:
            partes = s.split(" no ", 1)
            forma_afirmativa = f"{partes[0].strip()} {partes[1].strip()}"
            return Negacion(self._obtener_o_crear_atomo(forma_afirmativa))

        # 8. Proposición simple (átomo positivo)
        return self._obtener_o_crear_atomo(s)


# ==============================================================================
# 3. ESTRUCTURA DEL ÁRBOL SEMÁNTICO (TABLEAUX ANALÍTICOS)
# ==============================================================================
class ItemFormula:
    """Representa una fórmula dentro de un nodo del árbol y si ya fue aplicada."""
    def __init__(self, id_linea: int, formula: Formula, origen: str):
        self.id_linea = id_linea
        self.formula = formula
        self.origen = origen
        self.aplicada: bool = False
        self.paso_aplicacion: Optional[int] = None

    def texto_mostrar(self) -> str:
        marca = f" ✓[{self.paso_aplicacion}]" if self.aplicada else ""
        return f"({self.id_linea}) {self.formula}{marca}"


class NodoTableau:
    """Nodo jerárquico del árbol semántico."""
    def __init__(self, items: List[ItemFormula], padre: Optional["NodoTableau"] = None):
        self.items: List[ItemFormula] = items
        self.padre: Optional["NodoTableau"] = padre
        self.hijos: List["NodoTableau"] = []
        self.cerrada: bool = False
        self.atomo_contradiccion: Optional[str] = None

    def es_hoja(self) -> bool:
        return len(self.hijos) == 0

    def obtener_camino_items(self) -> List[ItemFormula]:
        """Devuelve todas las fórmulas desde la raíz hasta este nodo."""
        nodos = []
        actual: Optional[NodoTableau] = self
        while actual is not None:
            nodos.append(actual)
            actual = actual.padre
        nodos.reverse()
        camino = []
        for n in nodos:
            camino.extend(n.items)
        return camino

    def verificar_cierre(self) -> bool:
        """Cierra la rama con ✕ si contiene un átomo y su negación."""
        positivos: Set[str] = set()
        negativos: Set[str] = set()

        for item in self.obtener_camino_items():
            f = item.formula
            if isinstance(f, Atomo):
                positivos.add(f.letra)
            elif isinstance(f, Negacion) and isinstance(f.operando, Atomo):
                negativos.add(f.operando.letra)

        contradicciones = sorted(positivos.intersection(negativos))
        if contradicciones:
            self.cerrada = True
            self.atomo_contradiccion = contradicciones[0]
            return True
        return False

    def obtener_hojas_abiertas_debajo(self) -> List["NodoTableau"]:
        if self.es_hoja():
            return [] if self.cerrada else [self]
        hojas = []
        for h in self.hijos:
            hojas.extend(h.obtener_hojas_abiertas_debajo())
        return hojas

    def obtener_todas_las_hojas(self) -> List["NodoTableau"]:
        if self.es_hoja():
            return [self]
        hojas = []
        for h in self.hijos:
            hojas.extend(h.obtener_todas_las_hojas())
        return hojas

    def obtener_modelo(self) -> Dict[str, str]:
        """Extrae la asignación de valores de verdad (V/F) de una rama abierta."""
        modelo: Dict[str, str] = {}
        for item in self.obtener_camino_items():
            f = item.formula
            if isinstance(f, Atomo):
                modelo[f.letra] = "V"
            elif isinstance(f, Negacion) and isinstance(f.operando, Atomo):
                modelo[f.operando.letra] = "F"
        return modelo


class MotorTableau:
    """
    Construye y desarrolla el árbol semántico aplicando las 9 reglas de expansión:
    - Reglas α (lineales, no bifurcan): ∧, ¬∨, ¬→, ¬¬
    - Reglas β (bifurcan en 2 ramas)  : ∨, →, ↔, ¬∧, ¬↔
    """
    def __init__(self, formulas_iniciales: List[Formula]):
        self.contador_lineas = 1
        self.paso_actual = 0
        self.bitacora_pasos: List[str] = []

        items_raiz = []
        for idx, f in enumerate(formulas_iniciales, 1):
            items_raiz.append(ItemFormula(self.contador_lineas, f, f"Regla R{idx}"))
            self.contador_lineas += 1

        self.raiz = NodoTableau(items_raiz)
        self.raiz.verificar_cierre()

    @staticmethod
    def clasificar_formula(f: Formula) -> Optional[Tuple[str, str, List[List[Formula]]]]:
        if f.es_literal():
            return None

        # --- REGLAS ALFA (No bifurcan) ---
        if isinstance(f, Negacion) and isinstance(f.operando, Negacion):
            return ("α", "Doble negación (¬¬)", [[f.operando.operando]])

        if isinstance(f, Binaria) and f.op == "∧":
            return ("α", "Conjunción (∧)", [[f.izq, f.der]])

        if isinstance(f, Negacion) and isinstance(f.operando, Binaria) and f.operando.op == "∨":
            return ("α", "Negación de disyunción (¬∨)", [[Negacion(f.operando.izq), Negacion(f.operando.der)]])

        if isinstance(f, Negacion) and isinstance(f.operando, Binaria) and f.operando.op == "→":
            return ("α", "Negación de condicional (¬→)", [[f.operando.izq, Negacion(f.operando.der)]])

        # --- REGLAS BETA (Bifurcan en 2 ramas) ---
        if isinstance(f, Binaria) and f.op == "∨":
            return ("β", "Disyunción (∨)", [[f.izq], [f.der]])

        if isinstance(f, Binaria) and f.op == "→":
            return ("β", "Condicional (→)", [[Negacion(f.izq)], [f.der]])

        if isinstance(f, Binaria) and f.op == "↔":
            return (
                "β",
                "Bicondicional (↔)",
                [[f.izq, f.der], [Negacion(f.izq), Negacion(f.der)]],
            )

        if isinstance(f, Negacion) and isinstance(f.operando, Binaria) and f.operando.op == "∧":
            return ("β", "Negación de conjunción (¬∧)", [[Negacion(f.operando.izq)], [Negacion(f.operando.der)]])

        if isinstance(f, Negacion) and isinstance(f.operando, Binaria) and f.operando.op == "↔":
            return (
                "β",
                "Negación de bicondicional (¬↔)",
                [[f.operando.izq, Negacion(f.operando.der)], [Negacion(f.operando.izq), f.operando.der]],
            )

        return None

    def _buscar_siguiente_formula_a_expandir(self) -> Optional[Tuple[NodoTableau, ItemFormula]]:
        candidatos_alfa: List[Tuple[NodoTableau, ItemFormula]] = []
        candidatos_beta: List[Tuple[NodoTableau, ItemFormula]] = []

        cola = [self.raiz]
        while cola:
            nodo = cola.pop(0)
            hojas_abiertas = nodo.obtener_hojas_abiertas_debajo()
            if hojas_abiertas:
                for item in nodo.items:
                    if not item.aplicada and not item.formula.es_literal():
                        info = self.clasificar_formula(item.formula)
                        if info:
                            if info[0] == "α":
                                candidatos_alfa.append((nodo, item))
                            else:
                                candidatos_beta.append((nodo, item))
            for h in nodo.hijos:
                cola.append(h)

        if candidatos_alfa:
            return candidatos_alfa[0]
        if candidatos_beta:
            return candidatos_beta[0]
        return None

    def construir(self):
        while True:
            seleccion = self._buscar_siguiente_formula_a_expandir()
            if seleccion is None:
                break

            nodo_origen, item = seleccion
            info = self.clasificar_formula(item.formula)
            if info is None:
                break

            tipo_regla, nombre_regla, ramas_formulas = info
            hojas_abiertas = nodo_origen.obtener_hojas_abiertas_debajo()

            if not hojas_abiertas:
                item.aplicada = True
                continue

            self.paso_actual += 1
            item.aplicada = True
            item.paso_aplicacion = self.paso_actual

            desc_ramas = " | ".join([", ".join(str(f) for f in r) for r in ramas_formulas])
            self.bitacora_pasos.append(
                f"Paso {self.paso_actual}: Aplicada [{nombre_regla}] sobre ({item.id_linea}) {item.formula} "
                f"==> genera [{desc_ramas}] en {len(hojas_abiertas)} rama(s) abierta(s) debajo."
            )

            for hoja in hojas_abiertas:
                for sub_formulas in ramas_formulas:
                    nuevos_items = []
                    for sf in sub_formulas:
                        nuevos_items.append(
                            ItemFormula(
                                self.contador_lineas,
                                sf,
                                f"De ({item.id_linea}) por {nombre_regla}",
                            )
                        )
                        self.contador_lineas += 1
                    nuevo_hijo = NodoTableau(nuevos_items, padre=hoja)
                    nuevo_hijo.verificar_cierre()
                    hoja.hijos.append(nuevo_hijo)


# ==============================================================================
# 4. RENDERIZADOR VISUAL 2D DEL ÁRBOL EN CONSOLA (UNICODE BOX TREE)
# ==============================================================================
class RenderizadorArbolConsola:
    """Dibuja el árbol semántico jerárquicamente en 2D con cajas y flechas Unicode."""

    @classmethod
    def renderizar(cls, raiz: NodoTableau) -> str:
        lineas, _ = cls._renderizar_subarbol(raiz)
        return "\n".join(lineas)

    @classmethod
    def _crear_caja_nodo(cls, nodo: NodoTableau) -> Tuple[List[str], int]:
        lineas_contenido = [item.texto_mostrar() for item in nodo.items]

        if nodo.es_hoja():
            if nodo.cerrada:
                lineas_contenido.append(f"✕ CERRADA ({nodo.atomo_contradiccion} y ¬{nodo.atomo_contradiccion})")
            else:
                modelo = nodo.obtener_modelo()
                asig = ", ".join(f"{k}={v}" for k, v in sorted(modelo.items()))
                lineas_contenido.append("◯ ABIERTA")
                lineas_contenido.append(f"  {{{asig}}}")

        ancho_interno = max(len(l) for l in lineas_contenido)
        borde_sup = "┌─" + "─" * ancho_interno + "─┐"
        cuerpo = ["│ " + l.ljust(ancho_interno) + " │" for l in lineas_contenido]
        borde_inf = "└─" + "─" * ancho_interno + "─┘"

        caja = [borde_sup] + cuerpo + [borde_inf]
        ancho_total = ancho_interno + 4
        return caja, ancho_total // 2

    @classmethod
    def _renderizar_subarbol(cls, nodo: NodoTableau) -> Tuple[List[str], int]:
        caja, centro_caja = cls._crear_caja_nodo(nodo)
        ancho_caja = len(caja[0])

        if not nodo.hijos:
            return caja, centro_caja

        if len(nodo.hijos) == 1:
            lineas_hijo, centro_hijo = cls._renderizar_subarbol(nodo.hijos[0])
            ancho_hijo = len(lineas_hijo[0])

            centro_comun = max(centro_caja, centro_hijo)
            pad_izq_caja = centro_comun - centro_caja
            pad_izq_hijo = centro_comun - centro_hijo

            ancho_total = max(pad_izq_caja + ancho_caja, pad_izq_hijo + ancho_hijo)

            caja_alineada = [
                (" " * pad_izq_caja + l).ljust(ancho_total) for l in caja
            ]
            ultima = list(caja_alineada[-1])
            ultima[centro_comun] = "┬"
            caja_alineada[-1] = "".join(ultima)

            flecha = (" " * centro_comun + "▼").ljust(ancho_total)
            hijo_alineado = [
                (" " * pad_izq_hijo + l).ljust(ancho_total) for l in lineas_hijo
            ]

            return caja_alineada + [flecha] + hijo_alineado, centro_comun

        izq_lineas, izq_centro = cls._renderizar_subarbol(nodo.hijos[0])
        der_lineas, der_centro = cls._renderizar_subarbol(nodo.hijos[1])

        ancho_izq = len(izq_lineas[0])
        ancho_der = len(der_lineas[0])
        separacion = 4

        altura_max = max(len(izq_lineas), len(der_lineas))
        izq_padded = izq_lineas + [" " * ancho_izq] * (altura_max - len(izq_lineas))
        der_padded = der_lineas + [" " * ancho_der] * (altura_max - len(der_lineas))

        hijos_combinados = [
            l + (" " * separacion) + r for l, r in zip(izq_padded, der_padded)
        ]

        c1 = izq_centro
        c2 = ancho_izq + separacion + der_centro
        punto_medio = (c1 + c2) // 2

        if centro_caja > punto_medio:
            desplazamiento = centro_caja - punto_medio
            hijos_combinados = [" " * desplazamiento + l for l in hijos_combinados]
            c1 += desplazamiento
            c2 += desplazamiento
            punto_medio += desplazamiento
            pad_izq_caja = 0
        else:
            pad_izq_caja = punto_medio - centro_caja

        ancho_total = max(pad_izq_caja + ancho_caja, len(hijos_combinados[0]))

        caja_alineada = [
            (" " * pad_izq_caja + l).ljust(ancho_total) for l in caja
        ]
        ultima = list(caja_alineada[-1])
        ultima[punto_medio] = "┬"
        caja_alineada[-1] = "".join(ultima)

        hijos_alineados = [l.ljust(ancho_total) for l in hijos_combinados]

        linea_rama = [" "] * ancho_total
        linea_rama[c1] = "┌"
        for i in range(c1 + 1, c2):
            linea_rama[i] = "─"
        linea_rama[c2] = "┐"
        linea_rama[punto_medio] = "┴"

        linea_flechas = [" "] * ancho_total
        linea_flechas[c1] = "▼"
        linea_flechas[c2] = "▼"

        return (
            caja_alineada
            + ["".join(linea_rama), "".join(linea_flechas)]
            + hijos_alineados,
            punto_medio,
        )


# ==============================================================================
# 5. INTERFAZ GRÁFICA INTERACTIVA CON SELECTOR Y GUARDADO POR NOMBRE (TKINTER)
# ==============================================================================
def abrir_visor_grafico():
    """Abre la ventana gráfica con selector de escenarios guardados y guardado con nombre."""
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except ImportError:
        print("Tkinter no está instalado en este entorno. Usa las opciones en consola.")
        return

    nombre_inicial, reglas_iniciales = GestorEscenarios.obtener_ultimo_escenario()

    ventana = tk.Tk()
    ventana.title(f"Árboles Semánticos (Tableaux) - Escenario: {nombre_inicial}")
    ventana.geometry("1240x860")
    ventana.configure(bg="#f8fafc")

    # --- Barra superior: Selector y Guardado de Escenarios por Nombre ---
    barra_escenarios = tk.Frame(ventana, bg="#cbd5e1", padx=12, pady=8)
    barra_escenarios.pack(fill=tk.X)

    tk.Label(
        barra_escenarios,
        text="📂 Escenarios guardados:",
        bg="#cbd5e1",
        fg="#0f172a",
        font=("Consolas", 10, "bold"),
    ).pack(side=tk.LEFT)

    nombres_guardados = [n for n, _ in GestorEscenarios.listar_escenarios()]
    combo_escenarios = ttk.Combobox(
        barra_escenarios,
        values=nombres_guardados,
        width=36,
        font=("Consolas", 10),
        state="readonly",
    )
    if nombre_inicial in nombres_guardados:
        combo_escenarios.set(nombre_inicial)
    elif nombres_guardados:
        combo_escenarios.set(nombres_guardados[0])
    combo_escenarios.pack(side=tk.LEFT, padx=6)

    # Entrada para guardar con un nuevo nombre
    tk.Label(
        barra_escenarios,
        text="   ✏️ Nombre para guardar:",
        bg="#cbd5e1",
        fg="#0f172a",
        font=("Consolas", 10, "bold"),
    ).pack(side=tk.LEFT, padx=(10, 4))

    entry_nombre = tk.Entry(barra_escenarios, width=28, font=("Consolas", 10))
    entry_nombre.insert(0, nombre_inicial)
    entry_nombre.pack(side=tk.LEFT, padx=4)

    # --- Panel de edición de reglas ---
    panel_sup = tk.Frame(ventana, bg="#e2e8f0", padx=12, pady=8)
    panel_sup.pack(fill=tk.X)

    tk.Label(
        panel_sup,
        text="Reglas de la Base de Conocimiento (escribe una oración en español por línea):",
        bg="#e2e8f0",
        fg="#0f172a",
        font=("Consolas", 11, "bold"),
    ).pack(anchor="w")

    frame_entrada = tk.Frame(panel_sup, bg="#e2e8f0")
    frame_entrada.pack(fill=tk.X, pady=4)

    txt_reglas = tk.Text(frame_entrada, height=5, font=("Consolas", 11), bg="#ffffff", fg="#0f172a")
    txt_reglas.pack(side=tk.LEFT, fill=tk.X, expand=True)
    txt_reglas.insert("1.0", "\n".join(reglas_iniciales))

    txt_info = tk.Text(
        panel_sup,
        height=8,
        font=("Consolas", 10),
        bg="#0f172a",
        fg="#f8fafc",
        padx=10,
        pady=6,
    )
    txt_info.pack(fill=tk.X, pady=4)

    # --- Lienzo del árbol ---
    frame_canvas = tk.Frame(ventana, bg="#ffffff")
    frame_canvas.pack(fill=tk.BOTH, expand=True)

    hbar = tk.Scrollbar(frame_canvas, orient=tk.HORIZONTAL)
    hbar.pack(side=tk.BOTTOM, fill=tk.X)
    vbar = tk.Scrollbar(frame_canvas, orient=tk.VERTICAL)
    vbar.pack(side=tk.RIGHT, fill=tk.Y)

    canvas = tk.Canvas(
        frame_canvas,
        bg="#ffffff",
        xscrollcommand=hbar.set,
        yscrollcommand=vbar.set,
    )
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    hbar.config(command=canvas.xview)
    vbar.config(command=canvas.yview)

    def actualizar_lista_combo(seleccionar: Optional[str] = None):
        lista = [n for n, _ in GestorEscenarios.listar_escenarios()]
        combo_escenarios["values"] = lista
        if seleccionar and seleccionar in lista:
            combo_escenarios.set(seleccionar)

    def calcular_ancho_subarbol(nodo: NodoTableau) -> int:
        if not nodo.hijos:
            return 260
        return sum(calcular_ancho_subarbol(h) for h in nodo.hijos) + 40 * (len(nodo.hijos) - 1)

    def dibujar_nodo(nodo: NodoTableau, x_centro: int, y_top: int):
        lineas = [item.texto_mostrar() for item in nodo.items]
        color_fondo = "#f1f5f9"
        color_borde = "#475569"

        if nodo.es_hoja():
            if nodo.cerrada:
                lineas.append(f"✕ CERRADA ({nodo.atomo_contradiccion} y ¬{nodo.atomo_contradiccion})")
                color_fondo = "#fee2e2"
                color_borde = "#dc2626"
            else:
                asig = ", ".join(f"{k} = {v}" for k, v in sorted(nodo.obtener_modelo().items()))
                lineas.append(f"◯ ABIERTA: {asig}")
                color_fondo = "#dcfce7"
                color_borde = "#16a34a"

        ancho_caja = max(220, max(len(l) for l in lineas) * 8 + 28)
        alto_caja = len(lineas) * 20 + 18

        x1 = x_centro - ancho_caja // 2
        y1 = y_top
        x2 = x_centro + ancho_caja // 2
        y2 = y_top + alto_caja

        canvas.create_rectangle(x1, y1, x2, y2, fill=color_fondo, outline=color_borde, width=2)
        for i, linea in enumerate(lineas):
            canvas.create_text(
                x_centro,
                y1 + 14 + i * 20,
                text=linea,
                font=("Consolas", 10, "bold" if "✕" in linea or "◯" in linea else "normal"),
                fill="#0f172a",
            )

        if nodo.hijos:
            ancho_total_hijos = calcular_ancho_subarbol(nodo)
            x_cursor = x_centro - ancho_total_hijos // 2
            y_siguiente = y2 + 55

            for h in nodo.hijos:
                w_h = calcular_ancho_subarbol(h)
                x_hijo = x_cursor + w_h // 2
                canvas.create_line(
                    x_centro, y2, x_hijo, y_siguiente, arrow=tk.LAST, width=2, fill="#334155"
                )
                dibujar_nodo(h, x_hijo, y_siguiente)
                x_cursor += w_h + 40

    def resolver_y_dibujar(registrar_ultimo: bool = True):
        canvas.delete("all")
        lineas_texto = [l.strip() for l in txt_reglas.get("1.0", tk.END).splitlines() if l.strip()]
        if not lineas_texto:
            messagebox.showwarning("Aviso", "Escribe al menos una regla en español.")
            return

        nombre_actual = entry_nombre.get().strip() or "Escenario en edición"
        if registrar_ultimo:
            GestorEscenarios.registrar_ultimo_visto(nombre_actual, lineas_texto)
            ventana.title(f"Árboles Semánticos (Tableaux) - Escenario: {nombre_actual}")

        analizador = AnalizadorLenguajeNatural()
        formulas = [analizador.parsear(r) for r in lineas_texto]
        motor = MotorTableau(formulas)
        motor.construir()

        resumen = [f"ESCENARIO ACTIVO: {nombre_actual}"]
        atomos_str = "  |  ".join(
            f"{letra} = «{sig}»" for letra, sig in sorted(analizador.letra_a_significado.items())
        )
        resumen.append(f"TABLA DE ÁTOMOS : {atomos_str}")

        reglas_str = "  |  ".join(f"R{i}: {f}" for i, f in enumerate(formulas, 1))
        resumen.append(f"FÓRMULAS LÓGICAS: {reglas_str}")

        hojas = motor.raiz.obtener_todas_las_hojas()
        abiertas = [h for h in hojas if not h.cerrada]
        cerradas = [h for h in hojas if h.cerrada]

        resumen.append(f"RAMAS DEL ÁRBOL : {len(cerradas)} cerrada(s) (✕) y {len(abiertas)} abierta(s) (◯)")

        if abiertas:
            modelos_lista = []
            for idx, h in enumerate(abiertas, 1):
                m = h.obtener_modelo()
                asig = ", ".join(f"{k} = {v}" for k, v in sorted(m.items()))
                modelos_lista.append(f"Modelo {idx}: {{{asig}}}")
            resumen.append(f"CONCLUSIÓN      : CONSISTENTE -> {' ; '.join(modelos_lista)}")
        else:
            resumen.append(
                "CONCLUSIÓN      : INCONSISTENTE / CONTRADICTORIA (Todas las ramas se cerraron ✕)"
            )

        txt_info.config(state=tk.NORMAL)
        txt_info.delete("1.0", tk.END)
        txt_info.insert("1.0", "\n".join(resumen))
        txt_info.config(state=tk.DISABLED)

        ancho_req = max(1150, calcular_ancho_subarbol(motor.raiz) + 120)
        dibujar_nodo(motor.raiz, ancho_req // 2, 25)
        canvas.configure(scrollregion=canvas.bbox("all"))

    def accion_cargar_seleccionado():
        elegido = combo_escenarios.get().strip()
        if not elegido:
            return
        reglas = GestorEscenarios.cargar_escenario_por_nombre(elegido)
        if reglas:
            txt_reglas.delete("1.0", tk.END)
            txt_reglas.insert("1.0", "\n".join(reglas))
            entry_nombre.delete(0, tk.END)
            entry_nombre.insert(0, elegido)
            resolver_y_dibujar(registrar_ultimo=True)

    def accion_guardar_con_nombre():
        nombre_nuevo = entry_nombre.get().strip()
        if not nombre_nuevo:
            messagebox.showwarning("Falta nombre", "Escribe un nombre en el cuadro 'Nombre para guardar'.")
            return
        lineas_texto = [l.strip() for l in txt_reglas.get("1.0", tk.END).splitlines() if l.strip()]
        if not lineas_texto:
            messagebox.showwarning("Sin reglas", "Escribe al menos una regla antes de guardar.")
            return

        GestorEscenarios.guardar_escenario_con_nombre(nombre_nuevo, lineas_texto)
        actualizar_lista_combo(seleccionar=nombre_nuevo)
        resolver_y_dibujar(registrar_ultimo=True)
        messagebox.showinfo("Escenario guardado", f"Se guardó el escenario «{nombre_nuevo}» correctamente.")

    def accion_eliminar_seleccionado():
        elegido = combo_escenarios.get().strip()
        if not elegido:
            return
        if messagebox.askyesno("Eliminar escenario", f"¿Seguro que deseas eliminar «{elegido}»?"):
            GestorEscenarios.eliminar_escenario(elegido)
            actualizar_lista_combo()
            lista_restante = combo_escenarios["values"]
            if lista_restante:
                combo_escenarios.set(lista_restante[0])

    # Botones en la barra superior de escenarios
    btn_cargar = tk.Button(
        barra_escenarios,
        text="📥 Cargar seleccionado",
        command=accion_cargar_seleccionado,
        bg="#0284c7",
        fg="#ffffff",
        font=("Consolas", 9, "bold"),
        padx=8,
    )
    btn_cargar.pack(side=tk.LEFT, padx=4)

    btn_borrar = tk.Button(
        barra_escenarios,
        text="🗑️",
        command=accion_eliminar_seleccionado,
        bg="#dc2626",
        fg="#ffffff",
        font=("Consolas", 9),
        padx=6,
    )
    btn_borrar.pack(side=tk.LEFT, padx=2)

    btn_guardar = tk.Button(
        barra_escenarios,
        text="💾 Guardar escenario",
        command=accion_guardar_con_nombre,
        bg="#16a34a",
        fg="#ffffff",
        font=("Consolas", 9, "bold"),
        padx=10,
    )
    btn_guardar.pack(side=tk.LEFT, padx=6)

    # Botón principal de construir árbol
    btn_resolver = tk.Button(
        frame_entrada,
        text="Construir Árbol\nSemántico",
        command=lambda: resolver_y_dibujar(registrar_ultimo=True),
        bg="#2563eb",
        fg="#ffffff",
        font=("Consolas", 11, "bold"),
        padx=16,
        pady=10,
    )
    btn_resolver.pack(side=tk.LEFT, padx=10)

    # También carga automáticamente al cambiar la opción del desplegable
    combo_escenarios.bind("<<ComboboxSelected>>", lambda _e: accion_cargar_seleccionado())

    resolver_y_dibujar(registrar_ultimo=False)
    ventana.mainloop()


# ==============================================================================
# 6. FUNCIÓN PRINCIPAL DE REPORTE COMPLETO EN CONSOLA
# ==============================================================================
def procesar_base_conocimiento(titulo: str, reglas_naturales: List[str], registrar_ultimo: bool = True):
    if registrar_ultimo:
        GestorEscenarios.registrar_ultimo_visto(titulo, reglas_naturales)

    print("\n" + "═" * 84)
    print(f"  ESCENARIO: {titulo}")
    print("═" * 84)

    analizador = AnalizadorLenguajeNatural()
    formulas: List[Formula] = []

    print("\n[1] CONECTIVOS LÓGICOS RECONOCIDOS:")
    print("  ┌──────────────────────────┬─────────┬───────────────────────────────────────┐")
    print("  │ Expresión en texto       │ Símbolo │ Reglas de expansión (directa / ¬)     │")
    print("  ├──────────────────────────┼─────────┼───────────────────────────────────────┤")
    print("  │ «no» / «no es cierto que»│    ¬    │ ¬¬ (no bifurca)                       │")
    print("  │ «y»                      │    ∧    │ ∧ (no bifurca)  / ¬∧ (bifurca)        │")
    print("  │ «o»                      │    ∨    │ ∨ (bifurca)     / ¬∨ (no bifurca)     │")
    print("  │ «si… entonces»           │    →    │ → (bifurca)     / ¬→ (no bifurca)     │")
    print("  │ «si y solo si»           │    ↔    │ ↔ (bifurca)     / ¬↔ (bifurca)        │")
    print("  └──────────────────────────┴─────────┴───────────────────────────────────────┘")

    for r in reglas_naturales:
        formulas.append(analizador.parsear(r))

    print("\n[2] TABLA DE ÁTOMOS (PROPOSICIONES SIMPLES):")
    print("  ┌─────────┬──────────────────────────────────────────────────┐")
    print("  │ Letra   │ Significado (proposición simple afirmativa)      │")
    print("  ├─────────┼──────────────────────────────────────────────────┤")
    for letra, significado in sorted(analizador.letra_a_significado.items()):
        print(f"  │   {letra:<5} │ {significado:<48} │")
    print("  └─────────┴──────────────────────────────────────────────────┘")

    print("\n[3] BASE DE CONOCIMIENTO (REGLAS Y SUS FÓRMULAS LÓGICAS):")
    for i, (texto, form) in enumerate(zip(reglas_naturales, formulas), 1):
        print(f"  R{i}: «{texto}»")
        print(f"      Fórmula R{i}: {form}")

    motor = MotorTableau(formulas)
    motor.construir()

    print("\n[4] BITÁCORA DE EXPANSIÓN DEL ÁRBOL (SUPONIENDO R1..Rn VERDADERAS):")
    if motor.bitacora_pasos:
        for paso in motor.bitacora_pasos:
            print(f"  • {paso}")
    else:
        print("  • Todas las reglas iniciales ya son literales atómicos; no se requieren expansiones.")

    print("\n[5] VISUALIZACIÓN DEL ÁRBOL SEMÁNTICO (✓ = Fórmula aplicada, ✕ = Cerrada, ◯ = Abierta):")
    print()
    arbol_ascii = RenderizadorArbolConsola.renderizar(motor.raiz)
    for linea in arbol_ascii.splitlines():
        print("  " + linea)

    hojas = motor.raiz.obtener_todas_las_hojas()
    abiertas = [h for h in hojas if not h.cerrada]
    cerradas = [h for h in hojas if h.cerrada]

    print("\n[6] RESULTADO Y CONDICIONES EN LAS QUE TODAS LAS REGLAS SE CUMPLEN:")
    print(f"  • Total de ramas generadas : {len(hojas)}")
    print(f"  • Ramas cerradas (✕)       : {len(cerradas)}")
    print(f"  • Ramas abiertas (◯)       : {len(abiertas)}")

    if not abiertas:
        print("\n  CONCLUSIÓN: Todas las ramas se cerraron (✕).")
        print("  ==> La base de conocimiento es INCONSISTENTE / INSATISFACIBLE (contradictoria).")
        print("  ==> No existe ninguna asignación de verdad donde todas las reglas se cumplan a la vez.")
    else:
        print("\n  CONCLUSIÓN: La base de conocimiento es CONSISTENTE (satisfacible).")
        print("  ==> Condiciones (modelos) en las que todas las reglas son verdaderas:")
        todas_las_letras = sorted(analizador.letra_a_significado.keys())
        for idx, hoja in enumerate(abiertas, 1):
            modelo = hoja.obtener_modelo()
            asignaciones_str = []
            interpretacion_nl = []
            for letra in todas_las_letras:
                val = modelo.get(letra, "V/F (libre)")
                asignaciones_str.append(f"{letra} = {val}")
                sig = analizador.letra_a_significado[letra]
                if val == "V":
                    interpretacion_nl.append(f"sí ocurre «{sig}»")
                elif val == "F":
                    interpretacion_nl.append(f"NO ocurre «{sig}»")
                else:
                    interpretacion_nl.append(f"«{sig}» puede ser V o F")

            print(f"      Modelo {idx}: {', '.join(asignaciones_str)}")
            print(f"                En español: {'; '.join(interpretacion_nl)}.")
    print("═" * 84)


# ==============================================================================
# 7. MENÚ PRINCIPAL CON GESTIÓN DE ESCENARIOS POR NOMBRE
# ==============================================================================
if __name__ == "__main__":
    # 1. Al arrancar, abre automáticamente el último escenario visto antes de cerrar
    ultimo_titulo, ultimas_reglas = GestorEscenarios.obtener_ultimo_escenario()
    print(f"\n💾 [AUTO-CARGA] Abriendo tu último escenario visto: «{ultimo_titulo}»")
    procesar_base_conocimiento(ultimo_titulo, ultimas_reglas, registrar_ultimo=False)

    # 2. Bucle principal del menú
    while True:
        actual_titulo, actual_reglas = GestorEscenarios.obtener_ultimo_escenario()
        lista_guardados = GestorEscenarios.listar_escenarios()

        print("\n" + "═" * 76)
        print("  MENÚ PRINCIPAL - GESTOR DE ESCENARIOS Y ÁRBOLES SEMÁNTICOS")
        print(f"  📌 Escenario actual cargado: «{actual_titulo}»")
        print("═" * 76)
        print("  [1] Escribir un nuevo escenario en español (y guardarlo con nombre)")
        print(f"  [2] Seleccionar y cargar un escenario guardado ({len(lista_guardados)} disponibles)")
        print("  [3] Guardar o renombrar el escenario actual con un nuevo nombre")
        print("  [4] Eliminar un escenario guardado")
        print("  [5] Abrir Ventana Gráfica Interactiva (con menú desplegable de escenarios)")
        print("  [0] Salir")

        try:
            opcion = input("\n👉 Elige una opción (1-5 o 0): ").strip()
        except EOFError:
            break

        if opcion == "1":
            print("\nEscribe las reglas en español una por una y presiona Enter en cada línea.")
            print("(Deja el renglón vacío y presiona Enter cuando termines de escribir las reglas):\n")
            nuevas_reglas = []
            while True:
                try:
                    linea = input(f"  Regla {len(nuevas_reglas) + 1}: ").strip()
                except EOFError:
                    break
                if not linea:
                    break
                nuevas_reglas.append(linea)

            if nuevas_reglas:
                try:
                    nombre_escenario = input(
                        "\n✏️ Escribe un nombre para guardar este escenario (o Enter para no guardarlo en la lista): "
                    ).strip()
                except EOFError:
                    nombre_escenario = ""

                if nombre_escenario:
                    GestorEscenarios.guardar_escenario_con_nombre(nombre_escenario, nuevas_reglas)
                    procesar_base_conocimiento(nombre_escenario, nuevas_reglas, registrar_ultimo=True)
                    print(f"  ✅ Escenario guardado como «{nombre_escenario}» y establecido como último visto.")
                else:
                    procesar_base_conocimiento("Escenario temporal (Último visto)", nuevas_reglas, registrar_ultimo=True)
                    print("  💾 Quedó registrado como último visto (puedes nombrarlo después con la opción [3]).")
            else:
                print("  ⚠ No ingresaste ninguna regla.")

        elif opcion == "2":
            lista_guardados = GestorEscenarios.listar_escenarios()
            if not lista_guardados:
                print("  ⚠ No hay escenarios guardados todavía.")
                continue

            print("\n📂 ESCENARIOS GUARDADOS DISPONIBLES:")
            for idx, (nombre, reglas) in enumerate(lista_guardados, 1):
                vista_previa = " ; ".join(reglas[:2]) + ("..." if len(reglas) > 2 else "")
                print(f"  [{idx}] {nombre} ({len(reglas)} reglas: {vista_previa})")

            try:
                sel = input(f"\n👉 Escribe el número del escenario a cargar (1-{len(lista_guardados)}) o Enter para cancelar: ").strip()
            except EOFError:
                continue

            if sel.isdigit() and 1 <= int(sel) <= len(lista_guardados):
                nombre_elegido, reglas_elegidas = lista_guardados[int(sel) - 1]
                GestorEscenarios.cargar_escenario_por_nombre(nombre_elegido)
                procesar_base_conocimiento(nombre_elegido, reglas_elegidas, registrar_ultimo=True)
                print(f"  ✅ Escenario «{nombre_elegido}» cargado. Si cierras el programa, abrirá este al iniciar.")
            elif sel:
                print("  ⚠ Número inválido.")

        elif opcion == "3":
            print(f"\nEscenario actual: «{actual_titulo}»")
            for i, r in enumerate(actual_reglas, 1):
                print(f"  R{i}: {r}")
            try:
                nuevo_nombre = input("\n✏️ Escribe el nombre con el que quieres guardar este escenario: ").strip()
            except EOFError:
                nuevo_nombre = ""

            if nuevo_nombre:
                GestorEscenarios.guardar_escenario_con_nombre(nuevo_nombre, actual_reglas)
                print(f"  ✅ Guardado correctamente como «{nuevo_nombre}».")
            else:
                print("  ⚠ Operación cancelada.")

        elif opcion == "4":
            lista_guardados = GestorEscenarios.listar_escenarios()
            if not lista_guardados:
                print("  ⚠ No hay escenarios para eliminar.")
                continue

            print("\n🗑️ SELECCIONA EL ESCENARIO A ELIMINAR:")
            for idx, (nombre, _) in enumerate(lista_guardados, 1):
                print(f"  [{idx}] {nombre}")

            try:
                sel = input(f"\n👉 Número a eliminar (1-{len(lista_guardados)}) o Enter para cancelar: ").strip()
            except EOFError:
                continue

            if sel.isdigit() and 1 <= int(sel) <= len(lista_guardados):
                nombre_borrar, _ = lista_guardados[int(sel) - 1]
                GestorEscenarios.eliminar_escenario(nombre_borrar)
                print(f"  🗑️ Se eliminó el escenario «{nombre_borrar}».")

        elif opcion == "5":
            print("\nAbriendo ventana gráfica... (Cualquier escenario que elijas o guardes ahí quedará como último visto)")
            abrir_visor_grafico()

        elif opcion == "0":
            print(f"Programa finalizado. Al volver a abrirlo cargará: «{actual_titulo}».")
            break
        else:
            print("  ⚠ Opción no válida. Elige un número del 0 al 5.")