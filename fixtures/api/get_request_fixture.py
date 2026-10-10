from .base_fixture import BaseRequestFixture, request_columns

class GetRequestFixture(BaseRequestFixture):
    """HTTP GET fixture extending BaseRequestFixture."""
    DESCRIPTION = "Sends a GET request and returns the status code, a JSON value and more."
    COLUMNS = request_columns()
    
    def execute(self) -> bool:
        return self._make_request("GET")
