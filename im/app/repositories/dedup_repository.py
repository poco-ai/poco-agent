from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.dedup_event import DedupEvent


class DedupRepository:
    @staticmethod
    def exists(db: Session, *, key: str) -> bool:
        stmt = select(DedupEvent.key).where(DedupEvent.key == key)
        return db.execute(stmt).first() is not None

    @staticmethod
    def put(db: Session, *, key: str) -> None:
        if DedupRepository.exists(db, key=key):
            return
        db.add(DedupEvent(key=key))
        db.commit()

    @staticmethod
    def put_if_absent(db: Session, *, key: str) -> bool:
        db.add(DedupEvent(key=key))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return False
        return True
