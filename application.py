import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    cashamount = (db.execute("SELECT cash FROM users WHERE id = :userid", userid=session["user_id"]))[0]['cash']
    owned = db.execute("SELECT * FROM purchases WHERE userid = :userid", userid=session["user_id"])
    companies = []
    for i in owned:
        companies.append(i['company'])

    companies = list(set(companies))
    dbvals = dict.fromkeys(companies)

    for i, j in dbvals.items():
        dbvals[i] = 0
    for i in owned:
        dbvals[i['company']] += i['shares']

    final = []
    totalamount = 0
    for i, j in dbvals.items():
        totalamount += lookup(i)['price']*j
        final.append({'symbol': i, 'name': lookup(i)['name'], 'shares': j,
                      'price': usd(lookup(i)['price']), "total": usd(lookup(i)['price']*j)})
    totalamount += cashamount
    final.append({'symbol': "CASH", 'name': "", 'shares': "", 'price': "", "total": usd(cashamount)})
    return render_template("index.html", owned=final, totalamount=usd(totalamount))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "GET":
        return render_template("buy.html")
    else:
        cashamount = (db.execute("SELECT cash FROM users WHERE id = :userid",
                                 userid=session["user_id"]))[0]['cash']
        if not lookup(request.form.get("symbol")):
            return apology("invalid", 400)
        stock = lookup(request.form.get("symbol"))

        if not request.form.get("shares").isdigit():
            return apology("must enter int", 400)

        shares = int(request.form.get("shares"))
        price = stock['price'] * shares
        if price > cashamount or shares < 1:
            return render_template("buy.html")
        db.execute("INSERT INTO purchases(userid,shares,company,dateof,price) VALUES(:u,:sha, :company, CURRENT_TIMESTAMP,:p )",
                   u=session["user_id"], sha=shares, company=stock['symbol'], p=price)
        cashamount -= price
        db.execute("UPDATE users SET cash = :c WHERE id = :userid", c=cashamount, userid=session["user_id"])
        return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    owned = db.execute("SELECT * FROM purchases WHERE userid = :userid", userid=session["user_id"])
    return render_template("history.html", owned=owned)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")
    else:
        company = lookup(request.form.get("symbol"))

        if company:
            string = "A share of "+company["name"]+"("+company["symbol"]+") costs "+usd(company["price"])
            return render_template("quoted.html", thequote=string)
        else:
            return apology("invalid quote", 400)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        if not request.form.get("username"):
            return apology("must provide username", 400)
            # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)
        # Ensure password was submitted
        elif not request.form.get("confirmation"):
            return apology("must confirm password", 400)
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords must match", 400)

        if not db.execute("INSERT INTO users(username,hash) VALUES(:u,:h)", u=request.form.get("username"), h=generate_password_hash(request.form.get("password"))):
            return apology("username taken", 400)

        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "GET":
        owned = db.execute("SELECT * FROM purchases WHERE userid = :userid",
                           userid=session["user_id"])
        companies = []
        for i in owned:
            companies.append(i['company'])

        companies = list(set(companies))
        return render_template("sell.html", companies=companies)
    else:
        cashamount = (db.execute("SELECT cash FROM users WHERE id = :userid",
                                 userid=session["user_id"]))[0]['cash']

        owned = db.execute("SELECT * FROM purchases WHERE userid = :userid",
                           userid=session["user_id"])
        companies = []
        for i in owned:
            companies.append(i['company'])

        companies = list(set(companies))
        dbvals = dict.fromkeys(companies)

        for i, j in dbvals.items():
            dbvals[i] = 0
        for i in owned:
            dbvals[i['company']] += i['shares']

        if not lookup(request.form.get("symbol")) or not request.form.get("shares"):
            return apology("invalid", 400)

        stock = lookup(request.form.get("symbol"))

        if not request.form.get("shares").isdigit():
            return apology("must enter int", 400)

        shares = int(request.form.get("shares"))
        usershares = dbvals[stock['symbol']]

        price = stock['price'] * shares
        if shares > usershares or shares < 1:
            return apology("not enough shares", 400)
        shares *= -1
        db.execute("INSERT INTO purchases(userid,shares,company,dateof,price) VALUES(:u,:sha, :company, CURRENT_TIMESTAMP,:p )",
                   u=session["user_id"], sha=shares, company=stock['symbol'], p=price)
        cashamount += price
        db.execute("UPDATE users SET cash = :c WHERE id = :userid", c=cashamount, userid=session["user_id"])
        return redirect("/")


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
