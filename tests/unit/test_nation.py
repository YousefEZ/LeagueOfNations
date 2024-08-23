from host import gameplay_settings
from host.currency import Currency


def test_bank(player):
    assert player.bank.funds == Currency(gameplay_settings.GameplaySettings.bank.starter_funds)
