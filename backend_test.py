import requests
import sys
import json
from datetime import datetime
import time

class OmniChatAPITester:
    def __init__(self, base_url="https://omnichat-2.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.created_user_id = None
        self.created_conversation_id = None
        self.created_message_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
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

            print(f"   Status Code: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - {name}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ FAILED - {name}")
                print(f"   Expected status: {expected_status}, got: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error response: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"   Error text: {response.text}")
                return False, {}

        except requests.exceptions.RequestException as e:
            print(f"❌ FAILED - {name}")
            print(f"   Network Error: {str(e)}")
            return False, {}
        except Exception as e:
            print(f"❌ FAILED - {name}")
            print(f"   Unexpected Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("Root Endpoint", "GET", "", 200)

    def test_create_user(self):
        """Test user creation"""
        timestamp = datetime.now().strftime("%H%M%S")
        user_data = {
            "username": f"test_user_{timestamp}",
            "email": f"test_{timestamp}@omnichat.com",
            "avatar_url": "https://example.com/avatar.jpg"
        }
        
        success, response = self.run_test("Create User", "POST", "users", 200, user_data)
        if success and 'id' in response:
            self.created_user_id = response['id']
            print(f"   Created user ID: {self.created_user_id}")
        return success

    def test_get_users(self):
        """Test getting all users"""
        return self.run_test("Get Users", "GET", "users", 200)

    def test_update_user_status(self):
        """Test updating user status"""
        if not self.created_user_id:
            print("❌ SKIPPED - Update User Status (no user created)")
            return False
            
        return self.run_test(
            "Update User Status", 
            "PUT", 
            f"users/{self.created_user_id}/status?status=online", 
            200
        )

    def test_create_conversation(self):
        """Test conversation creation"""
        if not self.created_user_id:
            print("❌ SKIPPED - Create Conversation (no user created)")
            return False
            
        conv_data = {
            "name": "Test Conversation",
            "participants": [self.created_user_id]
        }
        
        success, response = self.run_test("Create Conversation", "POST", "conversations", 200, conv_data)
        if success and 'id' in response:
            self.created_conversation_id = response['id']
            print(f"   Created conversation ID: {self.created_conversation_id}")
        return success

    def test_get_conversations(self):
        """Test getting all conversations"""
        return self.run_test("Get Conversations", "GET", "conversations", 200)

    def test_create_message(self):
        """Test message creation"""
        if not self.created_user_id or not self.created_conversation_id:
            print("❌ SKIPPED - Create Message (missing user or conversation)")
            return False
            
        message_data = {
            "content": "Hello, this is a test message!",
            "sender_id": self.created_user_id,
            "sender_username": "test_user",
            "conversation_id": self.created_conversation_id,
            "message_type": "text"
        }
        
        success, response = self.run_test("Create Message", "POST", "messages", 200, message_data)
        if success and 'id' in response:
            self.created_message_id = response['id']
            print(f"   Created message ID: {self.created_message_id}")
        return success

    def test_get_messages(self):
        """Test getting messages for a conversation"""
        if not self.created_conversation_id:
            print("❌ SKIPPED - Get Messages (no conversation created)")
            return False
            
        return self.run_test(
            "Get Messages", 
            "GET", 
            f"conversations/{self.created_conversation_id}/messages", 
            200
        )

    def test_ai_chat(self):
        """Test AI chat integration"""
        if not self.created_user_id or not self.created_conversation_id:
            print("❌ SKIPPED - AI Chat (missing user or conversation)")
            return False
            
        ai_message_data = {
            "content": "What is artificial intelligence?",
            "sender_id": self.created_user_id,
            "sender_username": "test_user",
            "conversation_id": self.created_conversation_id,
            "message_type": "text"
        }
        
        print("   Note: AI response may take several seconds...")
        success, response = self.run_test("AI Chat Response", "POST", "ai/chat", 200, ai_message_data)
        
        if success:
            print("   ✅ AI Integration is working!")
            if 'content' in response:
                print(f"   AI Response: {response['content'][:100]}...")
        
        return success

def main():
    print("🚀 Starting OmniChat API Testing...")
    print("=" * 60)
    
    tester = OmniChatAPITester()
    
    # Test sequence
    tests = [
        ("Root Endpoint", tester.test_root_endpoint),
        ("Create User", tester.test_create_user),
        ("Get Users", tester.test_get_users),
        ("Update User Status", tester.test_update_user_status),
        ("Create Conversation", tester.test_create_conversation),
        ("Get Conversations", tester.test_get_conversations),
        ("Create Message", tester.test_create_message),
        ("Get Messages", tester.test_get_messages),
        ("AI Chat Integration", tester.test_ai_chat),
    ]
    
    print(f"\n📋 Running {len(tests)} API tests...\n")
    
    for test_name, test_func in tests:
        try:
            test_func()
        except Exception as e:
            print(f"❌ FAILED - {test_name}: {str(e)}")
        
        # Small delay between tests
        time.sleep(0.5)
    
    # Final results
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {tester.tests_run}")
    print(f"Passed: {tester.tests_passed}")
    print(f"Failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("\n🎉 ALL TESTS PASSED! Backend API is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {tester.tests_run - tester.tests_passed} tests failed. Check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())