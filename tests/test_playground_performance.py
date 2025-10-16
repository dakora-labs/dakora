"""
Performance and stress tests for Dakora Playground API
"""
import pytest
import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


@pytest.mark.performance
class TestPlaygroundPerformance:
    """Performance tests for playground API endpoints"""

    def test_health_endpoint_response_time(self, playground_url):
        """Test that health endpoint responds quickly"""
        start_time = time.time()
        response = requests.get(f"{playground_url}/api/health")
        end_time = time.time()

        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 0.1  # Should respond in under 100ms

    def test_template_list_response_time(self, playground_url):
        """Test that template list endpoint responds quickly"""
        start_time = time.time()
        response = requests.get(f"{playground_url}/api/templates")
        end_time = time.time()

        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 0.2  # Should respond in under 200ms

    def test_template_render_response_time(self, playground_url):
        """Test that template rendering completes quickly"""
        payload = {
            "inputs": {
                "name": "PerformanceTest"
            }
        }

        start_time = time.time()
        response = requests.post(
            f"{playground_url}/api/templates/simple-greeting/render",
            json=payload
        )
        end_time = time.time()

        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 0.5  # Should render in under 500ms

    def test_complex_template_render_performance(self, playground_url):
        """Test performance of complex template rendering"""
        payload = {
            "inputs": {
                "name": "ComplexPerformanceTest",
                "age": 30,
                "hobbies": ["reading", "coding", "gaming", "hiking", "photography"],
                "message": "This is a longer message to test template rendering performance with more complex data structures and longer text content."
            }
        }

        start_time = time.time()
        response = requests.post(
            f"{playground_url}/api/templates/complex-template/render",
            json=payload
        )
        end_time = time.time()

        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 1.0  # Should render complex template in under 1s


class TestPlaygroundConcurrency:
    """Concurrency and stress tests"""

    def test_concurrent_health_checks(self, playground_url):
        """Test handling of concurrent health check requests"""
        def make_health_request():
            response = requests.get(f"{playground_url}/api/health")
            return response.status_code == 200

        # Make 20 concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_health_request) for _ in range(20)]
            results = [future.result() for future in as_completed(futures)]

        # All requests should succeed
        assert all(results), "Some concurrent health checks failed"

    def test_concurrent_template_renders(self, playground_url):
        """Test concurrent template rendering"""
        def render_template(name_suffix):
            payload = {
                "inputs": {
                    "name": f"ConcurrentTest{name_suffix}"
                }
            }
            response = requests.post(
                f"{playground_url}/api/templates/simple-greeting/render",
                json=payload
            )
            return response.status_code == 200, response.json() if response.status_code == 200 else None

        # Make 15 concurrent render requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(render_template, i) for i in range(15)]
            results = [future.result() for future in as_completed(futures)]

        # All requests should succeed
        success_results = [result[0] for result in results]
        assert all(success_results), "Some concurrent renders failed"

        # Check that responses are correct
        successful_responses = [result[1] for result in results if result[0]]
        for response_data in successful_responses:
            assert response_data is not None, "Response data should not be None"
            assert "rendered" in response_data, "Response should contain 'rendered' field"
            assert "ConcurrentTest" in response_data["rendered"], "Rendered output should contain test marker"

    def test_mixed_concurrent_operations(self, playground_url):
        """Test mix of different concurrent operations"""
        results = []

        def health_check():
            response = requests.get(f"{playground_url}/api/health")
            results.append(("health", response.status_code == 200))

        def list_templates():
            response = requests.get(f"{playground_url}/api/templates")
            results.append(("list", response.status_code == 200))

        def get_template():
            response = requests.get(f"{playground_url}/api/templates/simple-greeting")
            results.append(("get", response.status_code == 200))

        def render_template():
            payload = {"inputs": {"name": "MixedTest"}}
            response = requests.post(
                f"{playground_url}/api/templates/simple-greeting/render",
                json=payload
            )
            results.append(("render", response.status_code == 200))

        def get_examples():
            response = requests.get(f"{playground_url}/api/examples")
            results.append(("examples", response.status_code == 200))

        # Create mixed workload
        operations = [health_check, list_templates, get_template, render_template, get_examples]
        threads = []

        # Start multiple threads for each operation type
        for _ in range(3):  # 3 of each operation type
            for operation in operations:
                thread = threading.Thread(target=operation)
                threads.append(thread)
                thread.start()

        # Wait for all operations to complete
        for thread in threads:
            thread.join()

        # All operations should succeed
        success_by_type = {}
        for operation_type, success in results:
            if operation_type not in success_by_type:
                success_by_type[operation_type] = []
            success_by_type[operation_type].append(success)

        for operation_type, successes in success_by_type.items():
            assert all(successes), f"Some {operation_type} operations failed"

    def test_rapid_successive_requests(self, playground_url):
        """Test handling of rapid successive requests from single client"""
        results = []
        payload = {"inputs": {"name": "RapidTest"}}

        # Make 30 requests as fast as possible
        for i in range(30):
            response = requests.post(
                f"{playground_url}/api/templates/simple-greeting/render",
                json=payload
            )
            results.append(response.status_code == 200)

        # All requests should succeed
        success_rate = sum(results) / len(results)
        assert success_rate >= 0.95, f"Success rate too low: {success_rate}"

    def test_large_input_handling(self, playground_url):
        """Test handling of large input data"""
        # Create large input string (10KB)
        large_text = "A" * 10000

        payload = {
            "inputs": {
                "name": "LargeInputTest",
                "message": large_text
            }
        }

        start_time = time.time()
        response = requests.post(
            f"{playground_url}/api/templates/complex-template/render",
            json=payload
        )
        end_time = time.time()

        assert response.status_code == 200
        assert large_text in response.json()["rendered"]

        # Should still complete in reasonable time even with large input
        response_time = end_time - start_time
        assert response_time < 2.0

    def test_memory_usage_stability(self, playground_url):
        """Test that repeated operations don't cause memory leaks"""
        # This test makes many requests to check for potential memory leaks
        # In a real environment, you'd monitor actual memory usage

        for batch in range(5):  # 5 batches of operations
            batch_results = []

            # Make 20 requests per batch
            for i in range(20):
                payload = {"inputs": {"name": f"MemoryTest{batch}_{i}"}}
                response = requests.post(
                    f"{playground_url}/api/templates/simple-greeting/render",
                    json=payload
                )
                batch_results.append(response.status_code == 200)

            # All requests in batch should succeed
            assert all(batch_results), f"Batch {batch} had failures"

            # Small delay between batches
            time.sleep(0.1)


