import pint

ureg = pint.UnitRegistry()
ureg.define("dinar = euro = dollar = [money] = $ = £ = ﺩ")
ureg.define("second = [time] = s = sec")
ureg.define("income_rate = dinar / second = [income rate] = $/s = £/s = ﺩ/s")

