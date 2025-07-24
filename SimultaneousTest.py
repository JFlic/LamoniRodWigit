#!/usr/bin/env python3
"""
Concurrent Ollama Model Test Script

This script tests if multiple Ollama model instances can handle
simultaneous requests by sending concurrent API calls and measuring
response times and success rates.
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime
from typing import List, Dict, Any
import statistics

class OllamaTestRunner:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen3:4b"):
        self.base_url = base_url
        self.model = model
        self.results = []
    
    async def check_ollama_status(self) -> Dict[str, Any]:
        """Check if Ollama service is running and responsive."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/version") as response:
                    if response.status == 200:
                        version_info = await response.json()
                        print(f"✅ Ollama is running - Version: {version_info.get('version', 'Unknown')}")
                        return {"status": "running", "version": version_info}
                    else:
                        print(f"❌ Ollama responded with status: {response.status}")
                        return {"status": "error", "code": response.status}
        except Exception as e:
            print(f"❌ Failed to connect to Ollama: {e}")
            return {"status": "offline", "error": str(e)}
    
    async def check_model_availability(self) -> bool:
        """Check if the specified model is available."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [model['name'] for model in data.get('models', [])]
                        if self.model in models:
                            print(f"✅ Model '{self.model}' is available")
                            return True
                        else:
                            print(f"❌ Model '{self.model}' not found. Available models: {models}")
                            return False
        except Exception as e:
            print(f"❌ Failed to check model availability: {e}")
            return False
    
    async def send_single_request(self, session: aiohttp.ClientSession, request_id: int, prompt: str) -> Dict[str, Any]:
        """Send a single request to Ollama and measure response time."""
        start_time = time.time()
        request_data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 50  # Limit response length for faster testing
            }
        }
        
        try:
            async with session.post(
                f"{self.base_url}/api/generate",
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                end_time = time.time()
                response_time = end_time - start_time
                
                if response.status == 200:
                    data = await response.json()
                    result = {
                        "request_id": request_id,
                        "status": "success",
                        "response_time": response_time,
                        "start_time": start_time,
                        "end_time": end_time,
                        "prompt": prompt,
                        "response_length": len(data.get("response", "")),
                        "total_duration": data.get("total_duration", 0),
                        "load_duration": data.get("load_duration", 0),
                        "prompt_eval_count": data.get("prompt_eval_count", 0),
                        "eval_count": data.get("eval_count", 0)
                    }
                    print(f"✅ Request {request_id}: {response_time:.2f}s")
                else:
                    result = {
                        "request_id": request_id,
                        "status": "error",
                        "response_time": response_time,
                        "start_time": start_time,
                        "end_time": end_time,
                        "error": f"HTTP {response.status}",
                        "prompt": prompt
                    }
                    print(f"❌ Request {request_id}: HTTP {response.status}")
                
                return result
                
        except asyncio.TimeoutError:
            end_time = time.time()
            result = {
                "request_id": request_id,
                "status": "timeout",
                "response_time": end_time - start_time,
                "start_time": start_time,
                "end_time": end_time,
                "error": "Request timed out",
                "prompt": prompt
            }
            print(f"⏰ Request {request_id}: Timeout after {result['response_time']:.2f}s")
            return result
            
        except Exception as e:
            end_time = time.time()
            result = {
                "request_id": request_id,
                "status": "exception",
                "response_time": end_time - start_time,
                "start_time": start_time,
                "end_time": end_time,
                "error": str(e),
                "prompt": prompt
            }
            print(f"💥 Request {request_id}: Exception - {e}")
            return result
    
    async def run_concurrent_test(self, num_requests: int = 5, custom_prompts: List[str] = None) -> Dict[str, Any]:
        """Run multiple concurrent requests to test parallel processing."""
        print(f"\n🚀 Starting concurrent test with {num_requests} simultaneous requests...")
        print(f"⏱️  Test started at: {datetime.now().strftime('%H:%M:%S')}")
        
        # Default prompts if none provided
        if custom_prompts is None:
            prompts = [
                "What is artificial intelligence?",
                "Explain quantum computing in simple terms.",
                "Write a short poem about technology.",
                "What are the benefits of renewable energy?",
                "Describe the process of photosynthesis.",
                "What is machine learning?",
                "Explain the concept of blockchain.",
                "What are the applications of 5G technology?",
                "Describe the importance of cybersecurity.",
                "What is the future of space exploration?"
            ]
        else:
            prompts = custom_prompts
        
        # Use prompts cyclically if we need more requests than prompts
        selected_prompts = [prompts[i % len(prompts)] for i in range(num_requests)]
        
        # Create concurrent tasks
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.send_single_request(session, i+1, prompt) 
                for i, prompt in enumerate(selected_prompts)
            ]
            
            # Execute all requests concurrently
            test_start = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            test_end = time.time()
            
            # Process results
            self.results = [r for r in results if isinstance(r, dict)]
            total_test_time = test_end - test_start
            
            return self.analyze_results(total_test_time)
    
    def analyze_results(self, total_test_time: float) -> Dict[str, Any]:
        """Analyze the test results and provide insights."""
        if not self.results:
            return {"error": "No results to analyze"}
        
        successful_requests = [r for r in self.results if r["status"] == "success"]
        failed_requests = [r for r in self.results if r["status"] != "success"]
        
        response_times = [r["response_time"] for r in successful_requests]
        
        # Check for true concurrency by looking at overlapping time windows
        overlapping_requests = 0
        for i, req1 in enumerate(self.results):
            for req2 in self.results[i+1:]:
                # Check if requests overlapped in time
                if (req1["start_time"] < req2["end_time"] and req2["start_time"] < req1["end_time"]):
                    overlapping_requests += 1
        
        analysis = {
            "test_summary": {
                "total_requests": len(self.results),
                "successful_requests": len(successful_requests),
                "failed_requests": len(failed_requests),
                "success_rate": len(successful_requests) / len(self.results) * 100,
                "total_test_duration": total_test_time,
                "overlapping_request_pairs": overlapping_requests
            },
            "timing_analysis": {},
            "concurrency_analysis": {},
            "performance_metrics": {}
        }
        
        if response_times:
            analysis["timing_analysis"] = {
                "average_response_time": statistics.mean(response_times),
                "median_response_time": statistics.median(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "std_deviation": statistics.stdev(response_times) if len(response_times) > 1 else 0
            }
        
        # Analyze concurrency
        if overlapping_requests > 0:
            analysis["concurrency_analysis"] = {
                "concurrent_execution_detected": True,
                "overlapping_request_pairs": overlapping_requests,
                "concurrency_evidence": "Requests executed with overlapping time windows",
                "parallel_processing_likely": total_test_time < sum(response_times) * 0.8
            }
        else:
            analysis["concurrency_analysis"] = {
                "concurrent_execution_detected": False,
                "evidence": "No overlapping request execution detected",
                "possible_sequential_processing": True
            }
        
        # Performance insights
        if successful_requests:
            total_tokens = sum(r.get("eval_count", 0) for r in successful_requests)
            avg_tokens_per_second = total_tokens / sum(response_times) if sum(response_times) > 0 else 0
            
            analysis["performance_metrics"] = {
                "total_tokens_generated": total_tokens,
                "average_tokens_per_second": avg_tokens_per_second,
                "requests_per_second": len(successful_requests) / total_test_time if total_test_time > 0 else 0
            }
        
        return analysis
    
    def print_detailed_report(self, analysis: Dict[str, Any]):
        """Print a detailed analysis report."""
        print("\n" + "="*80)
        print("🔍 CONCURRENT OLLAMA TEST RESULTS")
        print("="*80)
        
        summary = analysis["test_summary"]
        print(f"📊 Test Summary:")
        print(f"   Total Requests: {summary['total_requests']}")
        print(f"   Successful: {summary['successful_requests']}")
        print(f"   Failed: {summary['failed_requests']}")
        print(f"   Success Rate: {summary['success_rate']:.1f}%")
        print(f"   Total Test Duration: {summary['total_test_duration']:.2f}s")
        
        if "timing_analysis" in analysis and analysis["timing_analysis"]:
            timing = analysis["timing_analysis"]
            print(f"\n⏱️  Timing Analysis:")
            print(f"   Average Response Time: {timing['average_response_time']:.2f}s")
            print(f"   Median Response Time: {timing['median_response_time']:.2f}s")
            print(f"   Fastest Response: {timing['min_response_time']:.2f}s")
            print(f"   Slowest Response: {timing['max_response_time']:.2f}s")
            print(f"   Standard Deviation: {timing['std_deviation']:.2f}s")
        
        concurrency = analysis["concurrency_analysis"]
        print(f"\n🔄 Concurrency Analysis:")
        if concurrency["concurrent_execution_detected"]:
            print(f"   ✅ CONCURRENT EXECUTION DETECTED!")
            print(f"   📈 Overlapping Request Pairs: {concurrency['overlapping_request_pairs']}")
            print(f"   💡 Evidence: {concurrency['concurrency_evidence']}")
            if concurrency.get("parallel_processing_likely"):
                print(f"   🚀 Parallel processing appears to be working efficiently")
        else:
            print(f"   ❌ No concurrent execution detected")
            print(f"   ⚠️  Requests may be processed sequentially")
        
        if "performance_metrics" in analysis and analysis["performance_metrics"]:
            perf = analysis["performance_metrics"]
            print(f"\n📈 Performance Metrics:")
            print(f"   Total Tokens Generated: {perf['total_tokens_generated']}")
            print(f"   Average Tokens/Second: {perf['average_tokens_per_second']:.1f}")
            print(f"   Requests/Second: {perf['requests_per_second']:.2f}")
        
        print("\n" + "="*80)

async def main():
    """Main function to run the concurrent Ollama test."""
    print("🧪 Ollama Concurrent Model Test")
    print("================================")
    
    # Initialize test runner
    tester = OllamaTestRunner()
    
    # Check Ollama status
    print("\n1️⃣ Checking Ollama service status...")
    status = await tester.check_ollama_status()
    if status["status"] != "running":
        print("Cannot proceed - Ollama service is not available")
        return
    
    # Check model availability
    print("\n2️⃣ Checking model availability...")
    model_available = await tester.check_model_availability()
    if not model_available:
        print("Cannot proceed - Required model is not available")
        return
    
    # Run concurrent test
    print("\n3️⃣ Running concurrent test...")
    
    # Test with different numbers of concurrent requests
    test_scenarios = [3, 5, 8]  # Test with 3, 5, and 8 concurrent requests
    
    for num_requests in test_scenarios:
        print(f"\n{'='*60}")
        print(f"Testing with {num_requests} concurrent requests")
        print(f"{'='*60}")
        
        analysis = await tester.run_concurrent_test(num_requests)
        tester.print_detailed_report(analysis)
        
        # Wait a bit between tests
        if num_requests != test_scenarios[-1]:
            print("\n⏳ Waiting 10 seconds before next test...")
            await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n💥 Test failed with error: {e}")