import pytest


def pytest_addoption(parser):
    parser.addoption("--live", action="store_true", help="explicitly allow paid DeepSeek calls")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--live"):
        for item in items:
            if "live" in item.keywords:
                item.add_marker(pytest.mark.skip(reason="真实API未启用：使用 --live 且配置 .env"))
