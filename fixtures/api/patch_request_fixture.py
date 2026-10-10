from .base_fixture import BaseRequestFixture, request_columns

class PatchRequestFixture(BaseRequestFixture):
    """HTTP PATCH fixture extending BaseRequestFixture."""
    DESCRIPTION = "Sends a PATCH request with a JSON body and returns the status code, a JSON value and more."
    COLUMNS = request_columns(has_body=True)
    
    def execute(self) -> bool:
        return self._make_request("PATCH")
