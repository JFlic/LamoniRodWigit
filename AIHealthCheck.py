#!/usr/bin/env python3
"""
Health check script to test multiple AI instances
"""
import requests
import time
import json
import concurrent.futures
from datetime import datetime

# Configuration
OLLAMA_ENDPOINTS = [
    "http://localhost:11434",
    "http://localhost:11435"
]

API_ENDPOINTS = [
    "http://localhost:8001",
    "http://localhost:8002", 
    "http://localhost:8003"
]

NGINX_ENDPOINT = "http://localhost:80"

def test_ollama_instance(endpoint):
    """Test individual Ollama instance"""
    try:
        # Test if service is running
        response = requests.get(f"{endpoint}/api/tags", timeout=10)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"✅ {endpoint} - Running with {len(models)} models")
            return True
        else:
            print(f"❌ {endpoint} - HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ {endpoint} - Error: {e}")
        return False

def test_ollama_generation(endpoint, prompt="Hello, how are you?"):
    """Test Ollama generation capability"""
    try:
        start_time = time.time()
        response = requests.post(
            f"{endpoint}/api/generate",
            json={
                "model": "qwen2.5:7b",  # or your model name
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )
        end_time = time.time()
        
        if response.status_code == 200:
            result = response.json()
            duration = end_time - start_time
            print(f"✅ {endpoint} - Generated response in {duration:.2f}s")
            print(f"   Response: {result.get('response', '')[:100]}...")
            return True, duration
        else:
            print(f"❌ {endpoint} - Generation failed: {response.status_code}")
            return False, 0
    except Exception as e:
        print(f"❌ {endpoint} - Generation error: {e}")
        return False, 0

def test_api_instance(endpoint):
    """Test individual API instance"""
    try:
        # Test health endpoint (you may need to adjust this)
        response = requests.get(f"{endpoint}/health", timeout=10)
        if response.status_code == 200:
            print(f"✅ {endpoint} - API healthy")
            return True
        else:
            print(f"❌ {endpoint} - API unhealthy: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ {endpoint} - API error: {e}")
        return False

def test_concurrent_requests(endpoint, num_requests=5):
    """Test concurrent request handling"""
    print(f"\n🔄 Testing {num_requests} concurrent requests to {endpoint}")
    
    def make_request(request_id):
        try:
            start_time = time.time()
            response = requests.post(
                f"{endpoint}/api/generate",
                json={
                    "model": "qwen2.5:7b",
                    "prompt": f"Request {request_id}: What is 2+2?",
                    "stream": False
                },
                timeout=60
            )
            end_time = time.time()
            
            if response.status_code == 200:
                return {
                    'id': request_id,
                    'success': True,
                    'duration': end_time - start_time,
                    'response_length': len(response.json().get('response', ''))
                }
            else:
                return {
                    'id': request_id,
                    'success': False,
                    'duration': end_time - start_time,
                    'error': f"HTTP {response.status_code}"
                }
        except Exception as e:
            return {
                'id': request_id,
                'success': False,
                'duration': 0,
                'error': str(e)
            }
    
    # Execute concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
        futures = [executor.submit(make_request, i) for i in range(num_requests)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    # Analyze results
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    if successful:
        avg_duration = sum(r['duration'] for r in successful) / len(successful)
        max_duration = max(r['duration'] for r in successful)
        min_duration = min(r['duration'] for r in successful)
        
        print(f"✅ {len(successful)}/{num_requests} requests successful")
        print(f"   Average duration: {avg_duration:.2f}s")
        print(f"   Min duration: {min_duration:.2f}s")
        print(f"   Max duration: {max_duration:.2f}s")
    
    if failed:
        print(f"❌ {len(failed)} requests failed:")
        for f in failed:
            print(f"   Request {f['id']}: {f['error']}")
    
    return len(successful), len(failed)

def test_load_balancing():
    """Test if load balancer distributes requests"""
    print("\n🔄 Testing load balancing...")
    
    # Make multiple requests and check if they hit different instances
    # This requires your API to return which instance handled the request
    requests_made = []
    
    for i in range(10):
        try:
            response = requests.get(f"{NGINX_ENDPOINT}/api/health", timeout=10)
            if response.status_code == 200:
                # If your API returns instance info
                instance_info = response.headers.get('X-Instance-ID', 'unknown')
                requests_made.append(instance_info)
        except Exception as e:
            print(f"Load balancing test request {i} failed: {e}")
    
    if requests_made:
        unique_instances = set(requests_made)
        print(f"✅ Requests distributed across {len(unique_instances)} instances")
        for instance in unique_instances:
            count = requests_made.count(instance)
            print(f"   {instance}: {count} requests")
    else:
        print("❌ Could not test load balancing")

def main():
    print("🚀 Testing Multiple AI Instances")
    print("=" * 50)
    
    # Test individual Ollama instances
    print("\n1. Testing Ollama Instances:")
    ollama_results = []
    for endpoint in OLLAMA_ENDPOINTS:
        result = test_ollama_instance(endpoint)
        ollama_results.append(result)
    
    # Test Ollama generation
    print("\n2. Testing Ollama Generation:")
    for endpoint in OLLAMA_ENDPOINTS:
        test_ollama_generation(endpoint)
    
    # Test API instances
    print("\n3. Testing API Instances:")
    api_results = []
    for endpoint in API_ENDPOINTS:
        result = test_api_instance(endpoint)
        api_results.append(result)
    
    # Test concurrent requests
    print("\n4. Testing Concurrent Requests:")
    for endpoint in OLLAMA_ENDPOINTS:
        successful, failed = test_concurrent_requests(endpoint, 3)
    
    # Test load balancing
    test_load_balancing()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Summary:")
    print(f"Ollama instances healthy: {sum(ollama_results)}/{len(OLLAMA_ENDPOINTS)}")
    print(f"API instances healthy: {sum(api_results)}/{len(API_ENDPOINTS)}")
    
    if all(ollama_results) and all(api_results):
        print("🎉 All instances are working properly!")
    else:
        print("⚠️  Some instances need attention")

if __name__ == "__main__":
    main()