"""Download pinned method code only when requested; no changes to original benches."""
import subprocess
import shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SOURCES={'in3':('https://github.com/thunlp/Tell_Me_More.git','654fcec4da3b3465536d57b0d1995e8699a5a8f0'),'stitch':('https://github.com/Seattleyrz/contextual-intent.git','1115129590410e90cb7fe84c57098f9d404c56a9'),'voi':('https://github.com/dong-river/VOI_communication.git','27466a7832d5aafff82017a659e08942e18b01ae')}
for name,(url,sha) in SOURCES.items():
    target=ROOT/'.local/upstream'/name
    if target.exists() and not (target/'.git').exists():
        # A source snapshot copied to the server is retained as a backup.
        backup=target.with_name(name+'-source-snapshot')
        if backup.exists(): raise RuntimeError(f'Inspect existing snapshot before installing: {backup}')
        target.rename(backup)
    if not target.exists():
        subprocess.run(['git','clone',url,str(target)],check=True)
    subprocess.run(['git','-C',str(target),'checkout','--detach',sha],check=True)
