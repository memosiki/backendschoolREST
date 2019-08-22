import json

from app import app, db
import os
import tempfile

import pytest


@pytest.fixture
def client():
    # creating /tmp database for tests
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_fd, database_name = tempfile.mkstemp()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, database_name)
    app.config['TESTING'] = True
    db.create_all()

    client = app.test_client()
    yield client

    db.session.remove()
    db.drop_all()
    os.close(db_fd)
    os.unlink(database_name)


def test_relation_validation(client):
    # malformed relations

    with open('tests/citizens1.json') as f:
        data = json.load(f)

    data['citizens'][0]['relatives'] = [1]  # in relations with himself
    rv = client.post('/imports', data=json.dumps(data),
                     content_type='application/json')
    assert rv.status_code == 400

    data['citizens'][0]['relatives'] = [2, 5]  # wrong citizen_id
    rv = client.post('/imports', data=json.dumps(data),
                     content_type='application/json')
    assert rv.status_code == 400

    data['citizens'][0]['relatives'] = [3]  # one-sided relations
    rv = client.post('/imports', data=json.dumps(data),
                     content_type='application/json')
    assert rv.status_code == 400

    data['citizens'][0]['relatives'] = [2]


def test_imports_1(client):
    # adding a few clients
    with open('tests/citizens1.json') as f:
        original_data = json.load(f)
    rv = client.post('/imports', data=json.dumps(original_data),
                     content_type='application/json')
    if rv.status_code != 200:
        print(rv.data)
    assert rv.status_code == 201

    # checking how data added
    import_id = json.loads(rv.data)['data']['import_id']
    rv = client.get('/imports/{}/citizens'.format(import_id))

    assert rv.status_code == 200

    response_data = json.loads(rv.data)['data']
    original_data = original_data['citizens']

    assert len(response_data) == len(original_data)
    for c1, c2 in zip(response_data, original_data):
        c1['relatives'].sort()
        c2['relatives'].sort()
        assert c1 == c2


@pytest.mark.timeout(10)
def test_large_data(client):
    # adding a large number of clients
    with open('tests/citizens2.json') as f:
        original_data = json.load(f)
    rv = client.post('/imports', data=json.dumps(original_data),
                     content_type='application/json')

    assert rv.status_code == 201

    # checking how data added
    import_id = json.loads(rv.data)['data']['import_id']
    rv = client.get('/imports/{}/citizens'.format(import_id))

    assert rv.status_code == 200

    response_data = json.loads(rv.data)['data']
    original_data = original_data['citizens']

    assert len(response_data) == len(original_data)
    for c1, c2 in zip(response_data, original_data):
        c1['relatives'].sort()
        c2['relatives'].sort()
        assert c1 == c2


def test_preserving_characters(client):
    # api handles special characters adequately
    data = {"citizens": [{"citizen_id": 1,
                          "town": "موسكو",
                          "street": "\0 a ",
                          "building": "我真的很想吃",
                          "apartment": 7,
                          "name": "\t a \n b",
                          "birth_date": "26.12.1900",
                          "gender": "male",
                          "relatives": []}]}
    rv = client.post('/imports', data=json.dumps(data),
                     content_type='application/json')
    assert rv.status_code == 201

    import_id = json.loads(rv.data)['data']['import_id']
    rv = client.get('/imports/{}/citizens'.format(import_id))
    assert rv.status_code == 200

    response_data = json.loads(rv.data)['data']
    original_data = data['citizens']

    assert response_data == original_data


def test_import_invalid_id(client):
    # trying to get invalid import ids
    rv = client.get('/imports/-1/citizens')
    assert rv.status_code in [400, 404, 405]
    rv = client.get('/imports/test/citizens')
    assert rv.status_code in [400, 404, 405]
    rv = client.get('/test')
    assert rv.status_code in [400, 404, 405]
    rv = client.get('/imports/1/citizens/0')
    assert rv.status_code in [400, 404, 405]


def test_imports_2(client):
    # sending malformed data to server

    with open('tests/citizens1.json') as f:
        data = json.load(f)

    rv = client.post('/imports', data={},
                     content_type='application/json')
    assert rv.status_code == 400

    rv = client.post('/imports', data={None: None},
                     content_type='application/json')
    assert rv.status_code == 400

    rv = client.post('/imports', data={'citizens': []},
                     content_type='application/json')
    assert rv.status_code == 400

    rv = client.post('/imports', data={'citizens': None},
                     content_type='application/json')
    assert rv.status_code == 400

    data['citizens'][2] = None
    rv = client.post('/imports', data=json.dumps(data),
                     content_type='application/json')
    assert rv.status_code == 400

    data['citizens'][2] = 1
    rv = client.post('/imports', data=json.dumps(data),
                     content_type='application/json')
    assert rv.status_code == 400


