import sys
import os
import json

# Add modules directory to path
sys.path.append(os.path.join(os.getcwd(), 'modules'))

# We can test any of the modules since they all have the same safe_parse_json
from scoring_engine import safe_parse_json

def verify_safe_parse():
    test_cases = [
        {
            "name": "Clean JSON",
            "input": '{"key": "value"}',
            "expected": {"key": "value"}
        },
        {
            "name": "Markdown JSON Fence",
            "input": '```json\n{"key": "value"}\n```',
            "expected": {"key": "value"}
        },
        {
            "name": "Markdown Generic Fence",
            "input": '```\n{"key": "value"}\n```',
            "expected": {"key": "value"}
        },
        {
            "name": "Text before and after",
            "input": 'Here is the data: {"key": "value"} Hope this helps!',
            "expected": {"key": "value"}
        },
        {
            "name": "Array input",
            "input": 'Results: [{"item": 1}, {"item": 2}]',
            "expected": [{"item": 1}, {"item": 2}]
        },
        {
            "name": "Invalid JSON",
            "input": 'This is not JSON at all',
            "expected": None
        }
    ]

    print("--- VERIFYING SAFE_PARSE_JSON ---")
    passed = 0
    for case in test_cases:
        result = safe_parse_json(case["input"])
        if result == case["expected"]:
            print(f"✅ PASS: {case['name']}")
            passed += 1
        else:
            print(f"❌ FAIL: {case['name']}")
            print(f"   Input: {case['input']}")
            print(f"   Got: {result}")
            print(f"   Expected: {case['expected']}")

    print(f"\nSummary: {passed}/{len(test_cases)} cases passed.")
    return passed == len(test_cases)

if __name__ == "__main__":
    if verify_safe_parse():
        print("\nVerification successful!")
    else:
        print("\nVerification failed!")
        sys.exit(1)
