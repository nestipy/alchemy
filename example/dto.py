from dataclasses import dataclass


@dataclass
class CreateUserDto:
    email: str
    name: str
    password: str
