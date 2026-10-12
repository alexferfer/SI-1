import hashlib
import uuid
from quart import Quart, request, jsonify
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

app = Quart(__name__)

import os
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://alumnodb:1234@localhost:5432/si1")

DB_CONFIG = {
    "table_users": "usuarios",
    "col_id": "id",
    "col_username": "username",
    "col_password": "password_hash",
    "col_saldo": "saldo",
    "col_pais": "pais"
}

SECRET_UID = uuid.UUID("12345678-1234-1234-1234-123456781234")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_token_for_user(user_id: int) -> str:
    return str(uuid.uuid5(SECRET_UID, str(user_id)))

async def authenticate_request() -> int | None:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token_recibido = auth_header.split(" ")[1]

    query = text(f"SELECT {DB_CONFIG['col_id']} FROM {DB_CONFIG['table_users']}")
    async with async_session() as session:
        result = await session.execute(query)
        rows = result.fetchall()
        for row in rows:
            uid = row[0]
            if get_token_for_user(uid) == token_recibido:
                return uid
    return None

@app.put('/user')
async def create_user():
    data = await request.get_json()
    if not data or 'username' not in data or 'password' not in data or 'pais' not in data:
        return jsonify({"error": "Faltan campos obligatorios (username, password, pais)"}), 400

    username = data['username']
    pwd_hash = hash_password(data['password'])
    pais = data['pais']
    saldo_inicial = float(data.get('saldo', 0.0))

    query_check = text(f"SELECT {DB_CONFIG['col_id']} FROM {DB_CONFIG['table_users']} WHERE {DB_CONFIG['col_username']} = :uname")
    query_insert = text(f"""
        INSERT INTO {DB_CONFIG['table_users']} ({DB_CONFIG['col_username']}, {DB_CONFIG['col_password']}, {DB_CONFIG['col_pais']}, {DB_CONFIG['col_saldo']})
        VALUES (:uname, :pwd, :pais, :saldo)
        RETURNING {DB_CONFIG['col_id']}
    """)

    async with async_session() as session:
        async with session.begin():
            result = await session.execute(query_check, {"uname": username})
            if result.fetchone() is not None:
                return jsonify({"error": "El usuario ya existe"}), 409

            res_insert = await session.execute(query_insert, {
                "uname": username,
                "pwd": pwd_hash,
                "pais": pais,
                "saldo": saldo_inicial
            })
            new_id = res_insert.scalar_one()

    token = get_token_for_user(new_id)
    return jsonify({"id": new_id, "username": username, "token": token}), 201

@app.post('/user')
async def login():
    data = await request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Faltan credenciales"}), 400

    username = data['username']
    pwd_hash = hash_password(data['password'])

    query = text(f"""
        SELECT {DB_CONFIG['col_id']} 
        FROM {DB_CONFIG['table_users']} 
        WHERE {DB_CONFIG['col_username']} = :uname AND {DB_CONFIG['col_password']} = :pwd
    """)

    async with async_session() as session:
        result = await session.execute(query, {"uname": username, "pwd": pwd_hash})
        row = result.fetchone()
        if not row:
            return jsonify({"error": "Credenciales invalidas"}), 401

        user_id = row[0]
        token = get_token_for_user(user_id)
        return jsonify({"id": user_id, "token": token}), 200

@app.post('/logout')
async def logout():
    user_id = await authenticate_request()
    if not user_id:
        return jsonify({"error": "No autorizado"}), 401
    return jsonify({"message": "Sesion cerrada correctamente"}), 200

@app.delete('/user')
async def delete_user():
    user_id = await authenticate_request()
    if not user_id:
        return jsonify({"error": "No autorizado"}), 401

    query_delete = text(f"DELETE FROM {DB_CONFIG['table_users']} WHERE {DB_CONFIG['col_id']} = :uid")

    async with async_session() as session:
        async with session.begin():
            await session.execute(query_delete, {"uid": user_id})

    return jsonify({"message": "Usuario eliminado correctamente"}), 200

@app.patch('/user/saldo')
async def update_saldo():
    user_id = await authenticate_request()
    if not user_id:
        return jsonify({"error": "No autorizado"}), 401

    data = await request.get_json()
    if not data or 'cantidad' not in data:
        return jsonify({"error": "Falta el campo cantidad"}), 400

    cantidad = float(data['cantidad'])

    query_update = text(f"""
        UPDATE {DB_CONFIG['table_users']}
        SET {DB_CONFIG['col_saldo']} = {DB_CONFIG['col_saldo']} + :cant
        WHERE {DB_CONFIG['col_id']} = :uid
        RETURNING {DB_CONFIG['col_saldo']}
    """)

    async with async_session() as session:
        async with session.begin():
            res = await session.execute(query_update, {"cant": cantidad, "uid": user_id})
            nuevo_saldo = res.scalar_one()

    return jsonify({"message": "Saldo actualizado", "nuevo_saldo": float(nuevo_saldo)}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)