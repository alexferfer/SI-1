import uuid
from datetime import datetime
from quart import Quart, request, jsonify
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

app = Quart(__name__)

import os
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://alumnodb:1234@localhost:5432/si1")

DB_CONFIG = {
    "table_users": "usuarios",
    "table_movies": "peliculas",
    "table_orders": "pedidos",
    "table_order_items": "pedido_items",
    "table_ratings": "valoraciones",
    "sp_avg_rating": "sp_calcular_nota_media"
}

SECRET_UID = uuid.UUID("12345678-1234-1234-1234-123456781234")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

def get_token_for_user(user_id: int) -> str:
    return str(uuid.uuid5(SECRET_UID, str(user_id)))

async def authenticate_request() -> int | None:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token_recibido = auth_header.split(" ")[1]

    query = text(f"SELECT id FROM {DB_CONFIG['table_users']}")
    async with async_session() as session:
        result = await session.execute(query)
        for row in result.fetchall():
            uid = row[0]
            if get_token_for_user(uid) == token_recibido:
                return uid
    return None

@app.post('/peliculas')
async def create_movie():
    data = await request.get_json()
    if not data or 'titulo' not in data or 'año' not in data or 'precio' not in data:
        return jsonify({"error": "Faltan campos (titulo, año, precio)"}), 400

    query = text(f"""
        INSERT INTO {DB_CONFIG['table_movies']} (titulo, genero, año, precio, stock)
        VALUES (:titulo, :genero, :anio, :precio, :stock)
        RETURNING id
    """)

    params = {
        "titulo": data['titulo'],
        "genero": data.get('genero', 'General'),
        "anio": int(data['año']),
        "precio": float(data['precio']),
        "stock": int(data.get('stock', 10))
    }

    async with async_session() as session:
        async with session.begin():
            res = await session.execute(query, params)
            movie_id = res.scalar_one()

    return jsonify({"message": "Pelicula creada", "id": movie_id}), 201

@app.delete('/peliculas/<int:movie_id>')
async def delete_movie(movie_id):
    query = text(f"DELETE FROM {DB_CONFIG['table_movies']} WHERE id = :id RETURNING id")
    async with async_session() as session:
        async with session.begin():
            res = await session.execute(query, {"id": movie_id})
            row = res.fetchone()
            if not row:
                return jsonify({"error": "Pelicula no encontrada"}), 404

    return jsonify({"message": "Pelicula eliminada"}), 200

@app.get('/peliculas')
async def list_movies():
    genero = request.args.get('genero')
    anio = request.args.get('año')

    where_clauses = []
    params = {}

    if genero:
        where_clauses.append("genero = :genero")
        params["genero"] = genero
    if anio:
        where_clauses.append("año = :anio")
        params["anio"] = int(anio)

    sql_str = f"SELECT id, titulo, genero, año, precio, stock FROM {DB_CONFIG['table_movies']}"
    if where_clauses:
        sql_str += " WHERE " + " AND ".join(where_clauses)

    query = text(sql_str)

    async with async_session() as session:
        res = await session.execute(query, params)
        movies = [
            {"id": r[0], "titulo": r[1], "genero": r[2], "año": r[3], "precio": float(r[4]), "stock": r[5]}
            for r in res.fetchall()
        ]

    return jsonify({"peliculas": movies}), 200

@app.post('/carrito/items')
async def add_to_cart():
    user_id = await authenticate_request()
    if not user_id:
        return jsonify({"error": "No autorizado"}), 401

    data = await request.get_json()
    if not data or 'pelicula_id' not in data:
        return jsonify({"error": "Falta pelicula_id"}), 400

    movie_id = int(data['pelicula_id'])
    cantidad = int(data.get('cantidad', 1))

    query_cart_item = text(f"""
        WITH user_cart AS (
            INSERT INTO {DB_CONFIG['table_orders']} (usuario_id, estado)
            VALUES (:uid, 'CARRITO')
            ON CONFLICT DO NOTHING
            RETURNING id
        ),
        active_cart AS (
            SELECT id FROM user_cart
            UNION
            SELECT id FROM {DB_CONFIG['table_orders']} 
            WHERE usuario_id = :uid AND estado = 'CARRITO'
            LIMIT 1
        )
        INSERT INTO {DB_CONFIG['table_order_items']} (pedido_id, pelicula_id, cantidad, precio_unitario)
        SELECT active_cart.id, :mid, :cant, p.precio
        FROM active_cart, {DB_CONFIG['table_movies']} p
        WHERE p.id = :mid
        RETURNING id
    """)

    async with async_session() as session:
        async with session.begin():
            try:
                res = await session.execute(query_cart_item, {"uid": user_id, "mid": movie_id, "cant": cantidad})
                item_row = res.fetchone()
                if not item_row:
                    return jsonify({"error": "Pelicula no encontrada"}), 404
            except Exception as e:
                return jsonify({"error": f"Fallo al anadir al carrito: {str(e)}"}), 400

    return jsonify({"message": "Item anadido al carrito"}), 201

