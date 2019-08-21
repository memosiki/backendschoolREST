import json

from app import app
import os
import tempfile

import pytest


@pytest.fixture
def client():
    # db_fd, app.config['DATABASE'] = tempfile.mkstemp()
    # app.config['TESTING'] = True
    client = app.test_client()

    yield client

    # os.close(db_fd)
    # os.unlink(app.config['DATABASE'])


def test_imports_1(client):
    # test adding a few clients
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


def test_import_invalid_id(client):
    # trying to get invalid import ids
    rv = client.get('/imports/-1/citizens')
    assert rv.status_code == 404 or rv.status_code == 400
    rv = client.get('/imports/test/citizens')
    assert rv.status_code == 404 or rv.status_code == 400


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
    # sending malformed data to server

    with open('tests/citizens1.json') as f:
        original_data = json.load(f)
    original_data['citizens'][0]['name'] = 'Alex", 0 ,"" ,[]) DROP TABLE citizens;--'

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


# @pytest.mark.timeout(10)
def test_large_data(client):
    # test adding a few clients
    with open('tests/citizens2.json') as f:
        original_data = json.load(f)
    rv = client.post('/imports', data=json.dumps(original_data),
                     content_type='application/json')
    if rv.status_code != 201:
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
