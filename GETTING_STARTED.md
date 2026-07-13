# 🚀 Getting Started with ICICI Prudential AML API Framework

Welcome to the ICICI Prudential AML API Test Automation Framework! This guide will help you get up and running in **under 10 minutes**.

---

## 📋 **Prerequisites Checklist**

Before starting, ensure you have:

- [ ] **Windows 10/11** (or Windows Server 2016+)
- [ ] **Python 3.10 or higher** ([Download](https://www.python.org/downloads/))
- [ ] **Java 17 or higher** ([Download](https://www.oracle.com/java/technologies/downloads/))
- [ ] **Git** ([Download](https://git-scm.com/downloads))
- [ ] **PowerShell 5.1+** (pre-installed on Windows)
- [ ] **Modern Browser** (Chrome, Edge, Firefox)

---

## ⚙️ **Installation Steps**

### **Step 1: Verify Prerequisites**

Open PowerShell and run:

```powershell
# Check Python
python --version
# Expected: Python 3.10.x or higher

# Check Java
java -version
# Expected: openjdk version "17" or higher

# Check Git
git --version
# Expected: git version 2.x.x
```

If any command fails, install the missing prerequisite from the links above.

---

### **Step 2: Clone the Repository**

```powershell
# Navigate to your workspace
cd C:\Workspace  # Or your preferred directory

# Clone the repository
git clone <repository-url>

# Navigate into the project
cd ICICI_FitNesseAPIFramework
```

---

### **Step 3: Create Virtual Environment**

```powershell
# Create Python virtual environment
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\activate

# Your prompt should now show (.venv) prefix
```

---

### **Step 4: Install Dependencies**

```powershell
# Upgrade pip to latest version
python -m pip install --upgrade pip

# Install all required packages
pip install -r requirements.txt

# Verify installation
pip list
```

**Expected packages:**
- requests (HTTP library)
- pytest (testing framework)
- websocket-client (WebSocket support)
- grpcio (gRPC support)
- requests-oauthlib (OAuth2)
- gql (GraphQL)
- And more...

---

### **Step 5: Verify Installation**

```powershell
# Check FitNesse JAR exists
Test-Path fitnesse-standalone.jar
# Should return: True

# Check fixtures directory
Test-Path fixtures
# Should return: True

# List all fixtures
Get-ChildItem fixtures\*.py
```

---

## 🎬 **First Run**

### **Start the Server**

```powershell
# Simply run the batch file
.\start_server.bat
```

**What happens:**
1. Script checks and kills any processes using port 8080
2. FitNesse server starts on `http://localhost:8080`
3. Mock server starts on port 8089
4. Browser opens automatically (optional)

**Console output:**
```
Bootstrapping FitNesse, please wait...
...
Starting FitNesse on port: 8080
```

---

### **Access the Framework**

1. **Open Browser:**
   ```
   http://localhost:8080
   ```

2. **Login Screen:**
   - **Username:** `admin`
   - **Password:** `admin123`

3. **Welcome Dashboard:**
   - You'll see the ICICI Prudential branded dashboard
   - Navigation buttons: Home, Run, Report, Edit, etc.
   - Environment selector: Dev, QA, UAT, Prod

---

## 🧪 **Run Your First Test**

### **Option 1: Run Existing Tests**

1. Click **Home** in navigation
2. Navigate to **DummyAPI** suite
3. Click **▶ Run** button
4. Watch tests execute in real-time
5. View results (green = pass, red = fail)

### **Option 2: Create New Test**

#### **Step 1: Create Test Page**

1. Click **Home** in navigation
2. Click **+ Add Test** button
3. Enter page name: `MyFirstAPITest`
4. Click **Create**

#### **Step 2: Write Test**

Add this content:

```wiki
!define TEST_SYSTEM {slim}

!|import|
|fixtures|

!3 Test: Simple GET Request

!|script|Get Request Fixture|
|set url|https://jsonplaceholder.typicode.com/posts/1|
|execute get|
|check|status code|200|
|check|json value|userId|1|
|check|json value|title|sunt aut facere repellat provident occaecati excepturi optio reprehenderit|
```

#### **Step 3: Run Test**

1. Click **Test** button (top navigation)
2. Wait for execution
3. Review results:
   - **Green rows** = Assertions passed ✅
   - **Red rows** = Assertions failed ❌
   - **Yellow rows** = Errors/exceptions ⚠️

---

## 📖 **Understanding Test Structure**

### **Basic Test Anatomy**

```wiki
!define TEST_SYSTEM {slim}           # Declares SLIM test system

!|import|                            # Import section
|fixtures|                           # Imports all fixtures

!3 Test: Description                 # Test title (heading 3)

!|script|Get Request Fixture|        # Fixture table
|set url|https://api.example.com|    # Set URL
|execute get|                        # Execute request
|check|status code|200|              # Assert status code
|check|json value|$.name|John|       # Assert JSON field
```

### **Test Components**

1. **Import Block**: Loads Python fixtures
2. **Script Table**: Executes methods sequentially
3. **Decision Table**: Data-driven tests (multiple rows)
4. **Query Table**: Validates returned data sets

---

## 🎯 **Common Test Patterns**

### **Pattern 1: Simple GET Request**

```wiki
!|script|Get Request Fixture|
|set url|${BASE_URL}/users/1|
|execute get|
|check|status code|200|
```

### **Pattern 2: POST with JSON Body**

```wiki
!|script|Post Request Fixture|
|set url|${BASE_URL}/users|
|set body json|{"name": "John", "email": "john@example.com"}|
|execute post|
|check|status code|201|
|check|json value|$.id|exists|
```

### **Pattern 3: Authentication Flow**

```wiki
!|script|Auth Fixture|
|set url|${BASE_URL}/auth/login|
|set body json|{"username": "admin", "password": "admin123"}|
|execute post|
|set key|$.token|
|store token|

!|script|Get Request Fixture|
|set url|${BASE_URL}/profile|
|execute get|
|check|status code|200|
```

### **Pattern 4: OAuth2 Authentication**

```wiki
!|script|OAuth2 Fixture|
|set token url|${BASE_URL}/oauth/token|
|set client id|my_client_id|
|set client secret|my_client_secret|
|set grant type|client_credentials|
|get token|

!|script|Get Request Fixture|
|set url|${BASE_URL}/protected|
|set use oauth2|true|
|execute get|
|check|status code|200|
```

---

## 🔧 **Configuration**

### **Environment Variables**

Create `.env` file in root directory:

```env
# Base URLs
DEV_BASE_URL=https://dev-api.example.com
QA_BASE_URL=https://qa-api.example.com
UAT_BASE_URL=https://uat-api.example.com
PROD_BASE_URL=https://api.example.com

# Credentials
API_USERNAME=admin
API_PASSWORD=admin123

# OAuth2
OAUTH_CLIENT_ID=your_client_id
OAUTH_CLIENT_SECRET=your_client_secret
```

### **Using Environment Selector**

1. Click **⚙️** next to Env dropdown
2. Add environment:
   - **Name:** `DEV`
   - **URL:** `https://dev-api.example.com`
3. Click **Save Changes**
4. Select from dropdown to switch

---

## 📊 **Viewing Reports**

### **HTML Reports**

1. Click **📊 Report** in navigation
2. View test execution history
3. Filter by date, status, suite
4. Export to CSV/Excel

### **Logs**

```powershell
# View latest logs
Get-Content logs\framework.log.* -Tail 50

# Search for errors
Select-String -Path logs\framework.log.* -Pattern "ERROR|FAIL"
```

---

## ❓ **Troubleshooting**

### **Issue: Port 8080 Already in Use**

**Solution:**
```powershell
# Option 1: Use start_server.bat (auto-kills)
.\start_server.bat

# Option 2: Manual kill
netstat -ano | findstr :8080
taskkill /F /PID <process_id>
```

### **Issue: Python Module Not Found**

**Solution:**
```powershell
# Activate virtual environment
.\.venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### **Issue: Favicon Not Showing**

**Solution:**
```
1. Press Ctrl + Shift + Delete (Clear cache)
2. Select "Cached images and files"
3. Select "All time"
4. Click "Clear data"
5. Press Ctrl + F5 (Hard refresh)
```

### **Issue: Test Fails with Timeout**

**Solution:**
```wiki
!|script|Get Request Fixture|
|set url|${BASE_URL}/slow-endpoint|
|set timeout|60|        # Increase to 60 seconds
|set retries|3|         # Retry 3 times
|execute get|
```

---

## 🎓 **Next Steps**

1. **Explore Examples:**
   - Navigate to `FrontPage.DummyAPI`
   - Study existing test patterns
   - Run and modify tests

2. **Read Documentation:**
   - [README.md](README.md) - Full framework overview
   - [FIXTURES_GUIDE.md](FIXTURES_GUIDE.md) - Detailed fixture reference

3. **Create Test Suites:**
   - Organize tests by functionality
   - Use `SuiteSetUp` and `SuiteTearDown`
   - Implement data-driven tests

4. **Set Up CI/CD:**
   - Configure GitHub Actions
   - Set up Jenkins pipeline
   - Schedule automated runs

---

## 🤝 **Getting Help**

**Resources:**
- **Documentation:** [README.md](README.md)
- **Examples:** `FitNesseRoot/FrontPage/DummyAPI/`
- **Logs:** `logs/framework.log.*`

**Contact:**
- **QA Team:** qa@example.com
- **Support:** support@example.com

---

## ✅ **Checklist**

- [ ] Prerequisites installed
- [ ] Repository cloned
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] Server started successfully
- [ ] Login successful
- [ ] First test executed
- [ ] Reports viewed
- [ ] Environment configured

---

**🎉 Congratulations! You're now ready to start API testing with the ICICI Prudential AML Framework!**

**Happy Testing! 🚀**
