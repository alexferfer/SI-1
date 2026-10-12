import sys
import requests

USER_URL = "http://127.0.0.1:5050"
API_URL = "http://127.0.0.1:5051"

stats = {"passed": 0, "failed": 0}

def assert_test(name: str, condition: bool):
    if condition:
        print(f"  [OK] {name}")
        stats["passed"] += 1
    else:
        print(f"  [FAIL] {name}")
        stats["failed"] += 1

def run_tests():
    print("=" * 60)
    print("INICIANDO BATERÍA DE PRUEBAS - PRÁCTICA 2 (SI 2020/2027)")
    print("=" * 60)

    print("\n--- 1. Pruebas de Usuarios (user.py) ---")

    user_payload = {
        "username": "Joan",
        "password": "pep123",
        "pais": "España",
        "saldo": 50.0
    }
    r = requests.put(f"{USER_URL}/user", json=user_payload)
    assert_test("Registro de usuario válido (201)", r.status_code == 201)
    data_user = r.json() if r.status_code == 201 else {}
    assert_test("Respuesta contiene ID y Token", "id" in data_user and "token" in data_user)
    token = data_user.get("token", "")
    headers = {"Authorization": f"Bearer {token}"}

    r = requests.put(f"{USER_URL}/user", json=user_payload)
    assert_test("Rechazo por usuario duplicado (409)", r.status_code == 409)

    r = requests.put(f"{USER_URL}/user", json={"username": "incompleto"})
    assert_test("Rechazo por campos obligatorios faltantes (400)", r.status_code == 400)

    login_payload = {"username": "Joan", "password": "pep123"}
    r = requests.post(f"{USER_URL}/user", json=login_payload)
    assert_test("Login con credenciales correctas (200)", r.status_code == 200)
    assert_test("Token recibido coincide con el de registro", r.json().get("token") == token)

    r = requests.post(f"{USER_URL}/user", json={"username": "Joan", "password": "password_falsa"})
    assert_test("Login rechazado con clave incorrecta (401)", r.status_code == 401)

    r = requests.patch(f"{USER_URL}/user/saldo", headers=headers, json={"cantidad": 25.0})
    assert_test("Recarga de saldo autenticada (200)", r.status_code == 200)

    r = requests.patch(f"{USER_URL}/user/saldo", json={"cantidad": 10.0})
    assert_test("Recarga sin token rechazada (401)", r.status_code == 401)

    r = requests.post(f"{USER_URL}/logout", headers=headers)
    assert_test("Logout autenticado (200)", r.status_code == 200)

    print("\n--- 2. Pruebas de Catálogo de Películas (api.py) ---")

    movie_payload = {
        "titulo": "50 sombras de Joan",
        "genero": "Romance",
        "año": 2020,
        "precio": 9.99,
        "stock": 15
    }
    r = requests.post(f"{API_URL}/peliculas", json=movie_payload)
    assert_test("Creación de película en catálogo (201)", r.status_code == 201)
    movie_id = r.json().get("id") if r.status_code == 201 else None

    r = requests.post(f"{API_URL}/peliculas", json={"titulo": "Sin precio"})
    assert_test("Rechazo de creación por campos faltantes (400)", r.status_code == 400)

    r = requests.get(f"{API_URL}/peliculas")
    assert_test("Listado general de películas (200)", r.status_code == 200)

    r = requests.get(f"{API_URL}/peliculas?genero=Romance&año=2020")
    assert_test("Listado con filtros de género y año (200)", r.status_code == 200)

    print("\n--- 3. Pruebas de Carrito y Compras (api.py) ---")

    r = requests.post(f"{API_URL}/carrito/items", json={"pelicula_id": movie_id, "cantidad": 1})
    assert_test("Añadir al carrito sin token rechazado (401)", r.status_code == 401)

    r = requests.post(f"{API_URL}/carrito/items", headers=headers, json={"pelicula_id": movie_id, "cantidad": 2})
    assert_test("Añadir película al carrito en bloque (201)", r.status_code == 201)

    r = requests.post(f"{API_URL}/carrito/items", headers=headers, json={"pelicula_id": 999999, "cantidad": 1})
    assert_test("Añadir película inexistente al carrito (404)", r.status_code == 404)

    r = requests.post(f"{API_URL}/carrito/pagar", headers=headers)
    assert_test("Pago del carrito en bloque (200)", r.status_code == 200)
    if r.status_code == 200:
        data_pago = r.json()
        assert_test("Respuesta de pago incluye fecha_pago registrada", "fecha_pago" in data_pago)

    r = requests.post(f"{API_URL}/carrito/pagar", headers=headers)
    assert_test("Pago rechazado al no haber carrito pendiente (404)", r.status_code == 404)

    print("\n--- 4. Pruebas de Valoraciones y Stored Procedure (api.py) ---")

    r = requests.post(f"{API_URL}/peliculas/{movie_id}/votar", headers=headers, json={"puntuacion": 9.5})
    assert_test("Registro de voto válido [0-10] (201)", r.status_code == 201)

    r = requests.post(f"{API_URL}/peliculas/{movie_id}/votar", headers=headers, json={"puntuacion": 11.0})
    assert_test("Rechazo de voto con puntuación > 10 (400)", r.status_code == 400)

    r = requests.post(f"{API_URL}/peliculas/{movie_id}/votar", headers=headers, json={"puntuacion": -1.0})
    assert_test("Rechazo de voto con puntuación < 0 (400)", r.status_code == 400)

    r = requests.get(f"{API_URL}/peliculas/{movie_id}/valoracion")
    assert_test("Consulta de valoración media vía Stored Procedure (200)", r.status_code == 200)
    if r.status_code == 200:
        assert_test("Respuesta contiene nota media calculada", "nota_media" in r.json())

    print("\n--- 5. Pruebas de Historial de Ventas (api.py) ---")

    r = requests.get(f"{API_URL}/ventas/2020/España")
    assert_test("Consulta de ventas por año y país (200)", r.status_code == 200)
    if r.status_code == 200:
        assert_test("Estructura contiene lista de ventas", "ventas" in r.json())

    print("\n--- 6. Pruebas de Borrado y Limpieza ---")

    if movie_id:
        r = requests.delete(f"{API_URL}/peliculas/{movie_id}")
        assert_test("Borrado de película del catálogo (200)", r.status_code == 200)

    r = requests.delete(f"{API_URL}/peliculas/999999")
    assert_test("Borrado de película inexistente rechazado (404)", r.status_code == 404)

    r = requests.delete(f"{USER_URL}/user", headers=headers)
    assert_test("Eliminación de cuenta de usuario autenticado (200)", r.status_code == 200)

    r = requests.patch(f"{USER_URL}/user/saldo", headers=headers, json={"cantidad": 10.0})
    assert_test("Operación con token de usuario eliminado rechazada (401)", r.status_code == 401)

    print("\n" + "=" * 60)
    print(f"RESUMEN DE PRUEBAS:")
    print(f"  SUPERADAS: {stats['passed']}")
    print(f"  FALLIDAS:  {stats['failed']}")
    print("=" * 60)

    if stats["failed"] > 0:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    run_tests()