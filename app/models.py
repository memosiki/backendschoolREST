# from collections.abc import OrderedDict
import json
import sqlalchemy.types as types

from app import app, db
from app.config import DATEFORMAT
from uuid import uuid1


# Many to many relations
# relatives_table = db.Table('relation', db.Model.metadata,
#                            db.Column('uuid1', db.Integer, db.ForeignKey('citizens.uuid'), index=True),
#                            db.Column('uuid2', db.Integer, db.ForeignKey('citizens.uuid')),
#                            db.UniqueConstraint('uuid1', 'uuid2', name='unique_relation'))
#


def generate_uuid():
    return str(uuid1())


class Citizen(db.Model):
    __tablename__ = 'citizens'

    uuid = db.Column(db.String(32), primary_key=True, default=generate_uuid)

    citizen_id = db.Column(db.Integer)
    import_id = db.Column(db.Integer)

    town = db.Column(db.String)
    street = db.Column(db.String)
    building = db.Column(db.String)
    apartment = db.Column(db.Integer)
    name = db.Column(db.String)
    birth_date = db.Column(db.DateTime)
    gender = db.Column(db.String)

    # relatives = db.relationship('Citizen', secondary=relatives_table,
    #                             primaryjoin=uuid == relatives_table.c.uuid1,
    #                             secondaryjoin=uuid == relatives_table.c.uuid2,
    #                             backref='connected')

    # storing relatives as serialized Python list
    # its much faster to do either than storing relatives as many-to-many relations in database
    # and works well for any route
    # really depends on problem but this fits okay
    relatives = db.Column(db.PickleType)

    def to_dict(self) -> dict:
        return dict([
            ('citizen_id', self.citizen_id),
            ('town', self.town),
            ('street', self.street),
            ('building', self.building),
            ('apartment', self.apartment),
            ('name', self.name),
            ('birth_date', self.birth_date.strftime(DATEFORMAT)),
            ('gender', self.gender),
            ('relatives', self.relatives)
        ])
