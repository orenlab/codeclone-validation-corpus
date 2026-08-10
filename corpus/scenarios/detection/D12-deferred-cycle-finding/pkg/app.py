# mypy: ignore-errors

from pkg.a import ServiceA

RESULT = ServiceA().call_peer([1, 2, 3])