class TestPlaygroundStress:
    """Stress tests with high load"""

    @pytest.mark.slow
    def test_high_concurrency_stress(self, playground_url):
        """Stress test with high number of concurrent requests"""
        def make_request(request_id):
            try:
                payload = {"inputs": {"name": f"StressTest{request_id}"}}
                response = requests.post(
                    f"{playground_url}/api/templates/simple-greeting/render",
                    json=payload,
                    timeout=5  # 5 second timeout
                )
                return response.status_code == 200
            except requests.exceptions.Timeout:
                return False
            except Exception:
                return False

        # High concurrency stress test - 100 requests with 20 concurrent workers
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request, i) for i in range(100)]
            results = [future.result() for future in as_completed(futures)]

        success_rate = sum(results) / len(results)
        # Allow for some failures under high stress, but should still be mostly successful
        assert success_rate >= 0.8, f"Success rate under stress too low: {success_rate}"

    @pytest.mark.slow
    def test_sustained_load(self, playground_url):
        """Test sustained load over time"""
        results = []
        duration = 10  # 10 seconds of sustained load
        start_time = time.time()

        def sustained_requests():
            request_count = 0
            while time.time() - start_time < duration:
                try:
                    payload = {"inputs": {"name": f"SustainedTest{request_count}"}}
                    response = requests.post(
                        f"{playground_url}/api/templates/simple-greeting/render",
                        json=payload,
                        timeout=2
                    )
                    results.append(response.status_code == 200)
                    request_count += 1
                    time.sleep(0.05)  # Small delay between requests
                except Exception:
                    results.append(False)

        # Run sustained load test with 3 concurrent workers
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=sustained_requests)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should handle sustained load well
        if results:  # Only check if we actually made requests
            success_rate = sum(results) / len(results)
            assert success_rate >= 0.85, f"Sustained load success rate too low: {success_rate}"
            assert len(results) >= 100, "Should have made at least 100 requests during sustained test"


class TestPlaygroundResourceUsage:
    """Tests for resource usage and limits"""

    def test_request_size_limits(self, playground_url):
        """Test handling of very large requests"""
        # Create extremely large input (1MB)
        huge_text = "X" * (1024 * 1024)

        payload = {
            "inputs": {
                "name": "HugeInputTest",
                "message": huge_text
            }
        }

        try:
            response = requests.post(
                f"{playground_url}/api/templates/complex-template/render",
                json=payload,
                timeout=10
            )
            # Server should either handle it or reject with appropriate error
            assert response.status_code in [200, 413, 422]  # OK, Request Too Large, or Validation Error

            if response.status_code == 200:
                # If it succeeded, verify the content
                assert huge_text in response.json()["rendered"]

        except requests.exceptions.Timeout:
            # Timeout is acceptable for extremely large requests
            pass

    def test_concurrent_large_requests(self, playground_url):
        """Test handling of multiple concurrent large requests"""
        # Large but reasonable input size (50KB each)
        large_text = "Y" * (50 * 1024)

        def make_large_request(request_id):
            payload = {
                "inputs": {
                    "name": f"LargeRequest{request_id}",
                    "message": large_text
                }
            }
            try:
                response = requests.post(
                    f"{playground_url}/api/templates/complex-template/render",
                    json=payload,
                    timeout=15
                )
                return response.status_code == 200
            except Exception:
                return False

        # 5 concurrent large requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_large_request, i) for i in range(5)]
            results = [future.result() for future in as_completed(futures)]

        # Most should succeed
        success_rate = sum(results) / len(results)
        assert success_rate >= 0.6, f"Large request success rate too low: {success_rate}"