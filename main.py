from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime
import os
import uuid

app = FastAPI()


# =========================================================
# CONFIGURACIÓN CORS
# =========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# CONEXIÓN MONGODB
# =========================================================
client = MongoClient(os.environ["MONGO_URI"])

db = client["ISIS2304E10202610"]


# =========================================================
# INICIO
# =========================================================
@app.get("/")
def inicio():

    return {
        "estado": "API funcionando correctamente"
    }


# =========================================================
# RF1 - CREAR RESEÑA
# =========================================================
@app.post("/hoteles/{id_hotel}/resenas")
def post_resena(id_hotel: str, datos: dict):

    try:

        nueva_resena = {

            "id_hotel": id_hotel,

            "resena_id": str(uuid.uuid4()),

            "id_reserva": datos.get("id_reserva"),

            "id_cliente": datos.get("id_cliente"),

            "calificacion": int(
                datos.get("calificacion", 0)
            ),

            "texto": datos.get("texto"),

            "fecha_creacion":
                datetime.now().isoformat(),

            "estado": "publicada",

            "votos_utilidad": 0,

            "destacada": False,

            "respuesta_hotel": None
        }

        db["resenas"].insert_one(nueva_resena)

        return {

            "mensaje": "Reseña guardada",

            "resena_id":
                nueva_resena["resena_id"]
        }

    except Exception as e:

        return {
            "error": str(e)
        }


# =========================================================
# RF2 - EDITAR RESEÑA
# =========================================================
@app.put("/hoteles/{id_hotel}/resenas/{resena_id}")
def editar_resena(
    id_hotel: str,
    resena_id: str,
    datos: dict
):

    db["resenas"].update_one(

        {
            "id_hotel": id_hotel,
            "resena_id": resena_id
        },

        {
            "$set": {

                "texto":
                    datos.get("texto"),

                "calificacion":
                    datos.get("calificacion"),

                "fecha_edicion":
                    datetime.now().isoformat()
            }
        }
    )

    return {
        "mensaje": "Reseña actualizada"
    }


# =========================================================
# RF3 - ELIMINAR RESEÑA CLIENTE
# =========================================================
@app.delete("/hoteles/{id_hotel}/resenas/{resena_id}")
def eliminar_resena(
    id_hotel: str,
    resena_id: str
):

    db["resenas"].update_one(

        {
            "id_hotel": id_hotel,
            "resena_id": resena_id
        },

        {
            "$set": {
                "estado": "eliminada"
            }
        }
    )

    return {
        "mensaje": "Reseña eliminada"
    }


# =========================================================
# RF4 - CONSULTAR RESEÑAS HOTEL
# =========================================================
@app.get("/hoteles/{id_hotel}/resenas")
def get_resenas(id_hotel: str):

    try:

        resenas = list(

            db["resenas"].find(

                {
                    "id_hotel": id_hotel,
                    "estado": "publicada"
                },

                {
                    "_id": 0
                }
            ).sort("fecha_creacion", -1)
        )

        return resenas

    except Exception as e:

        return {
            "error": str(e)
        }


# =========================================================
# RF5 - VOTAR RESEÑA
# =========================================================
@app.post(
    "/hoteles/{id_hotel}/resenas/{resena_id}/voto"
)
def votar_resena(
    id_hotel: str,
    resena_id: str,
    datos: dict
):

    datos["id_hotel"] = id_hotel

    datos["resena_id"] = resena_id

    datos["fecha_voto"] = (
        datetime.now().isoformat()
    )

    db["votos_utilidad"].insert_one(datos)

    db["resenas"].update_one(

        {
            "id_hotel": id_hotel,
            "resena_id": resena_id
        },

        {
            "$inc": {
                "votos_utilidad": 1
            }
        }
    )

    return {
        "mensaje": "Voto registrado"
    }


# =========================================================
# RF6 - HISTORIAL CLIENTE
# =========================================================
@app.get("/clientes/{id_cliente}/resenas")
def get_resenas_cliente(id_cliente: str):

    resenas = list(

        db["resenas"].find(

            {
                "id_cliente": id_cliente
            },

            {
                "_id": 0
            }

        ).sort("fecha_creacion", -1)
    )

    return resenas


# =========================================================
# RF7 - RESPONDER RESEÑA
# =========================================================
@app.post(
    "/hoteles/{id_hotel}/resenas/{resena_id}/respuesta"
)
def responder_resena(
    id_hotel: str,
    resena_id: str,
    datos: dict
):

    db["resenas"].update_one(

        {
            "id_hotel": id_hotel,
            "resena_id": resena_id
        },

        {
            "$set": {

                "respuesta_hotel": {

                    "texto":
                        datos.get(
                            "texto_respuesta"
                        ),

                    "id_admin":
                        datos.get(
                            "id_admin"
                        ),

                    "fecha":
                        datetime.now().isoformat()
                }
            }
        }
    )

    return {
        "mensaje": "Respuesta registrada"
    }


# =========================================================
# RF8 - ELIMINAR RESEÑA ADMIN
# =========================================================
@app.delete(
    "/admin/hoteles/{id_hotel}/resenas/{resena_id}"
)
def eliminar_resena_admin(
    id_hotel: str,
    resena_id: str
):

    db["resenas"].update_one(

        {
            "id_hotel": id_hotel,
            "resena_id": resena_id
        },

        {
            "$set": {
                "estado": "eliminada_admin"
            }
        }
    )

    return {
        "mensaje":
            "Reseña eliminada por administrador"
    }


# =========================================================
# RF9 - DESTACAR RESEÑA
# =========================================================
@app.post(
    "/admin/hoteles/{id_hotel}/resenas/{resena_id}/destacar"
)
def destacar_resena(
    id_hotel: str,
    resena_id: str
):

    db["resenas"].update_many(

        {
            "id_hotel": id_hotel,
            "destacada": True
        },

        {
            "$set": {
                "destacada": False
            }
        }
    )

    db["resenas"].update_one(

        {
            "id_hotel": id_hotel,
            "resena_id": resena_id
        },

        {
            "$set": {
                "destacada": True
            }
        }
    )

    return {
        "mensaje": "Reseña destacada"
    }