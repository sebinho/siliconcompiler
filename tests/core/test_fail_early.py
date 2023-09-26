import siliconcompiler
from siliconcompiler.tools.yosys import syn_asic
from siliconcompiler.tools.surelog import parse

import pytest


@pytest.mark.quick
@pytest.mark.eda
def test_fail_early(capfd):
    chip = siliconcompiler.Chip('test')
    chip.set('input', 'rtl', 'verilog', 'fake.v')
    chip.load_target('freepdk45_demo')
    chip.set('option', 'mode', 'asic')
    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', parse)
    chip.node(flow, 'syn', syn_asic)
    chip.edge(flow, 'import', 'syn')

    with pytest.raises(siliconcompiler.SiliconCompilerError):
        chip.run()
    # Fail if 'syn' step is run
    out, _ = capfd.readouterr()
    assert "Halting step 'import'" in out
    assert "Halting step 'syn'" not in out
