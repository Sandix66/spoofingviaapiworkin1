import requests
import sys
import json
from datetime import datetime
import jwt

class MultiUserSystemTester:
    def __init__(self, base_url="https://ivrflow.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.user_token = None
        self.admin_id = None
        self.user_id = None
        self.created_user_id = None
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

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, token=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if token:
            test_headers['Authorization'] = f'Bearer {token}'
        
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

    def test_admin_login(self):
        """Test admin login"""
        print("\n" + "=" * 60)
        print("🔐 TESTING: ADMIN AUTHENTICATION")
        print("=" * 60)
        
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "Admin@voip.com", "password": "1234"}
        )
        
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            if 'user' in response:
                self.admin_id = response['user'].get('id')
                admin_role = response['user'].get('role')
                
                # Verify role in response
                if admin_role == "admin":
                    self.log_test("Admin Role in Response", True, f"Role: {admin_role}")
                else:
                    self.log_test("Admin Role in Response", False, f"Expected 'admin', got '{admin_role}'")
                
                # Decode JWT and verify role in token
                try:
                    decoded = jwt.decode(self.admin_token, options={"verify_signature": False})
                    print(f"   Token payload: {json.dumps(decoded, indent=2)}")
                    
                    # Check if role is in token (might be in sub or separate field)
                    if 'role' in decoded:
                        if decoded['role'] == 'admin':
                            self.log_test("Admin Role in JWT Token", True, f"Role in token: {decoded['role']}")
                        else:
                            self.log_test("Admin Role in JWT Token", False, f"Expected 'admin' in token, got '{decoded['role']}'")
                    else:
                        self.log_test("Admin Role in JWT Token", False, "Role field not found in JWT token")
                except Exception as e:
                    self.log_test("JWT Token Decode", False, f"Failed to decode token: {str(e)}")
            
            print(f"   Admin Token obtained: {self.admin_token[:20]}...")
            return True
        return False

    def test_user_login(self):
        """Test regular user login"""
        success, response = self.run_test(
            "Regular User Login",
            "POST",
            "auth/login",
            200,
            data={"email": "testuser@example.com", "password": "password"}
        )
        
        if success and 'access_token' in response:
            self.user_token = response['access_token']
            if 'user' in response:
                self.user_id = response['user'].get('id')
                user_role = response['user'].get('role')
                
                # Verify role
                if user_role == "user":
                    self.log_test("User Role in Response", True, f"Role: {user_role}")
                else:
                    self.log_test("User Role in Response", False, f"Expected 'user', got '{user_role}'")
            
            print(f"   User Token obtained: {self.user_token[:20]}...")
            return True
        return False

    def test_admin_authorization(self):
        """Test admin-only endpoint access"""
        print("\n" + "=" * 60)
        print("🔒 TESTING: ADMIN AUTHORIZATION")
        print("=" * 60)
        
        # Test 1: Admin can access admin endpoint
        success, response = self.run_test(
            "Admin Access to Admin Endpoint",
            "GET",
            "admin/users",
            200,
            token=self.admin_token
        )
        
        # Test 2: Regular user cannot access admin endpoint (should get 403)
        success2, response2 = self.run_test(
            "User Access to Admin Endpoint (Should Fail)",
            "GET",
            "admin/users",
            403,
            token=self.user_token
        )
        
        return success and success2

    def test_create_user(self):
        """Test creating a new user as admin"""
        print("\n" + "=" * 60)
        print("👤 TESTING: ADMIN USER MANAGEMENT - CREATE USER")
        print("=" * 60)
        
        new_user_data = {
            "email": f"testuser_{datetime.now().timestamp()}@example.com",
            "password": "testpass123",
            "name": "Test User Created by Admin",
            "role": "user",
            "credits": 50.0
        }
        
        success, response = self.run_test(
            "Create User with Custom Credits",
            "POST",
            "admin/users",
            200,
            data=new_user_data,
            token=self.admin_token
        )
        
        if success and 'user_id' in response:
            self.created_user_id = response['user_id']
            print(f"   Created User ID: {self.created_user_id}")
            
            # Verify user was created with correct credits
            success2, user_list = self.run_test(
                "Verify User Created",
                "GET",
                "admin/users",
                200,
                token=self.admin_token
            )
            
            if success2 and 'users' in user_list:
                created_user = next((u for u in user_list['users'] if u['id'] == self.created_user_id), None)
                if created_user:
                    if created_user.get('credits') == 50.0:
                        self.log_test("Verify User Credits", True, f"Credits: {created_user.get('credits')}")
                    else:
                        self.log_test("Verify User Credits", False, f"Expected 50.0, got {created_user.get('credits')}")
                else:
                    self.log_test("Verify User Created", False, "User not found in user list")
            
            return True
        return False

    def test_list_users(self):
        """Test listing all users"""
        success, response = self.run_test(
            "List All Users",
            "GET",
            "admin/users",
            200,
            token=self.admin_token
        )
        
        if success and 'users' in response:
            user_count = len(response['users'])
            print(f"   Total users: {user_count}")
            return True
        return False

    def test_update_user(self):
        """Test updating user information"""
        if not self.created_user_id:
            self.log_test("Update User", False, "No created user ID available")
            return False
        
        update_data = {
            "name": "Updated Test User",
            "credits": 100.0
        }
        
        success, response = self.run_test(
            "Update User Info",
            "PUT",
            f"admin/users/{self.created_user_id}",
            200,
            data=update_data,
            token=self.admin_token
        )
        
        if success:
            # Verify update
            success2, user_list = self.run_test(
                "Verify User Updated",
                "GET",
                "admin/users",
                200,
                token=self.admin_token
            )
            
            if success2 and 'users' in user_list:
                updated_user = next((u for u in user_list['users'] if u['id'] == self.created_user_id), None)
                if updated_user:
                    if updated_user.get('name') == "Updated Test User" and updated_user.get('credits') == 100.0:
                        self.log_test("Verify User Update", True, f"Name: {updated_user.get('name')}, Credits: {updated_user.get('credits')}")
                    else:
                        self.log_test("Verify User Update", False, f"Update not reflected correctly")
        
        return success

    def test_add_credits(self):
        """Test adding credits to user"""
        print("\n" + "=" * 60)
        print("💰 TESTING: CREDIT MANAGEMENT")
        print("=" * 60)
        
        if not self.created_user_id:
            self.log_test("Add Credits", False, "No created user ID available")
            return False
        
        credit_data = {
            "amount": 25.0,
            "reason": "Test credit addition"
        }
        
        success, response = self.run_test(
            "Add Credits to User",
            "POST",
            f"admin/users/{self.created_user_id}/credits",
            200,
            data=credit_data,
            token=self.admin_token
        )
        
        if success and 'new_credits' in response:
            new_credits = response['new_credits']
            print(f"   New credits balance: {new_credits}")
            
            # Should be 100 + 25 = 125
            if new_credits == 125.0:
                self.log_test("Verify Credit Addition", True, f"Credits: {new_credits}")
            else:
                self.log_test("Verify Credit Addition", False, f"Expected 125.0, got {new_credits}")
        
        return success

    def test_deduct_credits(self):
        """Test deducting credits from user"""
        if not self.created_user_id:
            self.log_test("Deduct Credits", False, "No created user ID available")
            return False
        
        credit_data = {
            "amount": -10.0,
            "reason": "Test credit deduction"
        }
        
        success, response = self.run_test(
            "Deduct Credits from User",
            "POST",
            f"admin/users/{self.created_user_id}/credits",
            200,
            data=credit_data,
            token=self.admin_token
        )
        
        if success and 'new_credits' in response:
            new_credits = response['new_credits']
            print(f"   New credits balance: {new_credits}")
            
            # Should be 125 - 10 = 115
            if new_credits == 115.0:
                self.log_test("Verify Credit Deduction", True, f"Credits: {new_credits}")
            else:
                self.log_test("Verify Credit Deduction", False, f"Expected 115.0, got {new_credits}")
        
        return success

    def test_user_credits_endpoint(self):
        """Test user credits endpoint"""
        success, response = self.run_test(
            "Get User Credits",
            "GET",
            "user/credits",
            200,
            token=self.user_token
        )
        
        if success and 'credits' in response:
            credits = response['credits']
            print(f"   User credits: {credits}")
            return True
        return False

    def test_insufficient_credits(self):
        """Test call initiation with insufficient credits"""
        print("\n" + "=" * 60)
        print("🚫 TESTING: INSUFFICIENT CREDITS HANDLING")
        print("=" * 60)
        
        # First, create a user with 0 credits
        zero_credit_user = {
            "email": f"zerocredit_{datetime.now().timestamp()}@example.com",
            "password": "testpass123",
            "name": "Zero Credit User",
            "role": "user",
            "credits": 0.0
        }
        
        success, response = self.run_test(
            "Create User with 0 Credits",
            "POST",
            "admin/users",
            200,
            data=zero_credit_user,
            token=self.admin_token
        )
        
        if success and 'user_id' in response:
            zero_credit_user_id = response['user_id']
            
            # Login as this user
            success2, login_response = self.run_test(
                "Login as Zero Credit User",
                "POST",
                "auth/login",
                200,
                data={"email": zero_credit_user['email'], "password": zero_credit_user['password']}
            )
            
            if success2 and 'access_token' in login_response:
                zero_credit_token = login_response['access_token']
                
                # Try to initiate a call (should fail with 402)
                call_config = {
                    "recipient_number": "+14155552671",
                    "caller_id": "+14245298701",
                    "recipient_name": "Test User",
                    "service_name": "Test Service",
                    "otp_digits": 6,
                    "language": "en"
                }
                
                success3, call_response = self.run_test(
                    "Initiate Call with 0 Credits (Should Fail)",
                    "POST",
                    "otp/initiate-call",
                    402,
                    data=call_config,
                    token=zero_credit_token
                )
                
                return success3
        
        return False

    def test_credit_deduction_on_call(self):
        """Test credit deduction when call starts"""
        print("\n" + "=" * 60)
        print("📞 TESTING: CREDIT DEDUCTION ON CALL START")
        print("=" * 60)
        
        # Get current credits for regular user
        success, response = self.run_test(
            "Get User Credits Before Call",
            "GET",
            "user/credits",
            200,
            token=self.user_token
        )
        
        if success and 'credits' in response:
            credits_before = response['credits']
            print(f"   Credits before call: {credits_before}")
            
            if credits_before < 1:
                # Add credits first
                credit_data = {"amount": 10.0, "reason": "Test credit for call"}
                self.run_test(
                    "Add Credits for Test",
                    "POST",
                    f"admin/users/{self.user_id}/credits",
                    200,
                    data=credit_data,
                    token=self.admin_token
                )
                credits_before = credits_before + 10.0
            
            # Initiate a call
            call_config = {
                "recipient_number": "+14155552671",
                "caller_id": "+14245298701",
                "recipient_name": "Test User",
                "service_name": "Test Service",
                "otp_digits": 6,
                "language": "en"
            }
            
            success2, call_response = self.run_test(
                "Initiate Call",
                "POST",
                "otp/initiate-call",
                200,
                data=call_config,
                token=self.user_token
            )
            
            if success2:
                # Check credits after call initiation
                success3, response3 = self.run_test(
                    "Get User Credits After Call",
                    "GET",
                    "user/credits",
                    200,
                    token=self.user_token
                )
                
                if success3 and 'credits' in response3:
                    credits_after = response3['credits']
                    print(f"   Credits after call: {credits_after}")
                    
                    # Should be deducted by 1
                    expected_credits = credits_before - 1
                    if credits_after == expected_credits:
                        self.log_test("Verify Credit Deduction", True, f"Deducted 1 credit (Before: {credits_before}, After: {credits_after})")
                        return True
                    else:
                        self.log_test("Verify Credit Deduction", False, f"Expected {expected_credits}, got {credits_after}")
        
        return False

    def test_user_profile(self):
        """Test user profile endpoint"""
        print("\n" + "=" * 60)
        print("👤 TESTING: USER PROFILE ENDPOINTS")
        print("=" * 60)
        
        success, response = self.run_test(
            "Get User Profile",
            "GET",
            "user/profile",
            200,
            token=self.user_token
        )
        
        if success:
            print(f"   User ID: {response.get('id')}")
            print(f"   Email: {response.get('email')}")
            print(f"   Name: {response.get('name')}")
            print(f"   Role: {response.get('role')}")
            print(f"   Credits: {response.get('credits')}")
            return True
        return False

    def test_change_password(self):
        """Test password change"""
        # Create a test user for password change
        test_user = {
            "email": f"pwdtest_{datetime.now().timestamp()}@example.com",
            "password": "oldpassword",
            "name": "Password Test User",
            "role": "user",
            "credits": 10.0
        }
        
        success, response = self.run_test(
            "Create User for Password Test",
            "POST",
            "admin/users",
            200,
            data=test_user,
            token=self.admin_token
        )
        
        if success:
            # Login as this user
            success2, login_response = self.run_test(
                "Login with Old Password",
                "POST",
                "auth/login",
                200,
                data={"email": test_user['email'], "password": "oldpassword"}
            )
            
            if success2 and 'access_token' in login_response:
                pwd_test_token = login_response['access_token']
                
                # Change password
                pwd_change_data = {
                    "current_password": "oldpassword",
                    "new_password": "newpassword123"
                }
                
                success3, pwd_response = self.run_test(
                    "Change Password",
                    "PUT",
                    "user/password",
                    200,
                    data=pwd_change_data,
                    token=pwd_test_token
                )
                
                if success3:
                    # Try to login with new password
                    success4, login_response2 = self.run_test(
                        "Login with New Password",
                        "POST",
                        "auth/login",
                        200,
                        data={"email": test_user['email'], "password": "newpassword123"}
                    )
                    
                    return success4
        
        return False

    def test_user_calls_history(self):
        """Test user call history endpoint"""
        success, response = self.run_test(
            "Get User Call History",
            "GET",
            "user/calls?limit=10",
            200,
            token=self.user_token
        )
        
        if success and 'calls' in response:
            call_count = len(response['calls'])
            print(f"   User has {call_count} calls in history")
            return True
        return False

    def test_user_stats(self):
        """Test user statistics endpoint"""
        success, response = self.run_test(
            "Get User Statistics",
            "GET",
            "user/stats",
            200,
            token=self.user_token
        )
        
        if success:
            print(f"   Total calls: {response.get('total_calls', 0)}")
            print(f"   Total duration: {response.get('total_duration_seconds', 0)}s")
            print(f"   Total spent: {response.get('total_credits_spent', 0)} credits")
            print(f"   Successful calls: {response.get('successful_calls', 0)}")
            return True
        return False

    def test_admin_stats(self):
        """Test admin dashboard statistics"""
        print("\n" + "=" * 60)
        print("📊 TESTING: ADMIN STATS & MONITORING")
        print("=" * 60)
        
        success, response = self.run_test(
            "Get Admin Dashboard Stats",
            "GET",
            "admin/stats",
            200,
            token=self.admin_token
        )
        
        if success:
            print(f"   Total users: {response.get('total_users', 0)}")
            print(f"   Active users: {response.get('active_users', 0)}")
            print(f"   Total calls today: {response.get('total_calls_today', 0)}")
            print(f"   Total calls all time: {response.get('total_calls_all_time', 0)}")
            print(f"   Total credits distributed: {response.get('total_credits_distributed', 0)}")
            print(f"   Total credits spent: {response.get('total_credits_spent', 0)}")
            return True
        return False

    def test_admin_activities(self):
        """Test admin activities endpoint"""
        success, response = self.run_test(
            "Get All User Activities",
            "GET",
            "admin/activities?limit=50",
            200,
            token=self.admin_token
        )
        
        if success and 'activities' in response:
            activity_count = len(response['activities'])
            print(f"   Total activities: {activity_count}")
            
            # Check if we have activities from our tests
            if activity_count > 0:
                print(f"   Recent activities:")
                for activity in response['activities'][:5]:
                    print(f"     - {activity.get('action_type')}: {activity.get('timestamp')}")
            
            return True
        return False

    def test_admin_calls(self):
        """Test admin calls endpoint"""
        success, response = self.run_test(
            "Get All Call History",
            "GET",
            "admin/calls?limit=50",
            200,
            token=self.admin_token
        )
        
        if success and 'calls' in response:
            call_count = len(response['calls'])
            print(f"   Total calls: {call_count}")
            return True
        return False

    def test_activity_logging(self):
        """Test activity logging"""
        print("\n" + "=" * 60)
        print("📝 TESTING: ACTIVITY LOGGING")
        print("=" * 60)
        
        # Get activities before
        success, response_before = self.run_test(
            "Get Activities Before",
            "GET",
            "admin/activities?limit=100",
            200,
            token=self.admin_token
        )
        
        if not success:
            return False
        
        activities_before = response_before.get('activities', [])
        
        # Create a user (should log activity)
        new_user = {
            "email": f"activitytest_{datetime.now().timestamp()}@example.com",
            "password": "testpass123",
            "name": "Activity Test User",
            "role": "user",
            "credits": 20.0
        }
        
        success2, user_response = self.run_test(
            "Create User (Activity Logging Test)",
            "POST",
            "admin/users",
            200,
            data=new_user,
            token=self.admin_token
        )
        
        if not success2:
            return False
        
        activity_test_user_id = user_response.get('user_id')
        
        # Add credits (should log activity)
        credit_data = {"amount": 15.0, "reason": "Activity logging test"}
        success3, credit_response = self.run_test(
            "Add Credits (Activity Logging Test)",
            "POST",
            f"admin/users/{activity_test_user_id}/credits",
            200,
            data=credit_data,
            token=self.admin_token
        )
        
        if not success3:
            return False
        
        # Get activities after
        success4, response_after = self.run_test(
            "Get Activities After",
            "GET",
            "admin/activities?limit=100",
            200,
            token=self.admin_token
        )
        
        if success4 and 'activities' in response_after:
            activities_after = response_after['activities']
            
            # Check for user_created activity
            user_created_activity = next((a for a in activities_after if a.get('action_type') == 'user_created' and a.get('details', {}).get('created_user_id') == activity_test_user_id), None)
            
            if user_created_activity:
                self.log_test("Activity Logged - User Created", True, f"Activity found: {user_created_activity.get('action_type')}")
            else:
                self.log_test("Activity Logged - User Created", False, "user_created activity not found")
            
            # Check for credit_added activity
            credit_added_activity = next((a for a in activities_after if a.get('action_type') == 'credit_added' and a.get('details', {}).get('target_user_id') == activity_test_user_id), None)
            
            if credit_added_activity:
                self.log_test("Activity Logged - Credit Added", True, f"Activity found: {credit_added_activity.get('action_type')}")
            else:
                self.log_test("Activity Logged - Credit Added", False, "credit_added activity not found")
            
            return user_created_activity is not None and credit_added_activity is not None
        
        return False

    def test_delete_user(self):
        """Test deleting a user"""
        print("\n" + "=" * 60)
        print("🗑️ TESTING: DELETE USER")
        print("=" * 60)
        
        if not self.created_user_id:
            self.log_test("Delete User", False, "No created user ID available")
            return False
        
        success, response = self.run_test(
            "Delete User",
            "DELETE",
            f"admin/users/{self.created_user_id}",
            200,
            token=self.admin_token
        )
        
        if success:
            # Verify user is deleted
            success2, user_list = self.run_test(
                "Verify User Deleted",
                "GET",
                "admin/users",
                200,
                token=self.admin_token
            )
            
            if success2 and 'users' in user_list:
                deleted_user = next((u for u in user_list['users'] if u['id'] == self.created_user_id), None)
                if deleted_user is None:
                    self.log_test("Verify User Deletion", True, "User not found in list (deleted)")
                else:
                    self.log_test("Verify User Deletion", False, "User still exists in list")
        
        return success

    def run_all_tests(self):
        """Run all multi-user system tests"""
        print("=" * 60)
        print("🚀 MULTI-USER SYSTEM TESTING STARTED")
        print("=" * 60)
        
        # 1. Admin Authentication
        if not self.test_admin_login():
            print("❌ Admin login failed. Stopping tests.")
            return self.print_summary()
        
        # 2. User Authentication
        if not self.test_user_login():
            print("❌ User login failed. Stopping tests.")
            return self.print_summary()
        
        # 3. Admin Authorization
        self.test_admin_authorization()
        
        # 4. Admin User Management
        self.test_create_user()
        self.test_list_users()
        self.test_update_user()
        
        # 5. Credit Management
        self.test_add_credits()
        self.test_deduct_credits()
        self.test_user_credits_endpoint()
        
        # 6. Credit System Tests
        self.test_insufficient_credits()
        self.test_credit_deduction_on_call()
        
        # 7. User Profile Endpoints
        self.test_user_profile()
        self.test_change_password()
        self.test_user_calls_history()
        self.test_user_stats()
        
        # 8. Admin Stats & Monitoring
        self.test_admin_stats()
        self.test_admin_activities()
        self.test_admin_calls()
        
        # 9. Activity Logging
        self.test_activity_logging()
        
        # 10. Delete User (cleanup)
        self.test_delete_user()
        
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
    tester = MultiUserSystemTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())
