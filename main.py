from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime
import os
import uuid
 
app = FastAPI()
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)
 
# Conexión usando variable de entorno MONGO_URI
client = MongoClient(os.environ["MONGO_URI"])
db = client["ISIS2304E10202610"]
 
@app.get("/")
def inicio():
    return {"estado": "API funcionando correctamente"}
 
# RF1 - CREAR RESEÑA
@app.post("/hoteles/{id_hotel}/resenas")
def post_resena(id_hotel: str, datos: dict):
    datos["id_hotel"]        = id_hotel
    datos["resena_id"]       = str(uuid.uuid4())
    datos["fecha_creacion"]  = datetime.now().isoformat()
    datos["estado"]          = "publicada"
    datos["votos_utilidad"]  = 0
    datos["destacada"]       = False
    datos["respuesta_hotel"] = None
    db["resenas"].insert_one(datos)
    return {"mensaje": "Reseña guardada", "resena_id": datos["resena_id"]}
 
# RF2 - EDITAR RESEÑA
@app.put("/hoteles/{id_hotel}/resenas/{resena_id}")
def editar_resena(id_hotel: str, resena_id: str, datos: dict):
    db["resenas"].update_one(
        {"id_hotel": id_hotel, "resena_id": resena_id},
        {"$set": {
            "texto":         datos.get("texto"),
            "calificacion":  datos.get("calificacion"),
            "fecha_edicion": datetime.now().isoformat()
        }}
    )
    return {"mensaje": "Reseña actualizada"}
 
# RF3 - ELIMINAR RESEÑA (cliente)
@app.delete("/hoteles/{id_hotel}/resenas/{resena_id}")
def eliminar_resena(id_hotel: str, resena_id: str):
    db["resenas"].update_one(
        {"id_hotel": id_hotel, "resena_id": resena_id},
        {"$set": {"estado": "eliminada"}}
    )
    return {"mensaje": "Reseña eliminada"}
 
# RF4 - CONSULTAR RESEÑAS DE UN HOTEL
@app.get("/hoteles/{id_hotel}/resenas")
def get_resenas(id_hotel: str):
    resenas = list(db["resenas"].find(
        {"id_hotel": id_hotel, "estado": "publicada"},
        {"_id": 0}
    ).sort("fecha_creacion", -1))
    return resenas
 
# RF5 - MARCAR RESEÑA COMO ÚTIL
@app.post("/hoteles/{id_hotel}/resenas/{resena_id}/voto")
def votar_resena(id_hotel: str, resena_id: str, datos: dict):
    datos["id_hotel"]   = id_hotel
    datos["resena_id"]  = resena_id
    datos["fecha_voto"] = datetime.now().isoformat()
    db["votos_utilidad"].insert_one(datos)
    db["resenas"].update_one(
        {"id_hotel": id_hotel, "resena_id": resena_id},
        {"$inc": {"votos_utilidad": 1}}
    )
    return {"mensaje": "Voto registrado"}
 
# RF6 - HISTORIAL DE RESEÑAS PROPIAS DEL CLIENTE
@app.get("/clientes/{id_cliente}/resenas")
def get_resenas_cliente(id_cliente: str):
    resenas = list(db["resenas"].find(
        {"id_cliente": id_cliente},
        {"_id": 0}
    ).sort("fecha_creacion", -1))
    return resenas
 
# RF7 - RESPONDER RESEÑA (administrador)
@app.post("/hoteles/{id_hotel}/resenas/{resena_id}/respuesta")
def responder_resena(id_hotel: str, resena_id: str, datos: dict):
    db["resenas"].update_one(
        {"id_hotel": id_hotel, "resena_id": resena_id},
        {"$set": {
            "respuesta_hotel": {
                "texto":    datos.get("texto_respuesta"),
                "id_admin": datos.get("id_admin"),
                "fecha":    datetime.now().isoformat()
            }
        }}
    )
    return {"mensaje": "Respuesta registrada"}
 
