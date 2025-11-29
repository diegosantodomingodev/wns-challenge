# WNS Challenge - Data Processing API

Solución al desafío técnico para WNS Asociados. Esta aplicación es una API construida en Python que procesa, normaliza y consolida datos provenientes de múltiples fuentes heterogéneas (Excel, PDF, Markdown) en un almacén de datos unificado.

## Decisiones de Arquitectura

Para resolver este desafío, se tomaron las siguientes decisiones técnicas:

### 1. Arquitectura Monolítica
Se optó por servir tanto el frontend (`index.html`) como la API desde la misma aplicación Python.
* **Motivo:** Simplifica el despliegue y las pruebas locales al evitar problemas de CORS y la necesidad de levantar múltiples contenedores para una prueba de concepto.

### 2. Persistencia en JSON (`data_warehouse.json`)
En lugar de implementar una base de datos SQL/NoSQL completa (como PostgreSQL o MongoDB), se utilizó un sistema de archivos plano JSON.
* **Motivo:** Para este volumen de datos y el alcance del challenge, un JSON ofrece portabilidad inmediata y cero configuración externa. Permite revisar los datos resultantes con cualquier editor de texto.

### 3. Estrategia de Normalización (`normalize_data.py`)
Se separó la lógica de extracción (ETL) del servidor web (`app.py`).
* **Motivo:** Mantiene el código modular. Si en el futuro se desea cambiar Flask/FastAPI por otro framework, la lógica de negocio en `normalize_data.py` permanece intacta. Se implementaron parsers específicos según la extensión del archivo (`.xlsx`, `.pdf`, `.md`).

### 4. Dockerización
Se incluyó un `Dockerfile` multietapa básico.
* **Motivo:** Garantizar que la aplicación funcione idénticamente en la máquina del evaluador que en el entorno de desarrollo, eliminando el problema de "en mi máquina funciona".

---

## Análisis de la Solución

### Fortalezas
* **Flexibilidad de Formatos:** La arquitectura permite agregar nuevos "parsers" para otros formatos (ej. CSV, XML) simplemente agregando una función nueva en `normalize_data.py` sin romper el resto del sistema.
* **Portabilidad:** Gracias a Docker y al uso de JSON, el proyecto no tiene dependencias de infraestructura externa.
* **Simplicidad:** El código es legible y sigue principios básicos de separación de responsabilidades.

### Debilidades y Áreas de Mejora
* **Escalabilidad de Datos:** El uso de un archivo JSON (`data_warehouse.json`) no es escalable. Si el archivo crece a varios gigabytes, la lectura/escritura en memoria será lenta y bloqueará el servidor.
    * *Mejora propuesta:* Migrar a SQLite o PostgreSQL.
* **Concurrencia:** Actualmente, si dos usuarios envían archivos simultáneamente, podría haber condiciones de carrera (race conditions) al escribir en el archivo JSON.
* **Validación de Errores:** Aunque se manejan excepciones básicas, archivos corruptos o con formatos inesperados dentro del PDF/Excel podrían detener el proceso.
**Transición a Modelo Relacional (SQL):**
    * *Limitación actual:* La persistencia en `JSON` carga todo el dataset en memoria y requiere reescribir el archivo completo ante cualquier cambio. Esto genera bloqueos de I/O y riesgo de corrupción de datos si ocurren escrituras simultáneas (Race Conditions). Además, no garantiza integridad referencial (ej: un ingrediente en una receta que no existe en la lista de precios).
    * *Mejora propuesta:* Migrar a **PostgreSQL** o **SQLite**
        * **Beneficios:**
          1. **Transacciones ACID:** Garantiza que los datos nunca queden en un estado inconsistente ante fallos.
          2. **Integridad Referencial:** Uso de *Foreign Keys* para asegurar que cada ingrediente de una receta exista válidamente en la tabla de productos.
          3. **Consultas Eficientes:** Uso de índices para filtrar recetas por fecha o costo sin recorrer todo el dataset (complejidad O(log n) vs O(n)).

* **Analytics Predictiva (Forecasting):**
    * *Limitación actual:* La aplicación es **reactiva**; solo calcula costos basados en la cotización del día o fechas pasadas. No ofrece valor estratégico para la planificación futura de costos.
    * *Mejora propuesta:* Implementar un modelo de **Regresión Lineal** o **Series Temporales (ARIMA/Prophet)** utilizando librerías como `scikit-learn` o `statsmodels`.
        * **Objetivo:** Entrenar el modelo con el histórico de la cotización del dólar
---------------------------------------------------------------------------------------------------------------------------
##  Instalación y Ejecución

### Requisitos
* Docker (Recomendado)
* O Python 3.9+ instalado localmente

### Opción A: Ejecución con Docker

1. **Construir la imagen:**
   ```bash
   docker build -t wns-api .

### Opción B: Local
\`\`\`bash
pip install -r requirements.txt
python app.py
\`\`\`
"

