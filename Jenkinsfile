pipeline {
    agent {
        label 'windows'  // Use Windows agent
    }
    
    parameters {
        choice(
            name: 'TEST_ENVIRONMENT',
            choices: ['dev', 'staging', 'uat', 'prod'],
            description: 'Target test environment'
        )
        string(
            name: 'TEST_SUITE',
            defaultValue: 'FrontPage',
            description: 'FitNesse test suite to run (e.g., FrontPage.Sanity, FrontPage.Smoke)'
        )
        booleanParam(
            name: 'SEND_EMAIL',
            defaultValue: true,
            description: 'Send email notification with test results'
        )
        booleanParam(
            name: 'FAIL_ON_ERROR',
            defaultValue: true,
            description: 'Fail the build if tests fail'
        )
    }
    
    environment {
        PYTHON_VERSION = '3.10'
        JAVA_HOME = tool name: 'JDK17', type: 'jdk'
        PATH = "${JAVA_HOME}\\bin;${env.PATH}"
        FITNESSE_PORT = '8080'
        MOCK_SERVER_PORT = '8089'
    }
    
    options {
        buildDiscarder(logRotator(numToKeepStr: '30', artifactNumToKeepStr: '15'))
        timestamps()
        timeout(time: 1, unit: 'HOURS')
        disableConcurrentBuilds()
    }
    
    triggers {
        // Run tests every day at 2 AM
        cron('0 2 * * *')
        
        // Trigger on SCM changes (if configured)
        pollSCM('H/15 * * * *')
    }
    
    stages {
        stage('Checkout') {
            steps {
                script {
                    echo "🔄 Checking out source code..."
                    checkout scm
                }
            }
        }
        
        stage('Setup Environment') {
            steps {
                script {
                    echo "⚙️ Setting up test environment..."
                    
                    // Set environment-specific variables
                    switch(params.TEST_ENVIRONMENT) {
                        case 'dev':
                            env.BASE_URL = 'https://dev-api.example.com'
                            env.MOCK_SERVER_URL = "http://localhost:${MOCK_SERVER_PORT}"
                            break
                        case 'staging':
                            env.BASE_URL = 'https://staging-api.example.com'
                            break
                        case 'uat':
                            env.BASE_URL = 'https://uat-api.example.com'
                            break
                        case 'prod':
                            env.BASE_URL = 'https://api.example.com'
                            break
                    }
                    
                    echo "📍 Test Environment: ${params.TEST_ENVIRONMENT}"
                    echo "🔗 Base URL: ${env.BASE_URL}"
                    echo "🧪 Test Suite: ${params.TEST_SUITE}"
                }
            }
        }
        
        stage('Install Dependencies') {
            steps {
                script {
                    echo "📦 Installing Python dependencies..."
                    bat '''
                        python --version
                        python -m pip install --upgrade pip
                        pip install -r requirements.txt
                    '''
                }
            }
        }
        
        stage('Validate Setup') {
            steps {
                script {
                    echo "✅ Validating environment setup..."
                    bat '''
                        echo Checking Java...
                        java -version
                        
                        echo Checking Python...
                        python --version
                        
                        echo Checking FitNesse JAR...
                        if exist "fitnesse-standalone.jar" (
                            echo ✅ FitNesse JAR found
                        ) else (
                            echo ❌ FitNesse JAR not found
                            exit /b 1
                        )
                        
                        echo Checking fixtures...
                        if exist "fixtures\\__init__.py" (
                            echo ✅ Fixtures directory found
                        ) else (
                            echo ❌ Fixtures directory not found
                            exit /b 1
                        )
                    '''
                }
            }
        }
        
        stage('Kill Existing Processes') {
            steps {
                script {
                    echo "🔪 Killing any existing FitNesse/Java processes on ports ${FITNESSE_PORT} and ${MOCK_SERVER_PORT}..."
                    bat '''
                        for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8080') do taskkill /f /pid %%a 2>nul
                        for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8089') do taskkill /f /pid %%a 2>nul
                        echo ✅ Ports cleared
                    '''
                }
            }
        }
        
        stage('Start FitNesse Server') {
            steps {
                script {
                    echo "🚀 Starting FitNesse server on port ${FITNESSE_PORT}..."
                    bat '''
                        set PYTHONPATH=%CD%
                        start /b java -cp ".;fitnesse-standalone.jar" fitnesseMain.FitNesseMain -p %FITNESSE_PORT% -e 0 > fitnesse_output.log 2> fitnesse_error.log
                        
                        REM Wait for FitNesse to start
                        echo Waiting for FitNesse to become ready...
                        timeout /t 5 /nobreak > nul
                        
                        powershell -Command "$maxRetries = 30; $retryCount = 0; do { Start-Sleep -Seconds 2; $retryCount++; try { $response = Invoke-WebRequest -Uri 'http://localhost:%FITNESSE_PORT%' -UseBasicParsing -TimeoutSec 2; if ($response.StatusCode -eq 200) { Write-Host '✅ FitNesse server is ready!'; break } } catch { Write-Host '⏳ Waiting for FitNesse... ($retryCount/$maxRetries)' } } while ($retryCount -lt $maxRetries); if ($retryCount -eq $maxRetries) { Write-Error '❌ FitNesse failed to start'; exit 1 }"
                    '''
                }
            }
        }
        
        stage('Run Tests') {
            steps {
                script {
                    echo "🧪 Running FitNesse test suite: ${params.TEST_SUITE}"
                    
                    try {
                        bat """
                            powershell -Command "
                                \\$testUrl = 'http://localhost:${FITNESSE_PORT}/${params.TEST_SUITE}?suite&format=json'
                                Write-Host '📍 Test URL: ' \\$testUrl
                                
                                try {
                                    \\$response = Invoke-WebRequest -Uri \\$testUrl -UseBasicParsing -TimeoutSec 600
                                    \\$testResults = \\$response.Content | ConvertFrom-Json
                                    
                                    # Extract results
                                    \\$right = \\$testResults.finalCounts.right
                                    \\$wrong = \\$testResults.finalCounts.wrong
                                    \\$exceptions = \\$testResults.finalCounts.exceptions
                                    \\$ignores = \\$testResults.finalCounts.ignores
                                    
                                    Write-Host ''
                                    Write-Host '📊 Test Results Summary:'
                                    Write-Host '✅ Passed: ' \\$right
                                    Write-Host '❌ Failed: ' \\$wrong
                                    Write-Host '⚠️  Exceptions: ' \\$exceptions
                                    Write-Host '⏭️  Ignored: ' \\$ignores
                                    Write-Host ''
                                    
                                    # Save results
                                    \\$testResults | ConvertTo-Json -Depth 10 | Out-File -FilePath 'test_results.json'
                                    
                                    # Set environment variables for reporting
                                    echo TEST_RIGHT=\\$right > test_counts.txt
                                    echo TEST_WRONG=\\$wrong >> test_counts.txt
                                    echo TEST_EXCEPTIONS=\\$exceptions >> test_counts.txt
                                    echo TEST_IGNORES=\\$ignores >> test_counts.txt
                                    
                                    # Fail if configured and tests failed
                                    if (${params.FAIL_ON_ERROR} -and (\\$wrong -gt 0 -or \\$exceptions -gt 0)) {
                                        Write-Error '❌ Tests failed! Build should fail.'
                                        exit 1
                                    }
                                    
                                    Write-Host '✅ Test execution completed!'
                                } catch {
                                    Write-Error '❌ Failed to run tests: ' \\$_
                                    exit 1
                                }
                            "
                        """
                        
                        // Read test counts for email notification
                        def countsFile = readFile('test_counts.txt')
                        def counts = [:]
                        countsFile.split('\\n').each { line ->
                            def parts = line.split('=')
                            if (parts.length == 2) {
                                counts[parts[0]] = parts[1].trim()
                            }
                        }
                        env.TEST_RIGHT = counts.TEST_RIGHT ?: '0'
                        env.TEST_WRONG = counts.TEST_WRONG ?: '0'
                        env.TEST_EXCEPTIONS = counts.TEST_EXCEPTIONS ?: '0'
                        env.TEST_IGNORES = counts.TEST_IGNORES ?: '0'
                        
                    } catch (Exception e) {
                        echo "❌ Test execution failed: ${e.message}"
                        currentBuild.result = 'UNSTABLE'
                        if (params.FAIL_ON_ERROR) {
                            error("Tests failed!")
                        }
                    }
                }
            }
        }
        
        stage('Collect Artifacts') {
            steps {
                script {
                    echo "📦 Collecting test artifacts..."
                    bat '''
                        if not exist "test-artifacts" mkdir test-artifacts
                        
                        REM Copy test results
                        if exist "FitNesseRoot\\files\\testResults" (
                            xcopy /E /I /Y "FitNesseRoot\\files\\testResults\\*" test-artifacts\\testResults\\
                        )
                        
                        REM Copy HTML report
                        if exist "FitNesseRoot\\files\\report.html" (
                            copy "FitNesseRoot\\files\\report.html" test-artifacts\\
                        )
                        
                        REM Copy logs
                        if exist "logs" (
                            xcopy /E /I /Y "logs\\*" test-artifacts\\logs\\
                        )
                        
                        REM Copy FitNesse logs
                        if exist "fitnesse_output.log" copy "fitnesse_output.log" test-artifacts\\
                        if exist "fitnesse_error.log" copy "fitnesse_error.log" test-artifacts\\
                        
                        REM Copy test results JSON
                        if exist "test_results.json" copy "test_results.json" test-artifacts\\
                    '''
                }
            }
        }
    }
    
    post {
        always {
            script {
                echo "🧹 Cleanup: Stopping FitNesse server..."
                bat '''
                    for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8080') do taskkill /f /pid %%a 2>nul
                    for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8089') do taskkill /f /pid %%a 2>nul
                '''
            }
            
            // Archive artifacts
            archiveArtifacts artifacts: 'test-artifacts/**/*', allowEmptyArchive: true, fingerprint: true
            
            // Publish HTML reports
            publishHTML([
                allowMissing: true,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'test-artifacts',
                reportFiles: 'report.html',
                reportName: 'FitNesse Test Report',
                reportTitles: 'API Test Results'
            ])
            
            // JUnit test results (if available)
            junit allowEmptyResults: true, testResults: 'test-artifacts/**/*.xml'
            
            // Clean workspace
            cleanWs deleteDirs: true, disableDeferredWipeout: true, notFailBuild: true
        }
        
        success {
            script {
                echo "✅ Build completed successfully!"
                
                if (params.SEND_EMAIL) {
                    emailext(
                        subject: "✅ FitNesse API Tests PASSED - ${params.TEST_SUITE} [${params.TEST_ENVIRONMENT}]",
                        body: """
                            <html>
                            <body>
                                <h2>✅ FitNesse API Test Results - SUCCESS</h2>
                                <p><strong>Build:</strong> ${env.BUILD_NUMBER}</p>
                                <p><strong>Environment:</strong> ${params.TEST_ENVIRONMENT}</p>
                                <p><strong>Test Suite:</strong> ${params.TEST_SUITE}</p>
                                <p><strong>Build URL:</strong> <a href="${env.BUILD_URL}">${env.BUILD_URL}</a></p>
                                
                                <h3>Test Summary</h3>
                                <table border="1" cellpadding="5" cellspacing="0">
                                    <tr><td>✅ Passed</td><td>${env.TEST_RIGHT}</td></tr>
                                    <tr><td>❌ Failed</td><td>${env.TEST_WRONG}</td></tr>
                                    <tr><td>⚠️ Exceptions</td><td>${env.TEST_EXCEPTIONS}</td></tr>
                                    <tr><td>⏭️ Ignored</td><td>${env.TEST_IGNORES}</td></tr>
                                </table>
                                
                                <p><a href="${env.BUILD_URL}FitNesse_20Test_20Report/">View Detailed Report</a></p>
                            </body>
                            </html>
                        """,
                        to: '${DEFAULT_RECIPIENTS}',
                        mimeType: 'text/html'
                    )
                }
            }
        }
        
        failure {
            script {
                echo "❌ Build failed!"
                
                if (params.SEND_EMAIL) {
                    emailext(
                        subject: "❌ FitNesse API Tests FAILED - ${params.TEST_SUITE} [${params.TEST_ENVIRONMENT}]",
                        body: """
                            <html>
                            <body>
                                <h2>❌ FitNesse API Test Results - FAILURE</h2>
                                <p><strong>Build:</strong> ${env.BUILD_NUMBER}</p>
                                <p><strong>Environment:</strong> ${params.TEST_ENVIRONMENT}</p>
                                <p><strong>Test Suite:</strong> ${params.TEST_SUITE}</p>
                                <p><strong>Build URL:</strong> <a href="${env.BUILD_URL}">${env.BUILD_URL}</a></p>
                                
                                <h3>Test Summary</h3>
                                <table border="1" cellpadding="5" cellspacing="0">
                                    <tr><td>✅ Passed</td><td>${env.TEST_RIGHT ?: 'N/A'}</td></tr>
                                    <tr><td>❌ Failed</td><td>${env.TEST_WRONG ?: 'N/A'}</td></tr>
                                    <tr><td>⚠️ Exceptions</td><td>${env.TEST_EXCEPTIONS ?: 'N/A'}</td></tr>
                                    <tr><td>⏭️ Ignored</td><td>${env.TEST_IGNORES ?: 'N/A'}</td></tr>
                                </table>
                                
                                <p><a href="${env.BUILD_URL}FitNesse_20Test_20Report/">View Detailed Report</a></p>
                                <p><a href="${env.BUILD_URL}console">View Console Output</a></p>
                            </body>
                            </html>
                        """,
                        to: '${DEFAULT_RECIPIENTS}',
                        mimeType: 'text/html'
                    )
                }
            }
        }
        
        unstable {
            script {
                echo "⚠️ Build is unstable!"
            }
        }
    }
}
