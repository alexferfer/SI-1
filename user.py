import hashlib
import uuid
from quart import Quart, request, jsonify

app = Quart(__name__)
SECRET_UID = uuid.UUID("12345678-1234-1234-1234-123456781234")
users_db = {}

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_token_uid(uid: str) -> str:
    return str(uuid.uuid5(SECRET_UID, uid))

@app.put('/user')
async def create_user():
    data = await request.get_json()

    if not data or 'name' not in data or 'password' not in data:
        return jsonify({"error": "mandatory data missing"}), 400
    
    username = data['name']
    password = data['password']

    if username in users_db:
        return jsonify({"error": "user already exists"}), 409

    user_uid = str(uuid.uuid4())
    hash_pwd = hash_password(password)

    users_db[username] = {"uid": user_uid, "pwd": hash_pwd}

    token = get_token_uid(user_uid)
    return jsonify({"uid": user_uid, "token": token}), 201

@app.post('/user')
async def login():
    data = await request.get_json()

    if not data or 'name' not in data or 'password' not in data:
        return jsonify({"error": "mandatory data missing"}), 400

    username = data['name']
    password = data['password']

    user = users_db.get(username)

    if not user or user["pwd"] != hash_password(password):
        return jsonify({"error": "invalid data"}), 401

    token = get_token_uid(user["uid"])
    return jsonify({"uid": user["uid"], "token": token}), 200

@app.patch('/user')
async def change_password():
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "authentication token missing"}), 401

    token = auth_header.split(' ')[1]

    target = None
    for username, data in users_db.items():
        if get_token_uid(data["uid"]) == token:
            target = username
            break

    if not target:
        return jsonify({"error": "invalid token"}), 401

    pwd_data = await request.get_json()

    if not pwd_data or 'password' not in pwd_data:
        return jsonify({"error": "password missing"}), 400

    users_db[target]['pwd'] = hash_password(pwd_data['password'])
    return jsonify({"message": "password changed successfully"}), 200

if __name__ == '__main__':
    app.run(host = '127.0.0.1', port = 5050)