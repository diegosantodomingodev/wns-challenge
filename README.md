Set-Content README.md "# WNS Challenge - Data Processing API

Solución al desafío técnico para WNS Asociados. Esta aplicación es una API construida en Python que procesa, normaliza y consolida datos provenientes de múltiples fuentes heterogéneas (Excel, PDF, Markdown) en un almacén de datos unificado.

## 🧠 Decisiones de Diseño y Arquitectura

### 1. Arquitectura Monolítica Ligera
Se sirve frontend y API desde la misma app Python para simplificar despliegue y pruebas.

### 2. Persistencia en JSON
Se usó JSON en lugar de SQL por portabilidad y simplicidad para el alcance del challenge.

### 3. Estrategia de Normalización
Lógica ETL separada en 'normalize_data.py' para modularidad.

### 4. Dockerización
Uso de Dockerfile multietapa para garantizar ejecución idéntica en cualquier entorno.

## ⚖️ Análisis de la Solución

### Fortalezas
* **Flexibilidad:** Fácil adición de nuevos parsers.
* **Portabilidad:** Cero dependencias externas complejas.

### Debilidades y Áreas de Mejora
* **Escalabilidad:** El JSON no escala bien con grandes volúmenes (solución: migrar a SQL).
* **Concurrencia:** Riesgo de 'race conditions' en escritura simultánea.
* **Procesamiento Inteligente (OCR/IA):** Integración futura de librerías como Tesseract/EasyOCR para documentos escaneados y LLMs para extracción de entidades complejas.

## 🛠️ Instalación y Ejecución

### Opción A: Docker (Recomendado)
\`\`\`bash
docker build -t wns-api .
docker run -p 5000:5000 --env-file .env wns-api
\`\`\`

### Opción B: Local
\`\`\`bash
pip install -r requirements.txt
python app.py
\`\`\`
"
