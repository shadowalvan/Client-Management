from dataclasses import dataclass
from typing import Optional


@dataclass
class Client:
    id: Optional[int]
    name: str
    client_code: str

    @classmethod
    def from_row(cls, row):
        return cls(
            id=row["id"],
            name=row["name"],
            client_code=row["client_code"],
        )

