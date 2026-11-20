"""Verify immutable distribution files; workspace and local environments are excluded."""
from pathlib import Path
import hashlib,json,sys
root=Path(__file__).resolve().parents[1]
def main():
 manifest=json.loads((root/'MANIFEST.json').read_text(encoding='utf-8'));errors=[]
 for name,expected in manifest['files'].items():
  p=root/name
  if not p.is_file() or p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:errors.append(name)
 print(json.dumps({'status':'passed' if not errors else 'failed','files_checked':len(manifest['files']),'errors':errors,'scope':'file integrity only; not authorship or runtime/J0 verification'},ensure_ascii=False,indent=2));return bool(errors)
if __name__=='__main__':sys.exit(main())
