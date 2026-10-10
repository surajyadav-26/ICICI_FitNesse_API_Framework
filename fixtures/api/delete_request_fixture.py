from .base_fixture import BaseRequestFixture, request_columns

class DeleteRequestFixture(BaseRequestFixture):
    """HTTP DELETE fixture extending BaseRequestFixture."""
    DESCRIPTION = "Sends a DELETE request and returns the status code, a JSON value and more."
    COLUMNS = request_columns()
    
    def execute(self) -> bool:
        return self._make_request("DELETE")
