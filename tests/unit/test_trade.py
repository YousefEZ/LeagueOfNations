import json
from typing import Dict
from unittest.mock import patch
from sqlalchemy.orm import Session
from host.gameplay_settings import GameplaySettings
from host.nation.trade import (
    TradeAcceptResponses,
    TradeCancelResponses,
    TradeDeclineResponses,
    TradeSelectResponses,
    TradeSentResponses,
)

from tests.test_utils import UserGenerator
from host.nation.types import resources

with open("tests/objects/resources.json", "r", encoding="utf8") as resources_file:
    Resources: Dict[str, resources.Resource] = {
        identifier: resources.Resource.model_validate(resource)
        for identifier, resource in json.load(resources_file).items()
    }

with open("tests/objects/bonus_resources.json", "r", encoding="utf8") as bonus_resources_file:
    BonusResources: Dict[str, resources.BonusResource] = {
        identifier: resources.BonusResource.model_validate(resource)
        for identifier, resource in json.load(bonus_resources_file).items()
    }


def test_trade_request(player, target):
    response = player.trade.send(target.identifier)
    assert response is TradeSentResponses.SUCCESS
    assert len(target.trade.offers_received) == 1
    assert target.trade.offers_received[0].sponsor == player.identifier
    assert len(player.trade.offers_sent) == 1
    assert player.trade.offers_sent[0].recipient == target.identifier


def test_trade_accept_agreement_exists(player, target):
    assert player.trade.send(target.identifier) is TradeSentResponses.SUCCESS
    assert target.trade.accept(player.identifier) is TradeAcceptResponses.SUCCESS
    assert player.trade.active_agreements[0].recipient == target.identifier
    assert target.trade.active_agreements[0].sponsor == player.identifier


def test_trade_accept_offer_removed(player, target):
    assert player.trade.send(target.identifier) is TradeSentResponses.SUCCESS
    assert target.trade.accept(player.identifier) is TradeAcceptResponses.SUCCESS
    assert not target.trade.offers_received
    assert not player.trade.offers_sent


def test_trade_resources_merged(player, target):
    assert player.trade.send(target.identifier) is TradeSentResponses.SUCCESS
    assert target.trade.accept(player.identifier) is TradeAcceptResponses.SUCCESS
    assert target.trade.all_resources() == set(target.trade.resources).union(player.trade.resources)


def test_trade_cancel(player, target):
    assert player.trade.send(target.identifier) is TradeSentResponses.SUCCESS
    assert target.trade.accept(player.identifier) is TradeAcceptResponses.SUCCESS
    assert target.trade.cancel(player.identifier) is TradeCancelResponses.SUCCESS


def test_trade_cancel_agreement_removed(player, target):
    assert player.trade.send(target.identifier) is TradeSentResponses.SUCCESS
    assert target.trade.accept(player.identifier) is TradeAcceptResponses.SUCCESS
    assert target.trade.cancel(player.identifier) is TradeCancelResponses.SUCCESS
    assert not player.trade.active_agreements
    assert not target.trade.active_agreements


def test_trade_decline_offer_removed(player, target):
    assert player.trade.send(target.identifier) is TradeSentResponses.SUCCESS
    assert target.trade.decline(player.identifier) is TradeDeclineResponses.SUCCESS
    assert not player.trade.offers_sent
    assert not target.trade.offers_received


def test_bonus_resources_merged(player):
    # replace the object in host.nation.types.resources Resources with the one defined in this file. It must propagate to other imports of the Resources object
    # but only within this scope
    with patch("host.nation.types.resources.Resources", Resources), patch(
        "host.nation.types.resources.BonusResources", BonusResources
    ), patch("host.nation.types.resources.RESOURCE_NAMES", list(Resources.keys())), patch(
        "host.nation.types.resources.BONUS_RESOURCE_NAMES", list(BonusResources.keys())
    ):
        import host.nation.types.resources as resources

        assert set(player.trade.resources).intersection(set(resources.RESOURCE_NAMES)) != set()
        player_resources = set(player.trade.resources)
        if "A" not in player_resources:
            swapped_resource = list(player_resources)[0]
            assert (
                player.trade.swap_resources(swapped_resource, "A") is TradeSelectResponses.SUCCESS
            )
            player_resources.remove(swapped_resource)
            player_resources.add("A")

        if "B" not in player_resources:
            swapped_resource = (
                list(player_resources)[0]
                if list(player_resources)[0] != "A"
                else list(player_resources)[1]
            )
            assert (
                player.trade.swap_resources(swapped_resource, "B") is TradeSelectResponses.SUCCESS
            )
        assert set(player.trade.all_resources()) == {"A", "B"}
        assert player.trade.bonus_resources() == {"AB"}


