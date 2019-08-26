from datetime import datetime

from marshmallow import Schema, fields, validates, ValidationError
from marshmallow import validate

from app import db
from app.models import Citizen
from app.config import DATEFORMAT


# schemes used only for validation

class PatchCitizenSchema(Schema):
    # PATCH /imports/$import_id/citizens/$citizen_id

    # although fields marked as required this check will not be applied
    # if partial = True argument passed

    # its not required by task but it's still a good feature to have some boundaries for string values
    # ( so in case of malicious import, it will not store enormous strings
    # all strings should not exceed 1000 symbols
    # seems like a reasonable and sufficient amount for any field in this context

    def has_one_letter_or_digit(value):
        if not any(c.isalnum() for c in value):
            raise ValidationError('Field have to contain at least 1 letter or digit')

    citizen_id = fields.Int(required=True, dump_only=True, validate=validate.Range(min=0))
    town = fields.Str(required=True, validate=[validate.Length(1, 1000), has_one_letter_or_digit])
    street = fields.Str(required=True, validate=[validate.Length(1, 1000), has_one_letter_or_digit])
    building = fields.Str(required=True, validate=[validate.Length(1, 1000), has_one_letter_or_digit])
    apartment = fields.Int(required=True, validate=validate.Range(min=0))
    name = fields.Str(required=True, validate=validate.Length(min=1))

    birth_date = fields.DateTime(DATEFORMAT, required=True)
    # its also validates like datetime.strptime(value, DATEFORMAT)

    gender = fields.Str(required=True, validate=validate.OneOf({"male", "female"}))
    relatives = fields.List(fields.Int(required=True, validate=validate.Range(min=1)), required=True)

    @validates('birth_date')
    def is_not_in_future(self, value):
        # birth date in the future
        now = datetime.utcnow()
        if value > now:
            raise ValidationError("Birth day can not be in the future.")

    @validates('relatives')
    def unique_relatives(self, value):
        # checks if citizen listed multiple times as relatives for a same person
        if len(value) != len(set(value)):
            raise ValidationError("Citizen have inconsistent list of relatives.")


class CitizenSchema(PatchCitizenSchema):
    # POST /import    for each element of 'citizens'

    # inherit all the fields of PatchCitizenSchema

    # consider that changing citizen_id does not changes elements of relatives list
    citizen_id = fields.Int(required=True, validate=validate.Range(min=0))


class InputDataSchema(Schema):
    # /import - POST
    #
    def unique_citizen_id(value):
        # checks if citizen ids are unique
        ids = [c['citizen_id'] for c in value]
        if len(ids) != len(set(ids)):
            raise ValidationError('Citizen ids are not unique.')

    # using validate= param instead of @validates so CitizenSchema validation occurs first
    # after this it is guaranteed that element has required structure
    # and no KeyError and TypeError exceptions will occur during validation
    # This very behaviour is only important with nested schemes
    citizens = fields.Nested(CitizenSchema, many=True, required=True, validate=unique_citizen_id)


def import_present(import_id: int) -> bool:
    # checks if such import id presented in database
    return db.session.query(Citizen.import_id).filter_by(import_id=import_id).first() is not None
