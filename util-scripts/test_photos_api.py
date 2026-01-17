#!/usr/bin/env python3
"""
Test Google Photos API Integration
Quick test to verify Photos API routes are working
"""
import requests
import json
import sys

# Test configuration
BASE_URL = "http://localhost:8080"
# For remote testing, use: BASE_URL = "https://backup.hofkensvermeulen.be"


def test_photos_albums():
    """Test the /api/photos/albums endpoint"""
    print("\n" + "="*60)
    print("Testing /api/photos/albums endpoint")
    print("="*60)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/photos/albums",
            params={'page_size': 50}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                albums = data.get('albums', [])
                print(f"✅ SUCCESS! Found {len(albums)} albums")
                
                # Display first few albums
                if albums:
                    print("\nFirst 5 albums:")
                    for i, album in enumerate(albums[:5], 1):
                        print(f"  {i}. {album['title']} ({album['media_items_count']} items)")
                
                return True, albums
            else:
                print(f"❌ FAILED: {data.get('error')}")
                return False, []
        elif response.status_code == 401:
            print("❌ FAILED: Not authenticated")
            print("Please login at:", f"{BASE_URL}/login")
            return False, []
        else:
            print(f"❌ FAILED: {response.text}")
            return False, []
            
    except requests.exceptions.ConnectionError:
        print(f"❌ FAILED: Cannot connect to {BASE_URL}")
        print("Make sure the app is running: python app.py")
        return False, []
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False, []


def test_photos_media(album_id=None):
    """Test the /api/photos/media endpoint"""
    print("\n" + "="*60)
    print("Testing /api/photos/media endpoint")
    print("="*60)
    
    try:
        params = {'page_size': 10}
        if album_id:
            params['album_id'] = album_id
        
        response = requests.get(
            f"{BASE_URL}/api/photos/media",
            params=params
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                items = data.get('items', [])
                print(f"✅ SUCCESS! Found {len(items)} media items")
                
                # Display first few items
                if items:
                    print("\nFirst 5 media items:")
                    for i, item in enumerate(items[:5], 1):
                        print(f"  {i}. {item['filename']} ({item['media_type']}) - {item['creation_time']}")
                
                return True, items
            else:
                print(f"❌ FAILED: {data.get('error')}")
                return False, []
        else:
            print(f"❌ FAILED: {response.text}")
            return False, []
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False, []


def test_recent_photos():
    """Test the /api/photos/recent endpoint"""
    print("\n" + "="*60)
    print("Testing /api/photos/recent endpoint")
    print("="*60)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/photos/recent",
            params={'days': 30, 'max_results': 10}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                items = data.get('items', [])
                print(f"✅ SUCCESS! Found {len(items)} recent photos (last 30 days)")
                
                if items:
                    print("\nRecent photos:")
                    for i, item in enumerate(items[:5], 1):
                        print(f"  {i}. {item['filename']} - {item['creation_time']}")
                
                return True, items
            else:
                print(f"❌ FAILED: {data.get('error')}")
                return False, []
        else:
            print(f"❌ FAILED: {response.text}")
            return False, []
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False, []


def main():
    """Run all tests"""
    print("="*60)
    print("GOOGLE PHOTOS API TEST SUITE")
    print("="*60)
    print(f"Testing against: {BASE_URL}")
    print("\nNOTE: You must be logged in for these tests to work")
    print(f"Login at: {BASE_URL}/login")
    
    # Test 1: Albums
    success1, albums = test_photos_albums()
    
    # Test 2: Media items
    success2, items = test_photos_media()
    
    # Test 3: Recent photos
    success3, recent = test_recent_photos()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    total_tests = 3
    passed = sum([success1, success2, success3])
    
    print(f"Tests passed: {passed}/{total_tests}")
    
    if passed == total_tests:
        print("\n✅ All tests PASSED! Photos API is working correctly.")
        print("\nYou can now:")
        print("1. View photos in the web UI at:", f"{BASE_URL}/photos")
        print("2. Sync albums to S3 via the API")
        return 0
    else:
        print("\n❌ Some tests FAILED. Check the errors above.")
        if not success1:
            print("\nTroubleshooting:")
            print("1. Make sure you're logged in")
            print("2. Check that Google Photos Library API is enabled")
            print("3. Re-authenticate if needed (delete token.pickle and login again)")
        return 1


if __name__ == '__main__':
    sys.exit(main())
