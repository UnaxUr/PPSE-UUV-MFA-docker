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
    return render_template(
        "message.html",
        title="MFA System",
        message="Protege tu cuenta con autenticacion multifactor.",
        link_url="/login",
        link_text="Iniciar Sesion"
    )


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

            return render_template(
                "message.html",
                title="Cuenta creada correctamente",
                message="El usuario se ha registrado correctamente.",
                link_url="/login",
                link_text="Ir al login"
            )

        except Exception as e:
            print(f"ERROR AL CREAR CUENTA: {e}", flush=True)

            return render_template(
                "message.html",
                title="Error al crear la cuenta",
                message="No se ha podido crear la cuenta.",
                link_url="/register",
                link_text="Volver"
            ), 500

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
            return render_template(
            "message.html",
            title="Acceso denegado",
            message="Usuario o contraseña incorrectos.",
            link_url="/login",
            link_text="Volver al login"
        ), 401


        from werkzeug.security import check_password_hash


        if not check_password_hash(user[2], password):
            return render_template(
            "message.html",
            title="Acceso denegado",
            message="Usuario o contraseña incorrectos.",
            link_url="/login",
            link_text="Volver al login"
        ), 401


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

            return render_template(
                "message.html",
                title="Login completado",
                message="Autenticación multifactor correcta.",
                link_url="/",
                link_text="Volver al inicio"
            )

        return render_template(
            "message.html",
            title="Código incorrecto",
            message="El código MFA no es válido. Inténtalo de nuevo.",
            link_url="/verify-mfa",
            link_text="Volver a verificar"
        ), 401

    return render_template("verify-mfa.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
