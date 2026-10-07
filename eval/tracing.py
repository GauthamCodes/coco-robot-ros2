"""Probe tracing availability without enabling or changing robot callbacks."""
import shutil
import subprocess


def availability():
    commands={}
    for args in (['ros2','trace','--help'],['lttng','--version'],['ros2','run','tracetools','status']):
        try:
            p=subprocess.run(args,capture_output=True,text=True,timeout=5)
            commands[' '.join(args)]={'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
        except (OSError,subprocess.TimeoutExpired) as exc:commands[' '.join(args)]={'unavailable':str(exc)}
    # The ros2 trace CLI is a convenience frontend. Direct owned LTTng UST
    # capture can work with the installed native tracetools provider alone.
    return {'commands':commands,'available':all(commands[k].get('returncode')==0 for k in ('lttng --version','ros2 run tracetools status')),
            'cli_available':commands['ros2 trace --help'].get('returncode')==0,
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
        if (self.created and self.command(['enable-event','--userspace','--session',self.name,'ros2:*'])
                and self.command(['add-context','--userspace','--session',self.name,'--type','vpid','--type','vtid'])):
            self.started=self.command(['start',self.name])
        return self.started

    def close(self):
        if self.started:self.command(['stop',self.name])
        if self.created:self.command(['destroy',self.name])
        return {'session':self.name,'started':self.started,'commands':self.commands,
                'ctf_files':[str(p.relative_to(self.output)) for p in self.output.rglob('*') if p.is_file()] if self.output.exists() else [],
                'executor_timing_verified':False,
                'note':'CTF must contain ros2 executor/callback events before timing availability is claimed'}


def inspect(output,owned_pids=()):
    """Read native CTF and pair callback spans within process/thread identity."""
    from collections import Counter,defaultdict
    import babeltrace
    from evidence import bag_hash
    collection=babeltrace.TraceCollection()
    if not collection.add_traces_recursive(str(output),'ctf'):raise ValueError('No readable CTF trace')
    counts=Counter();pending=defaultdict(list);durations=[];excluded=Counter();owned=set(owned_pids)
    for event in collection.events:
        pid=event['vpid']
        if pid not in owned:
            excluded[pid]+=1;continue
        counts[event.name]+=1
        if event.name not in ('ros2:callback_start','ros2:callback_end'):continue
        key=(event['vpid'],event['vtid'],event['callback'])
        if event.name.endswith('callback_start'):pending[key].append(event.timestamp)
        elif pending[key]:
            begin=pending[key].pop();duration=event.timestamp-begin
            if duration>=0:durations.append(dict(vpid=key[0],vtid=key[1],callback=key[2],start_trace_ns=begin,wall_duration_ns=duration))
    executor=sum(n for name,n in counts.items() if name.startswith('ros2:rclcpp_executor_'))
    return {'events':dict(counts),'callback_spans':durations,'unmatched_callback_starts':sum(map(len,pending.values())),
            'owned_pids':sorted(owned),'excluded_process_event_counts':dict(excluded),
            'executor_events':executor,'executor_timing_verified':bool(executor and durations),'trace_hash':bag_hash(output),
            'clock_domain':'LTTng trace clock nanoseconds; wall durations, not ROS/simulation time'}
