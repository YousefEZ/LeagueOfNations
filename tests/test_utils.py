import string

from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from host.gameplay_settings import GameplaySettings
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

GameplaySettings.metadata.minimum_nation_name_length = 1
GameplaySettings.metadata.maximum_nation_name_length = 500

print(
    "GameplaySettings.metadata.minimum_nation_name_length",
    GameplaySettings.metadata.minimum_nation_name_length,
)

CHARACTER_LENGTH = len(string.ascii_uppercase)


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
        return str(hex(UserGenerator.name_counter))[2:]

    @staticmethod
    def generate_player(session: Session) -> host.nation.Nation:
        user_id = UserGenerator.generate_id()
        user_name = UserGenerator.generate_name()
        response = host.nation.Nation.start(user_id, user_name, session)
        assert response is host.nation.StartResponses.SUCCESS, f"Failed to create user {response}"
        return host.nation.Nation(user_id, session)
