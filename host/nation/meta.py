from __future__ import annotations

from functools import cached_property

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from host import base_types
from host.nation import models


class Meta:
    def __init__(self, identifier: base_types.UserId, engine: Engine):
        self._identifier = identifier
        self._engine = engine

    @cached_property
    def metadata(self) -> models.MetadataModel:
        with Session(self._engine) as session:
            metadata = session.query(models.MetadataModel).filter_by(user_id=self._identifier).first()
        if metadata is None:
            raise ValueError(f"Metadata does not exist for {self._identifier}")
        return metadata

    @property
    def nation_name(self) -> str:
        return self.metadata.nation
