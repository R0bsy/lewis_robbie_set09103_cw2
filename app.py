from flask import Flask, render_template, flash, redirect, url_for, request, session, logging, g
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import sqlite3

app = Flask(__name__)

app.secret_key='secret123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///myflaskapp.db'
db = SQLAlchemy(app)


@app.route('/')
def index():
	return render_template('home.html')

@app.route('/about')
def about():
	return render_template('about.html')

@app.route('/articles')
def articles():
	conn = sqlite3.connect("myflaskapp.db")
	conn.row_factory = dict_factory
	cur = conn.cursor()
	result = cur.execute("select * from articles")
	articles = cur.fetchall()

	if result > 0:
		return render_template('articles.html', articles=articles)
	else:
		msg = 'No Articles Found'
		return render_template('articles.html', msg=msg)

	cur.close()

@app.route('/article/<string:id>/')
def article(id):
	
	conn = sqlite3.connect("myflaskapp.db")
	conn.row_factory = dict_factory
	cur = conn.cursor()
	result = cur.execute("SELECT * FROM articles WHERE id = ?", [id])
	article = cur.fetchone()

	return render_template('article.html', article=article)

class RegisterForm(Form):
	name = StringField('Name', [validators.Length(min=1, max=50)])
	username = StringField('Username', [validators.Length(min=4, max=25)])
	email = StringField('Email', [validators.Length(min=6, max=50)])
	password = PasswordField('Password', [
		validators.DataRequired(),
		validators.EqualTo('confirm', message='Passwords do not match')
	])
	confirm = PasswordField('Confirm Password')

@app.route('/register', methods=['GET', 'POST'])
def register():
	form = RegisterForm(request.form)
	if request.method == 'POST' and form.validate():
		name = form.name.data
		email = form.email.data
		username = form.username.data
		password = sha256_crypt.encrypt(str(form.password.data))

		conn = sqlite3.connect("myflaskapp.db")
		cur = conn.cursor()
		cur.execute("insert into users(name, email, username, password) values(?, ?, ?, ?)", (name, email, username, password))
		conn.commit()
		cur.close()
		
		flash('You are now registered and can log in', 'success')

		return redirect(url_for('login'))		
		
	return render_template('register.html', form=form)

def dict_factory(cursor, row):
	d = {}
	for idx, col in enumerate(cursor.description):
		d[col[0]] = row[idx]
	return d

@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		username = request.form['username']
		password_candidate = request.form['password']

		conn = sqlite3.connect("myflaskapp.db")
		conn.row_factory = dict_factory
		cur = conn.cursor()
		result = cur.execute("SELECT * FROM users WHERE username = ?", [username])
				

		if result > 0:
			data = cur.fetchone()
			password = data['password']
		
			if sha256_crypt.verify(password_candidate, password):
				session['logged_in'] = True
				session['username'] = username

				flash('You are now logged in', 'success')
				return redirect(url_for('dashboard'))
			else:
				error = 'Invalid login'
				return render_template('login.html', error=error)
			cur.close
		else:
			error = 'Username not found'
			return render_template('login.html', error=error)

	return render_template('login.html')	


def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorized, Please login', 'danger')
			return redirect(url_for('login'))
	return wrap


@app.route('/logout')
@is_logged_in
def logout():
	session.clear()
	flash('You are now logged out', 'success')
	return redirect(url_for('login'))

@app.route('/dashboard')
@is_logged_in
def dashboard():
	conn = sqlite3.connect("myflaskapp.db")
	conn.row_factory = dict_factory
	cur = conn.cursor()
	result = cur.execute("select * from articles")	
	articles = cur.fetchall()

	if result > 0:
		return render_template('dashboard.html', articles=articles)
	else:
		msg = 'No Articles Found'
		return render_template('dashboard.html', msg=msg)

	cur.close()	

class ArticleForm(Form):
	title = StringField('Title', [validators.Length(min=1, max=200)])
	body = TextAreaField('Body', [validators.Length(min=30)])
	
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
	form = ArticleForm(request.form)
	if request.method == 'POST' and form.validate():
		title = form.title.data
		body = form.body.data

		conn = sqlite3.connect("myflaskapp.db")
		cur = conn.cursor()
		cur.execute("insert into articles(title, body, author) values(?, ?, ?)", (title, body, session['username']))
		conn.commit()
		cur.close()

		flash('Article Created', 'success')

		return redirect(url_for('dashboard'))

	return render_template('add_article.html', form=form)


@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
	
	conn = sqlite3.connect("myflaskapp.db")
	conn.row_factory = dict_factory
	cur = conn.cursor()
	result = cur.execute("select * from articles where id = ?", [id])
	article = cur.fetchone()

	form = ArticleForm(request.form)
	form.title.data = article['title']
	form.body.data = article['body']

	
	if request.method == 'POST' and form.validate():
		title = request.form['title']
		body = request.form['body']

		conn = sqlite3.connect("myflaskapp.db")
		cur = conn.cursor()
		cur.execute("update articles set title=?, body=? where id = ?", (title, body, id))
		conn.commit()
		cur.close()

		flash('Article Updated', 'success')

		return redirect(url_for('dashboard'))

	return render_template('edit_article.html', form=form)


@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
	
	conn = sqlite3.connect("myflaskapp.db")
	conn.row_factory = dict_factory
	cur = conn.cursor()
	cur.execute("delete from articles where id = ?", [id])
	conn.commit()
	cur.close()

	flash('Article Deleted', 'success')

	return redirect(url_for('dashboard'))

if __name__ == '__main__':
	app.run(debug=True)