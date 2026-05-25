from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime
import os

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

client = MongoClient(os.environ["MONGO_URI"])
db = client["ISIS2304C30202610"]

# Mapa de hoteles por ciudad según Oracle (DA_POBLACION.sql)
HOTELES_POR_CIUDAD = {
    1:  [1, 2],   # Bogotá
    2:  [3, 4],   # Medellín
    3:  [5],      # Cali
    4:  [6],      # Cartagena
    5:  [7],      # Barranquilla
    6:  [8],      # Santa Marta
    7:  [9],      # Bucaramanga
    8:  [10],     # Pereira
    9:  [11],     # Manizales
    10: [12]      # Armenia
}

@app.get("/")
def inicio():
    return {"estado": "API de reportes Dann-Alpes funcionando correctamente"}

# -------------------------------------------------------
# RFC1 - Top 10 hoteles por calificación promedio
# Ejemplo: GET /reportes/top-hoteles?fecha_inicio=2024-06-01&fecha_fin=2025-05-01
# -------------------------------------------------------
@app.get('/reportes/top-hoteles')
def top_hoteles(fecha_inicio: str, fecha_fin: str):
    try:
        dt_inicio = datetime.fromisoformat(fecha_inicio)
        dt_fin    = datetime.fromisoformat(fecha_fin)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")

    pipeline = [
        { "$match": {
            "estado": "publicada",
            "fecha_creacion": {
                "$gte": dt_inicio,
                "$lte": dt_fin
            }
        }},
        { "$group": {
            "_id": "$id_hotel",
            "calificacion_promedio": { "$avg": "$calificacion" },
            "total_resenas": { "$sum": 1 }
        }},
        { "$sort": { "calificacion_promedio": -1 }},
        { "$limit": 10 },
        { "$project": {
            "_id": 0,
            "id_hotel": "$_id",
            "calificacion_promedio": { "$round": ["$calificacion_promedio", 2] },
            "total_resenas": 1
        }}
    ]
    resultado = list(db.resenas.aggregate(pipeline))
    return resultado

# -------------------------------------------------------
# RFC2 - Evolución mes a mes de la calificación de un hotel
# Ejemplo: GET /reportes/evolucion-hotel?id_hotel=1&anio=2024
# -------------------------------------------------------
@app.get('/reportes/evolucion-hotel')
def evolucion_hotel(id_hotel: int, anio: int):
    pipeline = [
        { "$match": {
            "estado": "publicada",
            "id_hotel": id_hotel,
            "fecha_creacion": {
                "$gte": datetime(anio, 1, 1),
                "$lte": datetime(anio, 12, 31)
            }
        }},
        { "$group": {
            "_id": { "mes": { "$month": "$fecha_creacion" }},
            "calificacion_promedio": { "$avg": "$calificacion" },
            "total_resenas": { "$sum": 1 }
        }},
        { "$sort": { "_id.mes": 1 }},
        { "$project": {
            "_id": 0,
            "mes": "$_id.mes",
            "calificacion_promedio": { "$round": ["$calificacion_promedio", 2] },
            "total_resenas": 1
        }}
    ]
    resultado = list(db.resenas.aggregate(pipeline))
    if not resultado:
        raise HTTPException(status_code=404, detail="No hay reseñas para ese hotel en ese año")
    return resultado

# -------------------------------------------------------
# RFC3 - Perfil comparativo de hoteles por ciudad
# Ejemplo: GET /reportes/comparativo-ciudad?id_ciudad=1
# -------------------------------------------------------
@app.get('/reportes/comparativo-ciudad')
def comparativo_ciudad(id_ciudad: int):
    ids_hoteles = HOTELES_POR_CIUDAD.get(id_ciudad)
    if not ids_hoteles:
        raise HTTPException(status_code=404, detail="Ciudad no encontrada")

    pipeline = [
        { "$match": {
            "estado": "publicada",
            "id_hotel": { "$in": ids_hoteles }
        }},
        { "$group": {
            "_id": "$id_hotel",
            "calificacion_promedio": { "$avg": "$calificacion" },
            "total_resenas": { "$sum": 1 },
            "con_respuesta": {
                "$sum": { "$cond": [{ "$ne": ["$respuesta_admin", None] }, 1, 0] }
            },
            "destacadas": {
                "$sum": { "$cond": ["$destacada", 1, 0] }
            }
        }},
        { "$project": {
            "_id": 0,
            "id_hotel": "$_id",
            "calificacion_promedio": { "$round": ["$calificacion_promedio", 2] },
            "total_resenas": 1,
            "pct_con_respuesta": {
                "$round": [{ "$multiply": [{ "$divide": ["$con_respuesta", "$total_resenas"] }, 100] }, 1]
            },
            "pct_destacadas": {
                "$round": [{ "$multiply": [{ "$divide": ["$destacadas", "$total_resenas"] }, 100] }, 1]
            }
        }},
        { "$sort": { "calificacion_promedio": -1 }}
    ]
    resultado = list(db.resenas.aggregate(pipeline))
    return resultado
