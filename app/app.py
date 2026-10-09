from flask import Flask, render_template, request, redirect, session
import psycopg2
import os
import pyotp
import qrcode
from werkzeug.security import generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

def get_db_connection():
    return psycopg2.connect(
        host=os.environ["DATABASE_HOST"],
        database=os.environ["DATABASE_NAME"],
        user=os.environ["DATABASE_USER"],
        password=os.environ["DATABASE_PASSWORD"]
    )


@app.route("/")
def home():
    return """
    <h1>MFA System</h1>
    <p>Flask funciona correctamente.</p>
    <p>Conexión con PostgreSQL: OK</p>
    <a href="/register">Crear cuenta</a>
    """


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        password_hash = generate_password_hash(password)
        mfa_secret = pyotp.random_base32()

        try:
            connection = get_db_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO users (username, password_hash, mfa_secret)
                VALUES (%s, %s, %s)
                """,
                (username, password_hash, mfa_secret)
            )

            connection.commit()

            cursor.close()
            connection.close()

            return """
            <h1>Cuenta creada correctamente</h1>
            <p>El usuario se ha registrado correctamente.</p>
            <a href="/login">Ir al login</a>
            """

        except Exception as e:

            return """
            <h1>Error al crear la cuenta</h1>
            <p>No se ha podido crear la cuenta</p>
            <a href="/register">Volver</a>
            """, 500

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id, username, password_hash, mfa_enabled
            FROM users
            WHERE username = %s
            """,
            (username,)
        )

        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if user is None:
            return "Usuario o contraseña incorrectos", 401

        from werkzeug.security import check_password_hash

        if not check_password_hash(user[2], password):
            return "Usuario o contraseña incorrectos", 401

        # Guardar temporalmente usuario pendiente de MFA
        session["mfa_pending_user_id"] = user[0]
        session["mfa_pending_username"] = user[1]

        # Si MFA activado, pedir código
        if user[3]:

            return redirect("/verify-mfa")

        # Si no MFA configurado
        session["user_id"] = user[0]
        session["username"] = user[1]

        return redirect("/setup-mfa")

    return render_template("login.html")

@app.route("/setup-mfa")
def setup_mfa():

    if "user_id" not in session:
        return redirect("/login")

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT username, mfa_secret FROM users WHERE id = %s",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    if user is None:
    	cursor.close()
    	connection.close()
    	return "Usuario no encontrado", 404

    cursor.close()
    connection.close()

    username = user[0]
    mfa_secret = user[1]

    totp = pyotp.TOTP(mfa_secret)

    otp_uri = totp.provisioning_uri(
        name=username,
        issuer_name="MFA System"
    )

    qr = qrcode.make(otp_uri)

    qr_path = "/app/static/mfa_qr.png"
    qr.save(qr_path)

    return render_template(
    "setup-mfa.html",
    username=username,
    mfa_secret=mfa_secret
)
@app.route("/verify-mfa", methods=["GET", "POST"])
def verify_mfa():

    if "mfa_pending_user_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        code = request.form["code"]

        user_id = session["mfa_pending_user_id"]

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT username, mfa_secret FROM users WHERE id = %s",
            (user_id,)
        )

        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if user is None:
            return "Usuario no encontrado", 404

        username = user[0]
        mfa_secret = user[1]

        totp = pyotp.TOTP(mfa_secret)

        if totp.verify(code):

            connection = get_db_connection()
            cursor = connection.cursor()

            cursor.execute(
                "UPDATE users SET mfa_enabled = TRUE WHERE id = %s",
                (user_id,)
            )

            connection.commit()

            cursor.close()
            connection.close()

            session["user_id"] = user_id
            session["username"] = username

            session.pop("mfa_pending_user_id", None)
            session.pop("mfa_pending_username", None)

            return """
            <h1>Login completado</h1>
            <p>Autenticación multifactor correcta.</p>
            """

        return """
        <h1>Código incorrecto</h1>
        <p>El código MFA no es válido.</p>
        <a href="/verify-mfa">Volver</a>
        """, 401

    return render_template("verify-mfa.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
