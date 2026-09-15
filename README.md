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
- ✅ **Custom ICICI Branding**: Official logos, colors (#A6192E red, #004A80 blue)
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
- ✅ **Jenkins Pipeline**: Parameterized builds, email notifications, HTML reports
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
└── Jenkinsfile                   # Jenkins Pipeline (332 lines)
```

---

## 🚀 **Quick Start**

### **1. Prerequisites**
- Python 3.10+ ([Download](https://www.python.org/downloads/))
- Java 17+ ([Download](https://www.oracle.com/java/technologies/downloads/))
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

### **Jenkins Pipeline**

**File:** `Jenkinsfile`

**Features:**
- ✅ Parameterized builds (environment, test suite)
- ✅ Email notifications (success/failure)
- ✅ HTML report publishing
- ✅ Artifact archiving (30 days)
- ✅ Scheduled builds (daily 2 AM)

**Setup:**
1. Create new Pipeline job in Jenkins
2. Point to `Jenkinsfile` in repository
3. Configure email settings in pipeline
4. Run with parameters

**Parameters:**
- `TEST_ENVIRONMENT`: dev/staging/uat/prod
- `TEST_SUITE`: FrontPage, FrontPage.Sanity, etc.
- `SEND_EMAIL`: Enable/disable notifications
- `FAIL_ON_ERROR`: Fail build on test failures

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
- GitHub Actions & Jenkins CI/CD integration
- Multi-environment support (Dev/QA/UAT/Prod)
- Automated HTML report generation

---

## 🏆 **Credits**

**Built By:** ICICI Prudential QA Engineering Team  
**Framework Version:** 2.1.0  
**Last Updated:** 2026-07-16  
**Status:** Production Ready ✅

---

**⭐ Star this repository if you find it useful!**
