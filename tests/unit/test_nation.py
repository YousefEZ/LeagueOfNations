from datetime import datetime

from host.defaults import defaults
from host.nation import Nation


def test_starting_player(userid, name, session):
    Nation.start(userid, name, session)
    assert Nation(userid, session).name == name
    assert Nation(userid, session).identifier == userid


def test_default_metadata(userid, name, session):
    player = Nation.start(userid, name, session)
    assert player.metadata.flag == defaults.meta.flag
    assert player.metadata.emoji == defaults.meta.emoji
    assert player.metadata.created <= datetime.now()
