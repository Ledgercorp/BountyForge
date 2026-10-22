"""One CLI run for a synthetic owned repair; no real customer work."""
import json
import tempfile
from pathlib import Path
from bountyforge.phase7_owned_demo import OwnedOnlyLedger,owned_demo

def main():
    with tempfile.TemporaryDirectory(prefix='bf-owned-phase7-') as d:
        root=Path(d);directory=root/'review';directory.mkdir(mode=0o700)
        store=OwnedOnlyLedger(root/'ledger.sqlite')
        try:result=owned_demo(store,directory)
        finally:store.close()
        print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
