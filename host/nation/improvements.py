from __future__ import annotations

import dataclasses
from typing import Optional, List, TYPE_CHECKING, Any, Dict

from sqlalchemy.orm import Session

from host.gameplay_settings import GameplaySettings
from host.nation.ministry import Ministry
from host.nation import types
from host.nation.models import ImprovementModel
from host.nation.types.boosts import BoostsLookup
from host.nation.types.improvements import ImprovementSchema
from host.nation.types.transactions import PurchaseResult, SellResult

if TYPE_CHECKING:
    from host.nation import Nation


@dataclasses.dataclass(frozen=True)
class ImprovementCollection:
    improvement: ImprovementSchema
    amount: int

    @property
    def boosts(self) -> BoostsLookup:
        return self.improvement.boosts.multiply(self.amount)


class Improvements(Ministry):

    def __init__(self, nation: Nation, session: Session):
        self._nation = nation
        self._session = session

    @property
    def models(self) -> List[ImprovementModel]:
        return self._session.query(ImprovementModel).filter_by(user_id=self._nation.identifier).all()

    def _get_model(self, improvement: str) -> Optional[ImprovementModel]:
        return self._session.query(ImprovementModel).filter_by(user_id=self._nation.identifier,
                                                               name=improvement).first()

    def buy(self, improvement: ImprovementSchema, amount: int) -> PurchaseResult:
        model = self._get_model(improvement.name)
        price = improvement.price * amount
        if not self._nation.bank.enough_funds(price):
            return PurchaseResult.INSUFFICIENT_FUNDS

        self._nation.bank.deduct(price)

        if model is None:
            model = ImprovementModel(user_id=self._nation.identifier, name=improvement.name, amount=amount)
            self._session.add(model)
        else:
            model.amount += amount
        self._session.commit()
        return PurchaseResult.SUCCESS

    def sell(self, improvement: ImprovementSchema, amount: int) -> SellResult:
        model = self._get_model(improvement.name)
        if model is None or model.amount < amount:
            return SellResult.INSUFFICIENT_AMOUNT

        cashback = improvement.cashback * amount
        self._nation.bank.add(cashback)
        if model.amount == amount:
            self._session.delete(model)
        else:
            model.amount -= amount
        self._session.commit()
        return SellResult.SUCCESS

    @property
    def owned(self) -> Dict[str, ImprovementCollection]:
        return {improvement.name: ImprovementCollection(types.improvements.Improvements[improvement.name],
                                                        improvement.amount) for
                improvement in self.models}

    def __getitem__(self, item: str) -> ImprovementCollection:
        return self.owned[item]

    def boost(self) -> BoostsLookup:
        return sum(
            (ImprovementCollection(types.improvements.Improvements[improvement.name], improvement.amount).boosts for
             improvement in
             self.models), BoostsLookup())
