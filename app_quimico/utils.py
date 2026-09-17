from app_quimico.models import ElementoQuimico

# Brackets and their matching pairs.
_PARES_APERTURA = {'(': ')', '[': ']', '{': '}'}
_PARES_CIERRE = {cierre: apertura for apertura, cierre in _PARES_APERTURA.items()}

# Allowed characters for strict IUPAC formulas (no whitespace, no punctuation).
_CARACTERES_PERMITIDOS = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789()[]{}')

# Hydrate separators that are explicitly rejected (not supported yet).
_SEPARADORES_HIDRATO = ('.', '·', '⋅', '∙')

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
        if not formula or not formula.strip():
            raise ValueError("Fórmula vacía: ingresá la fórmula química del compuesto.")

        # Hydrates are rejected explicitly to avoid silent miscounting.
        for separador in _SEPARADORES_HIDRATO:
            if separador in formula:
                raise ValueError(
                    "Hidratos no soportados: la fórmula contiene un separador de hidrato ('.' o '·'). "
                    "Esta notación (ej. 'CuSO4·5H2O') todavía no está soportada; ingresá solo la fórmula anhidra."
                )

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
                tokens.append(formula[i:j])
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

    def analizar_formula(self, formula_original):
        """
        Returns (pm_float, elementos_conteo) or raises ValueError with a
        user-friendly Spanish message for invalid input.
        """
        formula = formula_original
        self._validar_formula(formula)

        tokens = self._tokenizar(formula)

        conteo = {}
        multiplicadores_stack = [1]
        factor_actual = 1
        ultimo_subindice = 1

        # Right-to-left stack algorithm preserves group multipliers.
        tokens.reverse()
        for token in tokens:
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
                if cantidad_total == 0:
                    continue
                conteo[simbolo] = conteo.get(simbolo, 0) + cantidad_total
                ultimo_subindice = 1

        if len(multiplicadores_stack) > 1:
            raise ValueError("Fórmula incompleta: falta cerrar uno o más agrupadores.")
        if not conteo:
            raise ValueError("Fórmula vacía o la sintaxis es completamente inválida.")

        pm_total = 0.0
        for simbolo, cantidad in conteo.items():
            peso_atomico = self._obtener_peso_atomico(simbolo)
            if peso_atomico == 0.0:
                raise Exception(f"Error interno: Peso atómico de '{simbolo}' no encontrado en la caché.")
            pm_total += peso_atomico * cantidad

        return pm_total, conteo
