
import pytest
from utils import parse_message

# Пример корректного сообщения для парсинга
valid_message = """
Order #1905848770
1. Batwing: 159 (1 x 159)
The order is paid for.
Payment Amount: 159 RUB
Payment ID: Tinkoff Payment: 5060809602

Purchaser information:
Ваш_ник_в_ROBLOX: vepe211
Введите_ваш_телеграм_: Pavel
Phone: +79265377051

Additional information:
Transaction ID: 9961889:6682510345
Block ID: rec784210467
Form Name: Cart
https://mm2guns.com/knifes
"""

invalid_message_no_transaction = """
Order #1905848770
1. Batwing: 159 (1 x 159)
The order is paid for.
Payment Amount: 159 RUB
Payment ID: Tinkoff Payment: 5060809602

Purchaser information:
Ваш_ник_в_ROBLOX: vepe211
Введите_ваш_телеграм_: Pavel
Phone: +79265377051

Additional information:
Block ID: rec784210467
Form Name: Cart
https://mm2guns.com/knifes
"""

invalid_message_no_roblox_name = """
Order #1905848770
1. Batwing: 159 (1 x 159)
2. Song: 99 (5 x 99)
The order is paid for.
Payment Amount: 159 RUB
Payment ID: Tinkoff Payment: 5060809602

Purchaser information:
Введите_ваш_телеграм_: Pavel
Phone: +79265377051

Additional information:
Transaction ID: 9961889:6682510345
Block ID: rec784210467
Form Name: Cart
https://mm2guns.com/knifes
"""

def test_parse_valid_message():
    result = parse_message(valid_message)
    assert result is not None, "Парсер должен вернуть результат для валидного сообщения"
    assert result['roblox_name'] == "vepe211", "Неверно извлечено имя ROBLOX"
    assert result['transaction_id'] == "9961889", "Неверно извлечен Transaction ID"
    assert len(result['items']) == 1, "Должен быть извлечен один элемент"
    assert result['items'][0]['name'] == "Batwing", "Неверно извлечено название предмета"
    assert result['items'][0]['quantity'] == 159, "Неверно извлечено количество предметов"


def test_parse_invalid_message_no_transaction():
    result = parse_message(invalid_message_no_transaction)
    assert result is None, "Парсер должен вернуть None, если нет Transaction ID"


def test_parse_invalid_message_no_roblox_name():
    result = parse_message(invalid_message_no_roblox_name)
    assert result is None, "Парсер должен вернуть None, если нет ROBLOX имени"

def test_parse_empty_message():
    result = parse_message("")
    assert result is None, "Парсер должен вернуть None для пустого сообщения"