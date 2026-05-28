# run_all_tests.py — Runs all unit and integration tests in scratch/
import sys, os, subprocess

tests = [
    "test_conflict_resolution.py",
    "test_context_manager.py",
    "test_gatekeeper_rules.py",
    "test_capabilities.py",
    "test_soul_precision.py",
    "test_showbox_decision.py",
    "test_offline_embeddings.py",
    "run_benchmarks.py",
    "test_adaptive_decomposition.py",
    "test_additional_systems.py",
    "test_custom_presets.py",
    "test_evolution.py",
    "test_feedback.py",
    "test_integration_top5.py",
    "test_prompt_versioning.py",
    "test_soul_warnings.py",
    "test_swarm_e2e.py",
    "test_agent_optimizer.py",
    "test_swarm_stability.py",
    "test_agent_limit.py"
]

def main():
    print("============================================================")
    print(" 🚀 RUNNING ALL GNOM-HUB OFFLINE & INTEGRATION TESTS")
    print("============================================================")
    
    passed_cnt = 0
    failed = []
    
    python_bin = sys.executable
    scratch_dir = os.path.dirname(__file__)
    
    for t in tests:
        test_path = os.path.join(scratch_dir, t)
        print(f"\n👉 Running {t}...")
        try:
            res = subprocess.run([python_bin, test_path], capture_output=True, text=True, check=True)
            print(f"✅ Passed: {t}")
            passed_cnt += 1
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed: {t}")
            print("--- STDOUT ---")
            print(e.stdout)
            print("--- STDERR ---")
            print(e.stderr)
            failed.append(t)
            
    print("\n============================================================")
    print(" 📊 TEST SUMMARY")
    print("============================================================")
    print(f"Total Tests Run: {len(tests)}")
    print(f"Passed:          {passed_cnt}")
    print(f"Failed:          {len(failed)}")
    if failed:
        print(f"Failed Tests:    {failed}")
        sys.exit(1)
    else:
        print(" 🎉 ALL TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)

if __name__ == "__main__":
    main()
