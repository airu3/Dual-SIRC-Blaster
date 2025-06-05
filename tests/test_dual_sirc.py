import os
import builtins
import dual_sirc

# ensure mock mode for tests
os.environ['OBNIZ_MOCK'] = '1'


def test_sirc12_pattern():
    code = dual_sirc.sirc12(0x80)
    # start header + 12 bits * (burst+gap)
    assert len(code) == 2 + 12 * 2
    assert code[0] == dual_sirc.HEADER_US
    assert code[1] == dual_sirc.GAP_US
    # LSB of 0x80 -> 0
    assert code[2] == dual_sirc.BURST_0_US


def test_irblaster_send(capsys):
    b = dual_sirc.IRBlaster('A')
    b.connect()
    b.send([1, 2])
    captured = capsys.readouterr()
    assert 'mock' in captured.out
