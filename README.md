# 🏦 ICICI Prudential AML API Test Automation Framework v2.0

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FitNesse](https://img.shields.io/badge/FitNesse-Standalone-green.svg)](http://fitnesse.org/)
[![License](https://img.shields.io/badge/License-Enterprise-red.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)](README.md)

Enterprise-grade REST API testing framework for ICICI Prudential AML & Compliance Systems. Built on FitNesse SLIM with Python 3.10+ fixtures, featuring OAuth2, GraphQL, WebSocket, gRPC support, and comprehensive CI/CD automation.

---

## 📋 **Table of Contents**

- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Usage Guide](#-usage-guide)
- [Fixtures Reference](#-fixtures-reference)
- [CI/CD Integration](#-cicd-integration)
- [Security](#-security)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

---

## ✨ **Features**

### **Core Capabilities**
- ✅ **13 HTTP Method Fixtures**: GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS + specialized fixtures
- ✅ **OAuth2 Authentication**: 4 grant types (client_credentials, password, authorization_code, refresh_token)
- ✅ **GraphQL Support**: Queries, mutations, variables, error handling
- ✅ **WebSocket Testing**: ws:// and wss:// protocol support
- ✅ **gRPC Support**: Protocol Buffers compatibility
- ✅ **Mock Server**: Embedded HTTP server (port 8089) for offline testing
- ✅ **Multi-Environment**: Dynamic switching (Dev/QA/UAT/Prod)
- ✅ **Custom Reports**: HTML reports with pass/fail metrics and history

### **Enterprise Features**
- ✅ **Retry Mechanism**: Exponential backoff (1s→2s→4s→8s) on network failures
- ✅ **Configurable Timeout**: Default 15s, adjustable per request
- ✅ **URL Validation**: Pre-execution checks with warnings
- ✅ **SSL Verification Control**: Bypass self-signed certificates
- ✅ **Response Header Inspection**: Validate tokens, content-types, CORS
- ✅ **File Upload Support**: Multipart form-data for PDFs, images
- ✅ **cURL Logging**: Auto-generate curl commands for debugging
- ✅ **Daily Log Rotation**: 7-day retention with structured logging

### **UI/UX Enhancements** 🎨
- ✅ **Custom ICICI Branding**: Official logos, colors (#C23029 red, #053C6D blue)
- ✅ **Role-Based Access**: Admin, Editor, and Viewer roles
- ✅ **Fixed Header Navigation**: Stays at top while scrolling
- ✅ **Loading Indicators**: Visual feedback during test execution
- ✅ **Environment Selector**: Quick switching with persistent storage
- ✅ **Responsive Design**: Desktop-optimized with mobile support

### **🆕 Latest UX Improvements** (v2.1 - July 2026)
- ✅ **Smart Cancel Buttons**: 
  - Automatically detects form changes
  - No confirmation prompt for empty forms
  - Works across all FitNesse pages
- ✅ **Context-Aware Radio Defaults**:
  - Creating new page → Suite selected by default
  - Adding child to suite → Test selected by default
  - Skips auto-selection on properties page (preserves current type)
- ✅ **Universal Theme Application**:
  - MutationObserver monitors dynamic content
  - Auto-applies ICICI styling to new elements
  - Consistent branding everywhere
- ✅ **Enhanced Environment Management**:
  - Console logging for delete/save operations
  - Persistent storage with localStorage
  - Visual feedback for all changes
- ✅ **Developer Console Integration**:
  - RED banner on successful load
  - Detailed debugging messages
  - Easy troubleshooting

### **CI/CD Automation**
- ✅ **GitHub Actions**: Auto-trigger on push/PR, scheduled runs, manual dispatch
- ✅ **GitHub Actions**: unit tests, suite run, quality gate and reports on every push (`.github/workflows/automation-tests.yml`)
- ✅ **Multi-Environment**: Dev/Staging/UAT/Prod support
- ✅ **Artifact Archiving**: Test results saved for 30 days

---

## 🏗️ **Architecture**

```
ICICI_FitNesseAPIFramework/
│
├── start_server.bat              # Quick launcher (kills conflicts, starts server)
├── requirements.txt              # Python dependencies
├── plugins.properties            # FitNesse configuration
├── data/users.json               # Canonical UI and FitNesse user store
├── fitnesse-standalone.jar       # FitNesse engine
├── .gitignore                    # Security exclusions
│
├── fixtures/                     # Python SLIM Fixtures (15 files)
│   ├── __init__.py               # Package exports
│   ├── base_fixture.py           # Core HTTP engine (16KB)
│   ├── auth_fixture.py           # Bearer token auth (12KB)
│   ├── oauth2_fixture.py         # OAuth2 4 grant types (12KB)
│   ├── graphql_fixture.py        # GraphQL queries/mutations (9KB)
│   ├── get_request_fixture.py    # GET requests
│   ├── post_request_fixture.py   # POST requests
│   ├── put_request_fixture.py    # PUT requests
│   ├── patch_request_fixture.py  # PATCH requests
│   ├── delete_request_fixture.py # DELETE requests
│   ├── head_request_fixture.py   # HEAD requests
│   ├── options_request_fixture.py# OPTIONS requests
│   ├── websocket_fixture.py      # WebSocket client (4KB)
│   ├── grpc_request_fixture.py   # gRPC client (6KB)
│   ├── mock_server_fixture.py    # Mock HTTP server (5KB)
│   └── json_utils.py             # JSONPath utilities (2KB)
│
├── core/                         # Framework Core
│   ├── logger.py                 # Structured logging (daily rotation)
│   ├── fitnesse_watcher.py       # File sync watcher
│   └── report_generator.py       # HTML report builder
│
├── FitNesseRoot/                 # Wiki Content
│   ├── FrontPage/                # Dashboard (content.txt)
│   ├── PageHeader/               # Global header (615+ lines)
│   ├── ApiTests.wiki             # Test suite entry
│   └── files/                    # Static assets
│       ├── report.html           # Test report viewer
│       ├── report_history.json   # Historical data
│       └── fitnesse/icici/       # ICICI theme files
│           ├── img/icici-logo.png
│           ├── img/icici-favicon.ico (official)
│           └── templates/skeleton.vm
│
├── logs/                         # Execution Logs
│   └── framework.log.YYYY-MM-DD
│
├── .github/workflows/            # GitHub Actions
│   └── api-tests.yml             # CI/CD workflow (238 lines)
│
```

---

## 🚀 **Quick Start**

### **1. Prerequisites**
- Python 3.10+ ([Download](https://www.python.org/downloads/))
- Java 17+ ([Download](https://www.oracle.com/java/technologies/downloads/))
- Allure Commandline (required to generate the browsable Allure HTML report)
- Git (for cloning)

### **2. Clone Repository**
```bash
git clone <repository-url>
cd ICICI_FitNesseAPIFramework
```

### **3. Install Dependencies**
```powershell
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.\.venv\Scripts\activate

# Install packages
pip install -r requirements.txt

# Install browser runtime for Playwright UI tests
python -m playwright install chromium
```

Run the focused framework checks with `python -m pytest tests/unit`. The GitHub Actions workflow installs the
dependencies from `requirements.txt` and runs the selected FitNesse suite; public connectivity smoke pages should be
selected only when network access is available.

### **4. Start Server**
```powershell
.\start_server.bat
```

### **5. Access Framework**
1. Open browser: `http://localhost:8080`
2. **Login Credentials:**
   - Username: `admin`
   - Password: `admin123`
3. Click **▶ Run** to execute tests

---

## 📦 **Installation**

### **Detailed Setup**

#### **Step 1: Install Python 3.10+**
```powershell
# Verify Python installation
python --version
# Expected: Python 3.10.x or higher

# Verify pip
pip --version
```

#### **Step 2: Install Java 17+**
```powershell
# Verify Java installation
java -version
# Expected: openjdk version "17" or higher
```

#### **Step 3: Setup Virtual Environment**
```powershell
# Navigate to project directory
cd C:\ICICI_FitNesseAPIFramework

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip
```

#### **Step 4: Install Dependencies**
```powershell
# Install all required packages
pip install -r requirements.txt

# Verify installations
pip list
```

#### **Step 5: Verify FitNesse JAR**
```powershell
# Check if JAR exists
Test-Path fitnesse-standalone.jar
# Should return: True

# Check JAR size (should be ~10-15 MB)
(Get-Item fitnesse-standalone.jar).Length / 1MB
```

---

## 📖 **Usage Guide**

### **Creating Your First Test**

#### **Example 1: Simple GET Request**

1. Navigate to `FrontPage` → Click **+ Add Test**
2. Create test page: `MyFirstTest`
3. Add this content:

```wiki
!define TEST_SYSTEM {slim}

!|import|
|fixtures|

!|script|Get Request Fixture|
|set url|https://jsonplaceholder.typicode.com/posts/1|
|execute get|
|check|status code|200|
|check|json value|userId|1|
```

4. Click **Test** button to run

#### **Example 2: POST Request with Body**

```wiki
!|script|Post Request Fixture|
|set url|https://jsonplaceholder.typicode.com/posts|
|set body json|{"title": "foo", "body": "bar", "userId": 1}|
|execute post|
|check|status code|201|
|check|json value|id|101|
```

#### **Example 3: OAuth2 Authentication**

```wiki
!|script|OAuth2 Fixture|
|set token url|https://oauth.example.com/token|
|set client id|my_client_id|
|set client secret|my_client_secret|
|set grant type|client_credentials|
|get token|
|check|is token expired|false|

!|script|Get Request Fixture|
|set url|https://api.example.com/protected|
|set use oauth2|true|
|execute get|
|check|status code|200|
```

#### **Example 4: GraphQL Query**

```wiki
!|script|GraphQL Fixture|
|set url|https://api.example.com/graphql|
|set query|query { user(id: "1") { name email } }|
|execute|
|check|has errors|false|
|check|json value|data.user.name|John Doe|
```

### **Configuration**

#### **Timeout & Retry Settings**

```wiki
!|script|Get Request Fixture|
|set url|https://slow-api.example.com/endpoint|
|set timeout|30|
|set retries|3|
|set retry delay|2.0|
|execute get|
```

#### **SSL Verification (Self-Signed Certs)**

```wiki
!|script|Get Request Fixture|
|set url|https://internal-api.company.local/endpoint|
|set ssl verify|false|
|execute get|
```

#### **Custom Headers**

```wiki
!|script|Post Request Fixture|
|set url|https://api.example.com/endpoint|
|add header|Content-Type|application/json|
|add header|X-Custom-Header|custom-value|
|set body json|{"key": "value"}|
|execute post|
```

#### **File Upload**

```wiki
!|script|Post Request Fixture|
|set url|https://api.example.com/upload|
|set file path|C:\Documents\report.pdf|
|execute post|
|check|status code|200|
```

### **Environment Management**

#### **Via UI:**
1. Click **⚙️** next to Env dropdown in header
2. Click **Add Environment** row
3. Enter: `STAGING` and `https://staging-api.example.com`
4. Click **Save Changes**
5. Select from dropdown to switch

#### **Via LocalStorage (Browser Console):**
```javascript
// Get current environments
localStorage.getItem('ici_test_envs')

// Set new environment
const envs = [
  {name: 'DEV', url: 'https://dev-api.example.com'},
  {name: 'QA', url: 'https://qa-api.example.com'},
  {name: 'UAT', url: 'https://uat-api.example.com'},
  {name: 'PROD', url: 'https://api.example.com'}
];
localStorage.setItem('ici_test_envs', JSON.stringify(envs));
```

---

## 🔧 **Fixtures Reference**

### **Base Fixture** (`base_fixture.py`)

**Core HTTP engine inherited by all method fixtures.**

| Method | Description | Parameters |
|--------|-------------|------------|
| `setUrl(url)` | Set request URL | String (HTTP/HTTPS) |
| `setTimeout(seconds)` | Set timeout | Integer (default: 15) |
| `setRetries(count)` | Set max retries | Integer (default: 0) |
| `setRetryDelay(seconds)` | Set retry delay | Float (default: 1.0) |
| `setSslVerify(bool)` | Enable/disable SSL | Boolean (default: true) |
| `addHeader(key, value)` | Add custom header | String, String |
| `setBodyJson(json)` | Set JSON body | String (JSON) |
| `setFilePath(path)` | Set file for upload | String (path) |
| `statusCode()` | Get response code | Returns Integer |
| `responseBody()` | Get response text | Returns String |
| `responseTimeMs()` | Get latency | Returns Integer |
| `jsonValue(key)` | Extract JSON field | String (JSONPath) |

### **Auth Fixture** (`auth_fixture.py`)

**Bearer token authentication with static storage.**

| Method | Description |
|--------|-------------|
| `setUrl(url)` | Set auth endpoint |
| `setBodyJson(json)` | Set login credentials |
| `executePost()` | Send auth request |
| `setKey(path)` | Set token JSONPath |
| `storeToken()` | Save token globally |
| `getStoredToken()` | Retrieve token (static) |

**Example:**
```wiki
!|script|Auth Fixture|
|set url|https://api.example.com/auth/login|
|set body json|{"username": "admin", "password": "pass123"}|
|execute post|
|set key|$.token|
|store token|
```

### **OAuth2 Fixture** (`oauth2_fixture.py`)

**OAuth2 authentication with 4 grant types.**

| Method | Description |
|--------|-------------|
| `setTokenUrl(url)` | Set token endpoint |
| `setClientId(id)` | Set client ID |
| `setClientSecret(secret)` | Set client secret |
| `setUsername(user)` | Set username (password grant) |
| `setPassword(pass)` | Set password (password grant) |
| `setGrantType(type)` | Grant type: client_credentials, password, authorization_code, refresh_token |
| `getToken()` | Request access token |
| `refreshAccessToken()` | Refresh using refresh_token |
| `isTokenExpired()` | Check token expiry |

**Example:**
```wiki
!|script|OAuth2 Fixture|
|set token url|https://oauth.example.com/token|
|set client id|my_app_client|
|set client secret|secret123|
|set grant type|client_credentials|
|get token|
|check|is token expired|false|
```

### **GraphQL Fixture** (`graphql_fixture.py`)

**GraphQL query and mutation testing.**

| Method | Description |
|--------|-------------|
| `setUrl(url)` | Set GraphQL endpoint |
| `setQuery(query)` | Set GraphQL query/mutation |
| `setVariables(json)` | Set query variables |
| `setOperationName(name)` | Set operation name |
| `setUseOauth2(bool)` | Use OAuth2 token |
| `execute()` | Send GraphQL request |
| `hasErrors()` | Check for errors |
| `jsonValue(path)` | Extract from data |

**Example:**
```wiki
!|script|GraphQL Fixture|
|set url|https://api.example.com/graphql|
|set query|mutation CreateUser($name: String!) { createUser(name: $name) { id name } }|
|set variables|{"name": "John Doe"}|
|execute|
|check|has errors|false|
|check|json value|data.createUser.id|12345|
```

### **WebSocket Fixture** (`websocket_fixture.py`)

**WebSocket client for real-time testing.**

| Method | Description |
|--------|-------------|
| `connect(url)` | Connect to WebSocket |
| `send(message)` | Send message |
| `receive()` | Receive message |
| `close()` | Close connection |

### **Mock Server Fixture** (`mock_server_fixture.py`)

**Embedded HTTP server on port 8089.**

| Method | Description |
|--------|-------------|
| `start()` | Start mock server |
| `stop()` | Stop mock server |
| `isRunning()` | Check status |

---

## 🔄 **CI/CD Integration**

### **GitHub Actions**

**File:** `.github/workflows/api-tests.yml`

**Triggers:**
- ✅ Push to `main` or `develop` branches
- ✅ Pull requests to `main` or `develop`
- ✅ Scheduled: Daily at 2 AM UTC
- ✅ Manual dispatch with environment selection

**Usage:**
```bash
# Automatic trigger on push
git push origin main

# Manual trigger via GitHub UI
# Actions → FitNesse API Test Suite → Run workflow
# Select environment: dev/staging/uat
```

**Configuration:**
```yaml
name: FitNesse API Test Suite

on:
  push:
    branches: [ main, develop ]
  schedule:
    - cron: '0 2 * * *'
  workflow_dispatch:
    inputs:
      environment:
        type: choice
        options: [dev, staging, uat]
```

### **CI**

CI is GitHub Actions only; see the *CI* section near the end of this file. There is no Jenkins pipeline.

---

## 🔒 **Security**

### **Credentials Management**

**UI Application Roles:**
| Role | Username | Password | Permissions |
|------|----------|----------|-------------|
| Admin | `admin` | `admin123` | Full access, including Users |
| Editor | `editor` | `editor123` | Home, run, report, history, edit, add, and delete |
| Viewer | `viewer` | `viewer123` | Home, run, report, and history only |

Users can be added, edited, or deleted by an Admin from the **Users** option in the profile dropdown. The canonical UI user store is [data/users.json](data/users.json). The local user-store service serves and updates this file on `127.0.0.1:8090`; browser `localStorage` under `nirikshan_users` is retained only as a fallback cache.

**FitNesse Server Authentication:**
The application uses `data/users.json` for its Admin, Editor, and Viewer roles. `start_server.bat` starts FitNesse without the separate `passwords.txt` Basic Auth gate, so the UI role model controls the visible and permitted workflows. The root-level `passwords.txt` file is no longer required.

### **Sensitive Files Protection**

**`.gitignore` includes:**
```
passwords.txt
credentials.txt
*.key
*.pem
*.cert
.env
.env.local
```

**⚠️ NEVER commit:**
- API keys
- OAuth client secrets
- Database passwords
- Private keys

### **SSL/TLS**

For production, use SSL verification:
```wiki
!|script|Get Request Fixture|
|set url|https://api.example.com|
|set ssl verify|true|  # Always true in production
|execute get|
```

---

## 🐛 **Troubleshooting**

### **Common Issues**

#### **Issue 1: Port 8080 Already in Use**
```powershell
# Find process using port 8080
netstat -ano | findstr :8080

# Kill process
taskkill /F /PID <process_id>

# Or use start_server.bat (auto-kills)
.\start_server.bat
```

#### **Issue 2: Python Not Found**
```powershell
# Add Python to PATH
# Control Panel → System → Advanced → Environment Variables
# Add: C:\Python310 and C:\Python310\Scripts
```

#### **Issue 3: Module Not Found**
```powershell
# Activate virtual environment
.\.venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### **Issue 4: Favicon Not Showing**
```powershell
# Clear browser cache
# Chrome: Ctrl + Shift + Delete
# Select: Cached images and files
# Time range: All time
# Then hard refresh: Ctrl + F5
```

#### **Issue 5: Tests Failing with Timeout**
```wiki
# Increase timeout in test
!|script|Get Request Fixture|
|set timeout|60|  # 60 seconds
|set retries|5|
```

### **Logs Location**

**Framework Logs:**
```
logs/framework.log.2026-07-13
```

**FitNesse Logs:**
```
# Console output when running start_server.bat
```

**View Logs:**
```powershell
# Tail latest log
Get-Content logs\framework.log.* -Tail 50 -Wait

# Search for errors
Select-String -Path logs\framework.log.* -Pattern "ERROR"
```

---

## 🤝 **Contributing**

### **Development Workflow**

1. **Create Feature Branch**
```bash
git checkout -b feature/new-fixture
```

2. **Make Changes**
- Add new fixture in `fixtures/`
- Update `fixtures/__init__.py` exports
- Add tests in `FitNesseRoot/`

3. **Test Locally**
```powershell
.\start_server.bat
# Test your changes at http://localhost:8080
```

4. **Commit & Push**
```bash
git add .
git commit -m "feat: add new fixture for XYZ"
git push origin feature/new-fixture
```

5. **Create Pull Request**
- Describe changes
- Link related issues
- Request review

### **Code Standards**

- ✅ Python: PEP 8 compliant
- ✅ Docstrings: Google style
- ✅ Type hints: Required for public methods
- ✅ Error handling: Try-except with logging
- ✅ Testing: Add FitNesse wiki tests

---

## 📊 **Performance**

**Benchmarks:**
- Startup time: ~3-5 seconds
- Test execution: ~50-100ms per request (local mock)
- Test execution: ~200-500ms per request (remote API)
- Report generation: ~1-2 seconds (100 tests)
- Memory usage: ~150-250 MB (FitNesse + Python)

---

## 📝 **License**

Enterprise Internal Use Only - ICICI Prudential Life Insurance

---

## 📞 **Support**

**Contact:**
- **QA Team Lead**: qa@example.com
- **Framework Owner**: devops@example.com
- **Issue Tracker**: [GitHub Issues](https://github.com/org/repo/issues)

**Documentation:**
- **Wiki**: [Internal Confluence](https://wiki.company.com/fitnesse)
- **Training Videos**: [Internal Portal](https://training.company.com)

---

## 🎯 **Roadmap**

**v2.1 (Planned)**
- [ ] REST API documentation generator
- [ ] Performance testing support (load/stress)
- [ ] Database assertion fixtures (SQL/NoSQL)
- [ ] Kubernetes integration tests
- [ ] Advanced reporting with charts

**v2.2 (Future)**
- [ ] AI-powered test generation
- [ ] Visual regression testing
- [ ] Contract testing (Pact)
- [ ] Service virtualization

---

## 📝 **Changelog**

### **v2.1.0** - July 16, 2026
**UX Enhancements:**
- ✅ Smart cancel button with change detection (no confirmation for empty forms)
- ✅ Context-aware radio button defaults (Suite for new pages, Test for child pages)  
- ✅ Universal ICICI theme application with MutationObserver
- ✅ Enhanced environment management with console debugging
- ✅ Developer console integration with detailed logging

**Bug Fixes:**
- ✅ Fixed GitHub Actions PowerShell error with HTML tags in Write-Host
- ✅ Fixed cancel buttons not working on various pages
- ✅ Improved form change detection logic

**Developer Experience:**
- ✅ Added console logging for all UX operations
- ✅ RED banner indicator when JavaScript loads successfully
- ✅ Enhanced debugging messages for troubleshooting
- ✅ Updated .gitignore to exclude .zip backups and temp files

### **v2.0.0** - July 13, 2026
**Initial Release:**
- 15 Python fixtures for comprehensive API testing
- OAuth2, GraphQL, WebSocket, gRPC support
- Custom ICICI branding and theme
- GitHub Actions CI/CD integration
- Multi-environment support (Dev/QA/UAT/Prod)
- Automated HTML report generation

---

## 🏆 **Credits**

**Built By:** ICICI Prudential QA Engineering Team  
**Framework Version:** 2.1.0  
**Last Updated:** 2026-07-16  
## UI Step Library

Open **Step Builder** (profile menu) in the FitNesse header to compose tests visually and copy the result into a wiki page.
It has two table types:

- **Script table** - steps one after another, `| keyword | arg | keyword | arg |` against `fixtures.UiFixture` (the table below).
- **Column table** - pick a ready-made fixture (UI scenarios such as `login test`, `accessibility test`, and every API request fixture),
  see its columns marked *required*, *optional* or *result*, tick the optional ones you need, type one row per data set, and copy the
  finished table (no `|import|` table is needed). Required cells must be filled before the table can be added; a value containing `|` is wrapped
  so the wiki table stays intact; password-like cells are hidden while you type. Script steps and column tables can be mixed in one script.

The fixture list is read from the user store server (`http://localhost:8090/fixtures`) every time the Column table tab opens, so a new or edited fixture appears without a restart (restart `start_server.bat` once after updating the framework itself).

**Live Debug** (profile menu) runs the current page with visible browsers: every browser started in that run is headed, so all rows of a
column table are visible. It lasts 15 minutes and a normal **Run** switches it off. It only matters when `UI_HEADLESS=true`.

| Category | Steps |
|---|---|
| Browser | `open browser`, `navigate to`, `refresh page`, `go back`, `go forward`, `close browser` |
| Input | `enter text \| loc \| with value \| v`, `clear field`, `press key [\| on \| loc]` |
| Mouse | `click element`, `double click`, `right click`, `hover over`, `scroll to element` |
| Selection | `select dropdown \| loc \| option \| v`, `check checkbox`, `uncheck checkbox`, `select radio button`, `set toggle \| loc \| to \| on` |
| Wait | `wait for element visible/invisible/clickable [\| timeout \| ms]`, `wait for text`, `wait for page load`, `wait for timeout \| ms` |
| Verification | `ensure \| verify text present / text not present / element present / element not present / element visible / element enabled / field value \| loc \| equals \| v / dropdown value / url / page title` |
| Browser handling | `accept alert`, `dismiss alert` (place before the step that opens it), `verify alert text`, `switch to frame`, `switch to default frame`, `switch window`, `close current tab` |
| File | `upload file \| loc \| path \| p`, `verify file downloaded` |
| Variables | `set variable \| n \| to \| v`, `get variable`, `capture text to variable \| loc \| as \| n`, `generate test data \| type \| into \| n`; use `${n}` in any argument |
| Control flow | `if condition`, `else branch`, `end if`, `for each \| x \| in \| a,b,c` (or `1..5`), `end loop`, `break loop` |
| Error handling | `retry action \| n` (next step), `continue on failure` (default), `stop on failure`, `take screenshot` |
| Reusable flow | `execute reusable component \| Name [\| with \| k=v,k2=v2]` runs `data/components/Name.flow` |

### Reusable components

A component is a `.flow` file in `data/components/` (created when you add the first one), one step per line in the same pipe format
(`#` starts a comment); parameters arrive as `${name}`. Call it from a script table with
`| execute reusable component | Name | with | k=v,k2=v2 |`. For login, prefer the `login test` column table, which keeps the data in table columns and uses the `LoginPage` page object.

For deterministic API checks use the local mock server on port 8089 (`mock server fixture`); it needs no internet access.

### Fixture layout

```
core/                      shared code that is not a fixture: flow engine (flow.py), json helpers, reports, locators
fixtures/
  ui/                      UiFixture, column-table base (decision_fixture.py), scenario folders such as ui/scenario/login
  api/                     get/post/put/patch/delete/... request fixtures, auth, oauth2, graphql, grpc, websocket, mock server
  visual/                  visual_steps.py (the `verify visual match` steps UiFixture inherits); engine: core/visual_compare.py
  accessibility/           accessibility fixture (script table) and accessibility test (column table); engine: core/accessibility.py
pages/                     page objects: locators + actions per page (login_page.py, ...)
data/                      users.json and reusable components (data/components/*.flow)
```

Existing wiki pages keep working: `fixtures.UiFixture`, `| import | fixtures |` and the other short names are re-exported by
`fixtures/__init__.py`. Module fixtures use their folder path, e.g. `| import | fixtures.ui.scenario.login |`, and an area can be imported
whole, e.g. `| import | fixtures.api |`.
Wiki pages need no `import` table: the Slim runner searches every package under `fixtures/` automatically (`fixtures.fixture_packages()`), so a new fixture folder is found as soon as it exists. An explicit `import` table still works and is tried first.

### Column fixtures (one row per data set)

A column table runs the same test for many data sets. Put the inputs in columns and the expected result in a `?` column:

```
|login test|
|username|password|browser|login result?|
|admin|admin123||Success|
|admin|wrong-password||Invalid username or password.|
|admin|admin123|firefox|Success|
```

- **`browser` is optional.** Empty or missing means the browser selected in the environment settings; a value
  (`chromium`, `firefox`, `webkit`) applies to that row only. Failure screenshots are automatic, so there is no screenshot column.
- **Each row is its own fresh browser session and its own test case** in Allure (`LoginWithData - row 2: admin / ***`),
  with the steps of that row; the simple report shows a `ROW n` marker before them. A wrong result is also recorded as a
  failed step with the expected and actual values. Columns whose name contains `pass`, `pwd`, `secret`, `otp`, `cvv` or `pin`
  are masked in reports and logs.
- **`${UI_BASE_URL}` and other variables** work inside cells.
- **A new fixture** is a small class in its module folder (see `fixtures/ui/scenario/login/login_test.py`):

```python
from fixtures.ui.decision_fixture import DecisionFixture

class LoginTest(DecisionFixture):          # fixtures/ui/scenario/login/login_test.py, exported from fixtures/ui/scenario/login/__init__.py
    INPUTS = ("username", "password", "browser")
    OUTPUTS = ("login_result",)

    def run_row(self, row):                # row.username, row.get("browser", "default"), row.has("otp")
        self.do(self.ui.navigate_to, "${UI_BASE_URL}")      # do() stops the row if a step fails
        self.do(self.ui.enter_text_with_value, "LoginPage.username", row.username)
        return {"login_result": "Success"}                  # compared with the cell by FitNesse
```

Group fixtures per module (`fixtures/ui/scenario/login/`, `fixtures/ui/scenario/deposit/`, ...) and import the module on the wiki page.

**Declare the columns** so the Step Builder can list them (required / optional, allowed values, an example, a help line):

```python
from core.fixture_meta import input_column, output_column

class LoginTest(DecisionFixture):
    DESCRIPTION = "Logs in with each username and password and returns what the form shows."
    COLUMNS = (
        input_column("username", required=True, example="admin"),
        input_column("password", required=True, secret=True),
        input_column("browser", options=("chromium", "firefox", "webkit"), help="Optional. Empty = the environment's browser"),
        output_column("login_result", example="Success"),
    )
```

Names are snake_case (`login_result` is the `login result?` column). Any class under `fixtures/ui/scenario/`, `fixtures/accessibility/` or
`fixtures/api/` with `COLUMNS` shows up in the Step Builder automatically. `tests/unit/test_fixture_catalog.py` checks that every listed
column really exists on its fixture, and `tests/unit/test_wiki_pages.py` checks that the example pages only use columns the fixtures offer.

### API tables

Every request fixture is a column table too. Build one in the Step Builder (**Column table**, then e.g. `get request fixture`):

```
|get request fixture|
|url|key|status code?|json value?|
|${API_BASE_URL}/users/1|firstName|200|Emily|
|${API_BASE_URL}/users/99999|message|404|User with id '99999' not found|
```

`${API_BASE_URL}` is the API URL of the environment selected in the ENV selector. Optional columns: `basic auth`, `timeout`, `retries`,
`retry delay`, `ssl verify`, `header lookup`; POST / PUT / PATCH add `body json`. Results: `status code?`, `json value?`, `response time?`,
`response header?`, `response body?`. `auth fixture` logs in once and the later tables send the token automatically.
The Step Builder generates these tables (Column table, then the request fixture).

### Page objects and locators

Each application page is a Python class in `pages/` holding its locators (UPPER_CASE attributes) and its actions (methods):

```python
# pages/login_page.py
class LoginPage(BasePage):
    USERNAME = "role=textbox:Username"
    LOGIN_BUTTON = "role=button:Log In"

    def login(self, username, password):          # fixtures reuse the action
        self.fill("username", username)
        self.fill("password", password)
        self.click("login button")
```

- A locator is named after its attribute in lower case (`LOGIN_BUTTON` -> `login button`); case, spaces, `_` and `-` do not matter in tables.
- **Wiki tables:** `LoginPage.username` always resolves from that page. With no page selected, short names such as `username` resolve
  from `LoginPage` (our own login screen); `| use page | DashboardPage |` makes later short names resolve from that page first.
- **Step Builder:** pick the page and the locator drop-down lists that page's locators (short names for `LoginPage`, page-qualified for the rest).
- **Fixtures** call the page, e.g. `LoginPage(self.ui).login(row.username, row.password)`.
- **New page:** add `pages/<name>_page.py` with a `BasePage` subclass; nothing else to register. Locators are changed in code and reviewed in git.
Anything not found on the applicable page is treated as a normal selector.

The [`LoginAuthenticationTest` FitNesse page](./FitNesseRoot/FrontPage/LoginAuthenticationTest/content.txt) shows
login steps in a plain `fixtures.UiFixture` script table using the generic text-entry, click, and URL-verification
actions. The same fixture can be reused for other UI modules without a login-specific fixture.

### Accessibility testing (WCAG)

Checks a page with axe-core (vendored in `core/axe.min.js`, no install needed) and fails it when it has more violations than allowed.

Script table (one page):

```
|import|
|fixtures.accessibility|

|script|accessibility fixture|
|set url|${UI_BASE_URL}|
|set wcag version|2.1|
|set max violations|0|
|run accessibility check|
|check|status|PASS|
|show|violations|
|show|report|
```

Column table (one row per page or WCAG setting):

```
|accessibility test|
|url|wcag version|max violations|minimum impact|browser|violations?|compliance?|status?|
|${UI_BASE_URL}|2.1|0||||||PASS|
|${UI_BASE_URL}home|2.2|3|serious|firefox||||
```

- `wcag version` 2.0 / 2.1 / 2.2 (default 2.1), `wcag level` A / AA / AAA (default AA), `max violations` (default 0),
  `minimum impact` minor / moderate / serious / critical (findings below it are listed but not counted), `browser` optional.
- Results: `violations?`, `all violations?`, `passed checks?`, `needs review?`, `compliance?`, `status?`, `report?`
  (compliance = passed rules / (passed + violated + needs-review rules)).
- A page over its limit is a failed test case in Allure even without an expected cell. Each violation is an Allure step; the HTML report
  (impact, rule, WCAG tags, affected elements, how to fix) and the JSON are attached, and also saved in `FitNesseRoot/files/testResults/accessibility`.
- Build the table in the Step Builder (Column table, then `accessibility test`).

### Visual testing

Compare the screen with an approved baseline on every build:

```
| ensure | verify visual match | home page |
| ensure | verify visual match | home page | threshold | 0.5 |
| ensure | verify element visual match | LoginPage.login box | as | login-box |
| ignore visual region | css=.clock |
| set visual threshold | 0.2 |
| update visual baseline | home page |
```

- Baselines are PNGs in `data/visual/baselines/<browser>-<width>x<height>/<name>.png`. **Commit them**; you can also drop
  your own reference screenshots there. A browser/viewport pair never compares against another one.
- **Your own reference image:** put `<name>.png` in `fixtures/visual/baseline/` (for example `login page.png`). It is used for
  every browser and viewport, is never overwritten by a run (only by Approve or `update visual baseline`), and is scaled to the
  page when both have the same shape - use the `viewport` column to give the page the shape of the image.
- **Column table:** the Step Builder lists it as **Visual > visual test**:

```
|visual test|
|url           |name      |viewport |threshold|status?|
|${UI_BASE_URL}|login page|1600x1043|6        |passed |
```

  Columns: `url`, `name` (required); `viewport`, `threshold`, `ignore`, `browser` (optional); results `status?`, `difference?`,
  `message?`, `baseline?`.
- The first run for a name creates its baseline (reported as *new*). Set `VISUAL_FAIL_ON_NEW=true` in CI to fail instead.
- A comparison fails when more than the allowed % of pixels differ (`VISUAL_THRESHOLD`, default 0.1) or the image size
  changes. `VISUAL_PIXEL_TOLERANCE` (default 10 of 255) ignores faint anti-aliasing noise.
- Animations and the caret are frozen and fonts are awaited before every shot. `ignore visual region` paints a mask over
  dynamic content; set it before the baseline is created and keep it for later runs.
- **HTML report per comparison** (`report?` column, "Open full report" on the Visual Review Report, and attached to Allure): one
  self-contained file with the difference %, every differing area (position, size, baseline vs actual crop), the actual image with
  the areas marked, side-by-side / slider / diff views and a copy-ready defect description. Attach the file to the defect as it is.
- Baseline, actual and diff images are attached to Allure and the simple report. Open **Visual Review Report** (profile menu,
  `http://localhost:8090/visual`) to see side-by-side / slider / diff views and approve intended changes in one click.
- `VISUAL_UPDATE_BASELINE=true` re-baselines every comparison of a run; `VISUAL_FULL_PAGE=false` captures only the viewport.

Locators accept page locator names, plain CSS, XPath (`//div`) or prefixes `css= xpath= id= name= text= label= placeholder= testid= role=`.
IF conditions: `${a} == b` (`!= > < >= <= contains`) or `element visible: loc` / `element present:` / `element enabled:` / `text present:`.
A `.flow` file holds one step per line in the same pipe format (`#` starts a comment).

---

**Status:** Production Ready ✅

---

**⭐ Star this repository if you find it useful!**

## Reports

| Where | What |
|---|---|
| **Allure Report** (top bar button) | Allure dashboard. Each result is classified as UI, API, Visual or Accessibility (Behaviors tab and tags), shows its browser / page / WCAG parameters, and failures are grouped on the Categories tab (visual differences, accessibility violations, API failures, UI element problems). Visual steps carry baseline, actual and diff images; accessibility steps carry the full report and every violation; API steps carry request and response. |
| **Simple Report** (profile menu) | The plain run report with steps. |
| **Visual Review Report** (profile menu) | Baseline / actual / diff with one-click approval. |
| **Accessibility Report** (profile menu) | Every accessibility check run so far, newest first, each linking to its full WCAG report. Served by the user store server at `/accessibility`. |

Restart `start_server.bat` once so the user store server picks up the new `/accessibility` page.


## Using this framework for another application

Make one copy of the framework folder per application. Nothing in the code names an application or a port, so a copy needs
only configuration:

1. **`.env`** - `APP_NAME`, `APP_TITLE`, `FITNESSE_PORT`, `STORE_PORT`, `MOCK_SERVER_PORT` (see `.env.example`). Give each copy
   its own ports and two copies run side by side; `start_server.bat` frees only that copy's ports.
2. **Environments** - add the dev / uat / prod API and UI URLs in the ENV drawer (they are written to `.env`).
3. **Application code** - replace `pages/login_page.py` with your page objects, `fixtures/ui/scenario/login` with your scenarios,
   the `NirikshanFunctionalTesting` and `VisualRegression` suites with yours, `fixtures/visual/baseline/*.png` with your
   reference images, and `data/users.json` with your own users. The logo files are under `FitNesseRoot/files/fitnesse/icici/img`.

Everything else (`core/`, the fixture engines, the report generators, the Step Builder) is shared framework code; do not edit
it per application so fixes can be copied between copies.

### Flaky rows

`ROW_RETRIES=1` in `.env` re-runs a UI table row that errors or returns a wrong result, in a fresh browser. The first
failure keeps its screenshot and steps; a row that passes on a retry is reported as passed and flagged *flaky* in Allure
(the failed attempt is listed under Retries). `0` (default) turns it off.

### API response shape (`schema` column)

Request tables accept a `schema` column: a file name in `data/schemas` (`user` = `data/schemas/user.json`) or the JSON Schema
itself. A response that does not match fails the step in Allure and the simple report, and `schema valid?` shows `valid` or
the first differences (`$.id: expected integer but found string`). Supported keywords are listed in `core/json_schema.py`;
an unsupported keyword is reported instead of being ignored.

```
|get request fixture|
|url                            |key      |schema|status code?|schema valid?|
|${API_BASE_URL}/users/1        |firstName|user  |200         |valid        |
```

### CI

**GitHub Actions** (`.github/workflows/automation-tests.yml`) is the CI of this framework. On a push or pull request to
`main`, or when started by hand (Actions > Automation Tests > Run workflow), it:

1. runs the unit tests, which include the design rules in `tests/unit/test_architecture.py`;
2. starts FitNesse, runs the suite with `python -m core.ci_run` (exit code 1 = a table is wrong, 2 = FitNesse did not answer),
   and stops it again, all in one step;
3. builds the reports and applies the quality gate with `python -m core.ci_reports --gate` (a visual mismatch or an
   accessibility failure fails the job);
4. uploads the **test-reports** artifact: `testResults/allure-report/index.html`, `testResults/visual/index.html`,
   `testResults/accessibility/index.html` and `report.html`, plus a summary on the run page.

Settings: the manual run asks for `suite`, `api_url`, `ui_url` and `row_retries`; for push and pull-request runs set the
repository **variables** `API_BASE_URL` and `UI_BASE_URL` (Settings > Secrets and variables > Actions > Variables). They are
written to `VariablePage` before the run, so the environment under test is never taken from a committed file. Visual
baselines must be created on the runner (Windows) or they will differ by fonts: run once, then copy the images from the
artifact into `data/visual/baselines`. The nightly schedule is in the workflow file, commented out.

`python -m core.ci_run` and `python -m core.ci_reports` are plain Python, so any other runner can call them the same way.

**Reports on GitHub Pages (opt-in).** `python -m core.ci_reports --site site` gathers the Allure, visual, accessibility and
simple reports into one folder with an index page, and the workflow deploys it when the repository variable `PUBLISH_PAGES`
is `true` (Settings > Pages > Source: *GitHub Actions*). The link appears on the run page. On a public repository the site is
public, and the reports contain screenshots and the URLs of the environment under test, so leave it off unless that is fine.

**Repository must contain `waferslim/` as ordinary files.** If it was added from a folder that was itself a git repository,
git stores an empty "gitlink" and a fresh checkout has no Slim server, so no table can run. Fix once with
`git rm --cached waferslim`, `git add waferslim`, commit. The workflow's first step fails with that instruction when the
folder is empty.


### Pages behind a login, and alignment / size / colour checks

`visual test` and `layout test` take optional `username` and `password` columns. When they are filled, the row signs in
through the application's `pages/login_page.py` (`LoginPage.open()`, `.login(user, password)`, `.outcome()` returning
`Success`) before it opens the `url`, so a page that needs a login is compared and not the login screen. A refused login is
an `ERROR` row with the application's message. The password column is masked on screen and in the reports.

`layout test` compares the **position, size and colours** of the elements you list, not pixels, so a changed text or image is
ignored but a moved field, a resized box or a different colour is not:

```
|layout test|
|url               |name      |elements                                   |tolerance|username|password|status?|differences?|
|${UI_BASE_URL}home|home page |LoginPage.username, LoginPage.login button |2        |qa      |qa123   |passed |            |
```

Measured per element: left / top position, width, height, text colour, background colour, border colour and width, font size,
weight and family, and text alignment. Position and size may move by `tolerance` pixels (`LAYOUT_TOLERANCE`, default 2); colours
and fonts must match exactly. The first run for a name stores the values in `data/visual/layouts/<browser>-<w>x<h>/<name>.json`
(commit them); a hand-written `fixtures/visual/layout/<name>.json` is used instead when present. The `report?` link opens a
page with the measured values, the differences highlighted and a defect description; set `update` to `true` to accept a
change as the new baseline.


## Rules for AI coding tools and developers

`AGENTS.md` is the single rulebook: the layers, what may import what, where each kind of change goes, the hard rules and
when to ask the owner first. `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` and `.cursor/rules/framework.mdc`
only point to it, so any tool that reads one of them lands on the same rules.

`tests/unit/test_architecture.py` enforces the structural rules (import directions, no new top-level folder, no application
name or port in framework code, no killing processes by name, every column fixture declares its columns). A change that
breaks the design fails the normal test run.
