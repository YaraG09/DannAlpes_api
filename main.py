from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from datetime import datetime
import os
import uuid

app = FastAPI()

# =========================================================
# OPTIONS - Preflight CORS
# =========================================================
@app.options("/{rest_of_path:path}")
async def options_handler(request: Request, rest_of_path: str):
    response = JSONResponse(content={})
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

# =========================================================
# CORS Middleware
# =========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# Middleware - fuerza headers CORS en todas las respuestas
# =========================================================
@app.middleware("http")
async def add_cors(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

# =========================================================
# MONGODB
# =========================================================
client = MongoClient(os.environ["MONGO_URI"])
db = client["ISIS2304E10202610"]

# =========================================================
# INICIO
# =========================================================
@app.get("/")
def inicio():
    return {"estado": "API funcionando correctamente"}

# =========================================================
# RF1 - CREAR RESEÑA
# =========================================================
@app.post("/hoteles/{id_hotel}/resenas")
def post_resena(id_hotel: str, datos: dict):
    try:
        nueva_resena = {
            "id_hotel":        str(id_hotel),
            "resena_id":       str(uuid.uuid4()),
            "id_reserva":      str(datos.get("id_reserva")),
            "id_cliente":      str(datos.get("id_cliente")),
            "calificacion":    int(datos.get("calificacion", 0)),
            "texto":           str(datos.get("texto")),
            "fecha_creacion":  datetime.now(),
            "estado":          "publicada",
            "votos_utilidad":  0,
            "destacada":       False,
            "respuesta_hotel": None
        }

        db["resenas"].insert_one(nueva_resena)

        return {
            "mensaje": "Reseña guardada",
            "resena_id": nueva_resena["resena_id"]
        }

    except Exception as e:
        return {"error": str(e)}

# =========================================================
# RF2 - EDITAR RESEÑA
# =========================================================
@app.put("/hoteles/{id_hotel}/resenas/{resena_id}")
def editar_resena(id_hotel: str, resena_id: str, datos: dict):

    db["resenas"].update_one(
        {
            "id_hotel": id_hotel,
            "resena_id": resena_id
        },
        {
            "$set": {
                "texto": str(datos.get("texto")),
                "calificacion": int(datos.get("calificacion", 0)),
                "fecha_edicion": datetime.now()
            }
        }
    )

    return {"mensaje": "Reseña actualizada"}

# =========================================================
# RF3 - ELIMINAR RESEÑA CLIENTE
# =========================================================
@app.delete("/hoteles/{id_hotel}/resenas/{resena_id}")
def eliminar_resena(id_hotel: str, resena_id: str):

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

    return {"mensaje": "Reseña eliminada"}

# =========================================================
# RF4 - CONSULTAR RESEÑAS PÚBLICAS
# DESTACADAS PRIMERO
# =========================================================
@app.get("/hoteles/{id_hotel}/resenas")
def get_resenas(id_hotel: str):

    try:

        resenas = list(
            db["resenas"]
            .find(
                {
                    "id_hotel": id_hotel,
                    "estado": "publicada"
                },
                {
                    "_id": 0
                }
            )
            .sort([
                ("destacada", -1),
                ("fecha_creacion", -1)
            ])
        )

        return resenas

    except Exception as e:
        return {"error": str(e)}

# =========================================================
# RF5 - VOTAR RESEÑA
# =========================================================
@app.post("/hoteles/{id_hotel}/resenas/{resena_id}/voto")
def votar_resena(id_hotel: str, resena_id: str, datos: dict):

    voto = {
        "id_resena": str(resena_id),
        "id_usuario": str(datos.get("id_usuario")),
        "fecha_voto": datetime.now()
    }

    db["votos_utilidad"].insert_one(voto)

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

    return {"mensaje": "Voto registrado"}

# =========================================================
# RF6 - HISTORIAL CLIENTE
# =========================================================
@app.get("/clientes/{id_cliente}/resenas")
def get_resenas_cliente(id_cliente: str):

    resenas = list(
        db["resenas"]
        .find(
            {
                "id_cliente": id_cliente
            },
            {
                "_id": 0
            }
        )
        .sort("fecha_creacion", -1)
    )

    return resenas

# =========================================================
# RF7 - RESPONDER RESEÑA
# =========================================================
@app.post("/hoteles/{id_hotel}/resenas/{resena_id}/respuesta")
def responder_resena(id_hotel: str, resena_id: str, datos: dict):

    db["resenas"].update_one(
        {
            "id_hotel": id_hotel,
            "resena_id": resena_id
        },
        {
            "$set": {
                "respuesta_hotel": {
                    "texto": str(datos.get("texto_respuesta")),
                    "id_admin": str(datos.get("id_admin")),
                    "fecha": datetime.now()
                }
            }
        }
    )

    return {"mensaje": "Respuesta registrada"}

# =========================================================
# RF8 - ELIMINAR RESEÑA ADMIN
# =========================================================
@app.delete("/admin/hoteles/{id_hotel}/resenas/{resena_id}")
def eliminar_resena_admin(id_hotel: str, resena_id: str):

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

    return {"mensaje": "Reseña eliminada por administrador"}

# =========================================================
# RF9 - DESTACAR RESEÑA
# SOLO UNA DESTACADA POR HOTEL
# =========================================================
@app.post("/admin/hoteles/{id_hotel}/resenas/{resena_id}/destacar")
def destacar_resena(id_hotel: str, resena_id: str):

    # quitar destacada anterior
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

    # destacar nueva
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

    return {"mensaje": "Reseña destacada"}

# =========================================================
# ADMIN - VER TODAS LAS RESEÑAS
# DESTACADAS PRIMERO
# =========================================================
@app.get("/admin/hoteles/{id_hotel}/resenas")
def get_resenas_admin(id_hotel: str):

    try:

        resenas = list(
            db["resenas"]
            .find(
                {
                    "id_hotel": id_hotel
                },
                {
                    "_id": 0
                }
            )
            .sort([
                ("destacada", -1),
                ("fecha_creacion", -1)
            ])
        )

        return resenas

    except Exception as e:
        return {"error": str(e)}

# RFC 1
@app.get("/consultas/top-hoteles")
def top_hoteles(fecha_inicio: str, fecha_fin: str):
    """
    Devuelve los 10 hoteles con mayor calificación promedio
    entre fecha_inicio y fecha_fin (solo reseñas publicadas).
    Pipeline:
        1. $match: filtra por estado=publicada y rango de fechas
        2. $group: agrupa por id_hotel, calcula promedio y cuenta
        3. $sort: ordena descendente por calificacion_promedio
        4. $limit: toma los 10 primeros
        5. $project: renombra _id y redondea el promedio
    """
    try:
        fi = datetime.fromisoformat(fecha_inicio)
        ff = datetime.fromisoformat(fecha_fin)
    except ValueError:
        return {"error": "Formato de fecha inválido. Use YYYY-MM-DD."}

    pipeline = [
        {
            "$match": {
                "estado": "publicada",
                "fecha_creacion": {"$gte": fi, "$lte": ff},
            }
        },
        {
            "$group": {
                "_id": "$id_hotel",
                "calificacion_promedio": {"$avg": "$calificacion"},
                "total_resenas": {"$sum": 1},
            }
        },
        {"$sort": {"calificacion_promedio": -1}},
        {"$limit": 10},
        {
            "$project": {
                "_id": 0,
                "id_hotel": "$_id",
                "calificacion_promedio": {
                    "$round": ["$calificacion_promedio", 2]
                },
                "total_resenas": 1,
            }
        },
    ]

    return list(db["resenas"].aggregate(pipeline))

#RFC 2
@app.get("/consultas/evolucion/{id_hotel}")
def evolucion_hotel(id_hotel: str, anio: int):
    """
    Para el hotel indicado muestra la calificación promedio
    por mes durante el año solicitado.

    Pipeline:
        1. $match:filtra por id_hotel, estado=publicada y año
        2. $group:agrupa por mes, calcula promedio y cuenta
        3. $sort:ordena por mes (1 → 12)
        4. $project:construye etiqueta de mes legible
    """
    MESES = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
    }

    fecha_inicio = datetime(anio, 1, 1)
    fecha_fin    = datetime(anio, 12, 31)

    pipeline = [
        {
            "$match": {
                "id_hotel": id_hotel,
                "estado": "publicada",
                "fecha_creacion": {"$gte": fecha_inicio, "$lte": fecha_fin},
            }
        },
        {
            "$group": {
                "_id": {"mes": {"$month": "$fecha_creacion"}},
                "calificacion_promedio": {"$avg": "$calificacion"},
                "total_resenas": {"$sum": 1},
            }
        },
        {"$sort": {"_id.mes": 1}},
        {
            "$project": {
                "_id": 0,
                "mes_numero": "$_id.mes",
                "calificacion_promedio": {
                    "$round": ["$calificacion_promedio", 2]
                },
                "total_resenas": 1,
            }
        },
    ]

    filas = list(db["resenas"].aggregate(pipeline))

    # Añadir nombre del mes legible
    for fila in filas:
        fila["mes_nombre"] = MESES.get(fila["mes_numero"], "Desconocido")

    return {"id_hotel": id_hotel, "anio": anio, "evolucion": filas}

