import collections

from app import db
from app.config import DATEFORMAT

# Many to many relations
association_table = db.Table('relation', db.Model.metadata,
                             db.Column('id1', db.Integer, db.ForeignKey('citizens.id'), index=True),
                             db.Column('id2', db.Integer, db.ForeignKey('citizens.id')),
                             db.UniqueConstraint('id1', 'id2', name='unique_relation'))


# Adjacency list. A table with foreign key to itself.
class Citizen(db.Model):
    __tablename__ = 'citizens'

    id = db.Column(db.String(32), primary_key=True)

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
                                primaryjoin=id == association_table.c.id1,
                                secondaryjoin=id == association_table.c.id2,
                                backref='connected')

    def __repr__(self):
        return "{}:{} has {}" \
            .format(self.import_id, self.citizen_id, len(self.relatives))

    def to_dict(self) -> collections.OrderedDict:
        return collections.OrderedDict([
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
