from sqlalchemy.orm import Session
import pytest

from host.base_types import UserId
from host.nation import Nation

import tests.test_utils as utils


@pytest.fixture
def userid() -> UserId:
    return utils.UserGenerator.generate_id()


@pytest.fixture
def name() -> str:
    return utils.UserGenerator.generate_name()


@pytest.fixture
def session() -> Session:
    return utils.TestingSessionLocal()


@pytest.fixture
def player(session) -> Nation:
    return utils.UserGenerator.generate_player(session)


@pytest.fixture
def target(session) -> Nation:
    return utils.UserGenerator.generate_player(session)
