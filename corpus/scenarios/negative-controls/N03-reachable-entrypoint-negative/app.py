def helper_used() -> int:
    return 1


def app() -> int:
    return helper_used()


if __name__ == "__main__":
    raise SystemExit(app())
