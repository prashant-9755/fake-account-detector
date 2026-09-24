from flask import Flask, render_template, request, session, redirect, url_for
import joblib
import pandas as pd
import mysql.connector

app = Flask(__name__)

# Secret key for login session
app.secret_key = "fake-account-detection-secret-key"

# Load trained ML model
model = joblib.load("model/fake_account_model.pkl")


# MySQL connection
def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="root",
        database="fake_account_detection"
    )


# =========================
# HOME PAGE
# =========================

@app.route("/")
def home():
    return render_template("index.html")


# =========================
# ADMIN LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":

            session["admin_logged_in"] = True

            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid username or password!"
        )

    return render_template("login.html")


# =========================
# PREDICTION
# =========================

@app.route("/detect")
def detect():
    return render_template("detect.html")

@app.route("/predict", methods=["POST"])
def predict():

    followers = int(request.form["followers"])
    following = int(request.form["following"])
    posts = int(request.form["posts"])
    account_age = int(request.form["account_age"])
    profile_pic = int(request.form["profile_pic"])
    bio = int(request.form["bio"])

    # Create DataFrame
    data = pd.DataFrame([[
        followers,
        following,
        posts,
        account_age,
        profile_pic,
        bio
    ]], columns=[
        "followers",
        "following",
        "posts",
        "account_age",
        "profile_pic",
        "bio"
    ])

    # ML prediction
    prediction = model.predict(data)[0]

    probability = model.predict_proba(data)[0]

    fake_probability = probability[1] * 100
    genuine_probability = probability[0] * 100

    # Dynamic indicators
    indicators = []

    if following > followers * 5:
        indicators.append(
            "⚠️ Following is much higher than followers."
        )
    else:
        indicators.append(
            "✓ Followers and following ratio looks reasonable."
        )

    if posts < 10:
        indicators.append(
            "⚠️ Very low number of posts."
        )
    else:
        indicators.append(
            "✓ Account has reasonable posting activity."
        )

    if account_age < 6:
        indicators.append(
            "⚠️ Account is relatively new."
        )
    else:
        indicators.append(
            "✓ Account has been active for a longer period."
        )

    if profile_pic == 0:
        indicators.append(
            "⚠️ Profile picture is missing."
        )
    else:
        indicators.append(
            "✓ Profile picture is available."
        )

    if bio == 0:
        indicators.append(
            "⚠️ Profile bio is missing."
        )
    else:
        indicators.append(
            "✓ Profile bio is available."
        )

    # Final result
    if prediction == 1:

        result = "Fake / Suspicious Account"
        confidence = fake_probability

    else:

        result = "Genuine Account"
        confidence = genuine_probability

    confidence = round(confidence, 2)


    # Save detection in MySQL
    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
        INSERT INTO detection_history
        (
            followers,
            following,
            posts,
            account_age,
            profile_pic,
            bio,
            prediction,
            confidence
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            followers,
            following,
            posts,
            account_age,
            profile_pic,
            bio,
            result,
            confidence
        )

        cursor.execute(query, values)

        connection.commit()

        cursor.close()
        connection.close()

        print("Detection saved to MySQL successfully!")

    except mysql.connector.Error as error:

        print("MySQL Error:", error)

    return render_template(
        "result.html",
        result=result,
        confidence=confidence,
        indicators=indicators,
        followers=followers,
        following=following,
        posts=posts,
        account_age=account_age,
        profile_pic=profile_pic,
        bio=bio
    )


# =========================
# DETECTION HISTORY
# =========================

@app.route("/history")
def history():

    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT *
            FROM detection_history
            ORDER BY detected_at DESC
        """)

        records = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template(
            "history.html",
            records=records
        )

    except mysql.connector.Error as error:

        return f"MySQL Error: {error}"

# =========================
# ADMIN DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        filter_type = request.args.get("filter", "all")
        search = request.args.get("search", "").strip()

        # Base query
        base_query = """
            SELECT
                id, followers, following, posts,
                prediction, confidence, detected_at
            FROM detection_history
        """

        conditions = []
        params = []

        # Filter
        if filter_type == "fake":
            conditions.append("prediction = %s")
            params.append("Fake / Suspicious Account")

        elif filter_type == "genuine":
            conditions.append("prediction = %s")
            params.append("Genuine Account")

        # Search
        if search:
            conditions.append("""
                (
                    prediction LIKE %s
                    OR CAST(id AS CHAR) LIKE %s
                    OR CAST(followers AS CHAR) LIKE %s
                    OR CAST(following AS CHAR) LIKE %s
                )
            """)

            search_pattern = f"%{search}%"
            params.extend([
                search_pattern,
                search_pattern,
                search_pattern,
                search_pattern
            ])

        # Add WHERE condition
        query = base_query

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY detected_at DESC LIMIT 20"

        cursor.execute(query, tuple(params))
        records = cursor.fetchall()

        # Total accounts
        cursor.execute("SELECT COUNT(*) FROM detection_history")
        total = cursor.fetchone()[0]

        # Fake accounts
        cursor.execute("""
            SELECT COUNT(*)
            FROM detection_history
            WHERE prediction = 'Fake / Suspicious Account'
        """)
        fake = cursor.fetchone()[0]

        # Genuine accounts
        cursor.execute("""
            SELECT COUNT(*)
            FROM detection_history
            WHERE prediction = 'Genuine Account'
        """)
        genuine = cursor.fetchone()[0]

        cursor.close()
        connection.close()

        return render_template(
            "dashboard.html",
            total=total,
            fake=fake,
            genuine=genuine,
            recent_records=records,
            filter_type=filter_type,
            search=search
        )

    except mysql.connector.Error as error:
        return f"MySQL Error: {error}"

       
# =========================
# ADMIN DELETE ROUTER
# =========================

@app.route("/delete/<int:record_id>")
def delete_record(record_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "DELETE FROM detection_history WHERE id = %s",
            (record_id,)
        )

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("dashboard"))

    except mysql.connector.Error as error:
        return f"MySQL Error: {error}"

# =========================
# CLEAR HISTORY ROUTER
# =========================

@app.route("/clear-history")
def clear_history():
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("DELETE FROM detection_history")
        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("dashboard"))

    except mysql.connector.Error as error:
        return f"MySQL Error: {error}"


# =========================
# ADMIN LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.pop("admin_logged_in", None)

    return redirect(url_for("login"))


# =========================
# RUN APPLICATION
# =========================

if __name__ == "__main__":
    app.run(debug=True)