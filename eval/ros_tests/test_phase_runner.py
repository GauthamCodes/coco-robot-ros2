"""Synthetic runner orchestration; no node, simulator, or motion is started."""
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phase_control import execute

class ControlFixture:
    def __init__(self,failed=None):
        self.failed=failed;self.commands=[];self.checkpoints=[]
        self.records=[dict(phase='baseline',contract_valid=True)]*5
        self.validator=SimpleNamespace(reacquire=lambda _:None)
        self.clock=0
    def checkpoint(self,name,**fields):self.checkpoints.append((name,fields))
    def observation_checkpoint(self,name):self.checkpoint(name)
    def phase(self,name):pass
    def request(self,name):
        self.commands.append(name)
        outcome='failed' if name==self.failed else {'stow':'done','pick':'held','place':'placed'}[name]
        return dict(completed=True,status={'outcome':outcome})
    def approach(self):
        self.commands.append('approach');return dict(status={'outcome':'failed' if self.failed=='approach' else 'arrived'})
    def wait(self,predicate,_):return predicate()
    def get_clock(self):return self
    def now(self):
        self.clock+=3_000_000_000;return SimpleNamespace(nanoseconds=self.clock)

@pytest.mark.parametrize('failure,commands',[(None,['stow','approach','pick','place']),('stow',['stow']),('approach',['stow','approach']),('pick',['stow','approach','pick'])])
def test_no_skipped_or_unearned_control_transition(failure,commands):
    node=ControlFixture(failure);results=[];execute(node,results)
    assert node.commands==commands
    assert node.checkpoints[0][0]=='control_started'
    assert node.checkpoints[-1][0]=='control_finished'
    assert node.checkpoints[-1][1]['post_release_recording_window_complete'] is (True if failure is None else None)
