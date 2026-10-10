from .base_fixture import BaseRequestFixture, request_columns

class OptionsRequestFixture(BaseRequestFixture):
    """HTTP OPTIONS fixture extending BaseRequestFixture."""
    DESCRIPTION = "Sends an OPTIONS request and returns the status code and response headers."
    COLUMNS = request_columns(reads_json=False)
    
    def execute(self) -> bool:
        return self._make_request("OPTIONS")
