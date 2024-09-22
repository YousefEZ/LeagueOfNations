from __future__ import annotations

from enum import IntEnum, auto
import random
from datetime import datetime, timedelta
from itertools import chain
from typing import TYPE_CHECKING, List, Optional

from host.gameplay_settings import GameplaySettings
import host.nation.types
from host import base_types
from host.nation import ministry, models
from host.nation.types.resources import RESOURCE_NAMES, ResourceName
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from host.nation import Nation


class TradeSelectResponses(IntEnum):
    SUCCESS = 0
    INVALID_RESOURCE = auto()
    MISSING_RESOURCE = auto()
    ACTIVE_AGREEMENT = auto()
    DUPLICATE_RESOURCE = auto()


class TradeAcceptResponses(IntEnum):
    SUCCESS = 0
    TOO_MANY_ACTIVE_AGREEMENTS = auto()
    TRADE_PARTNER_FULL = auto()
    NOT_FOUND = auto()


class TradeSentResponses(IntEnum):
    SUCCESS = 0
    PARTNER_NOT_FOUND = auto()
    CANNOT_TRADE_WITH_SELF = auto()
    TOO_MANY_ACTIVE_AGREEMENTS = auto()
    TRADE_PARTNER_FULL = auto()


class TradeDeclineResponses(IntEnum):
    SUCCESS = 0
    NOT_FOUND = auto()


class TradeCancelResponses(IntEnum):
    SUCCESS = 0


class TradeRequest:
    def __init__(self, trade: models.TradeRequestModel):
        self._trade: Optional[models.TradeRequestModel] = trade

    @property
    def sponsor(self) -> base_types.UserId:
        if self._trade is None:
            raise ValueError("Trade has already been accepted or declined")
        return base_types.UserId(self._trade.sponsor)

    @property
    def recipient(self) -> base_types.UserId:
        if self._trade is None:
            raise ValueError("Trade has already been accepted or declined")
        return base_types.UserId(self._trade.recipient)

    @property
    def date(self) -> datetime:
        if self._trade is None:
            raise ValueError("Trade has already been accepted or declined")
        return self._trade.date

    @property
    def expires(self) -> datetime:
        if self._trade is None:
            raise ValueError("Trade has already been accepted or declined")
        return self._trade.date + timedelta(days=GameplaySettings.trade.offer_expire_days)

    def invalidate(self, session: Session) -> None:
        session.delete(self._trade)
        self._trade = None


class TradeAgreement:
    def __init__(self, trade: models.TradeModel):
        self._trade: Optional[models.TradeModel] = trade

    @property
    def sponsor(self) -> base_types.UserId:
        if self._trade is None:
            raise ValueError("Trade has been cancelled")
        return base_types.UserId(self._trade.sponsor)

    @property
    def recipient(self) -> base_types.UserId:
        if self._trade is None:
            raise ValueError("Trade has been cancelled")
        return base_types.UserId(self._trade.recipient)

    @property
    def date(self) -> datetime:
        if self._trade is None:
            raise ValueError("Trade has been cancelled")
        return self._trade.date

    def invalidate(self, session: Session) -> None:
        session.delete(self._trade)
        self._trade = None


def filter_expired(
    trades: List[models.TradeRequestModel], session: Session
) -> List[models.TradeRequestModel]:
    now = datetime.now()
    active_requests: List[models.TradeRequestModel] = []
    for trade in trades:
        if trade.date + timedelta(days=GameplaySettings.trade.offer_expire_days) < now:
            session.delete(trade)
        else:
            active_requests.append(trade)
    session.commit()
    return active_requests


class TradeError(Exception):
    pass


