"""Copy prepared deliverables to the authorized original project, without deleting files."""
from pathlib import Path
import shutil
import hashlib
import json
SOURCE=Path(__file__).resolve().parents[1]
DEST=Path('/Users/daniaromar/Desktop/Universitetet/7. Høst 2026/IND320/Project')

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def sync():
    #preserve every modified destination file once before applying our updates
    roots=['src','scripts','tests','pages','data','notebooks','reports','backups']
    files=[SOURCE/name for name in ['app.py','requirements.txt','requirements-dev.txt','requirements-lock.txt','README.md','.gitignore','pytest.ini'] if (SOURCE/name).exists()]
    for name in roots:
        files.extend(p for p in (SOURCE/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.tmp'))
    manifest=DEST/'backups/part3_sync_manifest.json'
    previous=json.loads(manifest.read_text()) if manifest.exists() else {}
    new={}
    for source in files:
        relative=source.relative_to(SOURCE);target=DEST/relative;key=str(relative)
        if target.exists() and digest(source)!=digest(target):
            if key in previous and digest(target)!=previous[key]:
                raise RuntimeError(f'Concurrent user edit detected, preserving file: {target}')
            backup=DEST/'backups/before_part3'/relative
            if not backup.exists() and 'backups' not in relative.parts:
                backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup)
        if not target.exists() or digest(source)!=digest(target):
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        new[key]=digest(source)
    manifest.parent.mkdir(parents=True,exist_ok=True);manifest.write_text(json.dumps(new,indent=2))
    print(f'Synchronized {len(new)} files without deleting files.')
if __name__=='__main__':sync()
