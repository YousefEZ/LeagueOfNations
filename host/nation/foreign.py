from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional, Union, Literal

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from host import alliance, base_types
from host.alliance import Alliance
import host.alliance.models
from host.nation.ministry import Ministry
from host.nation import models

if TYPE_CHECKING:
    from host.nation import Nation

AidMessages = Literal['success', 'insufficient_funds', 'invalid_recipient', 'invalid_amount', 'invalid_sponsor']


class Aid:

    def __init__(self, model: Union[models.AidModel, models.AidRequestModel]):
        self._model = model

    @property
    def model(self) -> Union[models.AidModel, models.AidRequestModel]:
        return self._model

    @property
    def id(self) -> int:
        return self._model.aid_id

    @property
    def sponsor(self) -> int:
        return self._model.sponsor

    @property
    def recipient(self) -> int:
        return self._model.recipient

    @property
    def expires(self) -> datetime:
        return self._model.date

    @property
    @base_types.ureg.wraps(base_types.Currency, None)
    def amount(self) -> base_types.Currency:
        return self._model.amount


class AidRequest(Aid):

    def __init__(self, model: models.AidRequestModel):
        super().__init__(model)


class AidAgreement(Aid):

    def __init__(self, model: models.AidModel):
        super().__init__(model)


class Foreign(Ministry):

    def __init__(self, player: Nation, engine: Engine):
        self._player = player
        self._engine = engine

    @property
    def sent(self) -> List[AidRequest]:
        return []

    def _send(self, request: models.AidRequestModel) -> None:
        with Session(self._engine) as session:
            session.add(request)
            session.commit()

    @base_types.ureg.wraps(None, [None, None, base_types.Currency])
    def send(self, recipient: base_types.UserId, amount: base_types.Currency) -> AidMessages:
        if recipient == self._player.identifier:
            return "cannot_be_sponsor"

        if amount < 0 * base_types.Currency:
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
            session.delete(request._model)
            session.commit()

    def accept(self, request: AidRequest) -> AidMessages:
        raise NotImplementedError

    def accept(self, request: AidRequest) -> AidMessages:
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
        with Session(self._engine) as session:
            member = session.query(alliance.models.AllianceMemberModel).filter_by(user=self._player.identifier).first()
            if member is None:
                return None
            return Alliance(member.id, self._engine)
