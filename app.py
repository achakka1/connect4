import secrets
import string
from threading import RLock

from flask import (
    Flask, flash, redirect, render_template,
    request, session, url_for
)

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

rooms = {}
room_lock = RLock()

ROWS = 6
COLUMNS = 7


def get_player_id():
    if "player_id" not in session:
        session["player_id"] = secrets.token_hex(16)

    return session["player_id"]


def find_winning_cells(board, player):
    # Horizontal, vertical, and both diagonal directions.
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

    for row in range(ROWS):
        for column in range(COLUMNS):
            for row_step, column_step in directions:
                cells = [
                    (row + i * row_step, column + i * column_step)
                    for i in range(4)
                ]

                if all(
                    0 <= r < ROWS
                    and 0 <= c < COLUMNS
                    and board[r][c] == player
                    for r, c in cells
                ):
                    return cells

    return []


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/play", methods=["GET", "POST"])
def play():
    error = None

    if request.method == "POST":
        player_id = get_player_id()
        action = request.form.get("action")

        with room_lock:
            if action == "create":
                characters = string.ascii_uppercase + string.digits

                while True:
                    code = "".join(
                        secrets.choice(characters) for _ in range(6)
                    )
                    if code not in rooms:
                        break

                rooms[code] = {
                    "players": [player_id],
                    "board": [
                        [0 for _ in range(COLUMNS)]
                        for _ in range(ROWS)
                    ],
                    "turn": 1,
                    "winner": None,
                    "draw": False,
                    "winning_cells": []
                }

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
    player_id = get_player_id()

    with room_lock:
        room = rooms.get(code)

        if room is None:
            return render_template(
                "error.html",
                message="That room does not exist. It may have expired."
            ), 404

        if player_id not in room["players"]:
            return render_template(
                "error.html",
                message="Join this room using its code first."
            ), 403

        player_number = room["players"].index(player_id) + 1

        return render_template(
            "game.html",
            code=code,
            player_number=player_number,
            player_count=len(room["players"]),
            board=room["board"],
            turn=room["turn"],
            winner=room["winner"],
            draw=room["draw"],
            winning_cells=room["winning_cells"]
        )


@app.route("/game/<code>/move", methods=["POST"])
def move(code):
    code = code.upper()
    player_id = get_player_id()

    with room_lock:
        room = rooms.get(code)

        if room is None:
            return render_template(
                "error.html",
                message="That room no longer exists. Create a new room."
            ), 404

        if player_id not in room["players"]:
            return render_template(
                "error.html",
                message="You must join this room before playing."
            ), 403

        player_number = room["players"].index(player_id) + 1
        column = request.form.get("column", type=int)

        if len(room["players"]) < 2:
            flash("Wait for Player 2 to join.")

        elif room["winner"] is not None or room["draw"]:
            flash("This game has ended. Create a new room to play again.")

        elif player_number != room["turn"]:
            flash("It isn't your turn yet.")

        elif column is None or not 0 <= column < COLUMNS:
            flash("Please choose a column from 1 to 7.")

        elif room["board"][0][column] != 0:
            flash("That column is full. Choose another column.")

        else:
            # Search from the bottom for the first empty space.
            for row in range(ROWS - 1, -1, -1):
                if room["board"][row][column] == 0:
                    room["board"][row][column] = player_number
                    break

            winning_cells = find_winning_cells(
                room["board"], player_number
            )

            if winning_cells:
                room["winner"] = player_number
                room["winning_cells"] = winning_cells

            elif all(cell != 0 for cell in room["board"][0]):
                room["draw"] = True

            else:
                room["turn"] = 3 - player_number

    return redirect(url_for("game", code=code))


@app.errorhandler(404)
def page_not_found(error):
    return render_template(
        "error.html",
        message="We couldn't find that page."
    ), 404


@app.errorhandler(500)
def server_error(error):
    return render_template(
        "error.html",
        message="Something went wrong. Please return to room selection."
    ), 500
    