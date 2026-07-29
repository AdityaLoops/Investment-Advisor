from flask import Flask, render_template, request, redirect,  url_for, session
import pandas as pd
import sys
import os
from models import create_user, verify_user
from database import create_table

# Add the project root to Python's search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
CSV_PATH = os.path.join(BASE_DIR, "..", "Data", "external", "risk_return_df_138funds_with_sentiment.csv")


from src.calculators import advise_investment_web
# creates the web app
app = Flask(__name__)
create_table()
app.secret_key= "your secret key"

risk_return_df = pd.read_csv(CSV_PATH)



@app.route("/", methods=["GET", "POST"])
# This is called a decorator.
# It tells Flask -> "Whenever someone visits /, run the function below."
# "/" ->  Means homepage.

def home():

    recommendations = None

    # Default values when page first opens
    principal = ""
    years = ""
    penalty = ""
    risk_column = "predicted_min_cagr"
    n =3

    logged_in = "user_id" in session
    if request.method == "POST":


        principal = int(float(request.form["principal"]))
        years = int(request.form["years"])
        penalty = float(request.form["penalty"])
        risk_column = request.form["risk_column"]

        n = int(request.form.get("n", 3))

        recommendations = advise_investment_web(
            risk_return_df,
            principal,
            years,
            penalty,
            risk_column,
            n
        )

    return render_template(
        "index.html",
        recommendations=recommendations,
        principal=principal,
        years=years,
        penalty=penalty,
        risk_column=risk_column,
        n =n,
        logged_in = logged_in
    )

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method =="POST":
        username= request.form['username']
        email = request.form['email']
        password = request.form['password']

        success =create_user(username, email, password)
        if not success:
            return render_template("register.html", error = "Email Already Registered")

        return redirect(url_for("home"))
    
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = verify_user(email, password)

        if not user:
            return render_template(
                "login.html",
                error="Wrong email or password"
            )
        session['user_id'] = user['id'] 
        return redirect(url_for("home"))

    return render_template("login.html")  



if __name__ == "__main__":
    app.run(debug=True)     