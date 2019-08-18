from app import app, db
from app.models import Citizen
from app.config import DATEFORMAT
from app import validate
from datetime import datetime, date
import uuid

from flask import request, abort, jsonify
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from numpy import percentile  # for percentiles


@app.route('/imports', methods=['POST'])
def post_imports():
    if not request.json:
        abort(400)
    # print(type(db.session.query(db.func.max(Citizen.import_id)).scalar()))
    # selecting new import id
    import_id = db.session.query(db.func.max(Citizen.import_id)).scalar()
    if import_id is not None:  # if there are imports in the table
        import_id += 1
    else:
        import_id = 1

    connections = []
    for person in request.json['citizens']:
        # datetime validation
        person['birth_date'] = datetime.strptime(person['birth_date'], DATEFORMAT)
        relatives = person['relatives'].copy()
        person.pop('relatives')
        person['import_id'] = import_id
        person['id'] = str(uuid.uuid1())
        c = Citizen(**person)
        for rel_id in relatives:
            # saving relations for later use
            connections.append((c.citizen_id, rel_id))
        db.session.add(c)
    import_query = Citizen.query.filter_by(import_id=import_id)
    try:
        for giver, receiver in connections:
            # adding connections between people
            # although names making relations in order giver->receiver

            # raises exc if none or multiple results found
            c = import_query.filter_by(citizen_id=giver).one()
            c.relatives.append(import_query.filter_by(citizen_id=receiver).one())

    except (MultipleResultsFound, NoResultFound):
        db.session.rollback()
        abort(400)
    db.session.commit()
    print(Citizen.query.all())
    return jsonify({'data': {"import_id": import_id}}), 201


@app.route('/imports/<int:import_id>/citizens', methods=['GET'])
def get_import(import_id):
    if not validate.import_present(import_id):
        abort(400)

    citizens = Citizen.query.filter_by(import_id=import_id).all()
    citizens = [c.to_dict() for c in citizens]
    return jsonify({'data': citizens}), 200


@app.route('/imports/<int:import_id>/citizens/birthdays', methods=['GET'])
def get_birthdays(import_id):
    if not validate.import_present(import_id):
        abort(400)

    import_query = Citizen.query.filter_by(import_id=import_id)
    months = range(1, 13)
    response = {i: [] for i in months}
    for citizen in import_query:
        print(citizen.relatives)
        print(type(citizen.relatives))
        for month in months:
            # todo: make counting of relatives by months some different way, this does not seem rigth
            count = len(list(filter(lambda p: p.birth_date.month == month, citizen.relatives)))
            if count:
                response[month].append({"citizen_id": citizen.citizen_id,
                                        "presents": count})
        for rel in citizen.relatives:
            pass
    return jsonify({'data': response}), 200


@app.route('/imports/<int:import_id>/towns/stat/percentile/age', methods=['GET'])
def get_percentile(import_id):
    if not validate.import_present(import_id):
        abort(400)

    percentile_params = [50, 75, 99]
    towns = db.session.query(Citizen.town).distinct()  # returns list of sqlalch.results
    towns = [elem.town for elem in towns]  # converting results to string representation

    dates_query = db.session.query(Citizen.birth_date).filter_by(import_id=import_id)
    response = {}
    for town in towns:
        bdays = dates_query.filter_by(town=town).all()

        def calculate_age(born: datetime) -> int:
            # returns age in years
            today = date.today()
            return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

        ages = [calculate_age(elem.birth_date) for elem in bdays]
        perc = list(percentile(ages, percentile_params))
        perc = [round(elem, 2) for elem in perc]
        response[town] = perc
    return jsonify({'data': response}), 200


@app.route('/imports/<int:import_id>/citizens/<int:citizen_id>', methods=['PATCH'])
def patch_modify(import_id, citizen_id):
    changes = request.json
    try:
        mod_citizen = Citizen.query.filter_by(import_id=import_id, citizen_id=citizen_id).one()

        disconnect_persons = set(p.citizen_id for p in mod_citizen.connected) \
                             - set(changes['relatives'])
        connect_persons = set(changes['relatives']) \
                          - set(p.citizen_id for p in mod_citizen.connected)
        for person_id in disconnect_persons:
            person = Citizen.query.filter_by(import_id=import_id, citizen_id=person_id).one()
            person.relatives.remove(mod_citizen)
        for person_id in connect_persons:
            person = Citizen.query.filter_by(import_id=import_id, citizen_id=person_id).one()
            person.relatives.append(mod_citizen)

        # clearing all relations this person emits
        # and adding all relations from request
        mod_citizen.relatives.clear()
        for person_id in changes['relatives']:
            person = Citizen.query.filter_by(import_id=import_id, citizen_id=person_id).one()
            mod_citizen.relatives.append(person)
            print(mod_citizen.relatives)
        for field, val in changes.items():
            if field not in {'relatives', 'birth_date'}:
                setattr(mod_citizen, field, val)
            elif field == 'birth_date':
                mod_citizen.birth_date = datetime.strptime(changes['birth_date'], DATEFORMAT)

    except (MultipleResultsFound, NoResultFound):

        db.session.rollback()
        abort(400)
    db.session.commit()
    return jsonify({'data': mod_citizen.to_dict()}), 200