@app.get("/consultas/comparativo")
def comparativo_ciudad(hoteles: str):
    """
    Recibe los IDs de los hoteles de una ciudad (obtenidos previamente
    de Oracle) y devuelve para cada uno:
        - calificacion_promedio
        - total_resenas
        - pct_con_respuesta  (% reseñas con respuesta de administrador)
        - pct_destacadas     (% reseñas marcadas como destacadas)
        - bajo_promedio_ciudad (bool: está por debajo del promedio de la ciudad)

    Nota: el campo 'respuesta_admin' debe existir en el documento de reseña
    cuando el administrador responde. Su ausencia se interpreta
    como sin respuesta.

    Pipeline:
        1. $match: filtra por lista de hoteles y estado publicada
        2. $group: estadísticas por hotel
        3. $addFields: calcula porcentajes
        4. $facet: separa resultado por hotel y promedio global
        5. Etapa final: marca hoteles bajo el promedio de ciudad
    """
    lista_hoteles = [h.strip() for h in hoteles.split(",") if h.strip()]

    pipeline = [
        {
            "$match": {
                "id_hotel": {"$in": lista_hoteles},
                "estado": "publicada",
            }
        },
        {
            "$group": {
                "_id": "$id_hotel",
                "calificacion_promedio": {"$avg": "$calificacion"},
                "total_resenas": {"$sum": 1},
                # Cuenta reseñas que tienen el campo respuesta_admin
                "con_respuesta": {
                    "$sum": {
                        "$cond": [ {"$ifNull": ["$respuesta_admin", False]}, 1, 0]
                    }
                },
                # Cuenta reseñas marcadas como destacadas=true
                "destacadas": {
                    "$sum": {"$cond": [{"$eq": ["$destacada", True]}, 1, 0]}
                },
            }
        },
        {
            "$addFields": {
                "calificacion_promedio": {"$round": ["$calificacion_promedio", 2]},
                "pct_con_respuesta": {
                    "$round": [{
                            "$multiply": [
                                {"$divide": ["$con_respuesta", "$total_resenas"]},
                                100,
                            ]}, 1,]
                },
                "pct_destacadas": {
                    "$round": [
                        {
                            "$multiply": [
                                {"$divide": ["$destacadas", "$total_resenas"]},
                                100,
                            ]
                        },
                        1,
                    ]
                },
            }
        },
        # $facet permite calcular el promedio de ciudad sobre el mismo conjunto
        {
            "$facet": {
                "por_hotel": [
                    {
                        "$project": {
                            "_id": 0,
                            "id_hotel": "$_id",
                            "calificacion_promedio": 1,
                            "total_resenas": 1,
                            "pct_con_respuesta": 1,
                            "pct_destacadas": 1,
                        }
                    }
                ],
                "promedio_ciudad": [
                    {
                        "$group": {
                            "_id": None,
                            "promedio": {"$avg": "$calificacion_promedio"},
                        }
                    }
                ],
            }
        },
    ]

    resultado = list(db["resenas"].aggregate(pipeline))
    if not resultado:
        return {"hoteles": [], "promedio_ciudad": None}

    datos = resultado[0]
    prom_ciudad_doc = datos.get("promedio_ciudad", [])
    promedio_ciudad = (
        round(prom_ciudad_doc[0]["promedio"], 2) if prom_ciudad_doc else None
    )

    hoteles_data = datos.get("por_hotel", [])
    for h in hoteles_data:
        h["bajo_promedio_ciudad"] = h["calificacion_promedio"] < promedio_ciudad if promedio_ciudad is not None else False

    return {
        "promedio_ciudad": promedio_ciudad,
        "hoteles": hoteles_data,
    }