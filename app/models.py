# from collections.abc import OrderedDict

from app import db
from app.config import DATEFORMAT
from uuid import uuid1

# Many to many relations
association_table = db.Table('relation', db.Model.metadata,
                             db.Column('uuid1', db.Integer, db.ForeignKey('citizens.uuid'), index=True),
                             db.Column('uuid2', db.Integer, db.ForeignKey('citizens.uuid')),
                             db.UniqueConstraint('uuid1', 'uuid2', name='unique_relation'))


def generate_uuid():
    return str(uuid1())


# Adjacency list. A table with foreign key to itself.
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

    relatives = db.relationship('Citizen', secondary=association_table,
                                primaryjoin=uuid == association_table.c.uuid1,
                                secondaryjoin=uuid == association_table.c.uuid2,
                                backref='connected')

    # def __repr__(self):
    #     return "{}:{} has {}" \
    #         .format(self.import_id, self.citizen_id, len(self.relatives))

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
            ('relatives', [rel.citizen_id for rel in
                           self.relatives])
        ])
