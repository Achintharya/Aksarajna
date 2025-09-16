#!/usr/bin/env python3
"""
Test script for Writing Style API endpoints
"""

import requests
import json
import sys

def test_writing_style_api():
    """Test all writing style API endpoints"""
    base_url = 'http://localhost:8000'
    
    print('🧪 Testing Writing Style API Endpoints')
    print('=' * 50)
    
    try:
        # Test 1: GET endpoint (should return existing content)
        print('1️⃣ Testing GET /api/writing-style')
        response = requests.get(f'{base_url}/api/writing-style', timeout=5)
        print(f'   ✅ Status: {response.status_code}')
        
        if response.status_code == 200:
            content = response.text
            preview = content[:100] + '...' if len(content) > 100 else content
            print(f'   📄 Content preview: {preview}')
            original_content = content
        else:
            print(f'   ❌ Error: {response.text}')
            return False
        
        # Test 2: PUT endpoint (update content)
        print('\n2️⃣ Testing PUT /api/writing-style')
        test_content = '''Test Writing Style

This is a test writing style for API validation.
It includes multiple lines and formatting.

Key characteristics:
- Clear and concise
- Professional tone
- Structured format
'''
        
        response = requests.put(
            f'{base_url}/api/writing-style', 
            json={'content': test_content},
            timeout=5
        )
        print(f'   ✅ Status: {response.status_code}')
        
        if response.status_code == 200:
            result = response.json()
            print(f'   📝 Response: {result["message"]}')
            print(f'   📊 Content length: {result["content_length"]} characters')
        else:
            print(f'   ❌ Error: {response.text}')
            return False
        
        # Test 3: GET endpoint again (verify update)
        print('\n3️⃣ Testing GET after update')
        response = requests.get(f'{base_url}/api/writing-style', timeout=5)
        print(f'   ✅ Status: {response.status_code}')
        
        if response.status_code == 200:
            updated_content = response.text
            if updated_content == test_content:
                print('   ✅ Content updated successfully!')
            else:
                print('   ❌ Content mismatch after update')
                return False
        else:
            print(f'   ❌ Error: {response.text}')
            return False
        
        # Test 4: INFO endpoint
        print('\n4️⃣ Testing GET /api/writing-style/info')
        response = requests.get(f'{base_url}/api/writing-style/info', timeout=5)
        print(f'   ✅ Status: {response.status_code}')
        
        if response.status_code == 200:
            info = response.json()
            print(f'   📁 File exists: {info["exists"]}')
            print(f'   📏 File size: {info["size"]} bytes')
            print(f'   📅 Last modified: {info["modified"]}')
            print(f'   📄 Content length: {info["content_length"]} characters')
        else:
            print(f'   ❌ Error: {response.text}')
            return False
        
        # Test 5: Restore original content
        print('\n5️⃣ Restoring original content')
        response = requests.put(
            f'{base_url}/api/writing-style', 
            json={'content': original_content},
            timeout=5
        )
        print(f'   ✅ Status: {response.status_code}')
        
        if response.status_code == 200:
            print('   ✅ Original content restored!')
        else:
            print(f'   ❌ Error restoring content: {response.text}')
            return False
        
        print('\n🎉 All Writing Style API tests passed successfully!')
        return True
        
    except requests.exceptions.ConnectionError:
        print('❌ Connection Error: Server not running on port 8000')
        print('💡 Please start the server with: python src/main.py')
        return False
        
    except requests.exceptions.Timeout:
        print('❌ Timeout Error: Server took too long to respond')
        return False
        
    except Exception as e:
        print(f'❌ Unexpected error: {e}')
        return False

def test_error_cases():
    """Test error handling"""
    base_url = 'http://localhost:8000'
    
    print('\n🔍 Testing Error Cases')
    print('=' * 30)
    
    try:
        # Test invalid content type
        print('1️⃣ Testing invalid request format')
        response = requests.put(
            f'{base_url}/api/writing-style',
            data='invalid json',
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        print(f'   Status: {response.status_code} (should be 422)')
        
        # Test missing content field
        print('\n2️⃣ Testing missing content field')
        response = requests.put(
            f'{base_url}/api/writing-style',
            json={'wrong_field': 'test'},
            timeout=5
        )
        print(f'   Status: {response.status_code} (should be 422)')
        
        print('\n✅ Error handling tests completed')
        
    except Exception as e:
        print(f'❌ Error during error testing: {e}')

if __name__ == '__main__':
    print('🚀 Starting Writing Style API Tests\n')
    
    # Run main tests
    success = test_writing_style_api()
    
    if success:
        # Run error case tests
        test_error_cases()
        print('\n🎯 All tests completed successfully!')
        sys.exit(0)
    else:
        print('\n💥 Some tests failed!')
        sys.exit(1)
