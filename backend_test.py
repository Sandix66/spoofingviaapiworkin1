import requests
import sys
import json
from datetime import datetime

class VoiceSpoofAPITester:
    def __init__(self, base_url="https://spoofing-connect.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} - {name}")
        if details:
            print(f"   Details: {details}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

            print(f"   Status: {response.status_code}")
            
            success = response.status_code == expected_status
            
            if success:
                try:
                    response_data = response.json()
                    self.log_test(name, True, f"Status: {response.status_code}")
                    return True, response_data
                except:
                    self.log_test(name, True, f"Status: {response.status_code}, No JSON response")
                    return True, {}
            else:
                try:
                    error_data = response.json()
                    self.log_test(name, False, f"Expected {expected_status}, got {response.status_code}. Error: {error_data}")
                except:
                    self.log_test(name, False, f"Expected {expected_status}, got {response.status_code}. Response: {response.text}")
                return False, {}

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test basic health endpoint"""
        return self.run_test("Health Check", "GET", "health", 200)

    def test_register(self, email, password, name):
        """Test user registration"""
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data={"email": email, "password": password, "name": name}
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            if 'user' in response:
                self.user_id = response['user'].get('id')
            print(f"   Token obtained: {self.token[:20]}...")
            return True
        return False

    def test_login(self, email, password):
        """Test user login"""
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data={"email": email, "password": password}
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            if 'user' in response:
                self.user_id = response['user'].get('id')
            print(f"   Token obtained: {self.token[:20]}...")
            return True
        return False

    def test_get_me(self):
        """Test get current user"""
        if not self.token:
            self.log_test("Get Current User", False, "No token available")
            return False
            
        success, response = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200
        )
        return success

    def test_send_voice_call(self):
        """Test sending a voice call"""
        if not self.token:
            self.log_test("Send Voice Call", False, "No token available")
            return False, None
            
        call_data = {
            "phone_number": "+6281234567890",
            "caller_id": "+6221123456",
            "message_text": "Halo, ini adalah test panggilan dari aplikasi Voice Spoof untuk project kampus.",
            "language": "id",
            "speech_rate": 1.0
        }
        
        success, response = self.run_test(
            "Send Voice Call",
            "POST",
            "voice/call",
            200,
            data=call_data
        )
        
        call_id = None
        if success and 'id' in response:
            call_id = response['id']
            print(f"   Call ID: {call_id}")
            print(f"   Status: {response.get('status', 'unknown')}")
            if response.get('error_message'):
                print(f"   Error: {response['error_message']}")
        
        return success, call_id

    def test_get_call_history(self):
        """Test getting call history"""
        if not self.token:
            self.log_test("Get Call History", False, "No token available")
            return False
            
        success, response = self.run_test(
            "Get Call History",
            "GET",
            "voice/history?limit=10",
            200
        )
        
        if success:
            call_count = len(response) if isinstance(response, list) else 0
            print(f"   Found {call_count} calls in history")
        
        return success

    def test_get_call_stats(self):
        """Test getting call statistics"""
        if not self.token:
            self.log_test("Get Call Stats", False, "No token available")
            return False
            
        success, response = self.run_test(
            "Get Call Statistics",
            "GET",
            "voice/stats",
            200
        )
        
        if success:
            print(f"   Total calls: {response.get('total_calls', 0)}")
            print(f"   Completed: {response.get('completed_calls', 0)}")
            print(f"   Failed: {response.get('failed_calls', 0)}")
            print(f"   Pending: {response.get('pending_calls', 0)}")
        
        return success

    def test_get_call_detail(self, call_id):
        """Test getting specific call details"""
        if not self.token or not call_id:
            self.log_test("Get Call Detail", False, "No token or call_id available")
            return False
            
        success, response = self.run_test(
            "Get Call Detail",
            "GET",
            f"voice/call/{call_id}",
            200
        )
        return success

    def run_all_tests(self):
        """Run comprehensive API tests"""
        print("=" * 60)
        print("🚀 VOICE SPOOF API TESTING STARTED")
        print("=" * 60)
        
        # Test credentials
        test_email = "test@kampus.ac.id"
        test_password = "password123"
        test_name = "Test User"
        
        # 1. Health check
        self.test_health_check()
        
        # 2. Test registration
        print(f"\n📝 Testing with user: {test_email}")
        if not self.test_register(test_email, test_password, test_name):
            # If registration fails, try login (user might already exist)
            print("Registration failed, trying login...")
            if not self.test_login(test_email, test_password):
                print("❌ Both registration and login failed. Stopping tests.")
                return self.print_summary()
        
        # 3. Test get current user
        self.test_get_me()
        
        # 4. Test voice call functionality
        call_success, call_id = self.test_send_voice_call()
        
        # 5. Test call history
        self.test_get_call_history()
        
        # 6. Test call statistics
        self.test_get_call_stats()
        
        # 7. Test call detail if we have a call_id
        if call_id:
            self.test_get_call_detail(call_id)
        
        return self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 ALL TESTS PASSED!")
            return 0
        else:
            print(f"\n⚠️  {self.tests_run - self.tests_passed} TESTS FAILED")
            
            # Print failed tests
            print("\nFailed Tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  ❌ {result['test']}: {result['details']}")
            
            return 1

def main():
    """Main test function"""
    tester = VoiceSpoofAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())