import re

from pysmiles import read_smiles, write_smiles

from app_quimico.models import ElementoQuimico

# Brackets and their matching pairs.
_PARES_APERTURA = {'(': ')', '[': ']', '{': '}'}
_PARES_CIERRE = {cierre: apertura for apertura, cierre in _PARES_APERTURA.items()}

# Allowed characters for strict IUPAC formulas (no whitespace, no punctuation).
_CARACTERES_PERMITIDOS = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789()[]{}')

# Hydrate separators: split the formula into segments (e.g. 'CuSO4·5H2O').
# '*' is accepted as the easy-to-type ASCII stand-in for the interpunct.
_SEPARADORES_HIDRATO = ('.', '·', '⋅', '∙', '*')

# Process-wide cache of atomic weights loaded from the DB only once.
_cache_pesos = None


def _cargar_pesos_atomicos():
    """Loads atomic weights from the DB once per process."""
    global _cache_pesos
    if _cache_pesos is None:
        elementos = ElementoQuimico.objects.all().values('simbolo_elemento', 'peso_atomico_elemento')
        _cache_pesos = {
            e['simbolo_elemento']: float(e['peso_atomico_elemento'])
            for e in elementos
        }
    return _cache_pesos


def invalidar_cache_pesos():
    """Drops the per-process weight cache so the next load re-reads the DB.

    Wired to ElementoQuimico post_save/post_delete signals so an updated
    atomic weight is picked up by the next calculation instead of serving
    stale values until process restart.
    """
    global _cache_pesos
    _cache_pesos = None


# Elementos cuyos hidrógenos implícitos se explicitan para el dibujo 2D.
# Decisión de diseño (p2-2d-diagrams T9, opción C): solo O/N/S; el H unido a
# carbono, fósforo o halógeno queda condensado.
_ELEMENTOS_H_EXPLICITOS = frozenset({'O', 'N', 'S'})


def expandir_heteroatomos(smiles):
    """Devuelve ``smiles`` con los H implícitos de O/N/S como átomos ``[H]``.

    Pensado para alimentar el render 2D (SmilesDrawer dibuja los ``[H]``
    escritos), no para almacenar: el SMILES guardado y la clasificación de
    enlace (T7) siguen usando el valor original.

    Defensivo por contrato: ante entrada vacía/None, SMILES no parseable o
    cualquier fallo de escritura devuelve la entrada tal cual, sin levantar,
    de modo que el render nunca se rompe. Sin caché a propósito: son unas
    pocas tarjetas chicas por página.

    Nota de implementación: ``pysmiles.write_smiles`` NO puede emitir ``[H]``
    por sí solo (``write_smiles_component`` llama a
    ``remove_explicit_hydrogens``, que pliega los H simples en ``hcount``).
    Por eso los nodos H agregados llevan ``isotope=''``: con la clave
    ``isotope`` presente, la condición de borrado de
    ``remove_explicit_hydrogens`` no se cumple y el H sobrevive hasta
    ``format_atom``, que lo escribe como ``[H]``. Esto depende de un detalle
    interno de pysmiles 2.1.0 (pineada en requirements.txt); la guarda de
    abajo (si falta ``[H]``, se devuelve el original) y el test de contrato
    lo cubren ante una actualización.
    """
    if not smiles:
        return smiles

    try:
        mol = read_smiles(smiles, zero_order_bonds=False)
    except Exception:
        return smiles

    if mol is None or len(mol.nodes) == 0:
        return smiles

    try:
        siguiente = max(mol) + 1
        agregados = 0
        for idx in list(mol.nodes):
            nodo = mol.nodes[idx]
            if nodo.get('element') not in _ELEMENTOS_H_EXPLICITOS:
                continue
            cantidad = nodo.get('hcount', 0) or 0
            if cantidad <= 0:
                continue
            for _ in range(cantidad):
                mol.add_node(siguiente, element='H', charge=0, hcount=0, isotope='')
                mol.add_edge(idx, siguiente, order=1)
                siguiente += 1
                agregados += 1
            # Los H ya son átomos: el hcount implícito debe quedar en cero
            # para que el writer no los cuente dos veces.
            nodo['hcount'] = 0
        resultado = write_smiles(mol)
    except Exception:
        return smiles

    if agregados and '[H]' not in resultado:
        return smiles

    return resultado


