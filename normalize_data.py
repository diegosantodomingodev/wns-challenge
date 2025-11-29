import json
import re
import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

# Librerías externas (pip install pandas openpyxl pdfplumber)
import pandas as pd
import pdfplumber

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ETL_Pipeline")

# --- CONSTANTES ---
INPUT_DIR = 'inputs'
OUTPUT_FILE = 'data_warehouse.json'


@dataclass
class IngredientItem:
    """Representa un ingrediente dentro de una receta."""
    id: str  
    name: str 
    qty_g: float

@dataclass
class Recipe:
    """Representa una receta completa."""
    name: str
    ingredients: List[IngredientItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "ingredients": [
                {"id": i.id, "name": i.name, "qty_g": i.qty_g} 
                for i in self.ingredients
            ]
        }

# --- nORMALIZACIÓN ---

class NormalizationService:
    
    
    # Source of Truth
    _MASTER_MAP = {
        # Verduras
        "tomate": "tomate", "lechuga": "lechuga", "zanahoria": "zanahoria", 
        "papa": "papa", "cebolla": "cebolla", "morron": "morron", "morrón": "morron", 
        "zapallo": "zapallo", "acelga": "acelga", "espinaca": "espinaca", 
        "brócoli": "brocoli", "brocoli": "brocoli", "coli": "brocoli",
        "berenjena": "berenjena", "calabaza": "calabaza", "pepino": "pepino", 
        "remolacha": "remolacha", "batata": "batata", "choclo": "choclo",
        
        # Carnes & Pescados
        "asado de tira": "asado_de_tira", "asado": "asado_de_tira",
        "vacio": "vacio", "vacío": "vacio",
        "bife de chorizo": "bife_de_chorizo", "lomo": "lomo", "cuadril": "cuadril", 
        "roast beef": "roast_beef", "falda": "falda", "matambre": "matambre", 
        "entraña": "entrana", "carne picada": "carne_picada", "carne picada especial": "carne_picada",
        "bondiola": "bondiola", "costillas": "costillas", "lomo de cerdo": "lomo_cerdo", 
        "jamón fresco": "jamon", "jamon fresco": "jamon", "panceta": "panceta",
        "pollo entero": "pollo", "pollo": "pollo", "pechuga": "pechuga", 
        "muslo": "muslo", "ala": "ala", "patamuslo": "patamuslo", "supremas": "supremas",
        "merluza fresca": "merluza", "merluza": "merluza",
        "salmón rosado": "salmon", "salmon": "salmon", 
        "corvina": "corvina", "lenguado": "lenguado", "pejerrey": "pejerrey", 
        "filet de abadejo": "abadejo", "abadejo": "abadejo",
        "calamar limpio": "calamar", "calamar": "calamar", "mejillones": "mejillones"
    }

    @classmethod
    def normalize(cls, text: str) -> Optional[str]:
        """Limpia el texto y busca una coincidencia en el mapa maestro."""
        if not isinstance(text, str): return None
        
        clean_text = text.lower().strip()
        
        # 1. Búsqueda exacta O(1)
        if clean_text in cls._MASTER_MAP:
            return cls._MASTER_MAP[clean_text]
            
        # 2. Búsqueda parcial (contiene) - O(N) pero robusto para variaciones
        for key, val in cls._MASTER_MAP.items():
            if key in clean_text:
                return val
        return None


class BaseExtractor(ABC):
    """Clase base abstracta para implementar el patrón Strategy."""
    def __init__(self, filename: str):
        self.filepath = os.path.join(INPUT_DIR, filename)

    @abstractmethod
    def extract(self) -> Any:
        pass

    def file_exists(self) -> bool:
        exists = os.path.exists(self.filepath)
        if not exists:
            logger.warning(f"Archivo saltado (no encontrado): {self.filepath}")
        return exists

class PriceExtractor(BaseExtractor):
    @abstractmethod
    def extract(self) -> Dict[str, float]:
        pass

class PDFPriceExtractor(PriceExtractor):
    """Extrae precios de PDFs usando análisis de layout (pdfplumber)."""
    
    def extract(self) -> Dict[str, float]:
        prices = {}
        if not self.file_exists(): return prices

        logger.info(f"Extrayendo precios de PDF: {self.filepath}")
        try:
            with pdfplumber.open(self.filepath) as pdf:
                full_text = "".join([p.extract_text() or "" for p in pdf.pages])
                
                for line in full_text.split('\n'):
                  
                    if '$' in line:
                        parts = line.split('$')
                        name_part = parts[0].strip()
                        
                        price_part_match = re.search(r'([\d\.,]+)', parts[1])
                        
                        if price_part_match:
                            price_str = price_part_match.group(1)
                            norm_key = NormalizationService.normalize(name_part)
                            
                            if norm_key:
                                try:
                                    #  eliminar puntos de mil, coma a punto
                                    final_price = float(price_str.replace('.', '').replace(',', '.'))
                                    prices[norm_key] = final_price
                                except ValueError:
                                    pass
        except Exception as e:
            logger.error(f"Fallo al procesar PDF: {e}")
            
        return prices