# RF8 - ELIMINAR RESEÑA (administrador)
@app.delete("/admin/hoteles/{id_hotel}/resenas/{resena_id}")
def eliminar_resena_admin(id_hotel: str, resena_id: str):
    db["resenas"].update_one(
        {"id_hotel": id_hotel, "resena_id": resena_id},
        {"$set": {"estado": "eliminada_admin"}}
    )
    return {"mensaje": "Reseña eliminada por administrador"}
 
# RF9 - DESTACAR RESEÑA (administrador)
@app.post("/admin/hoteles/{id_hotel}/resenas/{resena_id}/destacar")
def destacar_resena(id_hotel: str, resena_id: str):
    db["resenas"].update_many(
        {"id_hotel": id_hotel, "destacada": True},
        {"$set": {"destacada": False}}
    )
    db["resenas"].update_one(
        {"id_hotel": id_hotel, "resena_id": resena_id},
        {"$set": {"destacada": True}}
    )
    return {"mensaje": "Reseña destacada"}
 
# RFC1 - TOP 10 HOTELES POR CALIFICACIÓN PROMEDIO
@app.get("/consultas/top-hoteles")
def top_hoteles(fecha_inicio: str = None, fecha_fin: str = None):
    filtro = {"estado": "publicada"}
    if fecha_inicio:
        filtro["fecha_creacion"] = {"$gte": fecha_inicio}
    if fecha_fin:
        filtro.setdefault("fecha_creacion", {})["$lte"] = fecha_fin
    pipeline = [
        {"$match": filtro},
        {"$group": {
            "_id":           "$id_hotel",
            "promedio":      {"$avg": "$calificacion"},
            "total_resenas": {"$sum": 1}
        }},
        {"$sort":  {"promedio": -1}},
        {"$limit": 10},
        {"$project": {
            "_id":           0,
            "id_hotel":      "$_id",
            "promedio":      {"$round": ["$promedio", 2]},
            "total_resenas": 1
        }}
    ]
    return list(db["resenas"].aggregate(pipeline))
 
# RFC2 - EVOLUCIÓN DE REPUTACIÓN MES A MES
@app.get("/consultas/evolucion/{id_hotel}")
def evolucion_hotel(id_hotel: str, anio: int = 2024):
    pipeline = [
        {"$match": {
            "id_hotel": id_hotel,
            "estado":   "publicada",
            "fecha_creacion": {
                "$gte": f"{anio}-01-01",
                "$lte": f"{anio}-12-31"
            }
        }},
        {"$group": {
            "_id":           {"$substr": ["$fecha_creacion", 0, 7]},
            "promedio":      {"$avg": "$calificacion"},
            "total_resenas": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}},
        {"$project": {
            "_id":           0,
            "mes":           "$_id",
            "promedio":      {"$round": ["$promedio", 2]},
            "total_resenas": 1
        }}
    ]
    return list(db["resenas"].aggregate(pipeline))
 
# RFC3 - COMPARATIVO DE HOTELES POR CIUDAD
@app.get("/consultas/comparativo")
def comparativo():
    pipeline = [
        {"$match": {"estado": "publicada"}},
        {"$group": {
            "_id":           "$id_hotel",
            "promedio":      {"$avg": "$calificacion"},
            "total_resenas": {"$sum": 1},
            "con_respuesta": {"$sum": {
                "$cond": [{"$ne": ["$respuesta_hotel", None]}, 1, 0]
            }},
            "destacadas": {"$sum": {
                "$cond": ["$destacada", 1, 0]
            }}
        }},
        {"$project": {
            "_id":           0,
            "id_hotel":      "$_id",
            "promedio":      {"$round": ["$promedio", 2]},
            "total_resenas": 1,
            "con_respuesta": 1,
            "destacadas":    1
        }}
    ]
    return list(db["resenas"].aggregate(pipeline))
 
# AUXILIAR - Ver votos de una reseña
@app.get("/hoteles/{id_hotel}/resenas/{id_resena}/votos")
def get_votos(id_hotel: str, id_resena: str):
    votos = list(db["votos_utilidad"].find({"id_resena": id_resena}, {"_id": 0}))
    return votos

 