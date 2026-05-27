import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import gnom_hub.db
from gnom_hub.soul_retrieval import retrieve_relevant_facts

def print_banner(text):
    print("=" * 60)
    print(f" {text}")
    print("=" * 60)

def run_tests():
    print_banner("TESTING SOULAG HIGH-PRECISION RETRIEVAL")
    gnom_hub.db.init_db()
    
    # Seed a specific fact
    fact_key = "test_project_name_special_key"
    fact_val = "Der User wünscht sich ein spezielles Dateigrößen-Backup-Modul."
    gnom_hub.db.save_soul_fact(fact_key, fact_val, agent="TestSystem", priority="high")
    print(f"Seeded fact: {fact_key} -> '{fact_val}'")
    
    # Test 1: Short query "test"
    print("\n🔍 Test 1: Short query 'test'")
    res1 = retrieve_relevant_facts("test")
    print(f"Result: {res1}")
    assert res1 == [], f"Short query should return empty list, got: {res1}"
    print("✅ Passed: Short query returned nothing.")
    
    # Test 2: Unspecific query "hallo neu"
    print("\n🔍 Test 2: Unspecific query 'hallo neu'")
    res2 = retrieve_relevant_facts("hallo neu")
    print(f"Result: {res2}")
    assert res2 == [], f"Unspecific query should return empty list, got: {res2}"
    print("✅ Passed: Unspecific query returned nothing.")
    
    # Test 3: Longer query but low similarity ("Ich möchte einen Apfelkuchen backen und essen.")
    print("\n🔍 Test 3: Low similarity query")
    res3 = retrieve_relevant_facts("Ich möchte einen Apfelkuchen backen und essen.")
    print(f"Result: {res3}")
    assert res3 == [], f"Low similarity query should return empty list, got: {res3}"
    print("✅ Passed: Low similarity query returned nothing.")
    
    # Test 4: High similarity query ("Ich brauche ein Backup-Modul für Dateigrößen.")
    print("\n🔍 Test 4: High similarity query")
    res4 = retrieve_relevant_facts("Ich brauche ein Backup-Modul für Dateigrößen.")
    print(f"Result: {res4}")
    assert len(res4) > 0, "High similarity query should return matching facts!"
    assert any("Backup-Modul" in f for f in res4), f"Expected fact not found in: {res4}"
    print("✅ Passed: High similarity query returned the fact.")
    
    print_banner("ALL PRECISION RETRIEVAL TESTS PASSED!")

if __name__ == "__main__":
    run_tests()
