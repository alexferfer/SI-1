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

def get_public_path(uid):
    return os.path.join(STORAGE_DIR, uid, "public.json")

def load_public(uid):
    path = get_public_path(uid)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return {}
    with open(path, "r") as f:
        return json.load(f)

def save_public(uid, data):
    user_dir = os.path.join(STORAGE_DIR, uid)
    os.makedirs(user_dir, exist_ok=True)
    with open(get_public_path(uid), "w") as f:
        json.dump(data, f)

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
    public = load_public(uid)
    public[filename] = {"public": visibility}
    save_public(uid, public)

    return jsonify({"message": "file saved successfully"}), 201

@app.get('/file/<uid>')
async def list_files(uid):
    if not is_authorized(uid):
        return jsonify({"error": "unauthorized"}), 401
        
    user_dir = os.path.join(STORAGE_DIR, uid)
    if not os.path.exists(user_dir):
        return jsonify({"files": []}), 200
        
    public = load_public(uid)
    files = list(public.keys())
    return jsonify({"files": files}), 200

@app.get('/file/<uid>/<filename>')
async def get_file(uid, filename):
    file_path = get_file_path(uid, filename)
    
    if not os.path.exists(file_path):
        return jsonify({"error": "file not found"}), 404

    public = load_public(uid)
    is_public = public.get(filename, {}).get("public", False)

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

    if not os.path.exists(file_path):
        return jsonify({"error": "file not found"}), 404

    os.remove(file_path)
    
    public = load_public(uid)
    if filename in public:
        del public[filename]
        save_public(uid, public)

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
    public = load_public(uid)
    public[filename] = {"public": visibility}
    save_public(uid, public)

    return jsonify({"message": "visibility updated"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5051)