from app import app, db
from app.models import Citizen
from app.config import DATEFORMAT
from app import validate
from app.validate import InputDataSchema, PatchCitizenSchema
from datetime import datetime

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

    # try:
    # storing citizen ids of created and initialized citizens
    # (btw it is not good decision to store references to rows in table
    # because there are less than 2000 relations so it is no more than 2000 additional
    # table lookups, and citizens count is around 10'000 )
    created = set()
    initialized = set()
    for person in request.json['citizens']:
        # adding fields to store in database as separate imports
        relatives = person['relatives'].copy()
        person.pop('relatives')

        person['birth_date'] = datetime.strptime(person['birth_date'], DATEFORMAT)
        person['import_id'] = import_id

        citizen_id = person['citizen_id']
        if citizen_id in created:
            if citizen_id in initialized:
                # 'Citizen id {} is not unique'.format(citizen_id)
                abort(400)
            citizen = Citizen.query.filter_by(import_id=import_id, citizen_id=citizen_id)
            citizen.update(person)
            citizen: Citizen = citizen.one()  # from query to Citizen
            initialized.add(citizen_id)
        else:
            citizen = Citizen(**person)
            db.session.add(citizen)
            created.add(citizen_id)
            initialized.add(citizen_id)

        relative_id: int
        for relative_id in relatives:
            if relative_id == citizen_id:
                # Citizen {} is relatives with himself.'.format(relative)
                abort(400)

            if relative_id not in created:
                relative = Citizen(import_id=import_id, citizen_id=relative_id)
                db.session.add(relative)
                created.add(relative_id)
            else:
                relative = Citizen.query.filter_by(import_id=import_id, citizen_id=relative_id).one()
                if relative_id in initialized and citizen not in relative.relatives:
                    # 'Relation between citizens {} and {} is one-sided.'.format(relative_id, citizen_id))
                    abort(400)

            citizen.relatives.append(relative)
    if created != initialized:
        # 'Relations is malformed'
        abort(400)

    # except (MultipleResultsFound, NoResultFound, ValueError) as e:
    #     db.session.rollback()
    #     abort(400, str(e))
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

    import_query = db.session.query(Citizen).filter_by(import_id=import_id)
    months = range(1, 12 + 1)
    response = {i: [] for i in months}
    for citizen in import_query:
        for month in months:
            count = len(list(filter(lambda p: p.birth_date.month == month, citizen.relatives)))
            if count:
                response[month].append({"citizen_id": citizen.citizen_id,
                                        "presents": count})
    return jsonify({'data': response}), 200

    # import_query = db.session.query(Citizen).filter_by(import_id=import_id)
    # months = list(range(12))
    # response = [dict().copy() for i in months]
    # for citizen in import_query:
    #     month = citizen.birth_date.month - 1
    #     for relative in citizen.relatives:
    #         if relative.citizen_id in response[month]:
    #             response[month][relative.citizen_id] += 1
    #         else:
    #             response[month][relative.citizen_id] = 1
    # return {
    #            'data': {
    #                str(month + 1): [
    #                    {'citizen_id': cid, 'presents': val} for cid, val in response[month].items()
    #                ] for month in months
    #            }
    #        }, 200

    # response = {}
    # months = list(range(1, 12 + 1))
    # import_query = db.session.query(Citizen).filter_by(import_id=import_id)
    # for month in months:
    #     month_query = import_query.filter(db.extract('month', Citizen.birth_date) == month)
    #     count = {}
    #     for citizen in month_query:
    #         for relative in citizen.relatives:
    #             if relative.citizen_id in count:
    #                 count[relative.citizen_id] += 1
    #             else:
    #                 count[relative.citizen_id] = 1
    #     response[str(month)] = [{'citizen_id': cid, 'presents': val} for cid, val in count.items()]
    # return {'data': response}, 200


@app.route('/imports/<int:import_id>/towns/stat/percentile/age', methods=['GET'])
def get_percentile(import_id):
    if not validate.import_present(import_id):
        abort(400)

    # returns list of sqlalch.results of all distinct towns
    towns = db.session.query(Citizen.town).filter_by(import_id=import_id).distinct()
    # converting results to string representation
    towns = [elem.town for elem in towns]

    dates_query = db.session.query(Citizen.birth_date).filter_by(import_id=import_id)
    response = []
    for town in towns:
        bdays_by_town = dates_query.filter_by(town=town)

        def calculate_age(born: datetime) -> int:
            # returns age in years
            today = datetime.utcnow()
            return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

        ages = [calculate_age(elem.birth_date) for elem in bdays_by_town]
        response.append({
            'town': town,
            'p50': round(percentile(ages, 50, interpolation='linear')),
            'p75': round(percentile(ages, 75, interpolation='linear')),
            'p99': round(percentile(ages, 99, interpolation='linear')),
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
