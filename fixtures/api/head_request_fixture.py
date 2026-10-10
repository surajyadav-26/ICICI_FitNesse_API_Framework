from .base_fixture import BaseRequestFixture, request_columns

class HeadRequestFixture(BaseRequestFixture):
    """HTTP HEAD fixture extending BaseRequestFixture."""
    DESCRIPTION = "Sends a HEAD request and returns the status code and response headers."
    COLUMNS = request_columns(reads_json=False)
    
    def execute(self) -> bool:
        return self._make_request("HEAD")