@app.post('/carrito/pagar')
async def pay_cart():
    user_id = await authenticate_request()
    if not user_id:
        return jsonify({"error": "No autorizado"}), 401

    query_pay = text(f"""
        UPDATE {DB_CONFIG['table_orders']}
        SET estado = 'PAGADO', fecha_pago = NOW()
        WHERE usuario_id = :uid AND estado = 'CARRITO'
        RETURNING id, fecha_pago
    """)

    async with async_session() as session:
        async with session.begin():
            try:
                res = await session.execute(query_pay, {"uid": user_id})
                row = res.fetchone()
                if not row:
                    return jsonify({"error": "No hay carrito activo para pagar"}), 404
            except Exception as e:
                return jsonify({"error": f"Error en el pago: {str(e)}"}), 400

    return jsonify({"message": "Carrito pagado con exito", "pedido_id": row[0], "fecha_pago": str(row[1])}), 200

@app.post('/peliculas/<int:movie_id>/votar')
async def vote_movie(movie_id):
    user_id = await authenticate_request()
    if not user_id:
        return jsonify({"error": "No autorizado"}), 401

    data = await request.get_json()
    if not data or 'puntuacion' not in data:
        return jsonify({"error": "Falta el campo puntuacion"}), 400

    puntuacion = float(data['puntuacion'])
    if puntuacion < 0 or puntuacion > 10:
        return jsonify({"error": "La puntuacion debe estar comprendida entre 0 y 10"}), 400

    query = text(f"""
        INSERT INTO {DB_CONFIG['table_ratings']} (usuario_id, pelicula_id, puntuacion)
        VALUES (:uid, :mid, :score)
        ON CONFLICT (usuario_id, pelicula_id) 
        DO UPDATE SET puntuacion = EXCLUDED.puntuacion
        RETURNING id
    """)

    async with async_session() as session:
        async with session.begin():
            await session.execute(query, {"uid": user_id, "mid": movie_id, "score": puntuacion})

    return jsonify({"message": "Voto registrado correctamente"}), 201

@app.get('/peliculas/<int:movie_id>/valoracion')
async def get_movie_rating(movie_id):
    query = text(f"SELECT {DB_CONFIG['sp_avg_rating']}(:mid)")

    async with async_session() as session:
        res = await session.execute(query, {"mid": movie_id})
        rating = res.scalar_one_or_none()

    if rating is None:
        rating = 0.0

    return jsonify({"pelicula_id": movie_id, "nota_media": float(rating)}), 200

@app.get('/ventas/<int:anio>/<string:pais>')
async def get_ventas(anio, pais):
    query = text(f"""
        SELECT 
            o.id AS pedido_id,
            o.fecha_pago,
            u.username,
            u.pais,
            p.titulo,
            oi.cantidad,
            oi.precio_unitario,
            (oi.cantidad * oi.precio_unitario) AS subtotal
        FROM {DB_CONFIG['table_orders']} o
        JOIN {DB_CONFIG['table_users']} u ON o.usuario_id = u.id
        JOIN {DB_CONFIG['table_order_items']} oi ON oi.pedido_id = o.id
        JOIN {DB_CONFIG['table_movies']} p ON oi.pelicula_id = p.id
        WHERE o.estado = 'PAGADO'
          AND EXTRACT(YEAR FROM o.fecha_pago) = :anio
          AND u.pais = :pais
    """)

    async with async_session() as session:
        res = await session.execute(query, {"anio": anio, "pais": pais})
        rows = res.fetchall()

        ventas = [
            {
                "pedido_id": r[0],
                "fecha_pago": str(r[1]),
                "usuario": r[2],
                "pais": r[3],
                "pelicula": r[4],
                "cantidad": r[5],
                "precio_unitario": float(r[6]),
                "subtotal": float(r[7])
            }
            for r in rows
        ]

    return jsonify({"año": anio, "pais": pais, "total_registros": len(ventas), "ventas": ventas}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5051)