def test_trade_limit_exceeded(player, target, session: Session):
    for _ in range(GameplaySettings.trade.maximum_active_agreements):
        new_player = UserGenerator.generate_player(session)
        assert new_player.trade.send(player.identifier) is TradeSentResponses.SUCCESS
        assert player.trade.accept(new_player.identifier) is TradeAcceptResponses.SUCCESS

    assert len(player.trade.active_agreements) == GameplaySettings.trade.maximum_active_agreements
    assert player.trade.send(target.identifier) is TradeSentResponses.TOO_MANY_ACTIVE_AGREEMENTS
    assert not player.trade.offers_sent
    assert not target.trade.offers_received


def test_offer_recipient_trade_limit_exceeded(player, target, session: Session):
    for _ in range(GameplaySettings.trade.maximum_active_agreements):
        new_player = UserGenerator.generate_player(session)
        assert new_player.trade.send(target.identifier) is TradeSentResponses.SUCCESS
        assert target.trade.accept(new_player.identifier) is TradeAcceptResponses.SUCCESS

    assert len(target.trade.active_agreements) == GameplaySettings.trade.maximum_active_agreements
    assert player.trade.send(target.identifier) is TradeSentResponses.TRADE_PARTNER_FULL
    assert not player.trade.offers_sent
    assert not target.trade.offers_received


def test_offer_recipient_accept_partner_trade_limit_exceeded(player, target, session: Session):
    assert player.trade.send(target.identifier) is TradeSentResponses.SUCCESS
    for _ in range(GameplaySettings.trade.maximum_active_agreements):
        new_player = UserGenerator.generate_player(session)
        assert new_player.trade.send(player.identifier) is TradeSentResponses.SUCCESS
        assert player.trade.accept(new_player.identifier) is TradeAcceptResponses.SUCCESS

    assert len(player.trade.active_agreements) == GameplaySettings.trade.maximum_active_agreements
    assert target.trade.accept(player.identifier) is TradeAcceptResponses.TRADE_PARTNER_FULL
    assert len(player.trade.offers_sent) == 1
    assert len(target.trade.offers_received) == 1


def test_offer_recipient_accept_trade_limit_exceeded(player, target, session: Session):
    assert player.trade.send(target.identifier) is TradeSentResponses.SUCCESS
    for _ in range(GameplaySettings.trade.maximum_active_agreements):
        new_player = UserGenerator.generate_player(session)
        assert new_player.trade.send(target.identifier) is TradeSentResponses.SUCCESS
        assert target.trade.accept(new_player.identifier) is TradeAcceptResponses.SUCCESS

    assert len(target.trade.active_agreements) == GameplaySettings.trade.maximum_active_agreements
    assert target.trade.accept(player.identifier) is TradeAcceptResponses.TOO_MANY_ACTIVE_AGREEMENTS
    assert len(player.trade.offers_sent) == 1
    assert len(target.trade.offers_received) == 1


def test_number_of_offers_limit(player, target, session: Session):
    for _ in range(GameplaySettings.trade.maximum_number_of_offers_received):
        new_player = UserGenerator.generate_player(session)
        assert new_player.trade.send(target.identifier) is TradeSentResponses.SUCCESS

    assert (
        len(target.trade.offers_received)
        == GameplaySettings.trade.maximum_number_of_offers_received
    )
    assert player.trade.send(target.identifier) is TradeSentResponses.PARTNER_OFFERS_FULL


def test_number_of_offers_sent_limit(player, target, session: Session):
    for _ in range(GameplaySettings.trade.maximum_number_of_offers_sent):
        new_player = UserGenerator.generate_player(session)
        assert player.trade.send(new_player.identifier) is TradeSentResponses.SUCCESS

    assert len(player.trade.offers_sent) == GameplaySettings.trade.maximum_number_of_offers_sent
    assert player.trade.send(target.identifier) is TradeSentResponses.TOO_MANY_OFFERS_SENT


def test_no_offer_recipient_accept(player, target):
    assert target.trade.accept(player.identifier) is TradeAcceptResponses.NOT_FOUND
    assert not player.trade.active_agreements
    assert not target.trade.active_agreements


def test_no_offer_recipient_cancel(player, target):
    assert target.trade.cancel(player.identifier) is TradeCancelResponses.NOT_FOUND


def test_no_offer_recipient_decline(player, target):
    assert target.trade.decline(player.identifier) is TradeDeclineResponses.NOT_FOUND
    assert not player.trade.offers_sent
    assert not target.trade.offers_received


def test_cant_trade_with_self(player):
    assert player.trade.send(player.identifier) is TradeSentResponses.CANNOT_TRADE_WITH_SELF
