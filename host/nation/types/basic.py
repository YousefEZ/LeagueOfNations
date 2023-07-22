from typing import NewType

from host import ureg

Happiness = NewType("Happiness", float)
Population = NewType("Population", int)
Infrastructure = NewType("Infrastructure", int)
Technology = NewType("Technology", int)
Land = ureg.Registry.kilometer ** 2
