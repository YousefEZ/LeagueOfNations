from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional, Union, Literal

from sqlalchemy import Engine
from sqlalchemy.orm import Session

import host.currency
import host.ureg
from host import alliance, base_types
from host.alliance import Alliance
import host.alliance.models
from host.nation.ministry import Ministry
from host.nation import models

if TYPE_CHECKING:
    from host.nation import Nation

AidAcceptMessages = Literal["not_a_recipient", "insufficient_funds", "expired", "success"]

AidMessages = Literal[
    AidAcceptMessages,
    "cannot_be_sponsor", 'success', 'insufficient_funds', 'invalid_recipient', 'invalid_amount', 'invalid_sponsor'
]


class Aid:

    def __init__(self, model: Union[models.AidModel, models.AidRequestModel]):
        self._model = model

    @property
    def model(self) -> Union[models.AidModel, models.AidRequestModel]:
        return self._model

    @property
    def id(self) -> str:
        return self._model.aid_id

    @property
    def sponsor(self) -> base_types.UserId:
        return base_types.UserId(self._model.sponsor)

    @property
    def recipient(self) -> base_types.UserId:
        return base_types.UserId(self._model.recipient)

    @property
    def expires(self) -> datetime:
        return self._model.date

    @property
    @host.ureg.Registry.wraps(host.currency.Currency, None)
    def amount(self) -> host.currency.Currency:
        return self._model.amount


class AidRequest(Aid):

    def __init__(self, model: models.AidRequestModel):
        super().__init__(model)


class AidAgreement(Aid):

    def __init__(self, model: models.AidModel):
        super().__init__(model)


class Foreign(Ministry):

    def __init__(self, player: Nation, session: Session):
        self._player = player
        self._session = session

    @property
    def sent(self) -> List[AidRequest]:
        return []

    def _send(self, request: models.AidRequestModel) -> None:
        self._session.add(request)
        self._session.commit()

    @host.ureg.Registry.wraps(None, [None, None, host.currency.Currency])
    def send(self, recipient: base_types.UserId, amount: host.currency.Currency) -> AidMessages:
        if recipient == self._player.identifier:
            return "cannot_be_sponsor"

        if amount < 0 * host.currency.Currency:
            return "invalid_amount"

        if not self._player.bank.enough_funds(amount):
            return "insufficient_funds"

        request = models.AidRequestModel(aid_id=str(uuid.uuid4()),
                                         sponsor=self._player.identifier,
                                         recipient=recipient,
                                         amount=int(amount.magnitude),
                                         date=datetime.now())
        self._send(request)
        return "success"

    def remove_request(self, request: AidRequest) -> None:
        with Session(self._engine) as session:
            model_request = session.query(models.AidRequestModel).filter_by(aid_id=request.id).first()
            if model_request is None:
                return
            session.delete(model_request)
            session.commit()

    def _accept(self, request: AidRequest) -> None:
        ...

    def accept(self, request: AidRequest) -> AidAcceptMessages:
        if request.recipient != self._player.identifier:
            return "not_a_recipient"

        if not self._player.bank.enough_funds(request.amount):
            return "insufficient_funds"

        if request.expires < datetime.now():
            self.remove_request(request)
            return "expired"

        self._accept(request)

        return "success"

    @property
    def alliance(self) -> Optional[Alliance]:
        member = self._session.query(alliance.models.AllianceMemberModel).filter_by(
            user=self._player.identifier).first()
        if member is None:
            return None
        return Alliance(alliance.types.AllianceId(member.id), self._session)
