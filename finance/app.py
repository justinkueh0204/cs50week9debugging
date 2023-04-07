import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, transform_stock_quantity_rows_to_dictionary


# Configure application 
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    print(os.environ.get('API_KEY'))
    raise RuntimeError("API_KEY not set")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session["user_id"]
    user = db.execute("SELECT username FROM users WHERE id = ?", user_id)[0]["username"]
    groupedstockquantity = db.execute("SELECT stock_symbol, SUM(quantity) AS quantity, SUM(total_amount_paid) AS total_cash_per_stock_symbol FROM buystocks WHERE user_id = ? GROUP BY stock_symbol", user_id)
    # buystocktable is returned as a list of dictionary
    print(f"group stocked quantity is {groupedstockquantity}")

    # 1) Which stocks the user owns; 2) No. of shares owned; 3) the current price of each stock, and 4) the total value of each holding (i.e., shares times price).
    # 5) Also display the user’s current cash balance along with a grand total (i.e., stocks’ total value plus cash).

    #Create a dictionary so that HTML can read from the dictionary for each relevant row
    pricedict = {}
    total_cash_per_stock_symbol_dict = {}
    stock_value_sum = float(0)

    for row in groupedstockquantity:
        print(f"{row}")
        stock_symbol = row["stock_symbol"]
        quantity = row["quantity"]
        print(f"{quantity}")
        pricedict[stock_symbol] = lookup(stock_symbol)["price"]
        total_cash_per_stock_symbol_dict[stock_symbol] = quantity * pricedict[stock_symbol]
        stock_value_sum += total_cash_per_stock_symbol_dict[stock_symbol]
        print(f"{pricedict}")

    cash = db.execute("SELECT cash FROM users where id = ?", user_id)[0]["cash"]
    total_value = cash + stock_value_sum
    #print cash, print portfolio value
    ##variables: cash_value; total_value;
    return render_template("index.html", groupedstockquantity=groupedstockquantity, pricedict=pricedict, cash=cash, total_cash_per_stock_symbol_dict=total_cash_per_stock_symbol_dict, total_value=total_value, user = user)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")

    elif request.method == "POST":
        if request.form.get("symbol") == "":
            return apology("Missing stock input", 403)

        stock_info = lookup(request.form.get("symbol"))

        if not stock_info:
            return apology("invalid stock", 403)

        quantity = int(request.form.get("shares"))

        if quantity < 0:
            return apology("Quantity should be larger than 0", 403)

        price = stock_info["price"]
        symbol = stock_info["symbol"]
        # Check if quantity times stock price is <= "cash" in "users". If yes, execute trade
        total_price = float(price) * float(quantity)
        users_cash = float(db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"])

        # Store record of 1. WHO bought 2. WHAT 3. WHEN.
        # Table needs to include 1) UNIQUE transaction ID; 2) session user ID;
        # 3) Timestamp; 4) Stock symbol; 5) Stock price; 6) Total amount paid

        if total_price > users_cash:
            return apology("Not enough money", 403)

        user_id = session["user_id"]
        buystocks_rows = db.execute("SELECT * FROM buystocks")
        timestamp = db.execute("SELECT datetime()")[0]["datetime()"]
        if len(buystocks_rows) < 1:
            db.execute("INSERT INTO buystocks (unique_transaction_id, user_id, timestamp, stock_symbol, stock_price, total_amount_paid, quantity) VALUES (0, ?, ?, ?, ?, ?, ?)", session["user_id"], timestamp, symbol, price, total_price, quantity)

        else:
            db.execute("INSERT INTO buystocks (user_id, timestamp, stock_symbol, stock_price, total_amount_paid, quantity) VALUES (?, ?, ?, ?, ?, ?)", user_id, timestamp, symbol, price, total_price, quantity)

        leftover_cash = users_cash - total_price
        db.execute("UPDATE users SET cash = ? WHERE id = ?", leftover_cash, user_id)


            #fields: 0) unique_transaction_id; 1) user_id; 2) timestamp;
            #fields: 3) stock_symbol; 4) stock_price; 5) total_amount_paid

        return render_template("bought.html", user_id = user_id, quantity = quantity, timestamp = timestamp, symbol = symbol, price = price, total_price = total_price, leftover_cash = leftover_cash)


        # Update total amount of money in "cash" column from "users" table
        # Define UNIQUE indexes on any fields that should be unique.
        # Define (non-UNIQUE) indexes on any fields via which you will search (as via SELECT with WHERE).
        # Find out how much cash the user has. Validate that user has enough money. Show how much user has leftover




@app.route("/history")
@login_required
def history():
    """Show history of transactions"""



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
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

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
    if request.method == "GET":
        return render_template("quote.html")

    elif request.method == "POST":
        stock = request.form.get("stock")
        stock_info = lookup(stock)
        if not stock_info or not stock_info["name"] or not stock_info["price"] or not stock_info["symbol"]:
            return apology("invalid or empty stock", 403)
        name = stock_info["name"]
        price = stock_info["price"]
        symbol = stock_info["symbol"]
        print(price)
        return render_template("quoted.html", name = name, price = price, symbol = symbol)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    """Navigate to register HTML page"""
    # Bring user to this page if you click on a link
    if request.method == "GET":
        return render_template("register.html")

    else:
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        #If username not present
        if not username:
            return apology("Must provide username", 403)

        # Username should NOT exist. Query database and if number of rows less than 1, then it shouldn't exist
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(rows) != 0:
            return apology("Username already exists", 403)

        # Check if password was filled.
        if not password:
            return apology("Must provide password", 403)

        # Check if confirm_password was filled.
        if not confirm_password:
            return apology("Must confirm password", 403)

        # Check if password and confirm_password matches.
        if password != confirm_password:
            return apology("Password do not match", 403)

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hashed_password)

        return render_template("login.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    user_id = session["user_id"]
    groupedstockquantity = db.execute("SELECT stock_symbol, SUM(quantity) AS quantity FROM buystocks WHERE user_id = ? GROUP BY stock_symbol", user_id)
    cash = db.execute("SELECT cash FROM users where id = ?", user_id)[0]["cash"]
    stock_quantity_dictionary = transform_stock_quantity_rows_to_dictionary(groupedstockquantity)

    if request.method == "GET":
        return render_template("sell.html", list_of_stock_symbols=list(stock_quantity_dictionary.keys()))

    elif request.method == "POST":
        input_shares_quantity = float(request.form.get("shares"))
        symbol = request.form.get("sell")
        user_shares_quantity = stock_quantity_dictionary[symbol]
        price = lookup(symbol)["price"]

        if input_shares_quantity < 0:
            return apology("Please insert a postiive number", 403)

        elif input_shares_quantity > user_shares_quantity:
            return apology("Please insert a number lower than what the user already has", 403)

        else:
            # Update user's cash
            # Update user's stocks
            cash += (price * user_shares_quantity)
            # TODO: Add db call here to update
        return redirect('/')
    else:
        return apology("TODO")
