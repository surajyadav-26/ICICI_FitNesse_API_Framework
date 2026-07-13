import html
import json
import importlib
import grpc
from google.protobuf.json_format import Parse, MessageToJson
from core.logger import logger
from .json_utils import extract_json_field

class GrpcRequestFixture:
    """
    FitNesse SLIM Decision Table fixture for testing gRPC APIs dynamically.
    Allows specifying compiled pb2 modules, service stubs, and executing
    requests using standard JSON payloads.
    """
    def __init__(self) -> None:
        self._endpoint: str = ""
        self._pb2_module_name: str = ""
        self._pb2_grpc_module_name: str = ""
        self._service_stub_name: str = ""
        self._method_name: str = ""
        self._request_json: str = "{}"
        self._key: str = ""

        self._executed: bool = False
        self._response_json: dict = {}
        self._response_body: str = ""
        self._response_time_ms: int = 0

    # Setters
    def set_endpoint(self, endpoint: str) -> None:
        self._endpoint = html.unescape(endpoint).strip() if endpoint else ""
        # Validate gRPC endpoint format (typically host:port)
        if not self._endpoint:
            logger.warning("[gRPC] Endpoint is empty. Request will fail.")
        elif ":" not in self._endpoint:
            logger.warning(f"[gRPC] Endpoint should be in format 'host:port': {self._endpoint}")

    def setEndpoint(self, endpoint: str) -> None:
        self.set_endpoint(endpoint)

    def set_pb2_module(self, name: str) -> None:
        self._pb2_module_name = html.unescape(name).strip()

    def setPb2Module(self, name: str) -> None:
        self.set_pb2_module(name)

    def set_pb2_grpc_module(self, name: str) -> None:
        self._pb2_grpc_module_name = html.unescape(name).strip()

    def setPb2GrpcModule(self, name: str) -> None:
        self.set_pb2_grpc_module(name)

    def set_service_stub(self, name: str) -> None:
        self._service_stub_name = html.unescape(name).strip()

    def setServiceStub(self, name: str) -> None:
        self.set_service_stub(name)

    def set_method(self, name: str) -> None:
        self._method_name = html.unescape(name).strip()

    def setMethod(self, name: str) -> None:
        self.set_method(name)

    def set_request_json(self, json_str: str) -> None:
        self._request_json = html.unescape(json_str).strip()

    def setRequestJson(self, json_str: str) -> None:
        self.set_request_json(json_str)

    def set_key(self, key: str) -> None:
        self._key = html.unescape(key).strip()

    def setKey(self, key: str) -> None:
        self.set_key(key)

    # Execution
    def execute(self) -> bool:
        # Validate endpoint before making request
        if not self._endpoint:
            logger.error("[gRPC] Cannot execute request: Endpoint is empty")
            return False
        if ":" not in self._endpoint:
            logger.error(f"[gRPC] Cannot execute request: Invalid endpoint format (expected host:port): {self._endpoint}")
            return False
            
        try:
            logger.info(f"[gRPC] Dynamic invocation: Stub={self._service_stub_name}, Method={self._method_name} on {self._endpoint}")
            
            # 1. Dynamically import modules
            pb2 = importlib.import_module(self._pb2_module_name)
            pb2_grpc = importlib.import_module(self._pb2_grpc_module_name)

            # 2. Get Request message and Stub classes
            # Deduce Request type (typically method name + "Request")
            req_type_name = self._method_name + "Request"
            req_class = getattr(pb2, req_type_name)
            stub_class = getattr(pb2_grpc, self._service_stub_name)

            # 3. Parse JSON request body into Proto Message
            request_message = req_class()
            Parse(self._request_json, request_message)

            # 4. Connect and call service
            import time
            start = time.perf_counter()
            with grpc.insecure_channel(self._endpoint) as channel:
                stub = stub_class(channel)
                grpc_method = getattr(stub, self._method_name)
                # Execute RPC call
                response_message = grpc_method(request_message)
                
            self._response_time_ms = int((time.perf_counter() - start) * 1000)

            # 5. Serialize proto response back to JSON
            response_json_str = MessageToJson(response_message, preserving_proto_field_name=True)
            self._response_body = response_json_str
            self._response_json = json.loads(response_json_str)
            
            logger.info(f"[gRPC] Success in {self._response_time_ms}ms. Response: {self._response_body.strip()}")
            self._executed = True
            return True

        except Exception as e:
            logger.error(f"[gRPC] Invocation failed: {e}")
            self._response_body = f"error: {str(e)}"
            self._response_json = {}
            self._executed = False
            return False

    # Getters / Assertions
    def executed(self) -> bool:
        return self._executed

    def response_body(self) -> str:
        try:
            pretty = json.dumps(self._response_json, indent=2)
            return f"\n{{{{\n{pretty}\n}}}}\n"
        except Exception:
            return f"\n{{{{\n{self._response_body}\n}}}}\n"

    def response_time(self) -> int:
        return self._response_time_ms

    def response_field(self) -> str:
        return extract_json_field(self._response_json, self._key)

    def json_value(self) -> str:
        return self.response_field()
