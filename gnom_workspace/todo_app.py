# Simple To-Do List App
tasks = []
while True:
    cmd = input("Command (add/list/done/quit): ").strip().lower()
    if cmd == "quit": break
    elif cmd == "add": tasks.append(input("Task: "))
    elif cmd == "list":
        for i, t in enumerate(tasks):
            print(f"{i+1}. {t}")
    elif cmd == "done":
        idx = int(input("Task number: ")) - 1
        if 0 <= idx < len(tasks):
            print(f"Done: {tasks.pop(idx)}")
    else: print("Unknown command")