#!/usr/bin/env python3
"""
Test runner for FPL Optimizer

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --data-sources     # Run data source tests
    python run_tests.py --real-apis        # Run real API tests
    python run_tests.py --xpts             # Run xPts tests
    python run_tests.py --optimizer        # Run optimizer tests
"""

import sys
import subprocess
import argparse

def run_all_tests():
    """Run all tests"""
    print("🧪 Running All Tests")
    print("=" * 50)
    
    test_modules = [
        "fpl_optimizer.tests.test_data_sources",
        "fpl_optimizer.tests.test_real_apis", 
        "fpl_optimizer.tests.test_xpts",
        "fpl_optimizer.tests.test_optimizer"
    ]
    
    for module in test_modules:
        print(f"\n📋 Running {module}...")
        try:
            subprocess.run([sys.executable, "-m", module], check=True)
            print(f"✅ {module} completed successfully")
        except subprocess.CalledProcessError:
            print(f"❌ {module} failed")
            return False
    
    print("\n🎉 All tests completed!")
    return True

def run_specific_test(module_name):
    """Run a specific test module"""
    print(f"🧪 Running {module_name}")
    print("=" * 50)
    
    try:
        subprocess.run([sys.executable, "-m", f"fpl_optimizer.tests.{module_name}"], check=True)
        print(f"✅ {module_name} completed successfully")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ {module_name} failed")
        return False

def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description='FPL Optimizer Test Runner')
    parser.add_argument('--data-sources', action='store_true', help='Run data source tests')
    parser.add_argument('--real-apis', action='store_true', help='Run real API tests')
    parser.add_argument('--xpts', action='store_true', help='Run xPts tests')
    parser.add_argument('--optimizer', action='store_true', help='Run optimizer tests')
    
    args = parser.parse_args()
    
    if args.data_sources:
        run_specific_test("test_data_sources")
    elif args.real_apis:
        run_specific_test("test_real_apis")
    elif args.xpts:
        run_specific_test("test_xpts")
    elif args.optimizer:
        run_specific_test("test_optimizer")
    else:
        # Run all tests by default
        run_all_tests()

if __name__ == "__main__":
    main() 