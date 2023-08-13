from typing import NewType

from host import ureg

Happiness = NewType("Happiness", float)
Population = NewType("Population", int)
InfrastructureUnit = NewType("InfrastructureUnit", int)
TechnologyUnit = NewType("TechnologyUnit", int)
LandUnit = ureg.Registry.kilometer ** 2


@ureg.Registry.wraps(LandUnit, None)
def land(value: ureg.Registry.kilometer ** 2) -> LandUnit:
    return value * LandUnit
