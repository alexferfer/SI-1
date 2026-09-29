import os
import uuid
import json
from quart import Quart, request, jsonify

app = Quart(__name__)

SECRET_UID = uuid.UUID("12345678-1234-1234-1234-123456781234")
STORAGE_DIR = "storage"

if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)

def is_authorized(uid: str) -> bool:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return False
    
    token = auth_header.split(" ")[1]
    expected_token = str(uuid.uuid5(SECRET_UID, uid))
    return token == expected_token

def get_file_path(uid, filename):
    return os.path.join(STORAGE_DIR, uid, filename)

def get_meta_path(uid, filename):
    return os.path.join(STORAGE_DIR, uid, f"{filename}.meta")

@app.put('/file/<uid>/<filename>')
async def create_or_update_file(uid, filename):
    if not is_authorized(uid):
        return jsonify({"error": "unauthorized"}), 401
    
    data = await request.get_json()
    if not data or 'content' not in data:
        return jsonify({"error": "file content missing"}), 400

    user_dir = os.path.join(STORAGE_DIR, uid)
    os.makedirs(user_dir, exist_ok=True)
        
    with open(get_file_path(uid, filename), "w") as f:
        f.write(data['content'])
        
    visibility = data.get('public', False)
    with open(get_meta_path(uid, filename), "w") as f:
        f.write(str(visibility))

    return jsonify({"message": "file saved successfully"}), 201

@app.get('/file/<uid>')
async def list_files(uid):
    if not is_authorized(uid):
        return jsonify({"error": "unauthorized"}), 401
        
    user_dir = os.path.join(STORAGE_DIR, uid)
    if not os.path.exists(user_dir):
        return jsonify({"files": []}), 200
        
    files = [f for f in os.listdir(user_dir) if not f.endswith('.meta')]
    return jsonify({"files": files}), 200

@app.get('/file/<uid>/<filename>')
async def get_file(uid, filename):
    file_path = get_file_path(uid, filename)
    meta_path = get_meta_path(uid, filename)
    
    if not os.path.exists(file_path):
        return jsonify({"error": "file not found"}), 404

    is_public = False
    if os.path.exists(meta_path):
        with open(meta_path, "r") as f:
            is_public = f.read().strip() == "True"

    if not is_public and not is_authorized(uid):
        return jsonify({"error": "unauthorized. file is private"}), 401

    with open(file_path, "r") as f:
        content = f.read()
        
    return jsonify({"filename": filename, "content": content}), 200

@app.delete('/file/<uid>/<filename>')
async def delete_file(uid, filename):
    if not is_authorized(uid):
        return jsonify({"error": "unauthorized"}), 401

    file_path = get_file_path(uid, filename)
    meta_path = get_meta_path(uid, filename)

    if not os.path.exists(file_path):
        return jsonify({"error": "file not found"}), 404

    os.remove(file_path)
    if os.path.exists(meta_path):
        os.remove(meta_path)

    return jsonify({"message": "file deleted successfully"}), 200

@app.patch('/file/<uid>/<filename>')
async def change_visibility(uid, filename):
    if not is_authorized(uid):
        return jsonify({"error": "unauthorized"}), 401

    if not os.path.exists(get_file_path(uid, filename)):
        return jsonify({"error": "file not found"}), 404

    data = await request.get_json()
    if not data or 'public' not in data:
        return jsonify({"error": "public status missing"}), 400

    visibility = bool(data['public'])
    with open(get_meta_path(uid, filename), "w") as f:
        f.write(str(visibility))

    return jsonify({"message": "visibility updated"}), 200

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5051)