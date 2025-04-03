from flask import Flask, render_template, request, flash, session, redirect

app = Flask(__name__)
app.secret_key = 'behavior'


@app.route("/, methods=["GET", "POST"])
def home():
    # Handle POST request to check for logout
    if request.method == "POST":
        logout = request.form.get("check")
        if logout == "logout":
            session.clear()  # Clear the session
            flash("You have been logged out automatically.", "info")
            return redirect("/")  # Redirect to the same page (simulate logout)

    # Render the test form
    return render_template("test.html")


if __name__ == "__main__":
    app.run(debug=True)
