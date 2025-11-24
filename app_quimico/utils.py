import re
from decimal import Decimal
from app_quimico.models import ElementoQuimico 
from django.db.models import F # No es estrictamente necesario aquí, pero se mantiene si se usa F-expressions.

class CalculadoraPM:
    """
    Servicio que implementa el Algoritmo Stack (Pila) para calcular el Peso Molecular 
    y descomponer la fórmula, usando la base de datos ElementoQuimico.
    """
    
    def __init__(self):
        # Cache para almacenar los pesos atómicos en memoria
        self.peso_atomico_cache = {} 
        self._cargar_pesos_atomicos()

    def _cargar_pesos_atomicos(self):
        """Carga todos los pesos atómicos de la BD a la caché al iniciar."""
        # Se requiere .values('simbolo_elemento', 'peso_atomico_elemento') basado en tu modelo
        elementos = ElementoQuimico.objects.all().values('simbolo_elemento', 'peso_atomico_elemento')
        
        # Almacenamos usando el símbolo como clave y convertimos el Decimal a float (o Decimal si se prefiere mayor precisión)
        # Usamos float para mantener la lógica original, pero lo convertiremos a Decimal al final.
        self.peso_atomico_cache = {
            e['simbolo_elemento']: float(e['peso_atomico_elemento']) 
            for e in elementos
        }

    def _es_simbolo_valido(self, simbolo: str) -> bool:
        """Verifica si el símbolo existe en el caché de la BD."""
        return simbolo in self.peso_atomico_cache

    def _obtener_peso_atomico(self, simbolo: str) -> float:
        """Obtiene el peso atómico del caché."""
        return self.peso_atomico_cache.get(simbolo, 0.0)

    def analizar_formula(self, formula_original: str):
        """
        Método central que implementa la lógica Stack para obtener el PM y el conteo.
        Devuelve (pm_final_float, elementos_conteo) o lanza ValueError.
        """
        conteo = {}
        multiplicadores_stack = [1] 
        factor_actual = 1 
        
        # Patrón para tokenizar (letra(s), número, agrupador)
        tokens = re.findall(r'([A-Z][a-z]?|\d+|[()\[\]\{\}])', formula_original)
        tokens.reverse() 
        
        ultimo_subindice = 1 

        # 1. ANÁLISIS DE LA FÓRMULA (ALGORITMO STACK)
        for token in tokens:
            if token.isdigit():
                ultimo_subindice = int(token)
            elif token in [')', ']', '}']: # Agregué '}' para completar las llaves
                factor_actual *= ultimo_subindice
                multiplicadores_stack.append(factor_actual)
                ultimo_subindice = 1 
            elif token in ['(', '[', '{']: # Agregué '{'
                if len(multiplicadores_stack) > 1:
                    multiplicadores_stack.pop()
                    factor_actual = multiplicadores_stack[-1]
                    ultimo_subindice = 1
                else:
                    raise ValueError(f"Agrupador de apertura ('{token}') encontrado sin su cierre correspondiente.")

            # Caso 4: Símbolo Químico (Elemento)
            elif token.isalpha():
                simbolo = token
                
                # VALIDACIÓN DE AMBIGÜEDAD (CU vs Cu)
                if len(simbolo) == 2 and simbolo.isupper():
                    simbolo_capitalizado = simbolo.capitalize()
                    if self._es_simbolo_valido(simbolo_capitalizado):
                        raise ValueError(f"Símbolo ambiguo: '{simbolo}'. Nomenclatura IUPAC incorrecta. Use '{simbolo_capitalizado}'.")
                
                if not self._es_simbolo_valido(simbolo):
                    raise ValueError(f"Símbolo no reconocido: '{simbolo}'.")

                cantidad_total = ultimo_subindice * factor_actual
                if cantidad_total == 0: continue 

                conteo[simbolo] = conteo.get(simbolo, 0) + cantidad_total
                ultimo_subindice = 1 
            else:
                raise ValueError(f"Sintaxis inválida: Carácter o token no reconocido: '{token}'.")

        if len(multiplicadores_stack) > 1:
            raise ValueError("Fórmula incompleta: Falta cerrar uno o más agrupadores.")
        if not conteo:
            raise ValueError("Fórmula vacía o la sintaxis es completamente inválida.")
            
        # 2. CÁLCULO DEL PESO MOLECULAR
        pm_total = 0.0
        for simbolo, cantidad in conteo.items():
            peso_atomico = self._obtener_peso_atomico(simbolo)
            if peso_atomico == 0.0:
                raise Exception(f"Error interno: Peso atómico de '{simbolo}' no encontrado en la caché.")
            pm_total += peso_atomico * cantidad
        
        # Devolvemos el PM y el conteo
        return pm_total, conteo