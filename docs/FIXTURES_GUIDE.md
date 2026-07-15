# 📚 Fixtures Guide - ICICI Prudential AML API Framework

Complete reference guide for all Python fixtures available in the framework.

---

## 📑 **Table of Contents**

1. [Base Fixture](#base-fixture)
2. [Auth Fixture](#auth-fixture)
3. [HTTP Method Fixtures](#http-method-fixtures)
4. [OAuth2 Fixture](#oauth2-fixture)
5. [GraphQL Fixture](#graphql-fixture)
6. [WebSocket Fixture](#websocket-fixture)
7. [gRPC Fixture](#grpc-fixture)
8. [Mock Server Fixture](#mock-server-fixture)
9. [JSON Utils](#json-utils)

---

## 🔧 **Base Fixture**

**File:** `fixtures/base_fixture.py`

**Description:** Core HTTP engine inherited by all method-specific fixtures (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS). Handles authentication, headers, timeouts, retries, and response processing.

### **Configuration Methods**

#### **URL Configuration**

```wiki
|set url|https://api.example.com/endpoint|
```

**Validation:**
- Warns if URL doesn't start with http:// or https://
- Strips whitespace automatically

#### **Timeout Configuration**

```wiki
|set timeout|30|
```

**Default:** 15 seconds  
**Range:** 1-300 seconds

#### **Retry Configuration**

```wiki
|set retries|3|
|set retry delay|2.0|
```

**Retry Logic:**
- Retries only on `Timeout` or `ConnectionError`
- Uses exponential backoff: 1s → 2s → 4s → 8s
- Logs each retry attempt

**Example:**
```wiki
!|script|Get Request Fixture|
|set url|https://slow-api.example.com/endpoint|
|set timeout|10|
|set retries|3|
|set retry delay|1.5|
|execute get|
```

#### **SSL Verification**

```wiki
|set ssl verify|false|
```

**Use Cases:**
- Self-signed certificates
- Internal UAT/staging environments
- Development environments

⚠️ **Warning:** Always use `true` in production!

#### **Custom Headers**

```wiki
|add header|Content-Type|application/json|
|add header|X-API-Key|your_api_key|
|add header|X-Custom-Header|custom_value|
```

**Example:**
```wiki
!|script|Post Request Fixture|
|set url|https://api.example.com/data|
|add header|Authorization|Bearer token123|
|add header|X-Request-ID|12345|
|set body json|{"data": "value"}|
|execute post|
```

#### **Body JSON**

```wiki
|set body json|{"key": "value", "nested": {"field": "data"}}|
```

**Supports:**
- Simple objects
- Nested structures
- Arrays
- Special characters (auto-escaped)

#### **File Upload**

```wiki
|set file path|C:\Documents\report.pdf|
```

**Supports:**
- PDF files
- Images (JPG, PNG, GIF)
- Documents (DOC, XLS, TXT)
- Any binary format

**Example:**
```wiki
!|script|Post Request Fixture|
|set url|https://api.example.com/upload|
|set file path|C:\Reports\monthly_report.pdf|
|add header|X-Document-Type|financial_report|
|execute post|
|check|status code|200|
```

### **Response Methods**

#### **Status Code**

```wiki
|check|status code|200|
```

**Supports:**
- Single code: `200`
- Multiple codes: `200,201,204`
- Ranges: `2xx` (future feature)

#### **Response Body**

```wiki
|show|response body|
```

Returns the raw response text.

#### **Response Time**

```wiki
|show|response time ms|
```

Returns latency in milliseconds.

**Example:**
```wiki
!|script|Get Request Fixture|
|set url|https://api.example.com/fast-endpoint|
|execute get|
|check|status code|200|
|ensure|response time ms|<|500|
```

#### **JSON Value Extraction**

```wiki
|check|json value|$.user.name|John Doe|
```

**JSONPath Syntax:**
- `$.field` - Top-level field
- `$.user.name` - Nested field
- `$.users[0].id` - Array element
- `$.data.items[*].status` - Array filter

**Example:**
```wiki
!|script|Get Request Fixture|
|set url|https://api.example.com/user/1|
|execute get|
|check|json value|$.id|1|
|check|json value|$.name|John Doe|
|check|json value|$.email|john@example.com|
|check|json value|$.address.city|New York|
```

---

## 🔐 **Auth Fixture**

**File:** `fixtures/auth_fixture.py`

**Description:** Bearer token authentication with static storage. Tokens are shared across all fixtures in the same test run.

### **Basic Usage**

```wiki
!|script|Auth Fixture|
|set url|https://api.example.com/auth/login|
|set body json|{"username": "admin", "password": "admin123"}|
|execute post|
|set key|$.token|
|store token|
```

### **Complete Authentication Flow**

```wiki
!3 Step 1: Authenticate

!|script|Auth Fixture|
|set url|${BASE_URL}/auth/login|
|set body json|{"username": "admin", "password": "admin123"}|
|execute post|
|check|status code|200|
|set key|$.access_token|
|store token|

!3 Step 2: Use Token in Subsequent Requests

!|script|Get Request Fixture|
|set url|${BASE_URL}/protected/resource|
|execute get|
|check|status code|200|
```

**Note:** Token is automatically injected as `Authorization: Bearer <token>` header.

### **Token Storage**

**Static Storage:** Token is stored in class-level variable and persists across all fixtures.

**Retrieve Token:**
```python
from fixtures import AuthFixture
token = AuthFixture.get_stored_token()
```

---

## 🌐 **HTTP Method Fixtures**

### **GET Request Fixture**

**File:** `fixtures/get_request_fixture.py`

**Usage:**
```wiki
!|script|Get Request Fixture|
|set url|https://api.example.com/users/1|
|execute get|
|check|status code|200|
|check|json value|$.name|John Doe|
```

### **POST Request Fixture**

**File:** `fixtures/post_request_fixture.py`

**Usage:**
```wiki
!|script|Post Request Fixture|
|set url|https://api.example.com/users|
|set body json|{"name": "Jane", "email": "jane@example.com"}|
|execute post|
|check|status code|201|
|check|json value|$.id|exists|
```

### **PUT Request Fixture**

**File:** `fixtures/put_request_fixture.py`

**Usage:**
```wiki
!|script|Put Request Fixture|
|set url|https://api.example.com/users/1|
|set body json|{"name": "John Updated", "email": "john.new@example.com"}|
|execute put|
|check|status code|200|
```

### **PATCH Request Fixture**

**File:** `fixtures/patch_request_fixture.py`

**Usage:**
```wiki
!|script|Patch Request Fixture|
|set url|https://api.example.com/users/1|
|set body json|{"email": "john.updated@example.com"}|
|execute patch|
|check|status code|200|
```

### **DELETE Request Fixture**

**File:** `fixtures/delete_request_fixture.py`

**Usage:**
```wiki
!|script|Delete Request Fixture|
|set url|https://api.example.com/users/1|
|execute delete|
|check|status code|204|
```

### **HEAD Request Fixture**

**File:** `fixtures/head_request_fixture.py`

**Usage:**
```wiki
!|script|Head Request Fixture|
|set url|https://api.example.com/large-file.zip|
|execute head|
|check|status code|200|
|set header lookup|Content-Length|
|show|header value|
```

### **OPTIONS Request Fixture**

**File:** `fixtures/options_request_fixture.py`

**Usage:**
```wiki
!|script|Options Request Fixture|
|set url|https://api.example.com/endpoint|
|execute options|
|check|status code|200|
|set header lookup|Allow|
|show|header value|
```

---

## 🔑 **OAuth2 Fixture**

**File:** `fixtures/oauth2_fixture.py`

**Description:** OAuth2 authentication with support for 4 grant types.

### **Grant Type 1: Client Credentials**

**Use Case:** Machine-to-machine authentication

```wiki
!|script|OAuth2 Fixture|
|set token url|https://oauth.example.com/token|
|set client id|my_app_client_id|
|set client secret|my_app_secret|
|set grant type|client_credentials|
|get token|
|check|is token expired|false|
```

### **Grant Type 2: Password**

**Use Case:** User authentication with username/password

```wiki
!|script|OAuth2 Fixture|
|set token url|https://oauth.example.com/token|
|set client id|my_app_client_id|
|set client secret|my_app_secret|
|set username|john.doe|
|set password|secret123|
|set grant type|password|
|get token|
```

### **Grant Type 3: Authorization Code**

**Use Case:** Web application flow

```wiki
!|script|OAuth2 Fixture|
|set token url|https://oauth.example.com/token|
|set client id|my_app_client_id|
|set client secret|my_app_secret|
|set authorization code|AUTH_CODE_FROM_CALLBACK|
|set grant type|authorization_code|
|get token|
```

### **Grant Type 4: Refresh Token**

**Use Case:** Token renewal without re-authentication

```wiki
!|script|OAuth2 Fixture|
|set token url|https://oauth.example.com/token|
|set client id|my_app_client_id|
|set client secret|my_app_secret|
|set refresh token|REFRESH_TOKEN_VALUE|
|set grant type|refresh_token|
|get token|
```

### **Using OAuth2 Token in Requests**

```wiki
!3 Step 1: Get OAuth2 Token

!|script|OAuth2 Fixture|
|set token url|https://oauth.example.com/token|
|set client id|client123|
|set client secret|secret456|
|set grant type|client_credentials|
|get token|

!3 Step 2: Use Token

!|script|Get Request Fixture|
|set url|https://api.example.com/protected|
|set use oauth2|true|
|execute get|
|check|status code|200|
```

### **Token Expiry Checking**

```wiki
!|script|OAuth2 Fixture|
|check|is token expired|false|
```

**Auto-refresh:**
```wiki
!|script|OAuth2 Fixture|
|refresh access token|
```

---

## 📊 **GraphQL Fixture**

**File:** `fixtures/graphql_fixture.py`

**Description:** GraphQL query and mutation testing with variable support.

### **Simple Query**

```wiki
!|script|GraphQL Fixture|
|set url|https://api.example.com/graphql|
|set query|{ user(id: "1") { name email } }|
|execute|
|check|has errors|false|
|check|json value|data.user.name|John Doe|
```

### **Query with Variables**

```wiki
!|script|GraphQL Fixture|
|set url|https://api.example.com/graphql|
|set query|query GetUser($userId: ID!) { user(id: $userId) { name email age } }|
|set variables|{"userId": "1"}|
|execute|
|check|has errors|false|
|check|json value|data.user.name|John Doe|
|check|json value|data.user.age|30|
```

### **Mutation**

```wiki
!|script|GraphQL Fixture|
|set url|https://api.example.com/graphql|
|set query|mutation CreateUser($name: String!, $email: String!) { createUser(name: $name, email: $email) { id name email } }|
|set variables|{"name": "Jane Doe", "email": "jane@example.com"}|
|execute|
|check|has errors|false|
|check|json value|data.createUser.id|exists|
```

### **With Authentication**

```wiki
!|script|GraphQL Fixture|
|set url|https://api.example.com/graphql|
|set use oauth2|true|
|set query|{ me { name email } }|
|execute|
|check|has errors|false|
```

### **Error Handling**

```wiki
!|script|GraphQL Fixture|
|set url|https://api.example.com/graphql|
|set query|{ invalid_query }|
|execute|
|check|has errors|true|
```

---

## 🔌 **WebSocket Fixture**

**File:** `fixtures/websocket_fixture.py`

**Description:** WebSocket client for real-time bidirectional communication testing.

### **Basic Usage**

```wiki
!|script|WebSocket Fixture|
|connect|ws://echo.websocket.org|
|send|Hello WebSocket|
|show|receive|
|close|
```

### **Secure WebSocket (WSS)**

```wiki
!|script|WebSocket Fixture|
|connect|wss://secure.websocket.org|
|send|{"type": "ping"}|
|show|receive|
|close|
```

### **Complete Flow**

```wiki
!3 WebSocket Chat Test

!|script|WebSocket Fixture|
|connect|ws://chat.example.com/socket|
|send|{"action": "join", "room": "general"}|
|show|receive|
|send|{"action": "message", "text": "Hello World"}|
|show|receive|
|send|{"action": "leave"}|
|close|
```

---

## 🚀 **gRPC Fixture**

**File:** `fixtures/grpc_request_fixture.py`

**Description:** gRPC client for testing Protocol Buffer-based services.

### **Basic Usage**

```wiki
!|script|gRPC Request Fixture|
|set server url|localhost:50051|
|set proto file|protos/service.proto|
|set service name|UserService|
|set method name|GetUser|
|set request json|{"user_id": "1"}|
|execute|
|check|status code|OK|
|check|response field|name|John Doe|
```

### **With Metadata**

```wiki
!|script|gRPC Request Fixture|
|set server url|api.example.com:443|
|set proto file|protos/service.proto|
|set service name|OrderService|
|set method name|CreateOrder|
|add metadata|authorization|Bearer token123|
|add metadata|x-request-id|req-12345|
|set request json|{"product_id": "P001", "quantity": 2}|
|execute|
|check|status code|OK|
```

---

## 🎭 **Mock Server Fixture**

**File:** `fixtures/mock_server_fixture.py`

**Description:** Embedded HTTP server on port 8089 for offline testing.

### **Starting Mock Server**

```wiki
!|script|Mock Server Fixture|
|start|
|check|is running|true|
```

### **Using Mock Server**

```wiki
!3 Setup: Start Mock Server

!|script|Mock Server Fixture|
|start|

!3 Test: GET Request to Mock

!|script|Get Request Fixture|
|set url|http://localhost:8089/mock/users|
|execute get|
|check|status code|200|

!3 Teardown: Stop Mock Server

!|script|Mock Server Fixture|
|stop|
```

### **Automatic Management**

In `SuiteSetUp`:
```wiki
!|script|Mock Server Fixture|
|start|
```

In `SuiteTearDown`:
```wiki
!|script|Mock Server Fixture|
|stop|
```

---

## 🛠️ **JSON Utils**

**File:** `fixtures/json_utils.py`

**Description:** JSONPath extraction utilities with error handling.

### **Direct Usage in Python**

```python
from fixtures.json_utils import extract_json_field

response_json = {"user": {"name": "John", "age": 30}}

# Extract simple field
name = extract_json_field(response_json, "$.user.name")  # Returns: "John"

# Extract nested field
age = extract_json_field(response_json, "$.user.age")  # Returns: 30

# Invalid path (returns None)
invalid = extract_json_field(response_json, "$.invalid.path")  # Returns: None
```

### **JSONPath Patterns**

| Pattern | Description | Example |
|---------|-------------|---------|
| `$.field` | Root level field | `$.name` |
| `$.a.b.c` | Nested field | `$.user.address.city` |
| `$[0]` | Array index | `$.users[0]` |
| `$[*]` | All array elements | `$.users[*].name` |
| `$..field` | Recursive descent | `$..email` |

---

## 📝 **Best Practices**

### **1. Use Variables**

```wiki
!define BASE_URL {https://api.example.com}
!define API_KEY {your_api_key_here}

!|script|Get Request Fixture|
|set url|${BASE_URL}/users|
|add header|X-API-Key|${API_KEY}|
|execute get|
```

### **2. Organize Tests in Suites**

```
FrontPage/
  MyAPISuite/
    SuiteSetUp.wiki        # Start mock server, authenticate
    Test01_GetUsers.wiki
    Test02_CreateUser.wiki
    Test03_UpdateUser.wiki
    Test04_DeleteUser.wiki
    SuiteTearDown.wiki     # Stop mock server, cleanup
```

### **3. Use Descriptive Names**

✅ Good: `Test01_UserRegistration_ValidData`  
❌ Bad: `Test1`

### **4. Add Comments**

```wiki
!3 Test: User Registration with Valid Data
!note This test validates the user registration endpoint with all required fields.

!|script|Post Request Fixture|
|set url|${BASE_URL}/register|
|set body json|{"name": "John", "email": "john@example.com"}|
|execute post|
|check|status code|201|
```

### **5. Handle Errors Gracefully**

```wiki
!|script|Get Request Fixture|
|set url|${BASE_URL}/may-fail|
|set timeout|10|
|set retries|3|
|execute get|
|ensure|status code|200,500,503|  # Accept multiple codes
```

---

## 🔍 **Debugging Tips**

### **View Full Response**

```wiki
!|script|Get Request Fixture|
|set url|${BASE_URL}/endpoint|
|execute get|
|show|response body|
```

### **Check Response Time**

```wiki
!|script|Get Request Fixture|
|set url|${BASE_URL}/endpoint|
|execute get|
|show|response time ms|
```

### **Inspect Headers**

```wiki
!|script|Get Request Fixture|
|set url|${BASE_URL}/endpoint|
|execute get|
|set header lookup|Content-Type|
|show|header value|
```

### **Enable Verbose Logging**

Check `logs/framework.log.*` for detailed request/response logs.

---

## ✅ **Checklist**

- [ ] Understand Base Fixture methods
- [ ] Know how to use Auth Fixture
- [ ] Practiced HTTP method fixtures (GET, POST, etc.)
- [ ] Tested OAuth2 authentication
- [ ] Tried GraphQL queries
- [ ] Used WebSocket fixture
- [ ] Configured timeout and retries
- [ ] Handled SSL verification
- [ ] Used custom headers
- [ ] Extracted JSON values with JSONPath

---

**📚 For more information, see:**
- [README.md](README.md) - Framework overview
- [GETTING_STARTED.md](GETTING_STARTED.md) - Quick start guide

**Happy Testing! 🚀**
