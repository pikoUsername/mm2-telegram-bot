import dataclasses


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
