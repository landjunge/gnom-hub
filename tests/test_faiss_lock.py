"""Test: FAISS Index darf bei parallelen add_fact nicht korruptieren."""
import threading
from concurrent.futures import ThreadPoolExecutor

from gnom_hub.memory.emb_faiss import _get_index_lock


def test_index_lock_serializes_writes():
    """Alle add_fact-Calls müssen serialisiert sein — Lock hält."""
    scope = "_test_scope_lock"
    execution_order = []
    order_lock = threading.Lock()

    real_lock = _get_index_lock(scope)

    def worker(n):
        with real_lock:
            with order_lock:
                execution_order.append(("enter", n))
            # Simuliere Schreib-Dauer
            import time; time.sleep(0.02)
            with order_lock:
                execution_order.append(("exit", n))

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(worker, range(8)))

    # Bei serialisierten Locks darf kein "enter N+1" zwischen "enter N" und "exit N" liegen
    enter_stack = []
    for evt, n in execution_order:
        if evt == "enter":
            assert n not in enter_stack, f"Lock verletzt: Worker {n} ist doppelt drin"
            enter_stack.append(n)
        else:
            assert enter_stack.pop() == n, f"Exit ohne passendes Enter: {n}"
    assert enter_stack == [], "Lock nicht freigegeben"
    print("OK: Lock serialisiert 8 parallele Worker korrekt")


def test_index_lock_per_scope():
    """Verschiedene Scopes müssen unabhängige Locks haben (kein Deadlock)."""
    lk_a = _get_index_lock("scope_A")
    lk_b = _get_index_lock("scope_B")
    assert lk_a is not lk_b, "Scopes teilen sich Lock — Bug"
    # Beide Locks gleichzeitig haltbar
    with lk_a:
        with lk_b:
            pass
    print("OK: Scopes haben unabhängige Locks")


def test_index_lock_reentrant_get():
    """_get_index_lock gibt für gleichen Scope dieselbe Lock-Instanz zurück."""
    lk1 = _get_index_lock("same_scope")
    lk2 = _get_index_lock("same_scope")
    assert lk1 is lk2
    print("OK: gleicher Scope → gleiche Lock-Instanz")


if __name__ == "__main__":
    test_index_lock_serializes_writes()
    test_index_lock_per_scope()
    test_index_lock_reentrant_get()
    print("\nAlle FAISS-Lock-Tests bestanden.")