class Trade(ministry.Ministry):
    def __init__(self, player: Nation, session: Session):
        self._identifier: base_types.UserId = player.identifier
        self._player: Nation = player
        self._session: Session = session

    def swap_resources(self, old_resource: str, resource: str) -> TradeSelectResponses:
        if resource not in RESOURCE_NAMES:
            return TradeSelectResponses.INVALID_RESOURCE
        resource_model = (
            self._session.query(models.ResourcesModel)
            .filter_by(user_id=self._identifier, resource=old_resource)
            .first()
        )
        if resource_model is None:
            return TradeSelectResponses.MISSING_RESOURCE

        if resource in self.resources:
            return TradeSelectResponses.DUPLICATE_RESOURCE

        resource_model.resource = resource
        self._session.commit()
        return TradeSelectResponses.SUCCESS

    @property
    def resources(self) -> List[ResourceName]:
        resources = (
            self._session.query(models.ResourcesModel).filter_by(user_id=self._identifier).all()
        )
        if not resources:
            selected_resources = random.sample(
                RESOURCE_NAMES, k=GameplaySettings.trade.resources_per_nation
            )
            for resource in selected_resources:
                self._session.add(
                    models.ResourcesModel(user_id=self._identifier, resource=resource)
                )
            self._session.commit()
            return selected_resources
        return [ResourceName(resource.resource) for resource in resources]

    @property
    def all_resources(self) -> List[str]:
        return list(
            chain(
                self.resources,
                (
                    resource
                    for agreement in self.sponsored
                    for pair in self._player.find_player(agreement.recipient).trade.resources
                    for resource in pair
                ),
                (
                    resource
                    for agreement in self.recipient
                    for pair in self._player.find_player(agreement.sponsor).trade.resources
                    for resource in pair
                ),
            )
        )

    @property
    def sponsored(self) -> List[TradeAgreement]:
        trades = self._session.query(models.TradeModel).filter_by(sponsor=self._identifier).all()
        return [TradeAgreement(trade) for trade in trades]

    @property
    def recipient(self) -> List[TradeAgreement]:
        trades = self._session.query(models.TradeModel).filter_by(recipient=self._identifier).all()
        return [TradeAgreement(trade) for trade in trades]

    @property
    def active_agreements(self) -> List[TradeAgreement]:
        return self.sponsored + self.recipient

    @property
    def requests(self) -> List[TradeRequest]:
        requests = (
            self._session.query(models.TradeRequestModel)
            .filter_by(recipient=self._identifier)
            .all()
        )
        return [TradeRequest(request) for request in filter_expired(requests, self._session)]

    @property
    def received(self) -> List[TradeRequest]:
        requests = (
            self._session.query(models.TradeRequestModel)
            .filter_by(recipient=self._identifier)
            .all()
        )
        return [TradeRequest(request) for request in filter_expired(requests, self._session)]

    def _send(self, recipient: base_types.UserId) -> None:
        date = datetime.now()
        trade_request = models.TradeRequestModel(
            date=date,
            sponsor=self._identifier,
            recipient=recipient,
        )
        self._session.add(trade_request)
        self._session.commit()

    def send(self, recipient: base_types.UserId) -> TradeSentResponses:
        if self._identifier == recipient:
            return TradeSentResponses.CANNOT_TRADE_WITH_SELF

        if len(self.active_agreements) >= GameplaySettings.trade.maximum_active_agreements:
            return TradeSentResponses.TOO_MANY_ACTIVE_AGREEMENTS

        partner = self._player.find_player(recipient)
        if len(partner.trade.active_agreements) >= GameplaySettings.trade.maximum_active_agreements:
            return TradeSentResponses.TRADE_PARTNER_FULL

        self._send(recipient)
        return TradeSentResponses.SUCCESS

    def _accept(self, trade_request: TradeRequest) -> None:
        trade_agreement = models.TradeModel(
            date=trade_request.date,
            sponsor=trade_request.sponsor,
            recipient=trade_request.recipient,
        )
        self._session.add(trade_agreement)
        trade_request.invalidate(self._session)
        self._session.commit()

    def fetch_request_from(self, sponsor: base_types.UserId) -> Optional[TradeRequest]:
        requests = list(filter(lambda x: x.sponsor == sponsor, self.requests))
        if not requests:
            return None

        return requests[0]

    def fetch_agreement_with(self, partner: base_types.UserId) -> Optional[TradeAgreement]:
        agreements = list(
            filter(
                lambda x: x.sponsor == partner or x.recipient == partner,
                self.active_agreements,
            )
        )
        if not agreements:
            return None

        return agreements[0]

    def accept(self, sponsor: base_types.UserId) -> TradeAcceptResponses:
        trade_request = self.fetch_request_from(sponsor)

        if trade_request is None:
            return TradeAcceptResponses.NOT_FOUND

        if len(self.active_agreements) >= GameplaySettings.trade.maximum_active_agreements:
            return TradeAcceptResponses.TOO_MANY_ACTIVE_AGREEMENTS

        partner = self._player.find_player(trade_request.sponsor)
        if len(partner.trade.active_agreements) >= GameplaySettings.trade.maximum_active_agreements:
            return TradeAcceptResponses.TRADE_PARTNER_FULL

        self._accept(trade_request)
        return TradeAcceptResponses.SUCCESS

    def decline(self, sponsor: base_types.UserId) -> TradeDeclineResponses:
        trade_request = self.fetch_agreement_with(sponsor)
        if trade_request is None:
            return TradeDeclineResponses.NOT_FOUND
        trade_request.invalidate(self._session)
        return TradeDeclineResponses.SUCCESS

    def cancel(self, partner: base_types.UserId) -> TradeCancelResponses:
        trade_request = self.fetch_request_from(partner)
        if (
            self._identifier != trade_agreement.recipient
            and self._identifier != trade_agreement.sponsor
        ):
            raise TradeError("not a participant of this agreement")
        trade_agreement.invalidate(self._session)
        self._session.commit()
        return TradeCancelResponses.SUCCESS

    def boost(self) -> host.nation.types.boosts.BoostsLookup:
        return host.nation.types.boosts.BoostsLookup()
