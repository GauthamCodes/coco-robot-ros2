"""Probe tracing availability without enabling or changing robot callbacks."""
import shutil
import subprocess


def availability():
    commands={}
    for args in (['ros2','trace','--help'],['lttng','--version']):
        try:
            p=subprocess.run(args,capture_output=True,text=True,timeout=5)
            commands[' '.join(args)]={'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
        except (OSError,subprocess.TimeoutExpired) as exc:commands[' '.join(args)]={'unavailable':str(exc)}
    return {'commands':commands,'available':all(v.get('returncode')==0 for v in commands.values()),
            'executor_timing_verified':False,'note':'Availability is not proof of working UST session or captured executor events'}


class TraceSession:
    """Own one uniquely named LTTng UST session; never stop foreign sessions."""
    def __init__(self,output):
        import uuid
        self.name='coco-m1-'+uuid.uuid4().hex
        self.output=__import__('pathlib').Path(output)
        self.commands=[];self.created=False;self.started=False

    def command(self,args):
        try:
            p=subprocess.run(['lttng']+args,capture_output=True,text=True,timeout=10)
            value={'argv':['lttng']+args,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
        except (OSError,subprocess.TimeoutExpired) as exc:value={'argv':['lttng']+args,'unavailable':str(exc)}
        self.commands.append(value);return value.get('returncode')==0

    def start(self):
        self.created=self.command(['create',self.name,'--output',str(self.output)])
        if self.created and self.command(['enable-event','--userspace','--session',self.name,'ros2:*']):
            self.started=self.command(['start',self.name])
        return self.started

    def close(self):
        if self.started:self.command(['stop',self.name])
        if self.created:self.command(['destroy',self.name])
        return {'session':self.name,'started':self.started,'commands':self.commands,
                'ctf_files':[str(p.relative_to(self.output)) for p in self.output.rglob('*') if p.is_file()] if self.output.exists() else [],
                'executor_timing_verified':False,
                'note':'CTF must contain ros2 executor/callback events before timing availability is claimed'}
