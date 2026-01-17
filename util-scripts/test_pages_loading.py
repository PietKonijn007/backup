#!/usr/bin/env python3
"""
Test script to verify that all pages are loading correctly
"""
import requests
import sys
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def test_page_loads():
    """Test that all main pages load without errors"""
    base_url = "http://localhost:8080"
    
    # Configure requests with retries
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    
    # Test pages (these should redirect to login, which is expected)
    test_pages = {
        "/": "Dashboard",
        "/login": "Login",
        "/files": "Files", 
        "/logs": "Logs",
        "/settings": "Settings"
    }
    
    print("Testing page loads...")
    print("=" * 50)
    
    all_passed = True
    
    for path, expected_name in test_pages.items():
        try:
            url = f"{base_url}{path}"
            response = session.get(url, timeout=10)
            
            # Check if we get a response (200 or redirect)
            if response.status_code in [200, 302]:
                print(f"✅ {expected_name:12} ({path:12}) - Status: {response.status_code}")
                
                # For login page, check if it contains login form
                if path == "/login" and "username" in response.text.lower():
                    print(f"   └─ Login form detected")
                
                # For other pages, check if they redirect to login (expected behavior)
                elif path != "/login" and "login" in response.url:
                    print(f"   └─ Correctly redirects to login (authentication required)")
                    
            else:
                print(f"❌ {expected_name:12} ({path:12}) - Status: {response.status_code}")
                all_passed = False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ {expected_name:12} ({path:12}) - Error: {e}")
            all_passed = False
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("✅ All pages are loading correctly!")
        print("\nNext steps:")
        print("1. Open your browser and go to: http://localhost:8080")
        print("2. You should see the login page")
        print("3. After logging in, test each section:")
        print("   - Dashboard: Monitoring and daemon controls")
        print("   - Files: Backup configuration")
        print("   - Settings: System settings")
        print("   - Logs: Activity logs and troubleshooting")
        return True
    else:
        print("❌ Some pages failed to load properly")
        return False

def test_logs_api_structure():
    """Test that the logs API structure is correct (without authentication)"""
    print("\nTesting API structure...")
    print("=" * 30)
    
    try:
        # Test that the API endpoint exists (should redirect to login)
        response = requests.get("http://localhost:8080/api/logs", timeout=5)
        if "login" in response.url.lower():
            print("✅ Logs API endpoint exists and requires authentication")
        else:
            print("❌ Logs API endpoint response unexpected")
            
        # Test health endpoint (should be public)
        response = requests.get("http://localhost:8080/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health API endpoint is accessible")
            try:
                health_data = response.json()
                print(f"   └─ Health status: {health_data.get('status', 'unknown')}")
            except:
                print("   └─ Health endpoint returned non-JSON response")
        else:
            print(f"❌ Health API endpoint failed: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ API test failed: {e}")

def main():
    """Main test function"""
    print("Testing New GUI Implementation")
    print("=" * 50)
    
    try:
        # Test page loads
        pages_ok = test_page_loads()
        
        # Test API structure
        test_logs_api_structure()
        
        if pages_ok:
            print(f"\n🎉 Application is ready for testing!")
            print(f"Open http://localhost:8080 in your browser to test the new GUI")
            return 0
        else:
            print(f"\n⚠️  Some issues detected. Check the output above.")
            return 1
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())