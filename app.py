from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
import csv

app = Flask(__name__)
app.secret_key = "bookhive_secret_key"


# -------------------------------
# Database connection
# -------------------------------
def get_db_connection():
    conn = sqlite3.connect("library.db")
    conn.row_factory = sqlite3.Row
    return conn


# -------------------------------
# Home (role selection)
# -------------------------------
@app.route("/")
def home():
    return render_template("role_select.html")


# -------------------------------
# Login (Admin / Student)
# -------------------------------
@app.route("/login/<role>", methods=["GET", "POST"])
def login(role):
    if role not in ["admin", "student"]:
        return redirect("/")

    error = None

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=? AND role=?",
            (username, password, role)
        ).fetchone()
        conn.close()

        if user:
            session.clear()
            session["user_id"] = user["id"]      # IMPORTANT
            session["role"] = role               # IMPORTANT
            session["username"] = username

            if role == "admin":
                return redirect("/admin")
            else:
                return redirect("/student")
        else:
            error = "Invalid username or password"

    return render_template("login.html", role=role, error=error)


# -------------------------------
# Signup (Students only)
# -------------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    message = None

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        existing = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()

        if existing:
            message = "Username already exists"
            conn.close()
        else:
            conn.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, 'student')",
                (username, password)
            )
            conn.commit()
            conn.close()
            return redirect("/login/student")

    return render_template("signup.html", message=message)


# -------------------------------
# Admin dashboard
# -------------------------------
@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return redirect("/login/admin")
    return render_template("admin.html")


# -------------------------------
# Student dashboard
# -------------------------------
@app.route("/student")
def student():
    if session.get("role") != "student":
        return redirect("/login/student")
    return render_template("student.html")


# -------------------------------
# Add book (Admin)
# -------------------------------
@app.route("/admin/add", methods=["GET", "POST"])
def add_book():
    if session.get("role") != "admin":
        return redirect("/login/admin")

    message = None

    if request.method == "POST":
        book_id = request.form["book_id"]
        title = request.form["title"]
        author = request.form["author"]
        category = request.form["category"]

        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO books (id, title, author, category, available) VALUES (?, ?, ?, ?, 1)",
                (book_id, title, author, category)
            )
            conn.commit()
            message = "Book added successfully"
        except sqlite3.IntegrityError:
            message = "Book ID already exists"
        conn.close()

    return render_template("add_book.html", message=message)


# -------------------------------
# Issue book (Admin)
# -------------------------------
@app.route("/admin/issue", methods=["GET", "POST"])
def issue_book():
    if session.get("role") != "admin":
        return redirect("/login/admin")

    message = None

    if request.method == "POST":
        book_id = request.form["book_id"]

        conn = get_db_connection()
        book = conn.execute(
            "SELECT * FROM books WHERE id=?",
            (book_id,)
        ).fetchone()

        if book and book["available"] == 1:
            conn.execute(
                "UPDATE books SET available=0 WHERE id=?",
                (book_id,)
            )
            conn.commit()
            message = "Book issued successfully"
        else:
            message = "Book not found or already issued"

        conn.close()

    return render_template("issue_book.html", message=message)


# -------------------------------
# Return book (Admin)
# -------------------------------
@app.route("/admin/return", methods=["GET", "POST"])
def return_book():
    if session.get("role") != "admin":
        return redirect("/login/admin")

    message = None

    if request.method == "POST":
        book_id = request.form["book_id"]

        conn = get_db_connection()
        book = conn.execute(
            "SELECT * FROM books WHERE id=?",
            (book_id,)
        ).fetchone()

        if book and book["available"] == 0:
            conn.execute(
                "UPDATE books SET available=1 WHERE id=?",
                (book_id,)
            )
            conn.commit()
            message = "Book returned successfully"
        else:
            message = "Book not found or already available"

        conn.close()

    return render_template("return_book.html", message=message)


# -------------------------------
# Delete book (Admin)
# -------------------------------
@app.route("/admin/delete", methods=["GET", "POST"])
def delete_book():
    if session.get("role") != "admin":
        return redirect("/login/admin")

    message = None

    if request.method == "POST":
        book_id = request.form["book_id"]

        conn = get_db_connection()
        book = conn.execute(
            "SELECT * FROM books WHERE id=?",
            (book_id,)
        ).fetchone()

        if book:
            conn.execute(
                "DELETE FROM books WHERE id=?",
                (book_id,)
            )
            conn.commit()
            message = "Book deleted successfully"
        else:
            message = "Book not found"

        conn.close()

    return render_template("delete_book.html", message=message)


# -------------------------------
# Export books to CSV (Admin)
# -------------------------------
@app.route("/admin/export")
def export_books():
    if "role" not in session:
        return redirect("/login/admin")

    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books").fetchall()
    conn.close()

    filename = "books_export.csv"

    with open(filename, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["ID", "Title", "Author", "Category", "Available"])

        for book in books:
            writer.writerow([
                book["id"],
                book["title"],
                book["author"],
                book["category"],
                "Yes" if book["available"] == 1 else "No"
            ])

    return send_file(filename, as_attachment=True)


# -------------------------------
# Search books (Student)
# -------------------------------
@app.route("/search")
def search():
    if session.get("role") != "student":
        return redirect("/login/student")

    query = request.args.get("query", "").strip()
    conn = get_db_connection()

    if query.isdigit():
        books = conn.execute(
            "SELECT * FROM books WHERE id=?",
            (query,)
        ).fetchall()
    else:
        books = conn.execute(
            """
            SELECT * FROM books
            WHERE LOWER(title) LIKE LOWER(?)
               OR LOWER(author) LIKE LOWER(?)
               OR LOWER(category) LIKE LOWER(?)
            """,
            (f"%{query}%", f"%{query}%", f"%{query}%")
        ).fetchall()

    conn.close()
    return render_template("search.html", books=books)


# -------------------------------
# Logout
# -------------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# -------------------------------
# Run app
# -------------------------------
if __name__ == "__main__":
    app.run(debug=True)
