import secrets
import string

from flask import (
    Flask, redirect, render_template, request, session, url_for
)

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Rooms stay in memory while the server is running.
rooms = {}


def get_player_id():
    if "player_id" not in session:
        session["player_id"] = secrets.token_hex(16)
    return session["player_id"]


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/play", methods=["GET", "POST"])
def play():
    error = None

    if request.method == "POST":
        player_id = get_player_id()
        action = request.form.get("action")

        if action == "create":
            characters = string.ascii_uppercase + string.digits
            code = "".join(secrets.choice(characters) for _ in range(6))

            while code in rooms:
                code = "".join(
                    secrets.choice(characters) for _ in range(6)
                )

            rooms[code] = {"players": [player_id]}
            return redirect(url_for("game", code=code))

        elif action == "join":
            code = request.form.get("code", "").strip().upper()
            room = rooms.get(code)

            if not code:
                error = "Please enter a room code."
            elif room is None:
                error = "That room does not exist. Check the code."
            elif player_id in room["players"]:
                return redirect(url_for("game", code=code))
            elif len(room["players"]) >= 2:
                error = "That room already has two players."
            else:
                room["players"].append(player_id)
                return redirect(url_for("game", code=code))

        else:
            error = "Please choose Create room or Join room."

    return render_template("play.html", error=error)


@app.route("/game/<code>")
def game(code):
    code = code.upper()
    room = rooms.get(code)

    if room is None:
        return render_template(
            "error.html",
            message="That room does not exist. It may have expired."
        ), 404

    player_id = get_player_id()

    if player_id not in room["players"]:
        return render_template(
            "error.html",
            message="Join this room using its code before opening it."
        ), 403

    player_number = room["players"].index(player_id) + 1

    return render_template(
        "game.html",
        code=code,
        player_number=player_number,
        player_count=len(room["players"])
    )


@app.errorhandler(404)
def page_not_found(error):
    return render_template(
        "error.html",
        message="We couldn't find that page."
    ), 404