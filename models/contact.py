from dataclasses import dataclass
from typing import Optional


@dataclass
class Contact:
    id: Optional[int]
    name: str
    surname: str
    email: str

    @property
    def full_name(self) -> str:
        return f"{self.surname} {self.name}"

    @classmethod
    def from_row(cls, row):
        return cls(
            id=row["id"],
            name=row["name"],
            surname=row["surname"],
            email=row["email"],
        )

