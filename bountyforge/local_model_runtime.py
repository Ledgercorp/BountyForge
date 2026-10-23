"""Bounded lifecycle for the two exact trusted local models. No downloader."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import tempfile
import threading
import time
import urllib.request

from bountyforge.model import _NoRedirect
from bountyforge.model_profiles import profile_spec
from bountyforge.phase8_evaluation import require_credential_free_host


def digest_file(path):
    if path.is_symlink() or not path.is_file():raise ValueError('REGULAR_MODEL_ASSET_REQUIRED')
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def enforce_limits():
    for kind,cap in ((resource.RLIMIT_AS,10*1024**3),(resource.RLIMIT_CPU,180),
                     (resource.RLIMIT_CORE,0),(resource.RLIMIT_FSIZE,1024*1024)):
        resource.setrlimit(kind,(cap,cap))


class LocalRuntime:
    def __init__(self,model_profile):
        self.spec=profile_spec(model_profile);self.child=None;self.temporary=None;self.monitor=None
        self.done=threading.Event();self.log=None
        self.measurement={'model_profile':self.spec['id'],'model_sha256':self.spec['sha256'],
            'context_tokens':2048,'threads':2,'address_space_limit_bytes':10*1024**3,
            'cpu_limit_seconds':180,'wall_limit_seconds':180,'peak_rss_kib':None,'peak_address_kib':None,
            'observed_cpu_seconds':None,'cpu_observation':'Linux process counters at last sample before shutdown',
            'server_stopped':False,'wall_limit_reached':False}

    def _monitor(self):
        while not self.done.wait(0.5):
            if self.child.poll() is not None:return
            if time.monotonic()-self.started>180:
                self.measurement['wall_limit_reached']=True
                try:self.child.kill()
                except ProcessLookupError:pass
                return
            self._sample()

    def _sample(self):
        try:
            for row in Path('/proc/'+str(self.child.pid)+'/status').read_text().splitlines():
                key='peak_rss_kib' if row.startswith('VmHWM:') else 'peak_address_kib' if row.startswith('VmPeak:') else None
                if key:self.measurement[key]=max(self.measurement[key] or 0,int(row.split()[1]))
            stat=Path('/proc/'+str(self.child.pid)+'/stat').read_text()
            fields=stat[stat.rfind(')')+2:].split()
            seconds=(int(fields[11])+int(fields[12]))/os.sysconf('SC_CLK_TCK')
            self.measurement['observed_cpu_seconds']=max(self.measurement['observed_cpu_seconds'] or 0,seconds)
        except (OSError,ValueError):pass

    def __enter__(self):
        try:
            if os.uname().sysname!='Linux':raise ValueError('LINUX_ONLY')
            require_credential_free_host()
            base=Path.home()/'.cache/bountyforge';model=base/'models'/self.spec['filename']
            runtime=base/'runtime';archive=runtime/'llama-b11750-bin-ubuntu-x64.tar.gz'
            if digest_file(model)!=self.spec['sha256'] or digest_file(archive)!=self.spec['runtime_sha256']:
                raise ValueError('LOCAL_ASSET_DIGEST_REJECTED')
            subprocess.run(['tar','-xzf',str(archive),'-C',str(runtime),'--no-same-owner','--no-same-permissions'],check=True,timeout=30)
            binary=runtime/'llama-b11750/llama-server'
            self.temporary=tempfile.TemporaryDirectory(prefix='bf15-local-runtime-');self.log=open(Path(self.temporary.name)/'server.log','wb')
            self.started=time.monotonic()
            self.child=subprocess.Popen([str(binary),'-m',str(model),'--host','127.0.0.1','--port','8080',
                    '-t','2','-c','2048','-np','1'],env={'PATH':'/usr/local/bin:/usr/bin:/bin','LD_LIBRARY_PATH':str(binary.parent)},
                    stdout=self.log,stderr=self.log,preexec_fn=enforce_limits)
            self.monitor=threading.Thread(target=self._monitor,daemon=True);self.monitor.start()
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),_NoRedirect())
            deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                if self.child.poll() is not None:raise RuntimeError('RESOURCE_BOUNDED_SERVER_EXITED')
                try:
                    with opener.open('http://127.0.0.1:8080/health',timeout=1) as response:
                        value=json.loads(response.read(1024))
                        if type(value) is dict and value.get('status')=='ok':break
                except (OSError,ValueError):pass
                time.sleep(1)
            else:raise RuntimeError('LOCAL_MODEL_LOAD_TIMEOUT')
            self.measurement['load_seconds']=round(time.monotonic()-self.started,3);self._sample()
            return self
        except BaseException:
            self.__exit__(None,None,None);raise

    def __exit__(self,*_):
        self.done.set()
        if self.monitor is not None:self.monitor.join(timeout=2)
        if self.child is not None:
            self._sample()
            self.measurement['unexpected_exit']=self.child.poll() is not None
            if self.child.poll() is None:
                self.child.terminate()
                try:self.child.wait(timeout=5)
                except subprocess.TimeoutExpired:self.child.kill();self.child.wait(timeout=5)
            self.measurement['server_exit_code']=self.child.returncode
            self.measurement['server_elapsed_seconds']=round(time.monotonic()-self.started,3)
        self.measurement['server_stopped']=self.child is None or self.child.poll() is not None
        if self.log is not None:self.log.close()
        if self.temporary is not None:self.temporary.cleanup()
