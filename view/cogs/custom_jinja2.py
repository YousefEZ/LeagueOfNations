from jinja2 import FileSystemLoader, ChainableUndefined
from jinja2.environment import Environment

from host.base_types import render_currency, render_currency_rate, render_date


ENVIRONMENT = Environment(
    loader=FileSystemLoader("templates/"), autoescape=True, undefined=ChainableUndefined
)
ENVIRONMENT.filters["currency"] = render_currency
ENVIRONMENT.filters["currency_rate"] = render_currency_rate
ENVIRONMENT.filters["date"] = render_date
