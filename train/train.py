from flask import Flask, render_template, request
import psycopg2

app = Flask(__name__)


conn = psycopg2.connect(
    database="mouse_patterns",
    user="postgres",
    password="Joel@123",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/track", methods=["POST"])
def track():
    data = request.json
    user_id = data.get("user_id", "unknown")
    avg_mouse_x = data.get("avg_mouse_x")
    avg_mouse_y = data.get("avg_mouse_y")
    num_clicks = data.get("num_clicks")
    scroll_speed = data.get("scroll_speed")
    typing_speed = data.get("typing_speed")


    cursor.execute(
        """
        INSERT INTO user_behavior7 (user_id, avg_mouse_x, avg_mouse_y, num_clicks, scroll_speed, typing_speed)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (user_id, avg_mouse_x, avg_mouse_y, num_clicks, scroll_speed, typing_speed)
    )
    conn.commit()

    return {"message": "Data received"}, 200

if __name__ == "__main__":
    app.run(debug=True)
