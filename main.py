# coding: utf-8
import flask
import pymysql.cursors
import config
from datetime import datetime as dt
from locale import setlocale, LC_ALL
from flask_bcrypt import Bcrypt
import os
#from PIL import Image, ImageFont, ImageFilter, ImageDraw
#from resize_and_crop import resize_and_crop
#from random import randrange
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_babelex import Babel
from flask_sqlalchemy import SQLAlchemy

from wtforms import TextAreaField
from wtforms.widgets import TextArea

from werkzeug.routing import RequestRedirect

app = flask.Flask(__name__)
bcrypt = Bcrypt(app)
babel = Babel(app)

app.secret_key = config.secret_key

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://'+config.db_user+':'+config.db_pass+'@'+config.db_host+'/'+config.db_name + '?charset=utf8mb4'
#app.config['SQLALCHEMY_ECHO'] = True
db = SQLAlchemy(app)

#Database initialization

user_association = db.Table('user_association', db.Model.metadata,
	db.Column('city_id', db.Integer, db.ForeignKey('city.id'), primary_key=True),
	db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class User(db.Model):

	__table_args__ = { 'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8', 'mysql_collate': 'utf8_general_ci' }

	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(255))
	email = db.Column(db.String(255))
	password = db.Column(db.String(255))
	privileges = db.Column(db.Integer, default = 5)
	full_name = db.Column(db.String(255, collation='utf8_unicode_ci'))

class Post(db.Model):

	__table_args__ = { 'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8', 'mysql_collate': 'utf8_general_ci' }

	id = db.Column(db.Integer, primary_key=True)
	title = db.Column(db.String(255, collation='utf8_unicode_ci'))
	description = db.Column(db.String(255, collation='utf8_unicode_ci'))
	text = db.Column(db.String(16384, collation='utf8_unicode_ci'))

class Config(db.Model):

	__table_args__ = { 'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8', 'mysql_collate': 'utf8_general_ci' }

	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(60))
	value = db.Column(db.String(60))
	description = db.Column(db.String(255, collation='utf8_unicode_ci'))

class City(db.Model):
	__table_args__ = { 'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8', 'mysql_collate': 'utf8_general_ci' }

	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(255, collation='utf8_unicode_ci'))
	addr = db.Column(db.String(255, collation='utf8_unicode_ci'))
	date_start = db.Column(db.DateTime, nullable=False)
	date_end = db.Column(db.DateTime, nullable=False)
	users = db.relationship("User", secondary=user_association, lazy='subquery',
							backref=db.backref('users', lazy=True))
	event = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False)


class Event(db.Model):

	__table_args__ = { 'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8', 'mysql_collate': 'utf8_general_ci' }

	id = db.Column(db.Integer, primary_key=True)
	title = db.Column(db.String(255, collation='utf8_unicode_ci'))
	description = db.Column(db.String(255, collation='utf8_unicode_ci'))
	text = db.Column(db.String(16384, collation='utf8_unicode_ci'))
	#date = db.Column(db.DateTime, nullable=False)
	on_main = db.Column(db.Boolean)
	cities = db.relationship('City', backref='events', lazy=True)

	def __str__(self):
		return self.title
	
#is user logged in and is he allowed to access this page
def user_allowed(level):
	if "logged" in flask.session:
		if flask.session["privileges"] <= level:
			return True
		else:
			return False
	else:
		return False

#flask-admin

@babel.localeselector
def get_locale():
        return 'ru'

#restict access to /admin index
class MyAdminIndexView(AdminIndexView):
	def is_accessible(self):
		return user_allowed(2)

#list of users in admin
class UserView(ModelView):

	form_choices = {'privileges': config.privileges}

	column_choices = {'privileges': config.privileges}

	column_exclude_list = ['password',]
	form_excluded_columns = ['password',]

#restict access to user list
	def is_accessible(self):
		return user_allowed(2)


#text editor widget for admin
class CKTextAreaWidget(TextArea):
	def __call__(self, field, **kwargs):
		if kwargs.get('class'):
			kwargs['class'] += " ckeditor"
		else:
			kwargs.setdefault('class', 'ckeditor')
		return super(CKTextAreaWidget, self).__call__(field, **kwargs)

class CKTextAreaField(TextAreaField):
	widget = CKTextAreaWidget()

