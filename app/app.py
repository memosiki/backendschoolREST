from datetime import datetime

from config import Config
from flask import Flask
# from app import *
from flask import request, abort, jsonify
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# from app import routes, models

app = Flask(__name__)

app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# instead of database currently storing all data in memory
# db = []

#### MODELS

# Many to many relations
association_table = db.Table('relation', db.Model.metadata,
                             db.Column('citizen_id1', db.Integer, db.ForeignKey('citizens.citizen_id'), index=True),
                             db.Column('citizen_id2', db.Integer, db.ForeignKey('citizens.citizen_id')),
                             db.UniqueConstraint('citizen_id1', 'citizen_id2', name='unique_relation'))


# adjacency list. That is you have a table with foreign key to itself.
class Citizen(db.Model):
    __tablename__ = 'citizens'
    citizen_id = db.Column(db.Integer, primary_key=True)
    town = db.Column(db.String)
    street = db.Column(db.String)
    building = db.Column(db.String)
    apartment = db.Column(db.Integer)
    name = db.Column(db.String)
    birth_date = db.Column(db.DateTime)
    gender = db.Column(db.String)

    relatives = db.relationship('Citizen', secondary=association_table,
                                primaryjoin=citizen_id == association_table.c.citizen_id1,
                                secondaryjoin=citizen_id == association_table.c.citizen_id2,
                                backref='connected')

    def __repr__(self):
        return "{}->{}".format(self.citizen_id, len(self.relatives))


#### ROUTES
@app.route('/imports', methods=['POST'])
def imports():
    # DEBUG: clearing all table before each import
    Citizen.query.delete()
    db.session.commit()
    if not request.json:
        abort(400)
    dateformat = "%d.%m.%Y"
    connections = []
    for person in request.json['citizens']:
        # datetime validation
        person['birth_date'] = datetime.strptime(person['birth_date'], dateformat)
        relatives = person['relatives'].copy()
        person.pop('relatives')

        c = Citizen(**person)
        for rel_id in relatives:
            # saving relations for later use
            connections.append((c.citizen_id, rel_id))
        db.session.add(c)
    for giver, receiver in connections:
        # adding connections between people
        # although names making relations in order giver->receiver
        c = Citizen.query.get(giver)
        c.relatives.append(Citizen.query.get(receiver))

    db.session.commit()

    import_id = 0
    return jsonify({'data': {"import_id": import_id}}), 201


@app.route('/imports/<int:import_id>/citizens', methods=['GET'])
def get_import(import_id):
    return jsonify({'tasks': db[import_id - 1]})


if __name__ == '__main__':
    app.run(debug=True)
