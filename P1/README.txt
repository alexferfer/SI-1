DOCUMENTACION PRACTICA 1: SISTEMAS INFORMÁTICOS

Autores: Alejandro Fernandez Fernandez, Marcos Jimenez de las Moras
Grupo: 1322, pareja 11

Descripcion:
Servicio de almacenamiento de documentos compartidos basado en microservicios REST y framework Quart (python)
Servicio de usuarios (user.py): Puerto 5050. Gestiona registro, inicio de sesion y cambio de contraseña
Servicio de archivos (file.py): Puerto 5051. Gestiona directorios por UID, creación, lectura, borrado y visibilidad con control de acceso.

Requisitos previos:
1. Docker Engine y Docker Compose instalados
2. Python 3.12 (para ejecución local o cliente de pruebas)
3. Paquetes de Python: quart, requests (definidos en requirements.txt)

Ejecucion con docker compose:
1. Levantar y construir los contenedores de los microservicios:
   $ docker compose up --build
2. En otra terminal, ejecutar las pruebas automatizadas:
   $ python3 cliente.py
3. Detener y limpiar los contenedores:
   $ docker compose down

Ejecucion sin docker compose:
1. Activar el entorno virtual:
   $ source ~/venv/si1p1/bin/activate
2. En una terminal, arrancar el microservicio de usuarios:
   $ python3 user.py
3. En otra terminal, arrancar el microservicio de archivos:
   $ python3 file.py
4. En otra terminal, ejecutar las pruebas:
   $ python3 cliente.py