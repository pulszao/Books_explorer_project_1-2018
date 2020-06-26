import os
import requests
from flask import Flask, session, render_template, flash, request, session, redirect, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps


app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# create a session for the database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def login_required(f):
    """
    Decorate routes to require login.
    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function


@app.route("/index", methods=["GET", "POST"])
@login_required
def index():

    if request.method == "GET":
        return render_template("index.html")

    else:
        title = request.form.get("title")
        if title:
            title = '%'+ title +'%'

        author = request.form.get("author")
        if author:
            author = '%'+ author +'%'

        isbn = request.form.get("isbn")

        books = []

        if isbn:
            books = db.execute("SELECT * FROM books WHERE isbn = :isbn ORDER BY year", {"isbn": isbn}).fetchall()

        elif title:
            books = db.execute("SELECT * FROM books WHERE title like :title ORDER BY year", {"title": title}).fetchall()
            if author:
                books = db.execute("SELECT * FROM books WHERE title like :title "
                                "AND author LIKE :author ORDER BY year", {"title": title, "author": author}).fetchall()

        elif author:
            books = db.execute("SELECT * FROM books WHERE author like :author ORDER BY year", {"author": author}).fetchall()
            if title:
                books = db.execute("SELECT * FROM books WHERE title like :title "
                                "AND author LIKE :author ORDER BY year", {"title": title, "author": author}).fetchall()
        db.commit()

        if not books:
            flash("Provide a valid book!")
            return render_template("index.html")



        else:
            return render_template("search.html", books=books)


@app.route("/", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        username = request.form.get("username")

        # Ensure username was submitted
        if not request.form.get("username"):
            message = 'must provide username'
            number = '403'
            return render_template("error.html", message=message, number=number)

        # Ensure password was submitted
        elif not request.form.get("password"):
            message = 'must provide password'
            number = '403'
            return render_template("error.html", message=message, number=number)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).fetchall()
        empty = []


        # Ensure username exists and password is correct
        if rows == empty or not check_password_hash(rows[0]['hash'], request.form.get("password")):
            message = 'invalid username and/or password'
            number = '403'
            return render_template("error.html", message=message, number=number)

        # Remember which user has logged in
        session["user_id"] = rows[0]

        # Redirect user to home page
        return redirect("/index")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    if request.method == "GET":
        return render_template("register.html")

    else:
        number = '403'
        #ensure username was submited
        if not request.form.get("username"):
            message = 'must provide username'
            return render_template("error.html", message=message, number=number)

        #ensure password was submited
        elif not request.form.get("password"):
            message = 'must provide password'
            return render_template("error.html", message=message, number=number)

        # ensure password confirmation was submitted
        elif not request.form.get("confirmation"):
            message = 'must provide password confirmation'
            return render_template("error.html", message=message, number=number)

        # ensure password and confirmation match
        elif request.form.get("password") != request.form.get("confirmation"):
            message = 'password confirmation must match'
            return render_template("error.html", message=message, number=number)

        #hash password
        hash = generate_password_hash(request.form.get("password"))

        username = db.execute("SELECT username FROM users WHERE username=:username", {"username": request.form.get("username")}).fetchone()

        #ensure if username already exists
        if username == request.form.get("username"):
            return flash("This username is already taken.", 400)

        #save  username and password into table
        db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)", {"username":request.form.get("username"), "hash":hash})

        db.commit()

        #display confirmation message
        flash("Registered!")

        return redirect("/")


@app.route("/index/<isbn>", methods=["GET", "POST"])
@login_required
def book_page(isbn):
    if request.method == "POST":
        number = '403'
        user_id = session["user_id"]['id']

        review = request.form.get("review")
        if not review:
            message = 'Must provide a review!'
            return render_template("error.html", message=message, number=number)

        rate = request.form.get("rate")
        if rate == 'None':
            message = 'Must rate the book!'
            return render_template("error.html", message=message, number=number)

        elif review and rate:
            db.execute("INSERT INTO reviews (user_id, book_isbn, review, rating) VALUES "
                        "(:user_id, :isbn, :review, :rating)", {"user_id": user_id, "isbn": isbn,
                        "review": review, "rating": rate})
            db.commit()

            flash("Review Submitted!")
            return redirect("/index/"+isbn)

    else:
        query = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchall()
        title = query[0]['title']
        author = query[0]['author']
        year = query[0]['year']

        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "CinIx2iISem0iEEU4b8RA", "isbns": isbn})
        info = res.json()
        average_rating = info['books'][0]['average_rating']
        ratings_count = info['books'][0]['ratings_count']

        user_id = session['user_id']['id']
        #check if the user has already reviwed the book
        check = db.execute("SELECT review FROM reviews WHERE user_id = :user_id AND "
                            "book_isbn = :book_isbn", {"user_id": user_id, "book_isbn": isbn}).fetchall()
        empty = []

        #check if check is empty
        if check == empty:
            disable = ""
            placeholder = ""

        else:
            placeholder = "Review already wroted"
            disable = "disabled"

        review = db.execute("SELECT users.username, reviews.review, reviews.rating FROM reviews "
                            "JOIN users ON users.id = reviews.user_id "
                            "WHERE book_isbn=:book_isbn", {"book_isbn": isbn}).fetchall()
        total = db.execute("SELECT COUNT(review) as review FROM reviews WHERE book_isbn=:book_isbn", {"book_isbn": isbn}).fetchone()
        total = total[0]

        return render_template("book_page.html", title=title, author=author, isbn=isbn, year=year, disable=disable,
                                placeholder=placeholder, ratings_count=ratings_count, average_rating=average_rating,
                                review=review, total=total)


@app.route("/api/<isbn>", methods=["GET", "POST"])
def api(isbn):
    if request.method == "POST":
        return render_template("api.html")



    else:
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "CinIx2iISem0iEEU4b8RA", "isbns": isbn})
        info = res.json()
        average_rating = info['books'][0]['average_rating']
        review_count = info['books'][0]['reviews_count']
        title = db.execute("SELECT title FROM books WHERE isbn=:isbn", {"isbn": isbn}).fetchone()[0]
        author = db.execute("SELECT author FROM books WHERE isbn=:isbn", {"isbn": isbn}).fetchone()[0]
        year = db.execute("SELECT year FROM books WHERE isbn=:isbn", {"isbn": isbn}).fetchone()[0]

        return render_template("api.html", title=title, author=author, year=year, isbn=isbn, review_count=review_count, average_rating=average_rating)