import dataclasses
from typing import Optional, List

from sqlalchemy.orm import Session

from host.gameplay_settings import GameplaySettings
from host.nation import Ministry, Nation, types
from host.nation.models import ImprovementModel
from host.nation.types.boosts import BoostsLookup
from host.nation.types.improvements import ImprovementSchema
from host.nation.types.transactions import PurchaseResult, SellResult


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
                                                               improvement=improvement).first()

    def purchase_improvement(self, improvement: ImprovementSchema, amount: int) -> PurchaseResult:
        model = self._get_model(improvement.name)
        price = improvement.price * amount
        if not self._nation.bank.enough_funds(price):
            return PurchaseResult.INSUFFICIENT_FUNDS

        self._nation.bank.deduct(price)

        if model is None:
            model = ImprovementModel(user_id=self._nation.identifier, improvement=improvement.name, amount=amount)
            self._session.add(model)
        else:
            model.amount += amount
        self._session.commit()
        return PurchaseResult.SUCCESS

    def sell_improvement(self, improvement: ImprovementSchema, amount: int) -> SellResult:
        model = self._get_model(improvement.name)
        if model is None:
            return SellResult.INSUFFICIENT_AMOUNT
        if model.amount < amount:
            return SellResult.INSUFFICIENT_AMOUNT

        cashback = improvement.price * amount * GameplaySettings.interior.cashback_modifier
        self._nation.bank.add(cashback)
        if model.amount == amount:
            self._session.delete(model)
        else:
            model.amount -= amount
        self._session.commit()
        return SellResult.SUCCESS

    def boost(self) -> BoostsLookup:
        return sum(
            (ImprovementCollection(types.improvements.Improvements[improvement.name], improvement.amount).boosts for
             improvement in
             self.models), BoostsLookup())