def test_imports_3(client):
    # sanitizing input

    with open('tests/citizens1.json') as f:
        original_data = json.load(f)

    original_data['citizens'][0]['name'] = 'Alex", NULL, NULL, NULL); DROP TABLE citizens;--'

    rv = client.post('/imports', data=json.dumps(original_data),
                     content_type='application/json')
    assert rv.status_code == 201
    # checking how data added
    import_id = json.loads(rv.data)['data']['import_id']
    rv = client.get('/imports/{}/citizens'.format(import_id))
    assert rv.status_code == 200
    response_data = json.loads(rv.data)['data']
    original_data = original_data['citizens']

    assert len(response_data) == len(original_data)
    for c1, c2 in zip(response_data, original_data):
        c1['relatives'].sort()
        c2['relatives'].sort()
        assert c1 == c2


def test_field_validation(client):
    # validation of fields
    with open('tests/citizens1.json') as f:
        data = json.load(f)

    data['citizens'][0]['citizen_id'] = None
    rv = client.post('/imports', data=json.dumps(data),
                     content_type='application/json')
    assert rv.status_code == 400

    data['citizens'][0]['citizen_id'] = -1
    rv = client.post('/imports', data=json.dumps(data),
                     content_type='application/json')
    assert rv.status_code == 400

    data['citizens'][0]['citizen_id'] = "-1"
    rv = client.post('/imports', data=json.dumps(data),
                     content_type='application/json')
    assert rv.status_code == 400

    data['citizens'][0]['citizen_id'] = ""
    rv = client.post('/imports', data=json.dumps(data),
                     content_type='application/json')
    assert rv.status_code == 400

    data['citizens'][0]['citizen_id'] = 1
    data['citizens'][0]['town'] = ""
    rv = client.post('/imports', data=json.dumps(data),
                     content_type='application/json')
    assert rv.status_code == 400

    data['citizens'][0]['town'] = 2
    rv = client.post('/imports', data=json.dumps(data),
                     content_type='application/json')
    assert rv.status_code == 400

    data['citizens'][0]['town'] = "Москва"
    data['citizens'][0]['birth_date'] = '32.01.2019'
    rv = client.post('/imports', data=json.dumps(data),
                     content_type='application/json')
    assert rv.status_code == 400

    data['citizens'][0]['birth_date'] = '01.01.2030'
    rv = client.post('/imports', data=json.dumps(data),
                     content_type='application/json')
    assert rv.status_code == 400

    data['citizens'][0]['birth_date'] = '29.02.2019'
    rv = client.post('/imports', data=json.dumps(data),
                     content_type='application/json')
    assert rv.status_code == 400

    data['citizens'][0]['birth_date'] = None
    rv = client.post('/imports', data=json.dumps(data),
                     content_type='application/json')
    assert rv.status_code == 400

    data['citizens'][0]['birth_date'] = 123132
    rv = client.post('/imports', data=json.dumps(data),
                     content_type='application/json')
    assert rv.status_code == 400

    data['citizens'][0]['birth_date'] = []
    rv = client.post('/imports', data=json.dumps(data),
                     content_type='application/json')
    assert rv.status_code == 400

    data['citizens'][0]['birth_date'] = {1: 2}
    rv = client.post('/imports', data=json.dumps(data),
                     content_type='application/json')
    assert rv.status_code == 400

    data['citizens'][0]['birth_date'] = '20.08.2018'
    data['citizens'][0]['gender'] = 'NULL'
    rv = client.post('/imports', data=json.dumps(data),
                     content_type='application/json')
    assert rv.status_code == 400

    data['citizens'][0]['gender'] = 'female'
    data['citizens'][0]['relatives'] = None
    rv = client.post('/imports', data=json.dumps(data),
                     content_type='application/json')
    assert rv.status_code == 400

    data['citizens'][0]['relatives'] = {1: 2}
    rv = client.post('/imports', data=json.dumps(data),
                     content_type='application/json')
    assert rv.status_code == 400


