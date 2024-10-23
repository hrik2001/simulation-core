from typing import Any
from pydantic import BaseModel


class Base(BaseModel):
    def __pre_init__(self, args: Any) -> None:
        """
        This is executed before the initialization of the model
        """

    def __post_init__(self) -> None:
        """
        This is executed before the initialization of the model
        """

    def __init__(self, **payload):
        self.__pre_init__(payload)
        super().__init__(**payload)
        self.__post_init__()

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"
