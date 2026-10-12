import requests
import sys

USER_URL = "http://127.0.0.1:5050/user"
FILE_URL = "http://127.0.0.1:5051/file"

stats = {"passed": 0, "failed": 0}

def assert_test(name: str, condition: bool):
    if condition:
        print(f"  [OK] {name}")
        stats["passed"] += 1
    else:
        print(f"  [FAIL] {name}")
        stats["failed"] += 1

def run_tests():
    print("\nPruebas de user.py")
    
    # Probamos a crear un usuario válido
    print("\nProbamos a crear un usuario válido")
    r = requests.put(USER_URL, json={"name": "juan", "password": "a1b2c3"})
    assert_test("Código 201 al crear usuario", r.status_code == 201)
    data = r.json()
    assert_test("Devuelve UID y Token", "uid" in data and "token" in data)
    uid = data.get("uid")
    token = data.get("token")
    headers = {"Authorization": f"Bearer {token}"}

    # Probamos que funciona el control de duplicados
    r = requests.put(USER_URL, json={"name": "juan", "password": "abc123"})
    assert_test("Código 409 al intentar duplicar usuario", r.status_code == 409)

    # Probamos que falla con datos incompletos
    r = requests.put(USER_URL, json={"name": "alicia"})
    assert_test("Código 400 por falta de contraseña", r.status_code == 400)

    # Probamos el inicio de sesión válido
    print("\nProbamos los inicios de sesión")
    r = requests.post(USER_URL, json={"name": "juan", "password": "a1b2c3"})
    assert_test("Código 200 al iniciar sesión", r.status_code == 200)
    assert_test("El token devuelto es correcto", r.json().get("token") == token)

    # Probamos el inicio de sesión invalido
    r = requests.post(USER_URL, json={"name": "juan", "password": "wrong"})
    assert_test("Código 401 con credenciales erróneas", r.status_code == 401)

    # Cambiamos la contraseña de nuestro usuario
    print("\nProbamos el cambio de contraseña")
    r = requests.patch(USER_URL, headers=headers, json={"password": "abc123"})
    assert_test("Código 200 al actualizar contraseña", r.status_code == 200)

    # Probamos de nuevo el inicio de sesión con la nueva contraseña
    r = requests.post(USER_URL, json={"name": "juan", "password": "abc123"})
    assert_test("Código 200 al iniciar con la nueva contraseña", r.status_code == 200)
    assert_test("El token se mantiene igual tras cambio", r.json().get("token") == token)

    # Cambiamos la contraseña sin autorización
    r = requests.patch(USER_URL, json={"password": "abcd"})
    assert_test("Código 401 al intentar cambiar sin token", r.status_code == 401)

    # Probamos el login incompleto o vacío
    r = requests.post(USER_URL, json={})
    assert_test("Código 400 en login sin credenciales", r.status_code == 400)

    # Probamos el cambio de contraseña sin enviar el campo 'password'
    r = requests.patch(USER_URL, headers=headers, json={})
    assert_test("Código 400 en cambio de contraseña sin body", r.status_code == 400)

    # Probamos el cambio de contraseña con un token que no existe en el sistema
    fake_headers = {"Authorization": "Bearer 00000000-0000-0000-0000-000000000000"}
    r = requests.patch(USER_URL, headers=fake_headers, json={"password": "nueva"})
    assert_test("Código 401 en cambio de contraseña con token falso", r.status_code == 401)


    print("\nPruebas de file.py")
    
    file_base = f"{FILE_URL}/{uid}"

    # Probamos a crear un archivo privado
    print("\nProbamos a crear ficheros")
    r = requests.put(f"{file_base}/privado.txt", headers=headers, json={"content": "Texto privado", "public": False})
    assert_test("Código 201 al crear archivo privado", r.status_code == 201)

    # Creamos un archivo público
    r = requests.put(f"{file_base}/publico.txt", headers=headers, json={"content": "Texto publico", "public": True})
    assert_test("Código 201 al crear archivo público", r.status_code == 201)

    # Intentamos crear un archivo sin autorización
    r = requests.put(f"{file_base}/intruso.txt", json={"content": "Malicioso"})
    assert_test("Código 401 al crear sin token", r.status_code == 401)

    # Listamos el directorio del usuario
    print("\nProbamos a listar el directorio")
    r = requests.get(file_base, headers=headers)
    assert_test("Código 200 al listar directorio", r.status_code == 200)
    files = r.json().get("files", [])
    assert_test("Aparecen todos los ficheros listados", "privado.txt" in files and "publico.txt" in files)

    # Probamos a listar sin autorización
    r = requests.get(file_base)
    assert_test("Código 401 al intentar listar sin token", r.status_code == 401)

    # 14. Recuperar archivos (Lectura)
    print("\n-Probamos a leer ficheros")
    r = requests.get(f"{file_base}/privado.txt", headers=headers)
    assert_test("Código 200 al leer archivo privado propio", r.status_code == 200)

    r = requests.get(f"{file_base}/privado.txt")
    assert_test("Código 401 al intentar leer archivo privado ajeno sin token", r.status_code == 401)

    r = requests.get(f"{file_base}/publico.txt")
    assert_test("Código 200 al leer archivo público ajeno sin token", r.status_code == 200)
    assert_test("Contenido íntegro del archivo público", r.json().get("content") == "Texto publico")

    # Cambiamos la visibilidad del archivo
    print("\nProbamos a modificar si el fichero es público")
    r = requests.patch(f"{file_base}/privado.txt", headers=headers, json={"public": True})
    assert_test("Código 200 al cambiar de privado a público", r.status_code == 200)

    r = requests.get(f"{file_base}/privado.txt")
    assert_test("Código 200 al leer archivo recién expuesto al público", r.status_code == 200)

    # Probamos a borrar el archivo
    print("\nProbamos a borrar un archivo")
    r = requests.delete(f"{file_base}/publico.txt")
    assert_test("Código 401 al borrar sin token", r.status_code == 401)

    r = requests.delete(f"{file_base}/publico.txt", headers=headers)
    assert_test("Código 200 al borrar archivo con token", r.status_code == 200)

    r = requests.get(f"{file_base}/publico.txt")
    assert_test("Código 404 tras verificar que el archivo fue eliminado", r.status_code == 404)

    # Probamos PUT sin el campo 'content'
    r = requests.put(f"{file_base}/invalido.txt", headers=headers, json={"public": False})
    assert_test("Código 400 al crear archivo sin contenido", r.status_code == 400)

    # Probamos GET de un archivo inexistente
    r = requests.get(f"{file_base}/inexistente.txt", headers=headers)
    assert_test("Código 404 al leer archivo inexistente", r.status_code == 404)

    # EProbamos PATCH sin token
    r = requests.patch(f"{file_base}/privado.txt", json={"public": True})
    assert_test("Código 401 al cambiar visibilidad sin token", r.status_code == 401)

    # Probamos PATCH de un archivo inexistente
    r = requests.patch(f"{file_base}/no_existe.txt", headers=headers, json={"public": True})
    assert_test("Código 404 al cambiar visibilidad de archivo inexistente", r.status_code == 404)

    # Probamos PATCH sin el campo 'public'
    r = requests.patch(f"{file_base}/privado.txt", headers=headers, json={})
    assert_test("Código 400 al cambiar visibilidad sin campo 'public'", r.status_code == 400)

    # Probamos DELETE de un archivo inexistente
    r = requests.delete(f"{file_base}/fantasma.txt", headers=headers)
    assert_test("Código 404 al borrar archivo que no existe", r.status_code == 404)


    print("\nPruebas de seguridad multiusuario")

    # Creamos al usuario francisco y obtenemos su token
    r = requests.put(USER_URL, json={"name": "francisco", "password": "pass_francisco"})
    assert_test("Código 201 al crear segundo usuario (francisco)", r.status_code == 201)
    francisco_token = r.json().get("token")
    francisco_headers = {"Authorization": f"Bearer {francisco_token}"}

    # Volvemos a poner 'privado.txt' de Juan en estado privado
    requests.patch(f"{file_base}/privado.txt", headers=headers, json={"public": False})

    # Francisco intenta leer el archivo privado de Juan
    r = requests.get(f"{file_base}/privado.txt", headers=francisco_headers)
    assert_test("Código 401: Francisco no puede leer archivo privado de Juan", r.status_code == 401)

    # Francisco intenta listar el directorio de Juan
    r = requests.get(file_base, headers=francisco_headers)
    assert_test("Código 401: Francisco no puede listar los archivos de Juan", r.status_code == 401)

    # Francisco intenta borrar un archivo de Juan
    r = requests.delete(f"{file_base}/privado.txt", headers=francisco_headers)
    assert_test("Código 401: Francisco no puede borrar archivos de Juan", r.status_code == 401)

    print(f"\nPRUEBAS SUPERADAS: {stats['passed']}")
    print(f" \nPRUEBAS FALLIDAS:  {stats['failed']}")

    if stats["failed"] > 0:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
        run_tests()