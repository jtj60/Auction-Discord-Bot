from state_machine import StateMachine
import pytest

def test_nom_from_start():
  state_machine = StateMachine()
  state_machine.machine.nom_from_start()
  print(state_machine.machine.get_state())
  pass

# def test_get_working(): 
#   class Matter(object):
#     pass
#   lump = Matter()
#   from transitions import Machine
#   states = ['happy', 'sad']
#   machine = Machine(lump, states = states, transitions = [], initial='happy')
#   print(lump.state)
#   assert(lump.state == 'happy')

