# MFA System

## 1. Descripción del proyecto

MFA System es una aplicación web que permite registrar usuarios e iniciar sesión mediante autenticación multifactor (MFA). Además de la contraseña, el usuario debe introducir un código temporal de seis dígitos generado por una aplicación de autenticación, como Google Authenticator.

El proyecto está desarrollado con Flask y PostgreSQL, y utiliza Nginx como proxy inverso. Los servicios se ejecutan mediante Docker Compose.

### Tecnologías utilizadas

- **Python y Flask:** aplicación web.
- **PostgreSQL:** base de datos para almacenar las cuentas.
- **Nginx:** proxy inverso para acceder a la aplicación.
- **Docker y Docker Compose:** despliegue y gestión de los servicios.
- **PyOTP y QRCode:** generación de códigos MFA y códigos QR.

## 2. Requisitos previos

Antes de poner en marcha el proyecto, es necesario tener instalado:

- Docker Desktop con el motor de Docker funcionando, o Docker Engine en Linux.
- Docker Compose v2.
- Git para clonar el repositorio.
- Un navegador web.
- Una aplicación de autenticación, como Google Authenticator, instalada en el móvil.

En Windows se puede utilizar Docker Desktop con la integración de WSL 2.

## 3. Clonar el repositorio

Abre una terminal y ejecuta:

git clone https://github.com/UnaxUr/PPSE-UUV-MFA-docker.git


Entra en la carpeta del proyecto:


cd mfa-docker

## 4. Configurar las variables de entorno

El proyecto necesita un archivo `.env` para configurar las credenciales de PostgreSQL, la clave secreta de Flask y el puerto de acceso.

Si el repositorio incluye un archivo `.env.example`, crea una copia:

cp .env.example .env

Edita el archivo:

nano .env

Comprueba que las variables coinciden con las utilizadas en `docker-compose.yml`. Configura los datos de la base de datos, el puerto de Nginx y una clave secreta segura para Flask.

No utilices credenciales de ejemplo en un entorno real.

**Importante:** el archivo `.env` contiene información sensible y no debe subirse a GitHub. Para el repositorio debe utilizarse `.env.example` con valores de ejemplo y sin contraseñas reales.

## 5. Poner en marcha el proyecto

Desde la carpeta del proyecto, ejecuta:

docker compose up -d --build

Este comando construye la imagen de la aplicación cuando es necesario y pone en marcha los tres servicios: Flask, PostgreSQL y Nginx.

Comprueba su estado:

docker compose ps

PostgreSQL debe aparecer como `healthy` si el chequeo de salud está configurado y se ha completado correctamente. Los tres servicios deben estar en funcionamiento.

Para consultar los registros:

docker compose logs

Para consultar únicamente los registros de la aplicación:

docker compose logs app

## 6. Acceder a la aplicación

Abre el navegador y entra en:

http://localhost:8080

El puerto puede variar si se ha cambiado la variable `NGINX_PORT` en el archivo `.env`.

Desde la aplicación se puede:

1. Acceder a la pantalla inicial.
2. Crear una cuenta con un nombre de usuario y una contraseña.
3. Iniciar sesión.
4. Configurar la autenticación multifactor escaneando el código QR con una aplicación de autenticación.
5. Introducir el código temporal de seis dígitos para verificar la cuenta y completar el inicio de sesión.

## 7. Detener el proyecto

Para detener los servicios sin eliminar los datos almacenados en el volumen de PostgreSQL, ejecuta:

docker compose down

Para volver a iniciar el proyecto posteriormente:

docker compose up -d

Si solo se quiere detener temporalmente los contenedores sin eliminarlos, también se puede utilizar:

docker compose stop


Y para volver a ponerlos en funcionamiento:


docker compose start


**Importante:** no utilices `docker compose down -v` si quieres conservar los datos de PostgreSQL, ya que elimina los volúmenes asociados al proyecto.

## 8. Seguridad

- Las contraseñas de los usuarios se almacenan mediante hash.
- La autenticación multifactor utiliza códigos temporales TOTP.
- Las credenciales de la base de datos se configuran mediante variables de entorno.
- Nginx es el punto de acceso publicado para la aplicación; Flask y PostgreSQL permanecen en la red interna de Docker.
- El archivo `.env` no debe compartirse ni incluirse en el repositorio.
- La configuración actual está orientada a un proyecto de aprendizaje. Para utilizarla en producción sería necesario reforzar aspectos como HTTPS, gestión de secretos, servidor WSGI y controles adicionales de seguridad.
