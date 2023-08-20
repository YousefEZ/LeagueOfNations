from jinja2 import BaseLoader, FileSystemLoader
from jinja2.environment import Environment

from host.base_types import render_currency, render_currency_rate

ENVIRONMENT = Environment(loader=FileSystemLoader("templates/"))
ENVIRONMENT.filters["currency"] = render_currency
ENVIRONMENT.filters["currency_rate"] = render_currency_rate
