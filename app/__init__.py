from flask import Flask
from app.config import Config

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

db.create_all()

from app import routes

# The bottom import is a workaround to circular imports, a common problem with Flask applications.
