#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime

class DeadlineAPITester:
    def __init__(self, base_url="https://deadline-manager-2.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            print(f"   Status Code: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)}")
                    return True, response_data
                except:
                    return True, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error Response: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"   Error Response: {response.text}")
                return False, {}

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed - Network Error: {str(e)}")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        return self.run_test("Root API Endpoint", "GET", "api/", 200)

    def test_get_status_checks(self):
        """Test getting all status checks"""
        return self.run_test("Get Status Checks", "GET", "api/status", 200)

    def test_create_status_check(self):
        """Test creating a status check"""
        test_data = {
            "client_name": f"test_client_{datetime.now().strftime('%H%M%S')}"
        }
        return self.run_test("Create Status Check", "POST", "api/status", 200, data=test_data)

    def test_health_check(self):
        """Test if the application is accessible"""
        return self.run_test("Health Check", "GET", "", 200)

def main():
    print("🚀 Starting Backend API Tests for Deadline Manager")
    print("=" * 60)
    
    # Setup
    tester = DeadlineAPITester()
    
    # Test basic connectivity
    print("\n📡 Testing Basic Connectivity...")
    health_success, _ = tester.test_health_check()
    
    if not health_success:
        print("\n❌ Basic connectivity failed. Backend may not be running.")
        print("   Please check if the backend service is up and accessible.")
        return 1
    
    # Test API endpoints
    print("\n🔧 Testing API Endpoints...")
    
    # Test root endpoint
    root_success, _ = tester.test_root_endpoint()
    
    # Test status endpoints
    get_success, _ = tester.test_get_status_checks()
    create_success, created_data = tester.test_create_status_check()
    
    # Test getting status checks again to see if creation worked
    if create_success:
        print("\n🔄 Testing if created status check appears in list...")
        get_after_create_success, get_data = tester.test_get_status_checks()
        if get_after_create_success and isinstance(get_data, list) and len(get_data) > 0:
            print(f"✅ Found {len(get_data)} status check(s) in database")
        else:
            print("⚠️  No status checks found after creation")
    
    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 BACKEND TEST RESULTS")
    print(f"   Tests Run: {tester.tests_run}")
    print(f"   Tests Passed: {tester.tests_passed}")
    print(f"   Success Rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All backend tests passed!")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())