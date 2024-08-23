import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from host.base_types import UserId
from host.nation import Nation
import host.base_models


SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
host.base_models.Base.metadata.create_all(bind=engine)


@pytest.fixture
def userid() -> UserId:
    return UserId(int(str(int(uuid.uuid4()))[:10]))


@pytest.fixture
def name() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def player(userid, name) -> Nation:
    return Nation.start(userid, name, TestingSessionLocal())
