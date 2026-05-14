import os
import sys
import ast
import urllib.request

# Find the active Gnom-Hub Port
port = 3002
for p in range(3002, 4000):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{p}/api/stats", timeout=0.1)
        port = p
        break
    except:
        pass

os.environ["GNOM_HUB_PORT"] = str(port)
sys.path.insert(0, "./src")
from gnom_hub import hub_mcp

print(f"🚀 Starte Testreihe für Gnom-Hub auf Port {port}...")

passed = 0
failed = 0

def run_test(name, func, *args):
    global passed, failed
    try:
        res = func(*args)
        if res.startswith("Err"):
            print(f"❌ {name} fehlgeschlagen -> {res}")
            failed += 1
            return None
        
        try:
            res_obj = ast.literal_eval(res)
        except:
            res_obj = res
            
        print(f"✅ {name} erfolgreich")
        passed += 1
        return res_obj
    except Exception as e:
        print(f"❌ {name} Exception -> {e}")
        failed += 1
        return None

for i in range(1, 4):
    print(f"\n--- 🔄 TEST ITERATION {i} ---")
    
    # 1. create_agent
    a = run_test("create_agent", hub_mcp.create_agent, f"TestAgent_{i}", "Test Description")
    a_id = a.get("id") if isinstance(a, dict) else None
    
    if not a_id:
        print("Konnte Agenten nicht anlegen. Überspringe Iteration.")
        continue

    # 2. get_agent
    run_test("get_agent", hub_mcp.get_agent, a_id)

    # 3. search_agents
    run_test("search_agents", hub_mcp.search_agents, f"TestAgent_{i}")

    # 4. set_agent_status
    run_test("set_agent_status", hub_mcp.set_agent_status, a_id, "online")

    # 5. get_agent_status
    run_test("get_agent_status", hub_mcp.get_agent_status, a_id)

    # 6. list_all_agents
    run_test("list_all_agents", hub_mcp.list_all_agents)

    # 7. save_to_memory
    m1 = run_test("save_to_memory", hub_mcp.save_to_memory, a_id, f"Test Memory A {i}")
    m1_id = m1.get("id") if isinstance(m1, dict) else None
    
    m2 = run_test("save_to_memory", hub_mcp.save_to_memory, a_id, f"Test Memory B {i}")
    m2_id = m2.get("id") if isinstance(m2, dict) else None

    # 8. get_memory
    run_test("get_memory", hub_mcp.get_memory, a_id)

    # 9. count_memory
    run_test("count_memory", hub_mcp.count_memory, a_id)

    # 10. update_memory
    run_test("update_memory", hub_mcp.update_memory, m1_id, f"Updated Memory A {i}")

    # 11. search_memory
    run_test("search_memory", hub_mcp.search_memory, "Updated")

    # 12. delete_memory
    run_test("delete_memory", hub_mcp.delete_memory, m2_id)

    # 13. clear_agent_memory
    run_test("clear_agent_memory", hub_mcp.clear_agent_memory, a_id)

    # 14. get_system_stats
    run_test("get_system_stats", hub_mcp.get_system_stats)

    # 15. delete_agent
    run_test("delete_agent", hub_mcp.delete_agent, a_id)

print(f"\n=======================")
print(f"🏆 TEST ZUSAMMENFASSUNG")
print(f"=======================")
print(f"Gesamt-Tests: {passed + failed}")
print(f"Erfolgreich : {passed}")
print(f"Fehlgeschlagen: {failed}")
if failed == 0:
    print("🎉 ALLE TOOLS FUNKTIONIEREN PERFEKT!")
else:
    print("⚠️ ES GAB FEHLER BEIM TESTEN!")
