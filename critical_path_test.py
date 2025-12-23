import requests
import sys
import json
from datetime import datetime

class CriticalPathTester:
    def __init__(self, base_url="https://ivrflow.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.user_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.critical_failures = []

    def log_test(self, name, success, details="", is_critical=False):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        else:
            if is_critical:
                self.critical_failures.append({"test": name, "details": details})
        
        result = {
            "test": name,
            "success": success,
            "details": details,
            "critical": is_critical,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASSED" if success else "❌ FAILED"
        critical_marker = " [CRITICAL]" if is_critical else ""
        print(f"{status}{critical_marker} - {name}")
        if details:
            print(f"   Details: {details}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, is_critical=False):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
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
                    self.log_test(name, True, f"Status: {response.status_code}", is_critical)
                    return True, response_data
                except:
                    self.log_test(name, True, f"Status: {response.status_code}, No JSON response", is_critical)
                    return True, {}
            else:
                try:
                    error_data = response.json()
                    self.log_test(name, False, f"Expected {expected_status}, got {response.status_code}. Error: {error_data}", is_critical)
                except:
                    self.log_test(name, False, f"Expected {expected_status}, got {response.status_code}. Response: {response.text[:200]}", is_critical)
                return False, {}

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}", is_critical)
            return False, {}

    def test_admin_login(self):
        """Test admin login - CRITICAL"""
        print("\n" + "=" * 60)
        print("🔐 CRITICAL PATH 1: ADMIN LOGIN & AUTHENTICATION")
        print("=" * 60)
        
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "Admin@voip.com", "password": "1234"},
            is_critical=True
        )
        
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            print(f"   ✅ Admin token obtained: {self.admin_token[:20]}...")
            
            # Verify role is admin
            if 'user' in response and response['user'].get('role') == 'admin':
                self.log_test("Admin Role Verification", True, "Role is 'admin'", is_critical=True)
            else:
                self.log_test("Admin Role Verification", False, f"Role is not admin: {response.get('user', {}).get('role')}", is_critical=True)
            
            return True
        return False

    def test_user_login(self):
        """Test user login - CRITICAL"""
        print("\n" + "=" * 60)
        print("🔐 CRITICAL PATH 1: USER LOGIN & AUTHENTICATION")
        print("=" * 60)
        
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data={"email": "testuser@example.com", "password": "password"},
            is_critical=True
        )
        
        if success and 'access_token' in response:
            self.user_token = response['access_token']
            print(f"   ✅ User token obtained: {self.user_token[:20]}...")
            
            # Verify token generation
            if 'user' in response:
                self.log_test("Token Generation", True, "Token and user data returned", is_critical=True)
            else:
                self.log_test("Token Generation", False, "User data not in response", is_critical=True)
            
            return True
        return False

    def test_token_validation(self):
        """Test token validation - CRITICAL"""
        if not self.user_token:
            self.log_test("Token Validation", False, "No user token available", is_critical=True)
            return False
        
        headers = {'Authorization': f'Bearer {self.user_token}'}
        success, response = self.run_test(
            "Token Validation (Get Me)",
            "GET",
            "auth/me",
            200,
            headers=headers,
            is_critical=True
        )
        
        return success

    def test_basic_call_creation(self):
        """Test basic call creation - CRITICAL"""
        print("\n" + "=" * 60)
        print("📞 CRITICAL PATH 2: BASIC CALL CREATION")
        print("=" * 60)
        
        if not self.user_token:
            self.log_test("Call Creation", False, "No user token available", is_critical=True)
            return False, None
        
        headers = {'Authorization': f'Bearer {self.user_token}'}
        call_config = {
            "recipient_number": "+14155552671",
            "caller_id": "+14245298701",
            "recipient_name": "John Smith",
            "service_name": "Banking Account",
            "otp_digits": 6,
            "language": "en"
        }
        
        success, response = self.run_test(
            "Initiate Call",
            "POST",
            "otp/initiate-call",
            200,
            data=call_config,
            headers=headers,
            is_critical=True
        )
        
        session_id = None
        if success:
            if 'session_id' in response:
                session_id = response['session_id']
                print(f"   ✅ Session created: {session_id}")
                self.log_test("Session Creation", True, f"Session ID: {session_id}", is_critical=True)
            else:
                self.log_test("Session Creation", False, "No session_id in response", is_critical=True)
            
            if 'call_id' in response:
                print(f"   ✅ Call ID: {response['call_id']}")
                self.log_test("Call ID Generation", True, f"Call ID: {response['call_id']}", is_critical=True)
            else:
                self.log_test("Call ID Generation", False, "No call_id in response", is_critical=True)
        
        return success, session_id

    def test_core_endpoints(self):
        """Test core endpoints - CRITICAL"""
        print("\n" + "=" * 60)
        print("🔌 CRITICAL PATH 3: CORE ENDPOINTS")
        print("=" * 60)
        
        # Test GET /api/user/credits
        if self.user_token:
            headers = {'Authorization': f'Bearer {self.user_token}'}
            success, response = self.run_test(
                "GET /api/user/credits",
                "GET",
                "user/dashboard-stats",
                200,
                headers=headers,
                is_critical=True
            )
            
            if success:
                print(f"   Credits info retrieved successfully")
        
        # Test GET /api/user/calls
        if self.user_token:
            headers = {'Authorization': f'Bearer {self.user_token}'}
            success, response = self.run_test(
                "GET /api/user/calls",
                "GET",
                "user/calls?limit=10",
                200,
                headers=headers,
                is_critical=True
            )
            
            if success:
                calls = response.get('calls', [])
                print(f"   Retrieved {len(calls)} calls")
        
        # Test GET /api/admin/users
        if self.admin_token:
            headers = {'Authorization': f'Bearer {self.admin_token}'}
            success, response = self.run_test(
                "GET /api/admin/users",
                "GET",
                "admin/users",
                200,
                headers=headers,
                is_critical=True
            )
            
            if success:
                users = response.get('users', [])
                print(f"   Retrieved {len(users)} users")
        
        # Test GET /api/admin/stats
        if self.admin_token:
            headers = {'Authorization': f'Bearer {self.admin_token}'}
            success, response = self.run_test(
                "GET /api/admin/stats",
                "GET",
                "admin/stats",
                200,
                headers=headers,
                is_critical=True
            )
            
            if success:
                print(f"   Total users: {response.get('total_users', 0)}")
                print(f"   Total calls: {response.get('total_calls_all_time', 0)}")

    def test_admin_unlimited_credits(self):
        """Test that admin has unlimited credits (FUP doesn't block admin) - CRITICAL"""
        print("\n" + "=" * 60)
        print("💰 CRITICAL PATH 4: ADMIN UNLIMITED CREDITS (FUP CHECK)")
        print("=" * 60)
        
        if not self.admin_token:
            self.log_test("Admin Unlimited Credits", False, "No admin token available", is_critical=True)
            return False
        
        # Get admin profile
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        success, response = self.run_test(
            "Admin Profile Check",
            "GET",
            "auth/me",
            200,
            headers=headers,
            is_critical=True
        )
        
        if success:
            role = response.get('role')
            credits = response.get('credits', 0)
            print(f"   Admin role: {role}")
            print(f"   Admin credits: {credits}")
            
            # Admin should be able to make calls regardless of credits
            # This is verified by checking if admin can initiate calls
            call_config = {
                "recipient_number": "+14155552671",
                "caller_id": "+14245298701",
                "recipient_name": "Admin Test",
                "service_name": "Admin Service",
                "otp_digits": 6,
                "language": "en"
            }
            
            success2, response2 = self.run_test(
                "Admin Call Initiation (Bypass FUP)",
                "POST",
                "otp/initiate-call",
                200,
                data=call_config,
                headers=headers,
                is_critical=True
            )
            
            if success2:
                self.log_test("Admin FUP Bypass", True, "Admin can initiate calls (FUP doesn't block)", is_critical=True)
                return True
            else:
                self.log_test("Admin FUP Bypass", False, "Admin blocked from initiating calls", is_critical=True)
                return False
        
        return False

    def run_critical_path_tests(self):
        """Run all critical path tests"""
        print("=" * 60)
        print("🚨 CRITICAL PATH VERIFICATION STARTED")
        print("=" * 60)
        print("Testing core OTP Bot features after payment/Telegram/FUP modifications")
        print()
        
        # 1. Test Admin Login & Authentication
        admin_login_success = self.test_admin_login()
        
        # 2. Test User Login & Authentication
        user_login_success = self.test_user_login()
        
        # 3. Test Token Validation
        if user_login_success:
            self.test_token_validation()
        
        # 4. Test Basic Call Creation
        if user_login_success:
            call_success, session_id = self.test_basic_call_creation()
        
        # 5. Test Core Endpoints
        self.test_core_endpoints()
        
        # 6. Test Admin Unlimited Credits (FUP Check)
        if admin_login_success:
            self.test_admin_unlimited_credits()
        
        return self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 CRITICAL PATH TEST SUMMARY")
        print("=" * 60)
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if self.critical_failures:
            print(f"\n🚨 CRITICAL FAILURES: {len(self.critical_failures)}")
            for failure in self.critical_failures:
                print(f"  ❌ {failure['test']}")
                print(f"     {failure['details']}")
        
        if self.tests_passed == self.tests_run:
            print("\n✅ ALL CRITICAL PATHS WORKING - Core features intact!")
            return 0
        else:
            print(f"\n⚠️  {self.tests_run - self.tests_passed} TESTS FAILED")
            
            if self.critical_failures:
                print("\n🚨 CRITICAL ISSUES DETECTED - Core features may be broken!")
            
            # Print all failed tests
            print("\nFailed Tests:")
            for result in self.test_results:
                if not result['success']:
                    critical_marker = " [CRITICAL]" if result['critical'] else ""
                    print(f"  ❌ {result['test']}{critical_marker}")
                    print(f"     {result['details']}")
            
            return 1

def main():
    """Main test function"""
    tester = CriticalPathTester()
    return tester.run_critical_path_tests()

if __name__ == "__main__":
    sys.exit(main())