class CalculadoraPM:
    """Calculates molecular weight and element counts using the stack algorithm."""

    def __init__(self, pesos_atomicos=None):
        # Optional injection enables pure unit tests without a database.
        if pesos_atomicos is not None:
            self.peso_atomico_cache = dict(pesos_atomicos)
        else:
            self.peso_atomico_cache = _cargar_pesos_atomicos()

    def _es_simbolo_valido(self, simbolo):
        return simbolo in self.peso_atomico_cache

    def _obtener_peso_atomico(self, simbolo):
        return self.peso_atomico_cache.get(simbolo, 0.0)

    def _validar_formula(self, formula):
        """Validates one anhydrous segment (no hydrate separator inside)."""
        if not formula or not formula.strip():
            raise ValueError("Fórmula vacía: ingresá la fórmula química del compuesto.")

        for caracter in formula:
            if caracter not in _CARACTERES_PERMITIDOS:
                raise ValueError(
                    f"Sintaxis inválida: el carácter '{caracter}' no está permitido. "
                    "Usá nomenclatura IUPAC: símbolos que inician con mayúscula, números y agrupadores ( ), [ ] o { }."
                )

        self._validar_balance(formula)

    def _validar_balance(self, formula):
        stack = []
        for caracter in formula:
            if caracter in _PARES_APERTURA:
                stack.append(caracter)
            elif caracter in _PARES_CIERRE:
                if not stack or stack[-1] != _PARES_CIERRE[caracter]:
                    raise ValueError(
                        f"Agrupador desbalanceado: el cierre '{caracter}' no tiene una apertura correspondiente."
                    )
                stack.pop()
        if stack:
            raise ValueError(f"Agrupador desbalanceado: falta cerrar el agrupador '{stack[-1]}'.")

    def _normalizar_hidratos(self, formula):
        """Rewrites the accepted hydrate spellings into one canonical form.

        Whitespace around an explicit separator is irrelevant because the
        segments are stripped later, so it is dropped first; this keeps the
        substitution below from emitting two separators back to back when the
        user writes 'CuSO4 · 5H2O'. Whitespace directly before a digit is the
        separator itself, so 'CuSO4 5H2O' (and 'CuSO4   5H2O') behave exactly
        like 'CuSO4*5H2O'. Any other whitespace (before a letter or bracket) is
        preserved so strict validation still rejects 'Cu SO4' or 'CuSO4 H2O'.
        """
        formula = re.sub(r'\s*([.·⋅∙*])\s*', r'\1', formula)
        return re.sub(r'\s+(?=\d)', '*', formula)

    def _dividir_hidratos(self, formula):
        """Splits a raw formula on every hydrate separator, preserving order.

        A single-element result means the formula has no hydrate notation.
        """
        segmentos = [formula]
        for separador in _SEPARADORES_HIDRATO:
            siguientes = []
            for segmento in segmentos:
                siguientes.extend(segmento.split(separador))
            segmentos = siguientes
        return segmentos

    def _extraer_coeficiente_hidrato(self, segmento):
        """Splits a hydrate segment into (coeficiente, fórmula restante).

        The leading integer is optional and defaults to 1; zero is rejected
        with the same reasoning as a zero subscript.
        """
        i = 0
        n = len(segmento)
        while i < n and segmento[i].isdigit():
            i += 1
        if i == 0:
            return 1, segmento
        token = segmento[:i]
        if token.strip('0') == '':
            raise ValueError(
                "Coeficiente de hidrato inválido: el coeficiente '0' no tiene sentido químico. "
                "Los coeficientes de hidrato deben ser enteros positivos (ej. 'CuSO4·5H2O')."
            )
        return int(token), segmento[i:]

    def _tokenizar(self, formula):
        # Position-based scan: no character can be silently dropped.
        tokens = []
        i = 0
        n = len(formula)
        while i < n:
            caracter = formula[i]
            if caracter.isdigit():
                j = i
                while j < n and formula[j].isdigit():
                    j += 1
                token = formula[i:j]
                if token.strip('0') == '':
                    raise ValueError(
                        "Subíndice inválido: el subíndice '0' no tiene sentido químico. "
                        "Los subíndices deben ser enteros positivos (ej. 'H2O', no 'H0')."
                    )
                tokens.append(token)
                i = j
            elif caracter in _PARES_APERTURA or caracter in _PARES_CIERRE:
                tokens.append(caracter)
                i += 1
            elif caracter.isupper():
                j = i + 1
                if j < n and formula[j].islower():
                    j += 1
                tokens.append(formula[i:j])
                i = j
            else:
                # Lowercase-first token (e.g. 'cU', 'uc').
                raise ValueError(
                    f"Símbolo inválido: '{caracter}' no inicia con mayúscula. "
                    "Usá nomenclatura IUPAC (ej. 'Na' para sodio, 'Cl' para cloro)."
                )
        return tokens

    def _contar_tokens(self, tokens):
        """Counts atoms for one parsed segment using the right-to-left stack.

        Returns a {símbolo: cantidad} map without applying any hydrate
        coefficient; the caller merges segments.
        """
        conteo = {}
        multiplicadores_stack = [1]
        factor_actual = 1
        ultimo_subindice = 1

        # Right-to-left stack algorithm preserves group multipliers.
        for token in reversed(tokens):
            if token.isdigit():
                ultimo_subindice = int(token)
            elif token in _PARES_CIERRE:
                factor_actual *= ultimo_subindice
                multiplicadores_stack.append(factor_actual)
                ultimo_subindice = 1
            elif token in _PARES_APERTURA:
                if len(multiplicadores_stack) > 1:
                    multiplicadores_stack.pop()
                    factor_actual = multiplicadores_stack[-1]
                    ultimo_subindice = 1
                else:
                    raise ValueError(f"Agrupador de apertura ('{token}') sin su cierre correspondiente.")
            else:
                simbolo = token
                if not self._es_simbolo_valido(simbolo):
                    raise ValueError(f"Símbolo no reconocido: '{simbolo}'. Verificá la nomenclatura IUPAC.")
                cantidad_total = ultimo_subindice * factor_actual
                if cantidad_total <= 0:
                    # Unreachable since zero subscripts are rejected by the tokenizer;
                    # kept as a defensive invariant against silent zero counts.
                    raise ValueError("Subíndice inválido: se produjo un conteo de cero átomos.")
                conteo[simbolo] = conteo.get(simbolo, 0) + cantidad_total
                ultimo_subindice = 1

        if len(multiplicadores_stack) > 1:
            raise ValueError("Fórmula incompleta: falta cerrar uno o más agrupadores.")
        return conteo

    def analizar_formula(self, formula_original):
        """
        Returns (pm_float, elementos_conteo) or raises ValueError with a
        user-friendly Spanish message for invalid input.

        Hydrate notation is supported: separators break the formula into
        segments, and every segment after the first accepts an optional
        leading positive integer coefficient that multiplies the whole
        segment (e.g. 'CuSO4·5H2O' = CuSO4 + 5 x H2O). The separator may be
        omitted before a spaced coefficient, so 'CuSO4 5H2O' is equivalent.
        """
        if not formula_original or not formula_original.strip():
            raise ValueError("Fórmula vacía: ingresá la fórmula química del compuesto.")

        segmentos = self._dividir_hidratos(self._normalizar_hidratos(formula_original))
        tiene_hidrato = len(segmentos) > 1

        conteo_total = {}
        for indice, segmento in enumerate(segmentos):
            texto = segmento.strip()
            coeficiente = 1
            if tiene_hidrato and indice > 0:
                # The anhydrous part has no coefficient; hydrate parts may.
                coeficiente, texto = self._extraer_coeficiente_hidrato(texto)

            if not texto:
                if tiene_hidrato and indice == 0:
                    raise ValueError(
                        "Hidrato inválido: la fórmula no puede empezar con un separador de hidrato. "
                        "Indicá primero la fórmula anhidra (ej. 'CuSO4·5H2O')."
                    )
                raise ValueError(
                    "Hidrato inválido: falta la fórmula de uno de los segmentos del hidrato "
                    "(ej. 'CuSO4·5H2O')."
                )

            self._validar_formula(texto)
            conteo_segmento = self._contar_tokens(self._tokenizar(texto))
            if not conteo_segmento:
                raise ValueError("Fórmula vacía o la sintaxis es completamente inválida.")

            for simbolo, cantidad in conteo_segmento.items():
                conteo_total[simbolo] = conteo_total.get(simbolo, 0) + cantidad * coeficiente

        pm_total = 0.0
        for simbolo, cantidad in conteo_total.items():
            peso_atomico = self._obtener_peso_atomico(simbolo)
            if peso_atomico == 0.0:
                raise Exception(f"Error interno: Peso atómico de '{simbolo}' no encontrado en la caché.")
            pm_total += peso_atomico * cantidad

        return pm_total, conteo_total
