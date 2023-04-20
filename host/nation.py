from functools import cached_property

import sqlalchemy
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, Session

from host.bank import Bank


class Base(DeclarativeBase):
    pass


class MetadataModel(Base):
    __tablename__ = "metadata"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    nation: Mapped[str] = mapped_column(candidate_key=True)


class Metadata:
    def __init__(self, identifier: int):
        self._identifier = identifier
        self._metadata = sqlalchemy.select(MetadataModel).where(MetadataModel.user_id == self._identifier)

    @property
    def nation(self) -> str:
        return self._metadata.nation


class Nation:
    def __init__(self, identifier: int):
        self._identifier: int = identifier

    @cached_property
    def metadata(self) -> Metadata:
        return Metadata(self._identifier)

    @cached_property
    def bank(self) -> Bank:
        bank = Bank(self._identifier)
        return bank

    @property
    def nation(self) -> str:
        metadata = self.metadata
        return metadata.nation

    @staticmethod
    def start(identifier: int, name: str, engine: sqlalchemy.Engine) -> None:
        metadata = MetadataModel(user_id=identifier, nation=name)

        with Session(engine) as session:
            session.add(metadata)
            session.commit()
