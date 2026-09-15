import os
import glob
import datetime
import json

report_history = []
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_FILE = os.path.join(BASE_DIR, "FitNesseRoot", "files", "report.html")
HISTORY_JSON = os.path.join(BASE_DIR, "FitNesseRoot", "files", "report_history.json")

def html_escape(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#x27;")

def load_history() -> None:
    global report_history
    if os.path.exists(HISTORY_JSON):
        try:
            with open(HISTORY_JSON, "r", encoding="utf-8") as f:
                report_history = json.load(f)
        except Exception:
            report_history = []
    else:
        report_history = []

def save_history() -> None:
    global report_history
    try:
        os.makedirs(os.path.dirname(HISTORY_JSON), exist_ok=True)
        # Cap history list to last 150 requests to maintain speed and file size limits
        history_to_save = report_history[-150:]
        with open(HISTORY_JSON, "w", encoding="utf-8") as f:
            json.dump(history_to_save, f, indent=2)
    except Exception:
        pass

def scan_test_results() -> list:
    results = []
    test_results_dir = os.path.join(BASE_DIR, "FitNesseRoot", "files", "testResults")
    if not os.path.exists(test_results_dir):
        return results

    # Walk through the test results directory to find test run XML files
    for root, dirs, files in os.walk(test_results_dir):
        for d in dirs:
            dir_path = os.path.join(root, d)
            xml_files = glob.glob(os.path.join(dir_path, "*.xml"))
            if not xml_files:
                continue

            # Get the latest XML run file by sorting filenames (starts with timestamp)
            latest_file = max(xml_files, key=os.path.basename)
            filename = os.path.basename(latest_file)

            # Format: YYYYMMDDHHMMSS_R_W_I_E.xml
            name_part = filename.replace(".xml", "")
            parts = name_part.split("_")
            if len(parts) >= 5:
                timestamp_str = parts[0]
                right = int(parts[1])
                wrong = int(parts[2])
                ignored = int(parts[3])
                exceptions = int(parts[4])

                try:
                    formatted_time = f"{timestamp_str[0:4]}-{timestamp_str[4:6]}-{timestamp_str[6:8]} {timestamp_str[8:10]}:{timestamp_str[10:12]}:{timestamp_str[12:14]}"
                except Exception:
                    formatted_time = timestamp_str

                # Exclude root directory runs and format names beautifully
                clean_name = d.replace("FrontPage.", "")
                if clean_name and not clean_name.endswith("SuiteSetUp") and not clean_name.endswith("SuiteTearDown"):
                    results.append({
                        "name": clean_name,
                        "timestamp": formatted_time,
                        "timestamp_raw": timestamp_str,
                        "right": right,
                        "wrong": wrong,
                        "ignored": ignored,
                        "exceptions": exceptions
                    })
    # Sort results showing the most recently executed tests first
    results.sort(key=lambda x: x["timestamp_raw"], reverse=True)
    return results

def trigger_delayed_report() -> None:
    import subprocess
    import sys
    
    # We want to run the report generator after FitNesse writes the XML results to disk.
    # This happens immediately after the waferslim process exits.
    creationflags = 0
    if os.name == 'nt':
        creationflags = 0x08000000  # CREATE_NO_WINDOW on Windows to prevent console flashing

    cmd = [
        sys.executable,
        "-c",
        "import time, core.report_generator; time.sleep(2.0); core.report_generator.generate_html_report()"
    ]
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True, creationflags=creationflags)
    except Exception:
        pass

def add_record(record: dict) -> None:
    load_history()
    report_history.append(record)
    save_history()
    # Write the report immediately (fallback with current memory data)
    generate_html_report()
    # Trigger the delayed report so that it updates with the fresh XML file 2 seconds later!
    trigger_delayed_report()

