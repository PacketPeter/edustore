import sqlite3
import json
import email
import smtplib
import bcrypt
from schema import create_schema
import os
import flask
import flask_login

# Try to open autocomplete.json if it does not exist create it
try:
    with open('autocomplete.json', 'r') as f:
        pass
except FileNotFoundError:
    with open('autocomplete.json', 'w') as f:
        json.dump({'item_names': []}, f)

'''
logged_in_user = {
    district_id: user_initials:is_admin
}
'''
logged_in_user = {}
district_name_to_id = {}

app = flask.Flask(__name__)
app.secret_key = os.urandom(24)
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

class User(flask_login.UserMixin):
    pass

@login_manager.user_loader
def user_loader(username):
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()
    c.execute("""
        SELECT district_id FROM district_logins WHERE district_username = ?
    """, (username,))
    result = c.fetchone()
    conn.close()
    if not result:
        return

    user = User()
    user.id = username
    return user


@app.route('/', methods=['GET'])
def index():
    return flask.render_template('index.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if flask.request.method == 'GET':
        return flask.render_template('contact.html')

    elif flask.request.method == 'POST':
        name = flask.request.form['name']
        email = flask.request.form['email']
        district = flask.request.form['district']
        country = flask.request.form['country']

        conn = sqlite3.connect('inventory.db')
        c = conn.cursor()
        c.execute("""
            INSERT INTO contact VALUES (?, ?, ?, ?)
        """, (name, email, district, country))
        conn.commit()
        return flask.render_template('contact.html', success=True)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if flask.request.method == 'GET':
        return flask.render_template('login.html')

    elif flask.request.method == 'POST':
        district_username = flask.request.form['district_username']
        password = flask.request.form['password']

        conn = sqlite3.connect('inventory.db')
        c = conn.cursor()
        c.execute("""
            SELECT * FROM district_logins WHERE district_username = ?
        """, (district_username,))
        result = c.fetchone()
        conn.close()
        if not result:
            return flask.render_template('login.html', error=True)

        if bcrypt.checkpw(password.encode('utf-8'), result[2].encode('utf-8')):
            user = User()
            user.id = district_username
            district_name_to_id[district_username] = result[0]
            flask_login.login_user(user)
            return flask.redirect('/district_login')


@app.route('/district_login', methods=['GET', 'POST'])
@flask_login.login_required
def district_login():
    if flask.request.method == 'GET':
        if district_name_to_id[flask_login.current_user.id] in logged_in_user:
            return flask.redirect('/home')
        return flask.render_template('district_login.html')

    elif flask.request.method == 'POST':
        initials = str(flask.request.form['initials']).upper()
        conn = sqlite3.connect('inventory.db')
        c = conn.cursor()
        c.execute("""
            SELECT * FROM users WHERE initials = ? AND district_id = ?
        """, (initials, district_name_to_id[flask_login.current_user.id]))
        result = c.fetchone()
        conn.close()
        if not result:
            return flask.render_template('district_login.html', error=True)

        logged_in_user[district_name_to_id[flask_login.current_user.id]] = initials + ':' + str(result[2])
        return flask.redirect('/home')


@app.route('/home', methods=['GET'])
@flask_login.login_required
def home():
    if district_name_to_id[flask_login.current_user.id] not in logged_in_user:
        return flask.redirect('/district_login')

    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()
    c.execute("""
        SELECT * FROM districts WHERE district_id = ?
    """, (district_name_to_id[flask_login.current_user.id],))
    district_name = c.fetchone()[1]
    conn.close()

    is_admin = logged_in_user[district_name_to_id[flask_login.current_user.id]].split(':')[1]
    if is_admin:
        admin = " and are an admin. Please scan an item or choose from an option below."

    else:
        admin = ". Please scan an item to continue."

    if flask.request.args.get('success_message'):
        return flask.render_template('home.html', district_name=district_name, admin=admin, is_admin=is_admin, success_message=flask.request.args.get('success_message'), initials=logged_in_user[district_name_to_id[flask_login.current_user.id]].split(':')[0])

    if flask.request.args.get('error_message'):
        error_message = flask.request.args.get('error_message')
        if flask.request.args.get('specialized_error'):
            return flask.render_template('home.html', district_name=district_name, admin=admin, is_admin=is_admin, error_message=error_message, initials=logged_in_user[district_name_to_id[flask_login.current_user.id]].split(':')[0], specialized_error=True)
        else:
            return flask.render_template('home.html', district_name=district_name, admin=admin, is_admin=is_admin, error_message=error_message, initials=logged_in_user[district_name_to_id[flask_login.current_user.id]].split(':')[0])

    else:
        return flask.render_template('home.html', district_name=district_name, admin=admin, is_admin=is_admin, initials=logged_in_user[district_name_to_id[flask_login.current_user.id]].split(':')[0])


@app.route('/scan', methods=['POST'])
@flask_login.login_required
def scan():
    barcode = flask.request.form['scan']
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()
    c.execute("""
        SELECT * FROM items WHERE barcode = ? and district_id = ?
    """, (barcode, district_name_to_id[flask_login.current_user.id]))
    result = c.fetchone()
    conn.close()
    if not result:
        return flask.redirect('/home?error_message=ERROR: Item scanned does not exist in database. This is a fatal error, please try again, or if this is a new item, add it to the database by clicking &specialized_error=True')

    else:
        # See if there is a file in static named barcode.png
        try:
            with open(f'static/{barcode}.png', 'r') as f:
                file_exists = True
        except FileNotFoundError:
            file_exists = False

        return flask.render_template('item.html', barcode=barcode, part_name=result[2], file_exists=file_exists, initials=logged_in_user[district_name_to_id[flask_login.current_user.id]].split(':')[0])


@app.route('/additions', methods=['GET', 'POST'])
@flask_login.login_required
def additions():
    if flask.request.method == 'GET':
        with open('autocomplete.json', 'r') as f:
            data = json.load(f)
            data = data['item_names']
        return flask.render_template('additions.html', suggestions=data)

    elif flask.request.method == "POST":
        part_name = flask.request.form['part_name']
        manufacturer = flask.request.form['manufacturer']
        purchase_order = flask.request.form['purchase_order']
        price = flask.request.form['price']
        count = flask.request.form['count']

        conn = sqlite3.connect('inventory.db')
        c = conn.cursor()

        # If barcode is in the form, add that and the part name to the 'items' table, then continue
        try:
            barcode = flask.request.form['barcode']
            # First see if the barcode or name already exists in the 'items' table
            c.execute("""
                SELECT * FROM items WHERE (barcode = ? OR part_name = ?) AND district_id = ?
            """, (barcode, part_name, district_name_to_id[flask_login.current_user.id]))
            result = c.fetchone()
            if result:
                return flask.redirect(f'/home?error_message=ERROR: The barcode or part name you entered already exists. Please try again with different values.')

            c.execute("""
                INSERT INTO items VALUES (?, ?, ?)
            """, (district_name_to_id[flask_login.current_user.id], barcode, part_name))
            conn.commit()
        except KeyError:
            pass

        # Attempt to pull the barcode from the 'items' table, if something exists, just update, otherwise,
        # ask the user for the barcode info in order to add it
        c.execute("""
            SELECT * FROM items WHERE part_name = ? AND district_id = ?
        """, (part_name, district_name_to_id[flask_login.current_user.id]))
        result = c.fetchone()
        if not result:
            return flask.render_template('enter_barcode.html', part_name=part_name, manufacturer=manufacturer, purchase_order=purchase_order, price=price, count=count)

        c.execute("""
            INSERT INTO additions VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        """, (district_name_to_id[flask_login.current_user.id], part_name, manufacturer, purchase_order, price, count))
        conn.commit()
        c.execute("""
            SELECT * FROM master_count WHERE part_name = ? AND district_id = ?
        """, (part_name, district_name_to_id[flask_login.current_user.id]))
        result = c.fetchone()

        if result: # If the part already exists in the master count, update the count
            new_count = result[2] + int(count)
            c.execute("""
                UPDATE master_count SET count = ? WHERE part_name = ? AND district_id = ?
            """, (new_count, part_name, district_name_to_id[flask_login.current_user.id]))
            conn.commit()
            conn.close()
        else: # If the part does not exist in the master count, add it
            c.execute("""
                INSERT INTO master_count VALUES (?, ?, ?)
            """, (district_name_to_id[flask_login.current_user.id], part_name, count))
            conn.commit()
            # Update the autocomplete.json file to inclue the part name
            with open('autocomplete.json', 'r') as f:
                data = json.load(f)
                if part_name not in data['item_names']:
                    data['item_names'].append(part_name)
            with open('autocomplete.json', 'w') as f:
                json.dump(data, f)

        conn.close()
        if count == 1:
            return flask.redirect(f'/home?success_message=Success! You have added {count} {part_name} to inventory.')
        return flask.redirect(f'/home?success_message=Success! You have added {count} {part_name}\'s to inventory.')


@app.route('/removals', methods=['POST'])
@flask_login.login_required
def removals():
    part_name = flask.request.form['part_name']
    count = int(flask.request.form['quantity'])

    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()
    c.execute("""
        SELECT * FROM master_count WHERE part_name = ? AND district_id = ?
    """, (part_name, district_name_to_id[flask_login.current_user.id]))
    result = c.fetchone()
    if not result:
        conn.close()
        return flask.redirect(f'/home?error_message=ERROR: It appears this item does not have a database entry, add it by clicking &specialized_error=True')

    if result[2] < count:
        return flask.redirect(f'/home?error_message=ERROR: There has been a miscount and you are attempting to take more items than should exist, my count shows there should be {result[1]} of this item in inventory.')

    else:
        new_count = result[2] - count
        c.execute("""
            UPDATE master_count SET count = ? WHERE part_name = ? AND district_id = ?
        """, (new_count, part_name, district_name_to_id[flask_login.current_user.id]))

        c.execute("""
            INSERT INTO removals VALUES (?, ?, ?, ?, datetime('now'))
        """, (district_name_to_id[flask_login.current_user.id], logged_in_user[district_name_to_id[flask_login.current_user.id]].split(':')[0], part_name, count))

        conn.commit()
        conn.close()

        if new_count == 1:
            return flask.redirect(f'/home?success_message=Success! You have removed {count} {part_name} from inventory.')
        return flask.redirect(f'/home?success_message=Success! You have removed {count} {part_name}\'s from inventory.')


@app.route('/master-count', methods=['GET'])
@flask_login.login_required
def master_count():
    # Get the master counts for all items
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()
    c.execute("""
        SELECT part_name, count FROM master_count WHERE district_id = ?
    """, (district_name_to_id[flask_login.current_user.id],))
    result = c.fetchall()
    conn.close()
    return flask.render_template('master_count.html', master_count=result)


@app.route('/add-new-item', methods=['GET', 'POST'])
@flask_login.login_required
def add_new_item():
    if flask.request.method == 'GET':
        return flask.render_template('add_new_item.html')

    elif flask.request.method == 'POST':
        part_name = flask.request.form['part_name']
        barcode = flask.request.form['barcode']

        conn = sqlite3.connect('inventory.db')
        c = conn.cursor()

        try:
            c.execute("INSERT INTO items VALUES (?, ?, ?)", (district_name_to_id[flask_login.current_user.id], barcode, part_name))
            conn.commit()
            # Add the part name to autocomplete.json
            with open('autocomplete.json', 'r') as f:
                data = json.load(f)
                data['item_names'].append(part_name)
            with open('autocomplete.json', 'w') as f:
                json.dump(data, f)
            # Add to master count
            c.execute("""
                INSERT INTO master_count VALUES (?, ?, ?)
            """, (district_name_to_id[flask_login.current_user.id], part_name, 0))
            conn.commit()
            conn.close()
            return flask.redirect(f'/home?success_message=Success! You have added a new item to the database. To add the quantity of this item, click the Add Items button.')

        except sqlite3.IntegrityError:
            conn.close()
            return flask.redirect(f'/home?error_message=ERROR: The barcode or part name you entered already exists. Please try again with different values, to return to that page, click &specialized_error=True')


@app.route('/logout', methods=['GET'])
def logout():
    try:
        del logged_in_user[district_name_to_id[flask_login.current_user.id]]
    except:
        pass
    return flask.redirect('/district_login')


# Handle unauthorized users
@login_manager.unauthorized_handler
def unauthorized_handler():
    return flask.redirect('/login')

@app.errorhandler(405)
def method_not_allowed(e):
    return flask.redirect('/')

@app.errorhandler(404)
def page_not_found(e):
    return flask.redirect('/')

if __name__ == '__main__':
    create_schema()
    app.run(host='0.0.0.0', port='2323', debug=True)