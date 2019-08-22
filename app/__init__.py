from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from app.config import Config

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

from app import models

db.create_all()

from app import routes

# The bottom import is a workaround to circular imports
