# TFG Gmail Classifier — API Python

## Estructura del proyecto

```
tfg-api/
├── app/
│   ├── main.py               # Entrada FastAPI, registro de routers
│   ├── core/
│   │   ├── config.py         # Variables de entorno (.env)
│   │   ├── database.py       # Conexión PostgreSQL (SQLAlchemy)
│   │   └── security.py       # Autenticación por API Key
│   ├── models/
│   │   └── schemas.py        # Modelos Pydantic (request/response)
│   ├── services/
│   │   ├── classifier.py     # Lógica de clasificación (2 motores)
│   │   ├── keywords.py       # Motor keywords (baseline)
│   │   └── gemini_engine.py  # Motor Google Gemini 2.0 Flash
│   └── routers/
│       ├── classify.py       # POST /classify
│       └── stats.py          # GET /stats, GET /stats/export
├── tests/
│   └── test_classify.py      # Tests básicos
├── .env.example              # Variables de entorno de ejemplo
├── requirements.txt          # Dependencias
└── README.md
```

## Instalación

```bash
# 1. Clonar / subir al VPS
cd /opt
git clone ... tfg-api  # o subir por SFTP

# 2. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
nano .env   # rellenar con tus claves

# 5. Arrancar
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Endpoints

| Método | Ruta               | Descripción                        |
|--------|--------------------|------------------------------------|
| GET    | /health            | Estado de la API                   |
| POST   | /classify          | Clasificar un correo               |
| GET    | /stats             | Estadísticas generales             |
| GET    | /stats/categories  | Distribución por categoría         |
| GET    | /stats/export      | Descarga Excel con todo el historial |
