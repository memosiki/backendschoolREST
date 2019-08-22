import os

basedir = os.path.abspath(os.path.dirname(__file__))



class Config(object):
    # ...
    DATABASE_URL = 'test.db'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, DATABASE_URL)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # so response will not have sorted keys
    JSON_SORT_KEYS = False
    # sorting is done in order to ensure that independent of the hash seed of the dictionary
    # the return value will be consistent to not trash external HTTP caches.
    # but since storing order of elements in dict is implementation feature in 3.6 and property in 3.7
    # its nice to have response pretty-printed
    # used only in models.Citizen.to_dict()

DATEFORMAT = "%d.%m.%Y"
