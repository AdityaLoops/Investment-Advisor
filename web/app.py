from flask import Flask, render_template, request
import pandas as pd
import sys
import os

# Add the project root to Python's search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
CSV_PATH = os.path.join(BASE_DIR, "..", "Data", "external", "risk_return_df_138funds_filtered_min7yr.csv")


from src.calculators import advise_investment_web
# creates the web app
app = Flask(__name__)

risk_return_df = pd.read_csv(CSV_PATH)



@app.route("/", methods=["GET", "POST"])
def home():

    recommendations = None

    # Default values when page first opens
    principal = ""
    years = ""
    penalty = ""
    risk_column = "predicted_min_cagr"
    n =3

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
        n =n
    )
if __name__ == "__main__":
    app.run(debug=True)     