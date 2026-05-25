

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId

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

@app.get("/")
def inicio():
    return {"estado": "API funcionando correctamente"}

@app.get('/hoteles/{id_hotel}/resenas')
def get_reseñas_hotel(id_hotel: int):
    
        query = {
            "id_hotel": id_hotel,
            "estado": "publicada"
        }
        cursor = db.resenas.find(query).sort("fecha_creacion", -1)
        lista_reseñas = []
        for reseña in cursor:
            reseña["_id"] = str(reseña["_id"])
            lista_reseñas.append(reseña)
            
        return lista_reseñas

@app.post('/hoteles/{id_hotel}/resenas')
def create_reseña(id_hotel: int, reseña: dict):
        reseña["id_hotel"] = id_hotel
        reseña["fecha_creacion"] = datetime.now().isoformat()
        reseña["fecha_modificacion"] = datetime.now().isoformat()
        reseña["estado"] = "publicada"
        reseña["destacada"]= False
        reseña["votos_utilidad"] = {
            "total": 0,
            "usuarios": []
        }
        reseña['respuesta_admin'] = None
        resultado = db.resenas.insert_one(reseña)
        return {
            'mensaje': 'Reseña guardada con éxito',
            'id_generado': str(resultado.inserted_id)
        }
@app.put('/resenas/{id_resena}')
def editar_reseña(id_resena: str, datos: dict):
    try:
        object_id = ObjectId(id_resena)
    except InvalidId:
        raise HTTPException(status_code=400, detail="ID de reseña inválido")
    
    if "calificacion" not in datos or "texto" not in datos:
        raise HTTPException(status_code=400, detail="Faltan campos: calificacion y texto son requeridos")
    
    filtro = {"_id": object_id}
    nuevos_valores = {
        "$set": {
            "calificacion": datos["calificacion"],
            "texto": datos["texto"],
            "fecha_modificacion": datetime.now().isoformat()
        }
    }
    db.resenas.update_one(filtro, nuevos_valores)
    return {'mensaje': 'Reseña modificada correctamente'}

@app.patch('/resenas/{id_resena}/eliminar')
def eliminar_resena(id_resena: str):
    try:
        object_id = ObjectId(id_resena)
    except InvalidId:
        raise HTTPException(status_code=400, detail="ID de reseña inválido")

    filtro = {"_id": object_id}
    actualizacion = {"$set": {"estado": "eliminada"}}
    db.resenas.update_one(filtro, actualizacion)
    return {'mensaje': 'Reseña eliminada con éxito'}

@app.patch('/resenas/{id_resena}/votar')
def votar_reseña(id_resena: str, datos: dict):
    try:
        object_id = ObjectId(id_resena)
    except InvalidId:
        raise HTTPException(status_code=400, detail="ID de reseña inválido")

    filtro = {"_id": object_id}
    reseña_actual = db.resenas.find_one(filtro)
    
    if reseña_actual is None: 
        raise HTTPException(status_code=404, detail="Reseña no encontrada")
    
    id_usuario_vota = datos["id_cliente"]
    if id_usuario_vota in reseña_actual.get("votos_utilidad", {}).get("usuarios", []):
        raise HTTPException(status_code=400, detail="Ya votaste por esta reseña")
    
    actualizacion = {
        "$inc": {"votos_utilidad.total": 1},
        "$push": {"votos_utilidad.usuarios": id_usuario_vota}
    }
    db.resenas.update_one(filtro, actualizacion)
    return {'mensaje': 'Voto registrado'}

@app.get('/clientes/{id_cliente}/resenas')
def get_historial_cliente(id_cliente: int):
    cursor = db.resenas.find({"id_cliente": id_cliente}).sort("fecha_creacion", -1)
    lista = []
    for r in cursor:
        r["_id"] = str(r["_id"])
        lista.append(r)
    return lista
@app.patch('/resenas/{id_resena}/respuesta')
def responder_reseña(id_resena: str, datos: dict):
    try:
        object_id = ObjectId(id_resena)
    except InvalidId:
        raise HTTPException(status_code=400, detail="ID de reseña inválido")
    filtro = {"_id": object_id}
    actualizacion = {
            "$set": {
                "respuesta_admin": {
                    "texto": datos["texto_respuesta"],
                    "fecha": datetime.now().isoformat()
                }
            }
        }
    db.resenas.update_one(filtro, actualizacion)
    return {'mensaje': 'Respuesta del administrador guardada'}

@app.patch('/resenas/{id_resena}/destacar')
def destacar_reseña(id_resena: str, datos: dict):
    try:
        object_id = ObjectId(id_resena)
    except InvalidId:
        raise HTTPException(status_code=400, detail="ID de reseña inválido")
    
    id_hotel = datos["id_hotel"]
    
    db.resenas.update_many(
        {"id_hotel": id_hotel, "destacada": True},
        {"$set": {"destacada": False}}
    )
    db.resenas.update_one(
        {"_id": object_id},
        {"$set": {"destacada": True}}
    )
    return {'mensaje': 'Reseña marcada como destacada únicamente para este hotel'}
    