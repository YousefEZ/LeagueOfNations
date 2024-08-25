import string

from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import host.nation
import host.base_models
from host.base_types import UserId

SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
host.base_models.Base.metadata.create_all(bind=engine)


class UserGenerator:
    id_counter: int = 0
    name_counter: int = 0

    @staticmethod
    def generate_id() -> UserId:
        UserGenerator.id_counter += 1
        return UserId(UserGenerator.id_counter)

    @staticmethod
    def generate_name() -> str:
        UserGenerator.name_counter += 1
        return "".join(
            [
                string.ascii_uppercase[i % len(string.ascii_uppercase)]
                for i in range(1 + UserGenerator.name_counter // len(string.ascii_uppercase))
            ]
        )

    @staticmethod
    def generate_player(session: Session) -> host.nation.Nation:
        return host.nation.Nation.start(
            UserGenerator.generate_id(), UserGenerator.generate_name(), session
        )