#news form
class PostView(ModelView):

	form_overrides = dict(text=CKTextAreaField)

	create_template = 'admin/edit.html'
	edit_template = 'admin/edit.html'

	def is_accessible(self):
		return user_allowed(3)

#event form
class EventView(ModelView):

	form_overrides = dict(text=CKTextAreaField) #override "text" with ckEditor

	create_template = 'admin/event.html' #override original create and edit form with custom 
	edit_template = 'admin/event.html'

	form_excluded_columns = ['cities',] #hide cities list from this view

	@expose('/user_list', methods=('GET', 'POST')) #list of users registered on event
	def event_user_list(self, **kwargs):
		city_id = flask.request.args.get('id')
		self._template_args['users'] = City.query.get(city_id).users
		return ModelView.render(template = 'admin/user_list.html', self = self)

	def after_model_change(self, form, model, is_created):
		f = flask.request.form.to_dict(flat=False) #get data from page in dict
		if "city_name" in f:
			City.query.filter_by(event=model.id).delete() #delete cities with same event_id
			for i in range(0,len(f["city_name"])):
				new_city = City(name =f["city_name"][i], addr=f["city_addr"][i], date_start=f["city_date_start"][i], date_end=f["city_date_end"][i], event=model.id) #and then create new cities
				db.session.add(new_city)
				#ps if nothing was changed on page but it was saved, cities anyway will be deleted
				#and then created again
		else:
			flask.flash("Вы не указали ни одного города. Мероприятие не будет указано в календаре")
		db.session.commit()

	#this is custom form for event view: /templates/admin/event.html
	@expose('/edit/', methods=('GET', 'POST'))
	def edit_view(self):
		event = Event.query.get(flask.request.args.get('id'))# get post from db by it's id got from url ?id=<id>
		if flask.request.method == 'POST': #if post have to process data from page
			event.title = flask.request.form['title']
			event.description = flask.request.form['description']
			event.text = flask.request.form['text']
			if 'on_main' in flask.request.form: #if on_main is checked on the page set True
				event.on_main = True
			else:
				event.on_main = False

			f = flask.request.form.to_dict(flat=False) #get data from page in dict
			if "city_name" in f:
				City.query.filter_by(event=flask.request.args.get('id')).delete() #delete cities with same event_id
				for i in range(0,len(f["city_name"])):
					new_city = City(name =f["city_name"][i], addr=f["city_addr"][i], date_start=f["city_date_start"][i], date_end=f["city_date_end"][i], event=flask.request.args.get('id')) #and then create new cities
					db.session.add(new_city)
					#ps if nothing was changed on page but it was saved, cities anyway will be deleted
					#and then created again
			else:
				flask.flash("Вы не указали ни одного города. Мероприятие не будет указано в календаре")
			db.session.commit()

			return flask.redirect('/admin/event')
		else: #if GET have to send data to page from db
			self._template_args['title'] = event.title
			self._template_args['description'] = event.description
			self._template_args['text'] = event.text
			self._template_args['on_main'] = event.on_main
			self._template_args['cities'] = City.query.filter_by(event=flask.request.args.get('id')).all()

			return super(EventView, self).edit_view()

	def is_accessible(self):
		return user_allowed(3)

class ConfigView(ModelView):

	def is_accessible(self):
		return user_allowed(2)

#initilize admin page
admin = Admin(app, name='Administration', template_mode='bootstrap3', index_view=MyAdminIndexView())
admin.add_view(UserView(User, db.session, 'Пользователи'))
admin.add_view(PostView(Post, db.session, 'Новости'))
admin.add_view(EventView(Event, db.session, 'События'))
admin.add_view(ConfigView(Config, db.session, 'Конфигурация'))

@app.route('/fonts/<path:path>')
def send_fonts(path):
	return flask.send_from_directory('fonts', path)

#@app.route('/resize/<path:path>')
#def send_resize(path):
#	return flask.send_from_directory('resize', path)

#@app.route('/images/<path:path>')
#def send_images(path):
#	return flask.send_from_directory('images', path)

#@app.route('/thumbnails/<path:path>')
#def send_thumbain(path):
#	return flask.send_from_directory('thumbnails', path)

