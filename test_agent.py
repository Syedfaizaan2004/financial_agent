import requests
import json
import time

url = 'http://localhost:8000/agent'
intents = [
    {'query': 'Analyze AAPL', 'mode': 'quick', 'analysis_type': 'overview'},
    {'query': 'Analyze TSLA', 'mode': 'deep', 'analysis_type': 'overview'},
    {'query': 'Compare AAPL and MSFT', 'mode': 'deep', 'analysis_type': 'compare'},
    {'query': 'Forecast AAPL direction', 'mode': 'deep', 'analysis_type': 'forecast'},
    {'query': 'Bull vs Bear for AAPL', 'mode': 'deep', 'analysis_type': 'bullbear'},
    {'query': 'Hidden risks for AAPL', 'mode': 'deep', 'analysis_type': 'hidden_risks'},
    {'query': 'What is next for AAPL', 'mode': 'deep', 'analysis_type': 'next_analysis'}
]

print("Starting backend suite...")
for req in intents:
    print(f"Testing {req['analysis_type']} ({req['mode']})...")
    start = time.time()
    try:
        r = requests.post(url, json=req)
        data = r.json()
        status = data.get('status')
        errors = data.get('agent_errors', [])
        elapsed = time.time() - start
        print(f"  [{elapsed:.2f}s] Status: {status} | Errors: {len(errors)}")
        if status != 'ok':
            print(f"  [!] Failed or Partial: {errors}")
            
        if req['analysis_type'] == 'compare':
            assert 'peer_comparison' in data['raw_data'], "Missing peer_comparison in compare intent"
            assert len(data['company_snapshot']) == 5, "Company snapshot missing in compare intent"
        elif req['analysis_type'] == 'bullbear':
            assert len(data['investment_memo']['bear_case']) > 0, "Missing bear case in bullbear memo"
            assert len(data['investment_memo']['bull_case']) > 0, "Missing bull case in bullbear memo"
            
    except Exception as e:
        print(f"  [!] Request Failed: {e}")
        
print("Execution suite complete.")
