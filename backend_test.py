import requests
import sys
import json
from datetime import datetime

class VoiceSpoofAPITester:
    def __init__(self, base_url="https://ivrflow.preview.emergentagent.com/api"):
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

    def test_initiate_otp_call(self):
        """Test initiating an OTP bot call"""
        if not self.token:
            self.log_test("Initiate OTP Call", False, "No token available")
            return False, None
            
        call_config = {
            "recipient_number": "+14155552671",
            "caller_id": "+14245298701",
            "recipient_name": "John Smith",
            "service_name": "Banking Account",
            "otp_digits": 6,
            "language": "en"
        }
        
        success, response = self.run_test(
            "Initiate OTP Call",
            "POST",
            "otp/initiate-call",
            200,
            data=call_config
        )
        
        session_id = None
        if success and 'session_id' in response:
            session_id = response['session_id']
            print(f"   Session ID: {session_id}")
            print(f"   Call ID: {response.get('call_id', 'N/A')}")
            print(f"   Status: {response.get('status', 'unknown')}")
        
        return success, session_id

    def test_request_info_otp_email(self, session_id):
        """Test requesting Email OTP (6 digits)"""
        if not self.token or not session_id:
            self.log_test("Request Info - Email OTP", False, "No token or session_id available")
            return False
            
        success, response = self.run_test(
            "Request Info - Email OTP",
            "POST",
            f"otp/request-info/{session_id}?info_type=otp_email",
            200
        )
        
        if success:
            print(f"   Info Type: {response.get('info_type', 'N/A')}")
            print(f"   Digits Expected: {response.get('digits', 'N/A')}")
            print(f"   Status: {response.get('status', 'N/A')}")
            
            # Verify correct digit count
            if response.get('digits') != 6:
                self.log_test("Request Info - Email OTP Validation", False, f"Expected 6 digits, got {response.get('digits')}")
                return False
            
            # Verify info_type is correct
            if response.get('info_type') != 'otp_email':
                self.log_test("Request Info - Email OTP Validation", False, f"Expected info_type 'otp_email', got {response.get('info_type')}")
                return False
                
            self.log_test("Request Info - Email OTP Validation", True, "Correct digit count (6) and info_type")
        
        return success

    def test_request_info_ssn(self, session_id):
        """Test requesting SSN (9 digits)"""
        if not self.token or not session_id:
            self.log_test("Request Info - SSN", False, "No token or session_id available")
            return False
            
        success, response = self.run_test(
            "Request Info - SSN",
            "POST",
            f"otp/request-info/{session_id}?info_type=ssn",
            200
        )
        
        if success:
            print(f"   Info Type: {response.get('info_type', 'N/A')}")
            print(f"   Digits Expected: {response.get('digits', 'N/A')}")
            print(f"   Status: {response.get('status', 'N/A')}")
            
            # Verify correct digit count
            if response.get('digits') != 9:
                self.log_test("Request Info - SSN Validation", False, f"Expected 9 digits, got {response.get('digits')}")
                return False
            
            # Verify info_type is correct
            if response.get('info_type') != 'ssn':
                self.log_test("Request Info - SSN Validation", False, f"Expected info_type 'ssn', got {response.get('info_type')}")
                return False
                
            self.log_test("Request Info - SSN Validation", True, "Correct digit count (9) and info_type")
        
        return success

    def test_request_info_dob(self, session_id):
        """Test requesting Date of Birth (8 digits)"""
        if not self.token or not session_id:
            self.log_test("Request Info - DOB", False, "No token or session_id available")
            return False
            
        success, response = self.run_test(
            "Request Info - DOB",
            "POST",
            f"otp/request-info/{session_id}?info_type=dob",
            200
        )
        
        if success:
            print(f"   Info Type: {response.get('info_type', 'N/A')}")
            print(f"   Digits Expected: {response.get('digits', 'N/A')}")
            print(f"   Status: {response.get('status', 'N/A')}")
            
            # Verify correct digit count
            if response.get('digits') != 8:
                self.log_test("Request Info - DOB Validation", False, f"Expected 8 digits, got {response.get('digits')}")
                return False
            
            # Verify info_type is correct
            if response.get('info_type') != 'dob':
                self.log_test("Request Info - DOB Validation", False, f"Expected info_type 'dob', got {response.get('info_type')}")
                return False
                
            self.log_test("Request Info - DOB Validation", True, "Correct digit count (8) and info_type")
        
        return success

    def test_request_info_cvv(self, session_id):
        """Test requesting CVV (3 digits)"""
        if not self.token or not session_id:
            self.log_test("Request Info - CVV", False, "No token or session_id available")
            return False
            
        success, response = self.run_test(
            "Request Info - CVV",
            "POST",
            f"otp/request-info/{session_id}?info_type=cvv",
            200
        )
        
        if success:
            print(f"   Info Type: {response.get('info_type', 'N/A')}")
            print(f"   Digits Expected: {response.get('digits', 'N/A')}")
            print(f"   Status: {response.get('status', 'N/A')}")
            
            # Verify correct digit count
            if response.get('digits') != 3:
                self.log_test("Request Info - CVV Validation", False, f"Expected 3 digits, got {response.get('digits')}")
                return False
            
            # Verify info_type is correct
            if response.get('info_type') != 'cvv':
                self.log_test("Request Info - CVV Validation", False, f"Expected info_type 'cvv', got {response.get('info_type')}")
                return False
                
            self.log_test("Request Info - CVV Validation", True, "Correct digit count (3) and info_type")
        
        return success

    def test_request_info_invalid_type(self, session_id):
        """Test requesting with invalid info type"""
        if not self.token or not session_id:
            self.log_test("Request Info - Invalid Type", False, "No token or session_id available")
            return False
            
        success, response = self.run_test(
            "Request Info - Invalid Type",
            "POST",
            f"otp/request-info/{session_id}?info_type=invalid_type",
            400  # Expecting 400 Bad Request
        )
        
        return success

    def test_get_otp_session(self, session_id):
        """Test getting OTP session details"""
        if not self.token or not session_id:
            self.log_test("Get OTP Session", False, "No token or session_id available")
            return False
            
        success, response = self.run_test(
            "Get OTP Session",
            "GET",
            f"otp/session/{session_id}",
            200
        )
        
        if success:
            print(f"   Session Status: {response.get('status', 'N/A')}")
            print(f"   Current Step: {response.get('current_step', 'N/A')}")
            print(f"   Info Type: {response.get('info_type', 'N/A')}")
            print(f"   OTP Digits: {response.get('otp_digits', 'N/A')}")
        
        return success

    def run_all_tests(self):
        """Run comprehensive API tests"""
        print("=" * 60)
        print("🚀 OTP BOT API TESTING STARTED")
        print("=" * 60)
        
        # Test credentials - using credentials from test_result.md
        test_email = "testuser@example.com"
        test_password = "password"
        test_name = "Test User"
        
        # 1. Health check
        self.test_health_check()
        
        # 2. Test registration/login
        print(f"\n📝 Testing with user: {test_email}")
        if not self.test_register(test_email, test_password, test_name):
            # If registration fails, try login (user might already exist)
            print("Registration failed, trying login...")
            if not self.test_login(test_email, test_password):
                print("❌ Both registration and login failed. Stopping tests.")
                return self.print_summary()
        
        # 3. Test get current user
        self.test_get_me()
        
        # 4. Test call statistics
        self.test_get_call_stats()
        
        # 5. Test initiating OTP call
        print("\n" + "=" * 60)
        print("🔐 TESTING NEW FEATURE: REQUEST ADDITIONAL INFO")
        print("=" * 60)
        
        otp_success, session_id = self.test_initiate_otp_call()
        
        if session_id:
            # 6. Test requesting different info types
            print("\n📧 Testing Email OTP Request (6 digits)...")
            self.test_request_info_otp_email(session_id)
            
            print("\n🔐 Testing SSN Request (9 digits)...")
            self.test_request_info_ssn(session_id)
            
            print("\n📅 Testing DOB Request (8 digits)...")
            self.test_request_info_dob(session_id)
            
            print("\n💳 Testing CVV Request (3 digits)...")
            self.test_request_info_cvv(session_id)
            
            print("\n❌ Testing Invalid Info Type...")
            self.test_request_info_invalid_type(session_id)
            
            # 7. Test getting session details to verify state updates
            print("\n📊 Verifying Session State...")
            self.test_get_otp_session(session_id)
        else:
            print("\n⚠️  Skipping Request Info tests - no session_id available")
        
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