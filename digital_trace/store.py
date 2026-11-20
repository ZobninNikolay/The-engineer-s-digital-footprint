from __future__ import annotations
import json,sqlite3
from pathlib import Path
from contextlib import contextmanager
from .common import *
class Store:
 def __init__(self,root):
  self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True)
  self.db=sqlite3.connect(self.root/'state.sqlite3',timeout=15,isolation_level=None);self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=FULL')
  self.db.execute('CREATE TABLE IF NOT EXISTS records(kind TEXT,id TEXT,body TEXT,PRIMARY KEY(kind,id))')
  self.db.execute('CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY,at TEXT,action TEXT,body TEXT)')
 @contextmanager
 def transaction(self):
  self.db.execute('BEGIN IMMEDIATE')
  try:yield;self.db.commit()
  except: self.db.rollback();raise
 def get(self,k,i):
  row=self.db.execute('SELECT body FROM records WHERE kind=? AND id=?',(k,i)).fetchone()
  if row is None:raise TraceError('Missing '+k+': '+i)
  return json.loads(row[0])
 def all(self,k):return [json.loads(r[0]) for r in self.db.execute('SELECT body FROM records WHERE kind=? ORDER BY id',(k,))]
 def put(self,k,i,v):self.db.execute('INSERT OR REPLACE INTO records VALUES(?,?,?)',(k,i,canonical(v)))
 def audit(self,a,v):self.db.execute('INSERT INTO audit(at,action,body) VALUES(?,?,?)',(now(),a,canonical(v)))
 def close(self):self.db.close()
def initialize(root,role,environment,actor,semester_start):
 if role not in ('student','teacher','commission') or environment not in ('demo','pilot') or (role=='commission' and environment!='demo'):raise TraceError('Invalid role/environment')
 ident(actor);date(semester_start);s=Store(root)
 try:
  with s.transaction():
   if s.all('config'):raise TraceError('Workspace already initialized; role cannot be silently changed')
   s.put('config','main',{'role':role,'environment':environment,'actor':actor,'semester_start':semester_start,'limit':100,'used':0,'identity_assurance':'local_declared_not_SSO'})
 finally:s.close()
