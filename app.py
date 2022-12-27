from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../database/store.db'
db = SQLAlchemy(app)

act_user = None
stock_capacity = 250


class Store(db.Model):
    __tablename__ = "store"
    id = db.Column(db.Integer, primary_key=True)
    total_revenue = db.Column(db.Float())


class Account(db.Model):
    __tablename__ = "account"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200))
    name = db.Column(db.String(100))
    password = db.Column(db.String(200))
    category = db.Column(db.Integer)  # 0 for admin, 1 for client, 2 for supplier
    shopping_list = db.Column(db.Text)


class Product(db.Model):
    __tablename__ = "product"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    img_url = db.Column(db.String(500))
    description = db.Column(db.String(1000))
    price = db.Column(db.Float)
    stock = db.Column(db.Integer)
    total_sold = db.Column(db.Integer)
    supplier_id = db.Column(db.Integer)
    total_ordered = db.Column(db.Integer)
    warehouse_location = db.Column(db.String(3))


class Supplier(db.Model):
    __tablename__ = "supplier"
    id = db.Column(db.Integer, primary_key=True)
    id_account = db.Column(db.Integer)
    name = db.Column(db.String(200))
    email = db.Column(db.String(200))
    fee = db.Column(db.Float)
    products = db.Column(db.Text)
    company = db.Column(db.String(200))
    telephone = db.Column(db.String(200))
    address = db.Column(db.String(200))
    tax_number = db.Column(db.String(200))


with app.app_context():
    db.create_all()
    db.session.commit()



@app.route('/')
def home(status=False, message=None, color=None):
    accounts = Account.query.all()
    return render_template("index.html", status=status, message=message, color=color)


@app.route('/create-account')
def signup_btn(status=""):
    return render_template("signup.html", status=status)


@app.route('/signup', methods=['POST'])
def signup():
    repeated_email = False
    for i in Account.query.all():
        if i.email == request.form['email']:
            repeated_email = True
            break

    if repeated_email:
        return signup_btn("We already have an account with this e-mail. Maybe you want to log-in or use a different e-mail?")
    acc = Account(email=request.form['email'], name=request.form['name'], password=request.form['password'], category=1,
                  shopping_list="{}")
    db.session.add(acc)
    db.session.commit()

    return home(True, "Your account was successfully created!", "var(--bs-teal)")


@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    accounts = Account.query.all()
    found_email = False
    for i in accounts:
        if i.email == email:
            found_email = True
            break

    if not found_email:
        return home(True, "Sorry, we couldn't find your e-mail. You can try again or create a new account!", "Red")

    user = Account.query.filter_by(email=email)
    if not password == user[0].password:
        return home(True,
                    "Sorry, your password doesn't match with your e-mail. You can try again or recover your password!",
                    "Red")

    global act_user
    act_user = Account.query.filter_by(email=email).first().id

    products = Product.query.all()
    if Account.query.filter_by(id=act_user).first().category == 0:
        return redirect(url_for('overview'))
    elif Account.query.filter_by(id=act_user).first().category == 1:
        return redirect(url_for('store'))
    else:
        return redirect(url_for('supplier_overview'))


@app.route('/buy/<_id>', methods=['POST'])
def buy(_id):
    selected = Product.query.filter_by(id=_id).first()
    user = Account.query.filter_by(id=act_user).first()
    if selected.stock > 0:
        selected.stock = selected.stock - 1
        user.shopping_list = json.dumps(add_shopping_list(json.loads(user.shopping_list), selected))
        selected.total_sold = selected.total_sold + 1
        Store.query.all()[0].total_revenue = selected.price
        db.session.commit()

    return redirect(url_for('store'))


