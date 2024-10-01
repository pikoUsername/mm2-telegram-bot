import dataclasses
from enum import Enum


@dataclasses.dataclass
class Item:
	name: str
	amount: int
	unit_price: float


@dataclasses.dataclass
class ParsedMessageResult:
	items: list[Item]
	roblox_username: str
	transaction_id: str
	total_price: float


class TransactionStatus(Enum):
	sent = "sent"
	completed = "completed"
	failed = "failed"
