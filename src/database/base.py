from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from src.accounts.models import (  # noqa: E402, F401
    ActivationToken,
    User,
    UserGroup,
)
