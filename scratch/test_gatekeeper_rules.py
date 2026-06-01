#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Set up project root on path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gnom_hub.core.security.gatekeeper import is_command_safe_and_whitelisted

def run_tests():
    print("🧪 Running Gatekeeper Rule Verification Tests...")
    
    # Define test cases for command verification
    test_cases = [
        # (Command, Expected Safe, Expected Part of Reason)
        ("python3 file_size_calc.py", True, ""),
        ("PYTHONPATH=src python3 -m pytest", True, ""),
        ("git status", True, ""),
        ("git log -n 5 && git diff", True, ""),
        
        # Whitelist rejections
        ("sudo apt-get update", False, "nicht auf der Whitelist"),
        ("nmap -sV localhost", False, "nicht auf der Whitelist"),
        ("rm -rf /", False, "nicht erlaubt"),
        
        # Git subcommand checks
        ("git push --force", False, "git push ist Agenten nicht erlaubt"),
        
        # Pip pre-approved safe packages
        ("pip install fpdf2", True, ""),
        ("pip3 install pytest", True, ""),
        
        # Pip online API validation checks
        ("pip install requests", True, ""), # Pre-approved or should verify online successfully
        ("pip install flask", True, ""), # Should be verified online and be allowed
        ("pip install invalidpackage1234567890", False, "konnte nicht auf PyPI verifiziert werden"),
        
        # Chained commands: safe
        ("git status && python3 test.py", True, ""),
        # Chained commands: unsafe
        ("git status && sudo apt-get update", False, "nicht auf der Whitelist")
    ]
    
    failed = 0
    for idx, (cmd, expected_safe, reason_sub) in enumerate(test_cases):
        try:
            is_safe, reason = is_command_safe_and_whitelisted(cmd)
            status = "PASSED" if is_safe == expected_safe else "FAILED"
            
            if is_safe != expected_safe:
                print(f"❌ Test {idx+1} FAILED: '{cmd}' -> got (Safe={is_safe}, Reason='{reason}'), expected (Safe={expected_safe})")
                failed += 1
            elif not is_safe and reason_sub and reason_sub not in reason:
                print(f"❌ Test {idx+1} FAILED (Reason Mismatch): '{cmd}' -> got Reason='{reason}', expected it to contain '{reason_sub}'")
                failed += 1
            else:
                print(f"✅ Test {idx+1} PASSED: '{cmd}' -> Safe={is_safe} {f'(Reason: {reason})' if not is_safe else ''}")
        except Exception as e:
            print(f"💥 Test {idx+1} CRASHED: '{cmd}' -> {e}")
            failed += 1
            
    if failed == 0:
        print("\n🎉 All Gatekeeper verification tests PASSED!")
        sys.exit(0)
    else:
        print(f"\n❌ {failed} tests FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
