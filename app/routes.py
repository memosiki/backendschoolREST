from app import app, db
from app.models import Citizen
from app.config import DATEFORMAT
from app import validate
from app.validate import InputDataSchema, PatchCitizenSchema
from datetime import datetime, date
import uuid

from flask import request, abort, jsonify
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from numpy import percentile  # for percentiles


@app.route('/imports', methods=['POST'])
def post_imports():
    # first validation
    # fields should have allowed values
    # (no citizen relations validation yet)
    if not request.json:
        abort(400)
    errors = InputDataSchema().validate(request.json)
    if errors:
        # arguable decision to send information with advices how to structure request right
        # but i assume the exact route is unknown for anyone beside authorized personnel
        abort(400, str(errors))

    # selecting new import id
    import_id = db.session.query(db.func.max(Citizen.import_id)).scalar()
    # if there are imports in the table
    if import_id is not None:
        import_id += 1
    else:
        import_id = 1

    try:
        # all relations between people
        connections = {}
        for person in request.json['citizens']:
            # adding fields to store in database as separate imports
            relatives = person['relatives'].copy()
            person.pop('relatives')
            person['birth_date'] = datetime.strptime(person['birth_date'], DATEFORMAT)
            person['import_id'] = import_id
            person['id'] = str(uuid.uuid1())
            c = Citizen(**person)
            # saving relations for later use
            connections[c.citizen_id] = relatives
            db.session.add(c)

        # second validation
        # checking relation between people:
        # relation is two sided and such person exits
        import_query = Citizen.query.filter_by(import_id=import_id)
        for receiver, emitters in connections.items():
            # adding connections between people
            # making relations in order emitter->receiver
            # receiver is the one who gets record in db about relative

            for emitter in emitters:
                # validate if relation is two-way
                if receiver not in connections[emitter]:
                    # also raises KeyError if no such emitter exists
                    raise ValueError('Relation between citizens {} and {} is one-sided.'.format(receiver, emitter))
                if receiver == emitter:
                    raise ValueError('Citizen {} is relatives with himself.'.format(receiver))
                # raises exc if such citizen_id does not exist (or multiple results found)
                # this should have been guaranteed to not happen by previous step btw, BUT
                # function marked as [raises exc] so it is a good design to catch it anyways
                receiver_obj = import_query.filter_by(citizen_id=receiver).one()
                receiver_obj.relatives.append(import_query.filter_by(citizen_id=emitter).one())

    except (MultipleResultsFound, NoResultFound, ValueError, KeyError) as e:
        db.session.rollback()
        abort(400, str(e))
        # if it is a KeyError it prints the value of wrong key (citizen_id)
    db.session.commit()
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
    months = range(1, 12 + 1)
    response = {i: [] for i in months}
    for citizen in import_query:
        for month in months:
            count = len(list(filter(lambda p: p.birth_date.month == month, citizen.relatives)))
            if count:
                response[month].append({"citizen_id": citizen.citizen_id,
                                        "presents": count})
    return jsonify({'data': response}), 200


@app.route('/imports/<int:import_id>/towns/stat/percentile/age', methods=['GET'])
def get_percentile(import_id):
    if not validate.import_present(import_id):
        abort(400)

    # returns list of sqlalch.results of all distinct towns
    towns = db.session.query(Citizen.town).distinct()
    # converting results to string representation
    towns = [elem.town for elem in towns]

    dates_query = db.session.query(Citizen.birth_date).filter_by(import_id=import_id)
    response = []
    for town in towns:
        bdays_by_town = dates_query.filter_by(town=town).all()

        def calculate_age(born: datetime) -> int:
            # returns age in years
            today = datetime.utcnow()
            return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

        ages = [calculate_age(elem.birth_date) for elem in bdays_by_town]
        response.append({
            'town': town,
            'p50': round(percentile(ages, 50)),
            'p75': round(percentile(ages, 75)),
            'p99': round(percentile(ages, 99)),
        })
    return jsonify({'data': response}), 200


@app.route('/imports/<int:import_id>/citizens/<int:citizen_id>', methods=['PATCH'])
def patch_modify(import_id, citizen_id):
    if not validate.import_present(import_id):
        abort(400)
    if not request.json:
        abort(400)
    errors = PatchCitizenSchema(partial=True).validate(request.json)
    if errors:
        abort(400, str(errors))
    changes = request.json
    try:
        mod_citizen = Citizen.query.filter_by(import_id=import_id, citizen_id=citizen_id).one()

        if 'relatives' in changes:

            if citizen_id in changes['relatives']:
                raise ValueError('Citizen {} is relatives with himself.'.format(citizen_id))

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

            # clearing all relations this person receives
            # and adding all relations from request
            mod_citizen.relatives.clear()
            for person_id in changes['relatives']:
                person = Citizen.query.filter_by(import_id=import_id, citizen_id=person_id).one()
                mod_citizen.relatives.append(person)
        for field, val in changes.items():
            if field not in {'relatives', 'birth_date'}:
                setattr(mod_citizen, field, val)
            elif field == 'birth_date':
                mod_citizen.birth_date = datetime.strptime(changes['birth_date'], DATEFORMAT)

    except (MultipleResultsFound, NoResultFound, ValueError) as e:
        db.session.rollback()
        abort(400, str(e))
    else:
        db.session.commit()
        return jsonify({'data': mod_citizen.to_dict()}), 200
