# DS4B Risk Score Analyzer

## Ejecución local

1. Abre una terminal y activa el entorno Python del proyecto.
2. Ve a la carpeta de la API:
   cd 07_despliegue/api
3. Arranca la API:
   uvicorn api.main:app --reload --app-dir ..
4. Abre otra terminal, activa el mismo entorno y ve a la carpeta de la app:
   cd 07_despliegue/app
5. Instala dependencias si es necesario:
   pip install -r requirements.txt
6. Ejecuta la app:
   streamlit run app.py

## Notas
- No cierres la terminal de la API mientras usas la app.
- En local, la API debe estar activa en http://127.0.0.1:8000.
- En producción (Render), la app usa `API_BASE_URL = https://risk-scoring-api-o9ec.onrender.com`.

## Despliegue en Render (guía)
- Root Directory: 07_despliegue/app
- Build Command: pip install -r requirements.txt
- Start Command: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
- Variable manual: PYTHON_VERSION = 3.11.15

