"""HTTP / API fixtures. In a wiki page: `| import |` / `| fixtures.api |`, then e.g. `| get request fixture |`."""
from importlib import import_module

_FIXTURE_MODULES = {
    "AuthFixture": "auth_fixture",
    "GetRequestFixture": "get_request_fixture",
    "PostRequestFixture": "post_request_fixture",
    "PutRequestFixture": "put_request_fixture",
    "PatchRequestFixture": "patch_request_fixture",
    "DeleteRequestFixture": "delete_request_fixture",
    "HeadRequestFixture": "head_request_fixture",
    "OptionsRequestFixture": "options_request_fixture",
    "MockServerFixture": "mock_server_fixture",
    "WebSocketFixture": "websocket_fixture",
    "GrpcRequestFixture": "grpc_request_fixture",
    "OAuth2Fixture": "oauth2_fixture",
    "GraphQLFixture": "graphql_fixture",
}

__all__ = list(_FIXTURE_MODULES)


def __getattr__(name: str):
    module_name = _FIXTURE_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    fixture_class = getattr(import_module(f".{module_name}", __name__), name)
    globals()[name] = fixture_class
    return fixture_class