@app.route("/login", methods=['GET', 'POST'])
def login():
	error = None
	if flask.request.method == 'POST':
		#get data from form
		login = flask.request.form["login"] 
		password = flask.request.form["password"]
		user_data = User.query.filter_by(username = login).first()
		if user_data is not None:
			if bcrypt.check_password_hash(user_data.password, str(password)): #compare user input and password hash from db
				#set session info in crypted session cookie
				flask.session['logged'] = "yes"
				flask.session['username'] = login
				flask.session['privileges'] = user_data.privileges
				flask.session['full_name'] = user_data.full_name
				return flask.redirect(flask.url_for("index"))
			else:
				flask.flash("Wrong password. Try again")
		else:
			flask.flash("Wrong Login. Try again")
	return flask.render_template("login.html")

@app.route("/register", methods=['GET', 'POST'])
def register():
	if flask.request.method == 'POST':
		f = flask.request.form.to_dict(flat=False) #get data from form
	
		if [''] in f.values(): #if there's any empty field
			flask.flash("Не все поля заполнены")
		elif f['password'][0] != f['password_check'][0]: #if passwords doesn't match
			flask.flash("Пароли не совпадают")
		else:
			#check if username already in db
			if User.query.filter_by(username = f["login"][0]).first():
				flask.flash("Пользователь с таким именем уже существует")
			else:
				#create new user
				new_user = User(username = f["login"][0], email = f["email"][0], full_name = f["full_name"][0], password = bcrypt.generate_password_hash(str(f["password"][0])))
				db.session.add(new_user)
				db.session.commit()

		return flask.redirect(flask.url_for("login"))
	else:
		return flask.render_template("register.html")

@app.route("/logout")
def logout():
	flask.session.clear() #clear session when user log out
	return flask.redirect(flask.url_for("login"))

def get_username():
	if 'username' in flask.session: #show username on the page if user logged in
		return flask.session['username']
	else:
		return None

#create custom filter for jinja. We need it to switch locale to ru_RU
def format_datetime(value, format):
	setlocale(LC_ALL, 'ru_RU.utf8')
	return value.strftime(format)
#register filter in jinja
app.jinja_env.filters['datetime_ru'] = format_datetime

@app.route("/")
def index():
	on_main = Event.query.filter_by(on_main = True).order_by(Event.id.desc()).first() #get event with on_main tag
	posts = Post.query.order_by(Post.id.desc()).all() #get all news from the base
	return flask.render_template("index.html", username=get_username(), posts=posts, on_main=on_main)

@app.route("/events")
def events():
	posts = Event.query.order_by(Event.id.desc()).all() #get all events from the base
	return flask.render_template("events.html", username=get_username(), posts=posts)

@app.route("/news/<int:post_id>")
def news(post_id):
	post = Post.query.get(post_id) #get post from db by it's id
	return flask.render_template("post.html", username=get_username(), post=post)

@app.route("/event/<int:post_id>")
def event(post_id):
	post = Event.query.get(post_id) #get post from db by it's id
	cities = City.query.filter_by(event=post_id).all()
	return flask.render_template("post.html", username=get_username(), post=post, cities=cities)

@app.route("/event/register/<int:city_id>") #function that handles users registration on event
def register_on_event(city_id): #it's really unfinished, just adds user to the city's users list
	city = City.query.get(city_id)
	user = User.query.filter_by(username = flask.session["username"]).first()
	city.users.append(user)
	db.session.add(city)
	db.session.commit()
	return flask.redirect(flask.url_for("index"))

#route for calendar tab
@app.route('/calendar')
def calendar():
	return flask.render_template("cal.html", username = get_username())

@app.route('/profile/<username>')
def profile(username):
	user = User.query.filter_by(username = username).one()
	return flask.render_template("profile.html", user = user, username = get_username())

#return event data from db jsonified
@app.route('/data')
def return_data():
	json = []
	cities = City.query.all()
	for data in cities:
		event = Event.query.get(data.event)
		json.append({"id":str(data.id),"title":str(data.name + " " + event.title),"url":"/event/"+str(event.id),"start":str(data.date_start).replace(" ","T"), "end":str(data.date_end).replace(" ","T")})
	return flask.jsonify(json)

#run only if started standalone, not imported
if __name__ == "__main__":
	db.create_all()
	app.run(host=config.host, port=config.port)