import eje_cafetero_api


def test_package_importable():
    assert eje_cafetero_api is not None


def test_deliberately_broken_for_ci_verification():
    """Temporary: proves the CI workflow fails a broken test. Reverted after verification (#14)."""
    assert False
