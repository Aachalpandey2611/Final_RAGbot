from tests import test_adaptive_chunking as t
import sys

failed = False

for name in dir(t):
    if name.startswith("test_"):
        try:
            getattr(t, name)()
            print(f"PASS: {name}")
        except AssertionError as e:
            print(f"FAIL: {name} - {e}")
            failed = True
        except Exception as e:
            print(f"ERROR: {name} - {e}")
            failed = True

if failed:
    sys.exit(1)

print("All tests passed")
