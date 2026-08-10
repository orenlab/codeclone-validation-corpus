# mypy: ignore-errors


class ServiceB:
    def __init__(self) -> None:
        self.label = "b"

    def handle(self, values: list[int]) -> tuple[str, int]:
        from pkg.a import ServiceA

        return ServiceA().label, len(values)