@app.route('/purchases')
def purchases():
    user = Account.query.filter_by(id=act_user).first()
    if user.shopping_list != "{}":
        json_shopping_list = json.loads(user.shopping_list)
        shopping_list = []

        for i in json_shopping_list:
            product = json_shopping_list[i].split(',')
            shopping_list.append(product)

        total_spent = 0

        for i in shopping_list:
            total_spent = (total_spent + float(i[2])) * int(i[1])

        total_items = len(i)

        avg = "{:.2f}".format(total_spent / total_items)
        total_spent = "{:.2f}".format(total_spent)

        return render_template("purchases.html", user_products=shopping_list,
                               user=Account.query.filter_by(id=act_user).first(), total_spent=total_spent,
                               total_items=total_items, avg=avg)

    return render_template("purchases.html", user_products=[["", "", ""]],
                           user=Account.query.filter_by(id=act_user).first(), total_spent=0,
                           total_items=0, avg=0)


def add_shopping_list(original, new_product):
    if str(new_product.id) in original:
        un = original[str(new_product.id)].split(',')[1]
        original[str(new_product.id)] = new_product.title + ',' + str(int(un) + 1) + ',' + str(new_product.price)
    else:
        original[str(new_product.id)] = new_product.title + ',1,' + str(new_product.price)
    return original


@app.route('/store')
def store():
    return render_template("/store.html", products=Product.query.all(),
                           user=Account.query.filter_by(id=act_user).first())


@app.route('/overview')
def overview():
    t_clients = len(Account.query.filter_by(category=1).all())
    t_suppliers = len(Supplier.query.all())
    products = Product.query.all()

    t_revenue = 0
    t_fees = 0
    for i in products:
        t_revenue = t_revenue + float(i.price) * i.total_sold
        t_fees = t_fees + (float(Supplier.query.filter_by(id=i.supplier_id).first().fee) * i.total_ordered)

    t_profit = t_revenue - t_fees

    t_revenue = "{:.2f}".format(float(t_revenue))
    t_fees = "{:.2f}".format(float(t_fees))
    t_profit = "{:.2f}".format(float(t_profit))

    stock_actual = 0
    for i in products:
        stock_actual = stock_actual + i.stock

    global stock_capacity
    percent = "{:.2f}".format(stock_actual/stock_capacity * 100)

    return render_template("/overview.html", t_clients=t_clients, t_suppliers=t_suppliers, t_revenue=t_revenue,
                           t_fees=t_fees, t_profit=t_profit, user=Account.query.filter_by(id=act_user).first(), stock_capacity=stock_capacity, stock_actual=stock_actual, percent=percent, understock=(stock_actual/stock_capacity * 100) <= stock_capacity*0.1,
                           overstock=(stock_actual/stock_capacity * 100) > 100, reachedstock=(stock_actual/stock_capacity * 100) == 100)


@app.route('/clients_overview')
def clients_overview():
    clients = Account.query.filter_by(category=1).all()
    clients_list = []
    for i in clients:
        if i.category == 1:
            expenses = 0
            if i.shopping_list == '{}':
                expenses = 0
            else:
                for j in json.loads(i.shopping_list):
                    aux = json.loads(i.shopping_list)[j].split(',')
                    print("\n\n", aux)
                    expenses = expenses + float(aux[1]) * float(aux[2])
            clients_list.append([i.name, i.email, "{:.2f}".format(float(expenses))])
    return render_template("/clients_overview.html", clients=clients_list,
                           user=Account.query.filter_by(id=act_user).first(), total=len(clients))


@app.route('/suppliers_overview')
def suppliers_overview():
    suppliers = Supplier.query.all()
    suppliers_list = []
    for i in suppliers:
        g_income = 0
        t_fees = 0
        for j in json.loads(i.products):
            product = Product.query.filter_by(id=j).first()
            g_income = g_income + product.price * product.total_sold
            t_fees = t_fees + product.total_sold
        t_fees = t_fees * i.fee
        suppliers_list.append([i.id, i.name, i.email, i.fee, g_income, t_fees, g_income - t_fees, i.company, i.address, i.tax_number, i.telephone])
    return render_template("/suppliers_overview.html", suppliers=suppliers_list,
                           user=Account.query.filter_by(id=act_user).first(), total=len(suppliers))