def test_birthdays_and_percentiles(client):
    # is birthdays and percentiles working
    with open('tests/citizens1.json') as f:
        original_data = json.load(f)
    rv = client.post('/imports', data=json.dumps(original_data), content_type='application/json')
    assert rv.status_code == 201

    import_id = json.loads(rv.data)['data']['import_id']

    rv = client.get('/imports/{}/citizens'.format(import_id))
    assert rv.status_code == 200

    response_data = json.loads(rv.data)['data']
    original_data = original_data['citizens']
    assert response_data == original_data

    rv = client.get('/imports/{}/citizens/birthdays'.format(import_id))
    assert rv.status_code == 200
    assert json.loads(rv.data) == {
        "data": {"1": [], "2": [], "3": [], "4": [{"citizen_id": 1, "presents": 1}], "5": [], "6": [], "7": [], "8": [],
                 "9": [], "10": [], "11": [], "12": [{"citizen_id": 2, "presents": 1}]}}

    rv = client.get('/imports/{}/towns/stat/percentile/age'.format(import_id))
    assert rv.status_code == 200
    assert json.loads(rv.data) == {"data": [{"p50": 68.5, "p75": 93.25, "p99": 117.01, "town": "Москва"},
                                            {"p50": 1, "p75": 1, "p99": 1, "town": "Керчь"}]} \
           or json.loads(rv.data) == {"data": [{"p50": 1, "p75": 1, "p99": 1, "town": "Керчь"},
                                               {"p50": 68.5, "p75": 93.25, "p99": 117.01, "town": "Москва"}]}


def test_patch(client):
    # PATCH /imports/$import_id/citizens/$citizen_id

    with open('tests/citizens1.json') as f:
        original_data = json.load(f)
    rv = client.post('/imports', data=json.dumps(original_data), content_type='application/json')
    assert rv.status_code == 201
    import_id = json.loads(rv.data)['data']['import_id']
    data = {"name": "Иванова Мария Леонидовна", "town": "Москва", "street": "Льва Толстого", "building": "16к7стр5",
            "apartment": 7, "relatives": [2]}
    rv = client.patch('/imports/{}/citizens/1'.format(import_id), data=json.dumps(data),
                      content_type='application/json')
    assert rv.status_code == 200

    ## testing relations

    # remove relation with cascade
    data = {"relatives": []}
    rv = client.patch('/imports/{}/citizens/1'.format(import_id), data=json.dumps(data),
                      content_type='application/json')
    assert rv.status_code == 200
    rv = client.get('/imports/{}/citizens'.format(import_id))
    assert rv.status_code == 200
    response_data = json.loads(rv.data)['data']
    citizen_id = 1
    for elem in response_data:
        assert citizen_id not in elem['relatives']

    # add relation with cascade
    data = {"relatives": [2, 3]}
    rv = client.patch('/imports/{}/citizens/1'.format(import_id), data=json.dumps(data),
                      content_type='application/json')
    assert rv.status_code == 200
    rv = client.get('/imports/{}/citizens'.format(import_id))
    assert rv.status_code == 200
    response_data = json.loads(rv.data)['data']
    citizen_id = 1
    for elem in response_data:
        if elem['citizen_id'] != citizen_id:
            assert citizen_id in elem['relatives']

    # with themselves
    data = {"relatives": [1]}
    rv = client.patch('/imports/{}/citizens/1'.format(import_id), data=json.dumps(data),
                      content_type='application/json')
    assert rv.status_code == 400

    # wrong ids
    data = {"relatives": [999]}
    rv = client.patch('/imports/{}/citizens/1'.format(import_id), data=json.dumps(data),
                      content_type='application/json')
    assert rv.status_code == 400

    data = {"relatives": [0]}
    rv = client.patch('/imports/{}/citizens/1'.format(import_id), data=json.dumps(data),
                      content_type='application/json')
    assert rv.status_code == 400

    data = {"relatives": [-1]}
    rv = client.patch('/imports/{}/citizens/1'.format(import_id), data=json.dumps(data),
                      content_type='application/json')
    assert rv.status_code == 400

    data = {'citizen_id': 2}
    rv = client.patch('/imports/{}/citizens/1'.format(import_id), data=json.dumps(data),
                      content_type='application/json')
    assert rv.status_code == 400

    data = {'name': 2}
    rv = client.patch('/imports/{}/citizens/1'.format(import_id), data=json.dumps(data),
                      content_type='application/json')
    assert rv.status_code == 400

    data = {'name': 'Alex'}
    rv = client.patch('/imports/{}/citizens/1'.format(import_id), data=json.dumps(data),
                      content_type='application/json')
    assert rv.status_code == 200

    data = {"relatives": None}
    rv = client.patch('/imports/{}/citizens/1'.format(import_id), data=json.dumps(data),
                      content_type='application/json')
    assert rv.status_code == 400
