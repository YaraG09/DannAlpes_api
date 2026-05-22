from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime
import os

app = FastAPI()

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Conexión Mongo
#client = MongoClient("mongodb://ISIS2304E10202610:ARSN6yXE2VFh@157.253.236.88:8087")
#db = client["ISIS2304E10202610"]

# Conexión usando variable de entorno MONGO_URI
client = MongoClient(os.environ["MONGO_URI"])
db = client["ISIS2304E10202610"]

@app.get("/")
def inicio():
    return {"estado": "API funcionando correctamente"}


# RESEÑAS 

@app.get("/hoteles/{id_hotel}/resenas")
def get_resenas(id_hotel: str):
    resenas = list(db["resenas"].find({"id_hotel": id_hotel}, {"_id": 0}))
    return resenas

@app.post("/hoteles/{id_hotel}/resenas")
def post_resena(id_hotel: str, datos: dict):
    datos["id_hotel"] = id_hotel
    datos["fecha_creacion"] = datetime.now()
    datos["estado"] = "publicada"
    datos["votos_utilidad"] = 0
    datos["destacada"] = False
    db["resenas"].insert_one(datos)
    return {"mensaje": "Reseña guardada"}

@app.put("/hoteles/{id_hotel}/resenas/{resena_id}")
def editar_resena(id_hotel: str, resena_id: str, datos: dict):
    db["resenas"].update_one(
        {"id_hotel": id_hotel, "resena_id": resena_id},
        {"$set": datos}
    )
    return {"mensaje": "Reseña actualizada"}

@app.delete("/hoteles/{id_hotel}/resenas/{resena_id}")
def eliminar_resena(id_hotel: str, resena_id: str):
    db["resenas"].delete_one({"id_hotel": id_hotel, "resena_id": resena_id})
    return {"mensaje": "Reseña eliminada"}


# VOTOS DE UTILIDAD (colección: votos_utilidad)

@app.get("/hoteles/{id_hotel}/resenas/{id_resena}/votos")
def get_votos(id_hotel: str, id_resena: str):
    votos = list(db["votos_utilidad"].find(
        {"id_resena": id_resena},
        {"_id": 0}
    ))
    return votos


@app.post("/hoteles/{id_hotel}/resenas/{resena_id}/voto")
def votar_resena(id_hotel: str, resena_id: str, datos: dict):
    datos["id_hotel"] = id_hotel
    datos["resena_id"] = resena_id
    datos["fecha_voto"] = datetime.now()
    db["votos_utilidad"].insert_one(datos)

    # Actualizar contador en la reseña
    db["resenas"].update_one(
        {"id_hotel": id_hotel, "resena_id": resena_id},
        {"$inc": {"votos_utilidad": 1}}
    )
    return {"mensaje": "Voto registrado"}


