# mypy: ignore-errors


class ServiceA:
    def __init__(self) -> None:
        self.label = "a"

    def call_peer(self, values: list[int]) -> tuple[str, int]:
        from pkg.b import ServiceB

        return ServiceB().handle(values)
