
from sqlalchemy.types import TypeDecorator, String
from decimal import Decimal

class DecimalType(TypeDecorator):
    impl = String

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return Decimal(value)
        return value