def generate_html_report() -> None:
    if not report_history:
        load_history()

    # Scan native FitNesse XML run history to get actual assertion counts
    results = scan_test_results()

    # Detect if the latest execution session is a Suite Run or a Single Test Run.
    # results contains ALL pages, including suite pages (e.g., "DummyAPI", "Sanity")
    # and individual test pages (e.g., "DummyAPI.Add_User", "Sanity.loginTrubi").
    active_pages = []
    suite_name = "FITNESSE RUN"

    if results:
        latest_page = results[0]["name"]
        suite_name = latest_page.split(".")[0] if "." in latest_page else latest_page
        
        # Filter all results for the active namespace (excluding the parent suite page itself)
        current_suite_pages = [r for r in results if (r["name"].startswith(suite_name + ".") or r["name"] == suite_name) and r["name"] != suite_name]
        
        if current_suite_pages:
            latest_raw = current_suite_pages[0]["timestamp_raw"]
            try:
                latest_dt = datetime.datetime.strptime(latest_raw[:14], "%Y%m%d%H%M%S")
                
                # Find all pages in the suite completed within 60 seconds of the latest completion
                recent_pages = []
                for r in current_suite_pages:
                    try:
                        dt = datetime.datetime.strptime(r["timestamp_raw"][:14], "%Y%m%d%H%M%S")
                        if abs((latest_dt - dt).total_seconds()) <= 60:
                            recent_pages.append(r)
                    except Exception:
                        pass
                
                # If more than 1 page completed recently, it's a Suite Run!
                if len(recent_pages) > 1:
                    active_pages = recent_pages
                else:
                    # Single Test Run: Only include the latest page
                    active_pages = [current_suite_pages[0]]
            except Exception:
                active_pages = [current_suite_pages[0]]

    # Initialize empty request lists on all active pages
    for p in active_pages:
        p["requests"] = []

    # Map HTTP requests directly to their parent Test Pages using a strict proximity-matching logic.
    # Each request is matched to EXACTLY ONE page (the closest page in time), preventing duplicates
    # and mixing up requests between adjacent tests in a suite run.
    # OPTIMIZATION: Only consider recent requests (last 50) instead of all historical data
    recent_history = report_history[-50:] if len(report_history) > 50 else report_history
    active_requests = []
    for req in recent_history:
        try:
            req_dt = datetime.datetime.strptime(req["timestamp"], "%Y-%m-%d %H:%M:%S")
            
            closest_page = None
            min_diff = 999999
            
            for p in active_pages:
                try:
                    p_dt = datetime.datetime.strptime(p["timestamp_raw"][:14], "%Y%m%d%H%M%S")
                    diff = (p_dt - req_dt).total_seconds()
                    
                    # Request must execute during the page execution window (typically within 12s before completion)
                    if -2 <= diff <= 12:
                        abs_diff = abs(diff)
                        if abs_diff < min_diff:
                            min_diff = abs_diff
                            closest_page = p
                except Exception:
                    pass
                    
            if closest_page:
                closest_page["requests"].append(req)
                if req not in active_requests:
                    active_requests.append(req)
        except Exception:
            pass

    # Sort active pages showing the most recently executed first
    grouped_pages = sorted(active_pages, key=lambda x: x["timestamp_raw"], reverse=True)

    # Determine Active Suite Name from first active page
    if grouped_pages:
        latest_name = grouped_pages[0]["name"]
        suite_name = latest_name.split(".")[0] if "." in latest_name else latest_name

    # Calculate page-level metrics (Executive Summary KPI Cards)
    total_pages = len(grouped_pages)
    passed_pages = sum(1 for p in grouped_pages if p["wrong"] == 0 and p["exceptions"] == 0 and p["right"] > 0)
    failed_pages = total_pages - passed_pages
    pass_rate = int((passed_pages / total_pages) * 100) if total_pages > 0 else 0
    total_duration_ms = sum(r["response_time_ms"] for r in active_requests)
    formatted_duration = f"{total_duration_ms / 1000:.2f}s"

    # Calculate overall health summary across the active session test pages
    total_right = sum(r["right"] for r in active_pages) if active_pages else 0
    total_wrong = sum(r["wrong"] for r in active_pages) if active_pages else 0
    total_ignored = sum(r["ignored"] for r in active_pages) if active_pages else 0
    total_exceptions = sum(r["exceptions"] for r in active_pages) if active_pages else 0

    # Status Banner Details (Executive Level)
    if failed_pages > 0:
        status_banner_class = "banner-fail"
        status_banner_text = f"🚨 TEST RUN FAILED — {failed_pages} / {total_pages} Test Cases Failed (Action Required)"
    elif total_pages > 0:
        status_banner_class = "banner-pass"
        status_banner_text = "🎉 TEST RUN PASSED — 100% Succeeded! All APIs are operational."
    else:
        status_banner_class = "banner-empty"
        status_banner_text = "⚪ NO TEST RESULTS CAPTURED"

    # Compile HTML Rows for the Single Unified Dashboard Table (Simplified: Removed Assertions Column)
    pages_html = ""
    for idx, p in enumerate(grouped_pages):
        is_page_pass = p["wrong"] == 0 and p["exceptions"] == 0 and p["right"] > 0
        page_status_class = "status-pass" if is_page_pass else "status-fail"
        page_status_text = "✓ PASSED" if is_page_pass else "✗ FAILED"
        page_status_value = "passed" if is_page_pass else "failed"

        # Auto-expand failed rows automatically for QA & Dev immediate troubleshooting
        row_display_style = "table-row" if not is_page_pass else "none"
        
        # Build defect helpers if page failed
        defect_helper = ""
        if not is_page_pass:
            if p["exceptions"] > 0:
                defect_helper = f"<div class='defect-msg'>⚠️ Raised {p['exceptions']} exception during execution</div>"
            elif p["wrong"] > 0:
                defect_helper = f"<div class='defect-msg'>❌ Failed {p['wrong']} verification checks</div>"

        # Build clean assertion text
        assertion_info = f"{p['right']} right"
        if p['wrong'] > 0:
            assertion_info += f" • <span style='color:var(--fail); font-weight:700;'>{p['wrong']} wrong</span>"
        if p['exceptions'] > 0:
            assertion_info += f" • <span style='color:#eab308; font-weight:700;'>{p['exceptions']} exceptions</span>"

        requests_sub_html = ""
        if p["requests"]:
            for r_idx, r in enumerate(p["requests"]):
                is_success = 200 <= r["status_code"] < 400 or r["status_code"] == 204
                status_class = "status-pass" if is_success else "status-fail"
                method_class = f"badge-{r['method'].lower()}"
                
                req_body = html_escape(r["request_body"])
                resp_body = html_escape(r["response_body"])
                curl_cmd = html_escape(r["curl"])
                
                # Get JSON file path for download button
                json_file = r.get("json_file", "")
                download_btn = ""
                if json_file:
                    download_btn = f'<a href="/files/{json_file}" download class="download-json-btn" title="Download complete test data with assertions">📥 Download JSON</a>'

                req_details_display = "block" if not is_success else "none"

                requests_sub_html += f"""
                <div class="nested-request-row">
                    <div class="nested-request-header" onclick="toggleRequest({idx}, {r_idx})">
                        <span class="badge {method_class}">{r['method']}</span>
                        <span class="nested-url" title="{html_escape(r['url'])}">{html_escape(r['url'])}</span>
                        <span class="status-indicator {status_class}">{r['status_code']}</span>
                        <span class="nested-time">{r['response_time_ms']} ms</span>
                        {download_btn}
                    </div>
                    <div id="req-details-{idx}-{r_idx}" class="nested-request-details" style="display: {req_details_display};">
                        <div class="curl-section">
                            <div class="section-header">
                                <h4>💻 cURL Replicator Command</h4>
                                <button class="copy-btn" onclick="copyText(decodeURIComponent('{html_escape(r['curl'].replace("'", "%27").replace('"', "%22"))}'), this, event)">📋 Copy cURL</button>
                            </div>
                            <div class="code-box">
                                <code>{curl_cmd}</code>
                            </div>
                        </div>
                        <div class="body-split">
                            <div class="body-block">
                                <h4>📤 Request Body</h4>
                                <pre><code>{req_body or '[Empty Body]'}</code></pre>
                            </div>
                            <div class="body-block">
                                <h4>📥 Response Body</h4>
                                <pre><code>{resp_body or '[Empty Body]'}</code></pre>
                            </div>
                        </div>
                    </div>
                </div>
                """
        else:
            requests_sub_html = "<div class='no-requests'>No API HTTP requests were logged for this page run.</div>"

        # Collect all JSON file paths for "Download All" button
        json_files = [r.get("json_file", "") for r in p["requests"] if r.get("json_file")]
        download_all_btn = ""
        if json_files:
            json_files_list = ",".join([f"'/files/{jf}'" for jf in json_files])
            download_all_btn = f'''
                <button class="download-all-btn" onclick="downloadAll([{json_files_list}], '{html_escape(p['name'])}')">
                    📦 Download All ({len(json_files)})
                </button>
            '''

        pages_html += f"""
        <tr class="summary-row" onclick="togglePage({idx})" data-name="{html_escape(p['name'])}" data-status="{page_status_value}" title="Click to view requests audit trail">
            <td>
                <div class="test-title">
                    <strong>{html_escape(p['name'])}</strong>
                    <span class="assertion-summary">{assertion_info}</span>
                </div>
            </td>
            <td>{p['timestamp']}</td>
            <td>
                <span class="status-indicator {page_status_class}">{page_status_text}</span>
                {defect_helper}
            </td>
        </tr>
        <tr id="page-details-{idx}" class="details-row" style="display: {row_display_style};">
            <td colspan="3">
                <div class="nested-requests-container">
                    <div class="audit-header">
                        <h3>🔍 Executed API Requests Audit Trail</h3>
                        {download_all_btn}
                    </div>
                    {requests_sub_html}
                </div>
            </td>
        </tr>
        """

    if not pages_html:
        pages_html = "<tr><td colspan='3' style='text-align:center; color:var(--text-sub);'>No active test session execution history found. Executing a test will populate this.</td></tr>"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ICICI Nirikshan AML Application API & UI Report - Latest Test Run</title>
    <link rel="shortcut icon" type="image/x-icon" href="/files/fitnesse/icici/img/favicon.ico" />
    <link rel="icon" type="image/x-icon" href="/files/fitnesse/icici/img/favicon.ico" />
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-main: #f8fafc;
            --bg-card: #ffffff;
            --text-main: #0f172a;
            --text-sub: #475569;
            --primary: #A6192E;
            --primary-hover: #7E1322;
            --success: #16a34a;
            --fail: #ef4444;
            --border: #e2e8f0;
            --code-bg: #1e293b;
            --code-text: #f8fafc;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-main);
            color: var(--text-main);
            padding: 40px 20px;
            line-height: 1.5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        /* Premium Header */
        header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
            border-bottom: 2px solid var(--border);
            padding-bottom: 20px;
        }}
        .header-title h1 {{
            font-size: 28px;
            font-weight: 800;
            background: linear-gradient(135deg, #7E1322 0%, #A6192E 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .header-title p {{
            font-size: 14px;
            color: var(--text-sub);
            margin-top: 4px;
        }}
        .header-meta {{
            text-align: right;
            font-size: 13px;
            color: var(--text-sub);
            line-height: 1.6;
        }}
        
        /* Master Status Banner */
        .status-banner {{
            padding: 16px 24px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 16px;
            margin-bottom: 30px;
            display: flex;
            align-items: center;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        }}
        .banner-pass {{ background: #dcfce7; color: #15803d; border: 1px solid #bbf7d0; }}
        .banner-fail {{ background: #fee2e2; color: #b91c1c; border: 1px solid #fecaca; }}
        .banner-empty {{ background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }}

        /* KPI Cards Grid */
        .dashboard-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .kpi-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            position: relative;
            overflow: hidden;
        }}
        .kpi-card::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; height: 4px;
        }}
        .kpi-total::before {{ background: var(--primary); }}
        .kpi-success::before {{ background: var(--success); }}
        .kpi-failed::before {{ background: var(--fail); }}
        .kpi-passrate::before {{ background: #eab308; }}
        
        .kpi-label {{
            font-size: 13px;
            font-weight: 600;
            color: var(--text-sub);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .kpi-value {{
            font-size: 32px;
            font-weight: 800;
            margin-top: 12px;
            color: var(--text-main);
        }}
        .progress-container {{
            display: flex;
            align-items: center;
            gap: 16px;
            margin-top: 10px;
        }}
        .progress-bar {{
            flex: 1;
            height: 8px;
            background: #e2e8f0;
            border-radius: 4px;
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            background: var(--success);
            border-radius: 4px;
        }}
        .progress-text {{
            font-size: 13px;
            font-weight: 700;
            color: var(--success);
        }}
        
        /* Assertions Horizontal summary */
        .fitnesse-assertions-bar {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 30px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            padding: 14px 24px;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 500;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        }}
        .assert-label {{
            font-weight: 700;
            color: var(--text-main);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 12px;
        }}
        .assert-badge {{
            padding: 4px 10px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 13px;
            border: 1px solid transparent;
        }}
        .assert-right {{ background: #dcfce7; color: #15803d; border-color: #bbf7d0; }}
        .assert-wrong {{ background: #fee2e2; color: #b91c1c; border-color: #fecaca; }}
        .assert-exceptions {{ background: #fef9c3; color: #854d0e; border-color: #fef08a; }}
        .assert-ignored {{ background: #f1f5f9; color: #475569; border-color: #e2e8f0; }}

        /* Main Table Section */
        .report-section {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
            padding: 30px;
        }}
        .section-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
            flex-wrap: wrap;
            gap: 16px;
        }}
        .section-header h2 {{
            font-size: 20px;
            font-weight: 700;
        }}
        .table-controls {{
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }}
        .search-box {{
            padding: 8px 16px;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 13px;
            font-family: inherit;
            outline: none;
            width: 240px;
            transition: border 0.15s;
        }}
        .search-box:focus {{
            border-color: var(--primary);
        }}
        .filter-controls {{
            display: flex;
            gap: 8px;
        }}
        .filter-btn {{
            background: #f1f5f9;
            border: 1px solid var(--border);
            color: var(--text-sub);
            padding: 6px 12px;
            font-size: 12px;
            font-weight: 600;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.15s;
        }}
        .filter-btn.active {{
            background: var(--primary);
            color: #fff;
            border-color: var(--primary);
        }}
        
        .report-table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }}
        .report-table th {{
            padding: 14px 16px;
            background: #f8fafc;
            border-bottom: 2px solid var(--border);
            font-size: 12px;
            font-weight: 700;
            color: var(--text-sub);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .report-table td {{
            padding: 16px 16px;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
            color: var(--text-main);
            vertical-align: middle;
        }}
        
        .summary-row {{
            cursor: pointer;
            transition: background 0.15s;
        }}
        .summary-row:hover {{
            background: #f8fafc;
        }}
        .test-title {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        .test-title strong {{
            font-size: 15px;
            font-weight: 700;
        }}
        .assertion-summary {{
            font-size: 11px;
            color: var(--text-sub);
            font-weight: 500;
        }}
        .defect-msg {{
            font-size: 11px;
            color: var(--fail);
            font-weight: 600;
            margin-top: 6px;
        }}
        .details-row td {{
            background: #f8fafc;
            padding: 0 !important;
        }}
        
        /* Nested request timeline */
        .nested-requests-container {{
            padding: 24px 30px;
            border-bottom: 2px solid var(--border);
            background: #f8fafc;
            border-left: 4px solid var(--primary);
        }}
        .audit-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }}
        .nested-requests-container h3 {{
            font-size: 14px;
            font-weight: 700;
            color: var(--text-sub);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin: 0;
        }}
        .download-all-btn {{
            background: linear-gradient(135deg, #0284c7 0%, #0ea5e9 100%);
            color: white;
            padding: 8px 16px;
            border: none;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .download-all-btn:hover {{
            background: linear-gradient(135deg, #0369a1 0%, #0284c7 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }}
        .nested-request-row {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            margin-bottom: 12px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        }}
        .nested-request-header {{
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 14px 20px;
            cursor: pointer;
            user-select: none;
            transition: background 0.15s;
        }}
        .nested-request-header:hover {{
            background: #f8fafc;
        }}
        .nested-url {{
            font-family: monospace;
            font-size: 13px;
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .nested-time {{
            font-size: 12px;
            color: var(--text-sub);
            font-weight: 600;
        }}
        .nested-request-details {{
            padding: 20px 24px;
            border-top: 1px solid var(--border);
            background: #fafafa;
            animation: slideDown 0.2s ease-out;
        }}
        
        /* Badges */
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            width: 70px;
            text-align: center;
        }}
        .badge-get {{ background: #dbeafe; color: #1e40af; }}
        .badge-post {{ background: #dcfce7; color: #166534; }}
        .badge-put {{ background: #fef9c3; color: #854d0e; }}
        .badge-patch {{ background: #f3e8ff; color: #6b21a8; }}
        .badge-delete {{ background: #fee2e2; color: #991b1b; }}
        .badge-options {{ background: #e2e8f0; color: #475569; }}
        .badge-head {{ background: #fae8ff; color: #86198f; }}
        
        .status-indicator {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            min-width: 90px;
            text-align: center;
            border: 1px solid transparent;
        }}
        .status-pass {{ background: #dcfce7; color: #15803d; border-color: #bbf7d0; }}
        .status-fail {{ background: #fee2e2; color: #b91c1c; border-color: #fecaca; }}
        
        /* Code blocks */
        .curl-section {{
            margin-bottom: 24px;
        }}
        .curl-section h4, .body-block h4 {{
            font-size: 13px;
            font-weight: 700;
            color: var(--text-sub);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}
        .code-box {{
            background: var(--code-bg);
            border-radius: 8px;
            padding: 16px;
            position: relative;
            overflow-x: auto;
        }}
        .code-box code {{
            color: var(--code-text);
            font-family: monospace;
            font-size: 12px;
            white-space: pre-wrap;
        }}
        .copy-btn {{
            position: absolute;
            top: 10px; right: 10px;
            background: rgba(255,255,255,0.1);
            color: #fff;
            border: 1px solid rgba(255,255,255,0.2);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s;
        }}
        .copy-btn:hover {{
            background: rgba(255,255,255,0.25);
        }}
        .download-json-btn {{
            background: linear-gradient(135deg, #059669 0%, #10b981 100%);
            color: white;
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            margin-left: 12px;
            transition: all 0.2s;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .download-json-btn:hover {{
            background: linear-gradient(135deg, #047857 0%, #059669 100%);
            transform: translateY(-1px);
            box-shadow: 0 4px 6px rgba(0,0,0,0.15);
        }}
        .body-split {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
        }}
        .body-block pre {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            overflow-x: auto;
            max-height: 250px;
        }}
        .body-block code {{
            font-family: monospace;
            font-size: 12px;
            color: var(--text-main);
            white-space: pre-wrap;
        }}
        .no-requests {{
            font-size: 13px;
            color: var(--text-sub);
            font-style: italic;
            text-align: center;
            padding: 20px;
            background: var(--bg-card);
            border: 1px dashed var(--border);
            border-radius: 8px;
        }}
        @keyframes slideDown {{
            from {{ opacity: 0; transform: translateY(-4px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
    </style>
    <script>
        function togglePage(idx) {{
            var el = document.getElementById("page-details-" + idx);
            if (el.style.display === "none") {{
                el.style.display = "table-row";
            }} else {{
                el.style.display = "none";
            }}
        }}

        function toggleRequest(pageIdx, reqIdx) {{
            var el = document.getElementById("req-details-" + pageIdx + "-" + reqIdx);
            if (el.style.display === "none") {{
                el.style.display = "block";
            }} else {{
                el.style.display = "none";
            }}
        }}

        function copyText(text, btn, e) {{
            e.stopPropagation();
            navigator.clipboard.writeText(text).then(function() {{
                var original = btn.textContent;
                btn.textContent = "✔️ Copied!";
                setTimeout(function() {{
                    btn.textContent = original;
                }}, 1500);
            }});
        }}

        function downloadAll(filePaths, testName) {{
            // Download all JSON files for a test
            if (!filePaths || filePaths.length === 0) {{
                alert("No test data files available to download.");
                return;
            }}
            
            // Download each file sequentially with small delay
            filePaths.forEach(function(path, index) {{
                setTimeout(function() {{
                    var link = document.createElement('a');
                    link.href = path;
                    link.download = '';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                }}, index * 200); // 200ms delay between downloads
            }});
            
            // Show success message
            setTimeout(function() {{
                alert('Downloaded ' + filePaths.length + ' test data file(s) for ' + testName);
            }}, filePaths.length * 200 + 100);
        }}

        function filterAndSearch() {{
            var searchInput = document.getElementById("search-input").value.toLowerCase();
            var activeFilter = document.querySelector(".filter-btn.active").getAttribute("data-filter");
            
            var summaryRows = document.querySelectorAll(".summary-row");
            summaryRows.forEach(function(row, idx) {{
                var name = row.getAttribute("data-name").toLowerCase();
                var status = row.getAttribute("data-status");
                
                var matchSearch = name.indexOf(searchInput) > -1;
                var matchFilter = (activeFilter === "all") || (activeFilter === status);
                
                var detailsRow = document.getElementById("page-details-" + idx);
                
                if (matchSearch && matchFilter) {{
                    row.style.display = "table-row";
                }} else {{
                    row.style.display = "none";
                    detailsRow.style.display = "none";
                }}
            }});
        }}
        
        function setFilter(type, btn) {{
            var btns = document.querySelectorAll(".filter-btn");
            btns.forEach(function(b) {{ b.classList.remove("active"); }});
            btn.classList.add("active");
            btn.setAttribute("data-filter", type);
            filterAndSearch();
        }}
    </script>
</head>
<body>
    <div class="container">
        <header>
            <div style="display: flex; align-items: center; gap: 16px;">
                <img src="/files/fitnesse/icici/img/icici-favicon.ico" alt="ICICI Nirikshan" style="height: 52px; width: auto; object-fit: contain;">
                <div class="header-title">
                    <h1>ICICI Nirikshan AML Application API & UI Report</h1>
                    <p>Latest Test Run - Showing Most Recent Results</p>
                </div>
            </div>
            <div class="header-meta">
                <strong>Active Suite:</strong> {html_escape(suite_name) if suite_name else 'N/A'}<br>
                <strong>Environment:</strong> UAT Testing Portal<br>
                <strong>Report Generated:</strong> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                <strong>Execution Duration:</strong> {formatted_duration}
            </div>
        </header>

        <!-- Master Status Banner -->
        <div class="status-banner {status_banner_class}">
            {status_banner_text}
        </div>

        <div class="fitnesse-assertions-bar">
            <span class="assert-label">Suite Assertions Summary:</span>
            <span class="assert-badge assert-right">{total_right} right</span>
            <span class="assert-badge assert-wrong">{total_wrong} wrong</span>
            <span class="assert-badge assert-ignored">{total_ignored} ignored</span>
            <span class="assert-badge assert-exceptions">{total_exceptions} exceptions</span>
        </div>

        <!-- KPI Cards based on Test Pages -->
        <section class="dashboard-grid">
            <div class="kpi-card kpi-total">
                <span class="kpi-label">Total Test Cases</span>
                <span class="kpi-value">{total_pages}</span>
            </div>
            <div class="kpi-card kpi-success">
                <span class="kpi-label">Succeeded Cases</span>
                <span class="kpi-value">{passed_pages}</span>
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {pass_rate}%;"></div>
                    </div>
                    <span class="progress-text">{pass_rate}%</span>
                </div>
            </div>
            <div class="kpi-card kpi-failed">
                <span class="kpi-label">Failed Cases</span>
                <span class="kpi-value">{failed_pages}</span>
            </div>
            <div class="kpi-card kpi-passrate">
                <span class="kpi-label">Pass Rate</span>
                <span class="kpi-value">{pass_rate}%</span>
            </div>
        </section>

        <!-- Single Unified Test Execution Dashboard -->
        <section class="report-section" style="margin-bottom: 40px;">
            <div class="section-header">
                <h2>📋 Test Suite Execution Summary</h2>
                <div class="table-controls">
                    <input type="text" id="search-input" class="search-box" placeholder="🔍 Search Test Cases..." onkeyup="filterAndSearch()">
                    <div class="filter-controls">
                        <button id="filter-all" class="filter-btn active" data-filter="all" onclick="setFilter('all', this)">All ({total_pages})</button>
                        <button id="filter-pass" class="filter-btn" onclick="setFilter('passed', this)">Passed ({passed_pages})</button>
                        <button id="filter-fail" class="filter-btn" onclick="setFilter('failed', this)">Failed ({failed_pages})</button>
                    </div>
                </div>
            </div>
            
            <table class="report-table">
                <thead>
                    <tr>
                        <th style="width: 50%;">Test Case Name</th>
                        <th style="width: 30%;">Last Execution Time</th>
                        <th style="width: 20%;">Status</th>
                    </tr>
                </thead>
                <tbody>
                    {pages_html}
                </tbody>
            </table>
        </section>
    </div>
</body>
</html>
"""
    try:
        os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception:
        pass
