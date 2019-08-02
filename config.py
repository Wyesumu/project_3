db_name = "site"
db_host = "localhost" #database file storage
db_user ="site"
db_pass = "password"
host = "0.0.0.0" #0.0.0.0 to allow outside connection
port = "80"
secret_key = b'GJdvU3_%d!w7Nw#$d' #used to crypt session stored in cookies

UPLOAD_FOLDER = './images'
THUMBNAIL_FOLDER = './thumbnails'
RESIZE_FOLDER = './resize'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

width = 200
height = 200

privileges = [
				(1, 'Разработчик'),
				(2, 'Администратор'),
				(3, 'Автор курсов'),
				(4, 'Педагог'),
				(5, 'Студент'),
			]