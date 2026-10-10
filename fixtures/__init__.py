"""
Fixtures, grouped by area:

    fixtures/ui/             browser fixtures: UiFixture, column-table fixtures, scenario folders such as ui/scenario/login
    fixtures/api/            HTTP / auth / GraphQL / gRPC / WebSocket fixtures
    fixtures/visual/         visual-testing fixtures (comparison engine lives in core/visual_compare.py)
    fixtures/accessibility/  accessibility fixtures

Shared, non-fixture code lives in core/ (flow engine, json helpers, reports, locators).
This module re-exports the fixture classes by their short names (``fixtures.UiFixture``) for WaferSlim's
``fixtures`` type prefix, so existing wiki pages keep working.
"""
import os
from importlib import import_module

_FIXTURE_MODULES = {
    "AuthFixture": "api.auth_fixture",
    "GetRequestFixture": "api.get_request_fixture",
    "PostRequestFixture": "api.post_request_fixture",
    "PutRequestFixture": "api.put_request_fixture",
    "PatchRequestFixture": "api.patch_request_fixture",
    "DeleteRequestFixture": "api.delete_request_fixture",
    "HeadRequestFixture": "api.head_request_fixture",
    "OptionsRequestFixture": "api.options_request_fixture",
    "MockServerFixture": "api.mock_server_fixture",
    "WebSocketFixture": "api.websocket_fixture",
    "GrpcRequestFixture": "api.grpc_request_fixture",
    "OAuth2Fixture": "api.oauth2_fixture",
    "GraphQLFixture": "api.graphql_fixture",
    "UiFixture": "ui.ui_fixture",
    "SuiteHelper": "ui.suite_helper",
    "AccessibilityFixture": "accessibility.accessibility_fixture",
}

__all__ = list(_FIXTURE_MODULES)


def __getattr__(name: str):
    module_name = _FIXTURE_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    fixture_class = getattr(import_module(f".{module_name}", __name__), name)
    globals()[name] = fixture_class
    return fixture_class


def fixture_packages() -> list:
    """Every package under fixtures/ (``fixtures``, ``fixtures.ui.scenario.login``, ...). The Slim runner searches them all, so
    a wiki page needs no ``import`` table."""
    root = os.path.dirname(os.path.abspath(__file__))
    found = [__name__]
    for folder, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not d.startswith(("__", ".")))
        if folder != root and "__init__.py" in files:
            found.append(__name__ + "." + os.path.relpath(folder, root).replace(os.sep, "."))
    return found