@app.route('/create_supplier')
def create_supplier():
    return render_template("/create_supplier.html")


@app.route('/create_supplier_func', methods=['POST'])
def create_supplier_func():
    acc = Account(email=request.form['email'], name=request.form['name'], password=request.form['password'], category=2,
                  shopping_list="{}")
    db.session.add(acc)
    acc_id = Account.query.filter_by(email=request.form['email']).first().id
    sup = Supplier(email=request.form['email'], name=request.form['name'], fee=float(request.form['fee']),
                   products="[]", id_account=acc.id, address=request.form['address'], tax_number=request.form['tax_number'], company=request.form['company'], telephone=request.form['telephone'])
    db.session.add(sup)
    db.session.commit()

    return redirect(url_for('suppliers_overview'))


@app.route('/products_overview')
def products_overview():
    products = Product.query.all()
    products_list = []
    for i in products:
        supplier = Supplier.query.filter_by(id=i.supplier_id).first().name
        products_list.append([i.img_url, i.id, i.title, i.description, i.price, i.stock, i.total_sold, supplier, i.warehouse_location])

    stock_actual = 0
    for i in products:
        stock_actual = stock_actual + i.stock

    global stock_capacity

    return render_template('/products_overview.html', user=Account.query.filter_by(id=act_user).first(),
                           total=len(products), products=products_list, stock_actual=stock_actual, stock_capacity=stock_capacity)


@app.route('/create_product')
def create_product():
    return render_template('/create_product.html')


@app.route('/create_product_func', methods=['POST'])
def create_product_func():
    supplier = Supplier.query.filter_by(id=request.form['s_id']).first()
    s_fee = supplier.fee
    price = float(request.form['price']) + float(s_fee)
    pro = Product(title=request.form['title'], description=request.form['description'], img_url=request.form['img'],
                  stock=0, total_sold=0, supplier_id=request.form['s_id'], price=price, total_ordered=0, warehouse_location=request.form['location'])

    products = json.loads(supplier.products)
    products.append(len(Product.query.all()) + 1)
    supplier.products = json.dumps(products)

    db.session.add(pro)
    db.session.commit()

    return redirect(url_for('products_overview'))


@app.route('/order/<_id>')
def order(_id):
    Product.query.filter_by(id=_id).first().stock = Product.query.filter_by(id=_id).first().stock + 10
    Product.query.filter_by(id=_id).first().total_ordered = Product.query.filter_by(id=_id).first().total_ordered + 10
    db.session.commit()
    return redirect(url_for('products_overview'))


@app.route('/delete/<_id>')
def delete(_id):
    supplier = Supplier.query.filter_by(id=Product.query.filter_by(id=_id).first().supplier_id).first()
    products = json.loads(supplier.products)
    products.remove(int(_id))
    supplier.products = json.dumps(products)

    db.session.delete(Product.query.filter_by(id=_id).first())
    db.session.commit()

    return redirect(url_for('products_overview'))


@app.route('/supplier_overview')
def supplier_overview():
    user = Account.query.filter_by(id=act_user).first()
    supplier = Supplier.query.filter_by(id_account=act_user).first()

    products = []
    total_sold = 0
    total_items = 0
    for i in json.loads(supplier.products):
        j = Product.query.filter_by(id=i).first()
        products.append([j.title, j.total_ordered, j.total_ordered * supplier.fee])
        total_items = total_items + j.total_ordered
        total_sold = total_sold + j.total_ordered * supplier.fee

    avg = "{:.2f}".format(total_sold/total_items) if total_items > 0 else 0

    return render_template("supplier_overview.html", supplier_products=products,
                           user=Account.query.filter_by(id=act_user).first(), total_sold=total_sold,
                           total_items=total_items, avg=avg )


if __name__ == '__main__':
    app.run(debug=True)
