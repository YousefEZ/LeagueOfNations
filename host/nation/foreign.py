from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from enum import IntEnum, auto
from typing import TYPE_CHECKING, List, Optional, Set, Tuple, Union

import host.alliance.models as alliance_models
from host import alliance, base_types, gameplay_settings
from host.alliance import Alliance
from host.currency import Currency, Price
from host.nation import models
from host.nation.ministry import Ministry
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from host.nation import Nation

SLOT_EXPIRY_TIME = timedelta(days=gameplay_settings.GameplaySettings.foreign.aid_slot_expire_days)


class AidRejectCode(IntEnum):
    SUCCESS = auto()
    DOES_NOT_EXIST = auto()
    NOT_THE_RECIPIENT = auto()


class AidAcceptCode(IntEnum):
    SUCCESS = auto()
    NOT_THE_RECIPIENT = auto()
    EXPIRED = auto()
    ZERO_SLOTS = auto()
    DOES_NOT_EXIST = auto()


class AidRequestCode(IntEnum):
    SUCCESS = auto()
    PLAYER_NOT_EXISTS = auto()
    SAME_AS_SPONSOR = auto()
    INSUFFICIENT_FUNDS = auto()
    INVALID_RECIPIENT = auto()
    INVALID_AMOUNT = auto()
    ABOVE_LIMIT = auto()
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
    def amount(self) -> Currency:
        return Currency(self._model.amount)

    @property
    def reason(self) -> str:
        return self._model.reason


class AidRequest(Aid):
    def __init__(self, model: models.AidRequestModel):
        super().__init__(model)

    @property
    def expires(self) -> datetime:
        assert isinstance(self._model, models.AidRequestModel)
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
        assert isinstance(self._model, models.AidModel)
        return self._model.accepted

    @property
    def expires(self) -> datetime:
        assert isinstance(self._model, models.AidModel)
        return self._model.accepted + SLOT_EXPIRY_TIME

    @classmethod
    def from_id(cls, aid_id: str, session: Session) -> Optional[AidAgreement]:
        model = session.query(models.AidModel).filter_by(aid_id=aid_id).first()
        if model is None:
            return None
        return cls(model)


class Foreign(Ministry):
    def __init__(self, player: Nation, session: Session):
        self._player = player
        self._session = session

    @property
    def free_slots(self) -> int:
        return gameplay_settings.GameplaySettings.foreign.maximum_aid_slots - len(
            self.recipient_agreements
        )

    def _remove_expired_agreements(self) -> None:
        self._session.query(models.AidModel).filter(
            models.AidModel.accepted + SLOT_EXPIRY_TIME >= datetime.now()
        ).delete()
        self._session.commit()

    @property
    def sponsored_agreements(self) -> List[AidAgreement]:
        self._remove_expired_agreements()
        return [
            AidAgreement(agreement)
            for agreement in self._session.query(models.AidModel)
            .filter_by(sponsor=self._player.identifier)
            .all()
        ]

    @property
    def recipient_agreements(self) -> List[AidAgreement]:
        self._remove_expired_agreements()
        return [
            AidAgreement(agreement)
            for agreement in self._session.query(models.AidModel)
            .filter_by(recipient=self._player.identifier)
            .all()
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

    def _send(self, recipient: base_types.UserId, amount: Price, reason: str) -> None:
        request = models.AidRequestModel(
            aid_id=str(uuid.uuid4()),
            sponsor=self._player.identifier,
            recipient=recipient,
            amount=int(amount),
            date=datetime.now(),
            expires=datetime.now() + timedelta(days=3),
            reason=reason,
        )
        self._player.bank.deduct(amount)
        self._session.add(request)
        self._session.commit()

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
            for request in self._session.query(models.AidRequestModel)
            .filter_by(sponsor=self._player.identifier)
            .all()
        ]

    def _verify_send_request(
        self, recipient: base_types.UserId, amount: Price, reason: str
    ) -> AidRequestCode:
        if not self._player.find_player(recipient).exists:
            return AidRequestCode.PLAYER_NOT_EXISTS

        if recipient == self._player.identifier:
            return AidRequestCode.SAME_AS_SPONSOR

        if not self._player.find_player(recipient).exists:
            return AidRequestCode.INVALID_RECIPIENT

        if amount > Price(gameplay_settings.GameplaySettings.foreign.maximum_aid_amount):
            return AidRequestCode.ABOVE_LIMIT

        if not self._player.bank.can_purchase(amount):
            return AidRequestCode.INSUFFICIENT_FUNDS

        if not reason.isascii():
            return AidRequestCode.REASON_NOT_ASCII

        if len(reason) > 200:
            return AidRequestCode.REASON_TOO_LONG

        return AidRequestCode.SUCCESS

    def send(self, recipient: base_types.UserId, amount: Price, reason: str) -> AidRequestCode:
        code = self._verify_send_request(recipient, amount, reason)
        if code is AidRequestCode.SUCCESS:
            return code

        self._send(recipient, amount, reason)
        return AidRequestCode.SUCCESS

    def _cancel_request(self, request: AidRequest) -> None:
        model_request = (
            self._session.query(models.AidRequestModel).filter_by(aid_id=request.id).first()
        )
        if model_request is None:
            return
        self._player.find_player(request.sponsor).bank.receive(request.amount)
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
            amount=int(request.amount),
            date=request.date,
            accepted=datetime.now(),
            reason=request.reason,
        )
        self._session.delete(request.model)
        self._session.add(agreement)
        self._player.bank.receive(request.amount)
        return AidAgreement(agreement)

    def _verify_accept_request(self, request: AidRequest) -> AidAcceptCode:
        if request.recipient != self._player.identifier:
            return AidAcceptCode.NOT_THE_RECIPIENT

        if self._session.query(models.AidRequestModel).filter_by(aid_id=request.id).first() is None:
            return AidAcceptCode.DOES_NOT_EXIST

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

        if self._session.query(models.AidRequestModel).filter_by(aid_id=request.id).first() is None:
            return AidRejectCode.DOES_NOT_EXIST

        self._cancel_request(request)
        return AidRejectCode.SUCCESS

    @property
    def alliance(self) -> Optional[Alliance]:
        member = (
            self._session.query(alliance_models.AllianceMemberModel)
            .filter_by(user_id=self._player.identifier)
            .first()
        )
        if member is None:
            return None
        return Alliance(alliance.types.AllianceId(member.id), self._session)