class ExcelPriceExtractor(PriceExtractor):
    """Extrae precios de Excel/CSV mediante barrido ."""
    
    def extract(self) -> Dict[str, float]:
        prices = {}
        # Fallback para manejar extensión incorrecta
        if not os.path.exists(self.filepath) and self.filepath.endswith('.xlsx'):
             csv_path = self.filepath.replace('.xlsx', '.xlsx - Hoja1.csv')
             if os.path.exists(csv_path):
                 self.filepath = csv_path
        
        if not self.file_exists(): return prices

        logger.info(f"Extrayendo precios de Excel/CSV: {self.filepath}")
        try:
            # Detectar motor
            if self.filepath.endswith('.csv'):
                df = pd.read_csv(self.filepath, header=None)
            else:
                df = pd.read_excel(self.filepath, header=None)
            
            # Barrido: Buscar patrón (Texto) -> (Precio) en celdas adyacentes
            for r in range(df.shape[0]):
                for c in range(df.shape[1] - 1):
                    val_name = str(df.iat[r, c])
                    val_price = str(df.iat[r, c+1])
                    
                    norm_key = NormalizationService.normalize(val_name)
                    
                    # Validar si val_price parece dinero
                    if norm_key and ('$' in val_price or val_price.replace('.','').isdigit()):
                        try:
                            clean_p = val_price.replace('$', '').replace('.', '').replace(',', '.').strip()
                            prices[norm_key] = float(clean_p)
                        except ValueError: pass
                        
        except Exception as e:
            logger.error(f"Fallo al procesar Excel: {e}")
            
        return prices

class RecipeExtractor(BaseExtractor):
    """Extrae recetas estructuradas desde Markdown."""
    
    def extract(self) -> List[Recipe]:
        recipes = []
        if not self.file_exists(): return recipes

        logger.info(f"Extrayendo recetas de MD: {self.filepath}")
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Dividir por bloques H1 (# Titulo)
            blocks = re.split(r'^#\s+', content, flags=re.MULTILINE)
            
            for block in blocks:
                lines = [l.strip() for l in block.split('\n') if l.strip()]
                if not lines: continue
                
                title = lines[0]
                if "Lista" in title: continue # Saltar índices o basura
                
                ingredients = []
                for line in lines[1:]:
                    parsed_ing = self._parse_ingredient_line(line)
                    if parsed_ing:
                        ingredients.append(parsed_ing)
                
                if ingredients:
                    recipes.append(Recipe(name=title, ingredients=ingredients))
                    
        except Exception as e:
            logger.error(f"Fallo al procesar MD: {e}")
            
        return recipes

    def _parse_ingredient_line(self, line: str) -> Optional[IngredientItem]:
        """Parsea una línea de texto a un objeto ingrediente usando Regex."""
        # Patrón A: "1 kg de Tomate" / "250 grs de ..."
        match = re.search(r'([\d\.,]+)\s*(kg|g|kgs|grs)\s*(?:de)?\s*(.+)', line, re.IGNORECASE)
        
        # Patrón B: "Tomate: 500 g" (Formato inverso)
        if not match:
            match = re.search(r'(.+):\s*([\d\.,]+)\s*(kg|g|kgs|grs)', line, re.IGNORECASE)
            if match:
                prod, cant, unit = match.groups()
            else:
                return None
        else:
            cant, unit, prod = match.groups()
            
        norm_key = NormalizationService.normalize(prod)
        if not norm_key:
            return None
            
        try:
            qty = float(cant.replace(',', '.'))
            # Normalizar todo a gramos
            if unit.lower().startswith('kg'):
                qty *= 1000
            
            return IngredientItem(id=norm_key, name=prod.strip(), qty_g=qty)
        except ValueError:
            return None

# --- (Pipeline) ---

class DataPipeline:
    def __init__(self):
        self.prices_data: Dict[str, float] = {}
        self.recipes_data: List[Recipe] = []

    def run(self):
        logger.info(">>> INICIANDO PIPELINE ETL <<<")
        
        # 1. Ingesta de Precios
        pdf_ex = PDFPriceExtractor("verduleria.pdf")
        xls_ex = ExcelPriceExtractor("Carnes y Pescados.xlsx")
        
        self.prices_data.update(pdf_ex.extract())
        self.prices_data.update(xls_ex.extract())
        
        logger.info(f"Precios consolidados: {len(self.prices_data)} ítems.")

        # 2. Ingesta de Recetas
        md_ex = RecipeExtractor("Recetas.md")
        self.recipes_data = md_ex.extract()
        
        logger.info(f"Recetas procesadas: {len(self.recipes_data)} recetas.")

        # 3. Guardado (Load)
        self._save()
        logger.info(">>> PIPELINE FINALIZADO CON ÉXITO <<<")

    def _save(self):
        output = {
            "metadata": {"version": "2.0", "generated_by": "Python ETL"},
            "prices": self.prices_data,
            "recipes": [r.to_dict() for r in self.recipes_data]
        }
        
        try:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=4, ensure_ascii=False)
            logger.info(f"Data Warehouse guardado en: {os.path.abspath(OUTPUT_FILE)}")
        except IOError as e:
            logger.error(f"Error guardando archivo final: {e}")

# --- inpoint ---
if __name__ == "__main__":
    pipeline = DataPipeline()
    pipeline.run()