from app import db
from app.models import Citizen


def import_present(import_id: int) -> bool:
    # checks if such import id presented in database
    return db.session.query(Citizen.import_id).filter_by(import_id=import_id).first() is not None
