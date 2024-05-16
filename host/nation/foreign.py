from __future__ import annotations

from enum import IntEnum, auto
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Optional, Set, Tuple, Union

from sqlalchemy.orm import Session

import host.currency
import host.ureg
from host import alliance, base_types, gameplay_settings
from host.alliance import Alliance
import host.alliance.models as alliance_models
from host.nation.ministry import Ministry
from host.nation import models

if TYPE_CHECKING:
    from host.nation import Nation


class AidRejectCode(IntEnum):
    SUCCESS = auto()
    NOT_THE_RECIPIENT = auto()


class AidAcceptCode(IntEnum):
    SUCCESS = auto()
    NOT_THE_RECIPIENT = auto()
    EXPIRED = auto()
    ZERO_SLOTS = auto()


class AidRequestCode(IntEnum):
    SUCCESS = auto()
    PLAYER_NOT_EXISTS = auto()
    SAME_AS_SPONSOR = auto()
    INSUFFICIENT_FUNDS = auto()
    INVALID_RECIPIENT = auto()
    INVALID_AMOUNT = auto()
    ABOVE_LIMIT = auto()
    INVALID_SPONSOR = auto()
    REASON_NOT_ASCII = auto()
    REASON_TOO_LONG = auto()


class AidCancelCode(IntEnum):
    SUCCESS = auto()
    DOES_NOT_EXIST = auto()
    NOT_A_SPONSOR = auto()


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
    def date(self) -> datetime:
        return self._model.date

    @property
    @host.ureg.Registry.wraps(host.currency.Currency, None)
    def amount(self) -> host.currency.Currency:
        return self._model.amount


class AidRequest(Aid):
    def __init__(self, model: models.AidRequestModel):
        super().__init__(model)

    @property
    def expires(self) -> datetime:
        return self._model.expires

    @classmethod
    def from_id(cls, aid_id: str, session: Session) -> Optional[AidRequest]:
        model = session.query(models.AidRequestModel).filter_by(aid_id=aid_id).first()
        if model is None:
            return None
        return cls(model)


class AidAgreement(Aid):
    def __init__(self, model: models.AidModel):
        super().__init__(model)

    @property
    def accepted(self) -> datetime:
        return self._model.accepted

    @classmethod
    def from_id(cls, aid_id: str, session: Session) -> Optional[AidAgreement]:
        model = session.query(models.AidModel).filter_by(aid_id=aid_id).first()
        if model is None:
            return None
        return cls(model)


SLOT_EXPIRY_TIME = timedelta(days=gameplay_settings.GameplaySettings.foreign.aid_slot_expire_days)


