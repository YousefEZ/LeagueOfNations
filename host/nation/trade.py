from __future__ import annotations

import random
from datetime import datetime, timedelta
from itertools import chain
from typing import TYPE_CHECKING, List, Literal, Optional
from uuid import uuid4

import host.nation.types
from host import base_types
from host.nation import ministry, models
from host.nation.types.resources import RESOURCE_NAMES
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from host.nation import Nation

AcceptMessages = Literal["trade_accepted", "too_many_active_agreements", "trade_partner_full"]

SendMessages = Literal[
    "trade_sent",
    "partner_not_found",
    "cannot_trade_with_self",
    "too_many_active_agreements",
    "trade_partner_full",
]

DeclineMessages = Literal["trade_declined"]

CancelMessages = Literal["trade_cancelled"]


class TradeRequest:
    def __init__(self, trade: models.TradeRequestModel):
        self._trade: Optional[models.TradeRequestModel] = trade

    @property
    def id(self) -> str:
        if self._trade is None:
            raise ValueError("Trade has already been accepted or declined")
        return self._trade.trade_id

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
        return self._trade.expires

    def invalidate(self) -> None:
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

    def invalidate(self) -> None:
        self._trade = None


def filter_expired(
    trades: List[models.TradeRequestModel], session: Session
) -> List[models.TradeRequestModel]:
    now = datetime.now()
    active_requests: List[models.TradeRequestModel] = []
    for trade in trades:
        if trade.expires < now:
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

    @property
    def resources(self) -> host.nation.types.resources.ResourcePair:
        resources = (
            self._session.query(models.ResourcesModel).filter_by(user_id=self._identifier).first()
        )
        if resources is None:
            selected_resources = random.sample(RESOURCE_NAMES, k=2)
            resources = models.ResourcesModel(
                user_id=self._identifier,
                primary=selected_resources[0],
                secondary=selected_resources[1],
            )
            self._session.add(resources)
            self._session.commit()
        return host.nation.types.resources.ResourcePair(resources.primary, resources.secondary)

    @resources.setter
    def resources(self, resources: host.nation.types.resources.ResourcePair) -> None:
        resource_model = models.ResourcesModel(
            user_id=self._identifier,
            primary=resources.primary,
            secondary=resources.secondary,
        )
        self._session.add(resource_model)
        self._session.commit()

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
            self._session.query(models.TradeRequestModel).filter_by(sponsor=self._identifier).all()
        )
        return [TradeRequest(request) for request in filter_expired(requests, self._session)]

    def _send(self, recipient: base_types.UserId) -> None:
        date = datetime.now()
        trade_request = models.TradeRequestModel(
            trade_id=str(int(uuid4())),
            date=date,
            expires=date + timedelta(days=1),
            sponsor=self._identifier,
            recipient=recipient,
        )
        self._session.add(trade_request)
        self._session.commit()

    def send(self, recipient: base_types.UserId) -> SendMessages:
        if self._identifier == recipient:
            return "cannot_trade_with_self"

        if len(self.active_agreements) >= 5:
            return "too_many_active_agreements"

        partner = self._player.find_player(recipient)
        if len(partner.trade.active_agreements) >= 5:
            return "trade_partner_full"

        self._send(recipient)
        return "trade_sent"

    def _accept(self, trade_request: TradeRequest) -> None:
        trade_agreement = models.TradeModel(
            trade_id=trade_request.id,
            date=trade_request.date,
            sponsor=trade_request.sponsor,
            recipient=trade_request.recipient,
        )
        self._session.delete(trade_request)
        self._session.add(trade_agreement)
        self._session.commit()
        trade_request.invalidate()

    def accept(self, trade_request: TradeRequest) -> AcceptMessages:
        if self._identifier != trade_request.recipient:
            raise TradeError("not a recipient of this request")

        if len(self.active_agreements) >= 5:
            return "too_many_active_agreements"

        partner = self._player.find_player(trade_request.sponsor)
        if len(partner.trade.active_agreements) >= 5:
            return "trade_partner_full"

        self._accept(trade_request)
        return "trade_accepted"

    def decline(self, trade_request: TradeRequest) -> DeclineMessages:
        if self._identifier != trade_request.recipient:
            raise TradeError("not a recipient of this request")
        self._session.delete(trade_request)
        self._session.commit()
        trade_request.invalidate()
        return "trade_declined"

    def cancel(self, trade_agreement: TradeAgreement) -> CancelMessages:
        if (
            self._identifier != trade_agreement.recipient
            and self._identifier != trade_agreement.sponsor
        ):
            raise TradeError("not a participant of this agreement")
        self._session.delete(trade_agreement)
        self._session.commit()
        trade_agreement.invalidate()
        return "trade_cancelled"

    def boost(self) -> host.nation.types.boosts.BoostsLookup:
        return host.nation.types.boosts.BoostsLookup()
