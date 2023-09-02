import re

from siliconcompiler.tools.yosys.yosys import setup as setup_tool
from siliconcompiler.tools.yosys.syn_asic import setup_asic, prepare_synthesis_libraries
from siliconcompiler.tools.yosys.syn_fpga import setup_fpga
from siliconcompiler import sc_open


def setup(chip):
    '''
    Perform logical equivalence checks
    '''

    # Generic tool setup.
    setup_tool(chip)

    # Generic ASIC / FPGA mode setup.
    mode = chip.get('option', 'mode')
    if mode == 'asic':
        setup_asic(chip)
    elif mode == 'fpga':
        setup_fpga(chip)

    tool = 'yosys'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)
    design = chip.top()

    # Set yosys script path.
    chip.set('tool', tool, 'task', task, 'script', 'sc_lec.tcl',
             step=step, index=index, clobber=False)

    # Input/output requirements.
    if not chip.valid('input', 'netlist', 'verilog') or \
       not chip.get('input', 'netlist', 'verilog', step=step, index=index):
        chip.set('tool', tool, 'task', task, 'input', design + '.vg', step=step, index=index)
    # if not chip.get('input', 'rtl', 'verilog'):
        # TODO: Not sure this logic makes sense? Seems like reverse of tcl
        # chip.set('tool', tool, 'task', task, 'input', design + '.v', step=step, index=index)

    chip.set('tool', tool, 'task', task, 'var', 'induction_steps', '10',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'induction_steps',
             'Number of induction steps for yosys equivalence checking',
             field='help')


def pre_process(chip):
    if chip.get('option', 'mode') == 'asic':
        prepare_synthesis_libraries(chip, include_dff=False)


##################################################
def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    with sc_open(step + ".log") as f:
        for line in f:
            if line.endswith('Equivalence successfully proven!\n'):
                chip._record_metric(step, index, 'drvs', 0, step + ".log")
                continue

            errors = re.search(r'Found a total of (\d+) unproven \$equiv cells.', line)
            if errors is not None:
                num_errors = int(errors.group(1))
                chip._record_metric(step, index, 'drvs', num_errors, step + ".log")