class Foreign(Ministry):
    def __init__(self, player: Nation, session: Session):
        self._player = player
        self._session = session

    @property
    def free_slots(self) -> int:
        return gameplay_settings.GameplaySettings.foreign.maximum_aid_slots - len(self.recipient_agreements)

    @property
    def sponsored_agreemenets(self) -> List[AidAgreement]:
        self._session.query(models.AidModel).filter(
            models.AidModel.accepted + SLOT_EXPIRY_TIME < datetime.now()
        ).delete()
        return [
            AidAgreement(agreement)
            for agreement in self._session.query(models.AidModel).filter_by(sponsor=self._player.identifier).all()
        ]

    @property
    def recipient_agreements(self) -> List[AidAgreement]:
        self._session.query(models.AidModel).filter(
            models.AidModel.accepted + SLOT_EXPIRY_TIME < datetime.now()
        ).delete()
        return [
            AidAgreement(agreement)
            for agreement in self._session.query(models.AidModel).filter_by(recipient=self._player.identifier).all()
        ]

    @property
    def received_requests(self) -> List[AidRequest]:
        return self._remove_expired_requests(
            {
                AidRequest(request)
                for request in self._session.query(models.AidRequestModel)
                .filter_by(recipient=self._player.identifier)
                .all()
            }
        )

    @property
    def sponsorships(self) -> List[AidRequest]:
        return self._remove_expired_requests(
            {
                AidRequest(request)
                for request in self._session.query(models.AidRequestModel)
                .filter_by(sponsor=self._player.identifier)
                .all()
            }
        )

    @host.ureg.Registry.check(None, None, host.currency.Currency, None)
    def _send(self, recipient: base_types.UserId, amount: host.currency.Currency, reason: str) -> AidRequest:
        request = models.AidRequestModel(
            aid_id=str(uuid.uuid4()),
            sponsor=self._player.identifier,
            recipient=recipient,
            amount=int(amount.magnitude),
            date=datetime.now(),
            expires=datetime.now() + timedelta(days=3),
        )
        self._player.bank.deduct(amount)
        self._session.add(request)
        self._session.commit()
        return AidRequest(request)

    def _remove_expired_requests(self, requests: Set[AidRequest]) -> List[AidRequest]:
        removed_requests = set()
        for request in requests:
            if request.expires < datetime.now():
                self._cancel_request(request)
                removed_requests.add(request)
        return list(requests - removed_requests)

    @property
    def sponsors(self) -> List[AidRequest]:
        return [
            AidRequest(request)
            for request in self._session.query(models.AidRequestModel).filter_by(sponsor=self._player.identifier).all()
        ]

    @host.ureg.Registry.check(None, None, host.currency.Currency, None)
    def _verify_send_request(
        self, recipient: base_types.UserId, amount: host.currency.Currency, reason: str
    ) -> AidRequestCode:
        if not self._player.find_player(recipient).exists:
            return AidRequestCode.PLAYER_NOT_EXISTS

        if recipient == self._player.identifier:
            return AidRequestCode.SAME_AS_SPONSOR

        if not self._player.find_player(recipient).exists:
            return AidRequestCode.INVALID_RECIPIENT

        if amount < host.currency.lnd(0):
            return AidRequestCode.INVALID_AMOUNT

        if amount > host.currency.lnd(gameplay_settings.GameplaySettings.foreign.maximum_aid_amount):
            return AidRequestCode.ABOVE_LIMIT

        if not self._player.bank.enough_funds(amount):
            return AidRequestCode.INSUFFICIENT_FUNDS

        if not reason.isascii():
            return AidRequestCode.REASON_NOT_ASCII

        if len(reason) > 200:
            return AidRequestCode.REASON_TOO_LONG

        return AidRequestCode.SUCCESS

    @host.ureg.Registry.wraps(None, [None, None, host.currency.Currency, None])
    def send(
        self, recipient: base_types.UserId, amount: host.currency.Currency, reason: str
    ) -> Tuple[AidRequestCode, Optional[AidRequest]]:
        code = self._verify_send_request(recipient, amount * host.currency.Currency, reason)
        if code != AidRequestCode.SUCCESS:
            return code, None

        request = self._send(recipient, amount * host.currency.Currency, reason)
        return AidRequestCode.SUCCESS, request

    def _cancel_request(self, request: AidRequest) -> None:
        model_request = self._session.query(models.AidRequestModel).filter_by(aid_id=request.id).first()
        if model_request is None:
            return
        self._player.find_player(request.sponsor).bank.add(request.amount)
        self._session.delete(model_request)
        self._session.commit()

    def cancel(self, request: AidRequest) -> AidCancelCode:
        if request.sponsor != self._player.identifier:
            return AidCancelCode.NOT_A_SPONSOR

        self._cancel_request(request)
        return AidCancelCode.SUCCESS

    def _accept(self, request: AidRequest) -> AidAgreement:
        agreement = models.AidModel(
            aid_id=request.id,
            sponsor=request.sponsor,
            recipient=request.recipient,
            amount=int(request.amount.magnitude),
            date=request.date,
            accepted=datetime.now(),
        )
        self._session.delete(request.model)
        self._session.add(agreement)
        self._player.bank.add(request.amount)
        return AidAgreement(agreement)

    def _verify_accept_request(self, request: AidRequest) -> AidAcceptCode:
        if request.recipient != self._player.identifier:
            return AidAcceptCode.NOT_THE_RECIPIENT

        if request.expires < datetime.now():
            self._cancel_request(request)
            return AidAcceptCode.EXPIRED

        if self.free_slots < 1:
            return AidAcceptCode.ZERO_SLOTS

        return AidAcceptCode.SUCCESS

    def accept(self, request: AidRequest) -> Tuple[AidAcceptCode, Optional[AidAgreement]]:
        code = self._verify_accept_request(request)
        if code != AidAcceptCode.SUCCESS:
            return code, None

        agreement = self._accept(request)
        return AidAcceptCode.SUCCESS, agreement

    def reject(self, request: AidRequest) -> AidRejectCode:
        if request.recipient != self._player.identifier:
            return AidRejectCode.NOT_THE_RECIPIENT

        self._cancel_request(request)
        return AidRejectCode.SUCCESS

    @property
    def alliance(self) -> Optional[Alliance]:
        member = (
            self._session.query(alliance_models.AllianceMemberModel).filter_by(user_id=self._player.identifier).first()
        )
        if member is None:
            return None
        return Alliance(alliance.types.AllianceId(member.id), self._session)
