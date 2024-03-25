import os
from siliconcompiler.tools._common import add_require_input, add_frontend_requires, get_input_files


def setup(chip):
    '''
    Imports VHDL and converts it to verilog
    '''

    # Standard Setup
    tool = 'ghdl'
    clobber = False

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    chip.set('tool', tool, 'exe', 'ghdl')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=4.0.0-dev', clobber=clobber)

    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=clobber)
    chip.set('tool', tool, 'task', task, 'option', '',
             step=step, index=index, clobber=clobber)
    chip.set('tool', tool, 'task', task, 'stdout', 'destination', 'output',
             step=step, index=index)
    chip.set('tool', tool, 'task', task, 'stdout', 'suffix', 'v',
             step=step, index=index)

    # Schema requirements
    add_require_input(chip, 'input', 'rtl', 'vhdl')
    add_frontend_requires(chip, [])

    design = chip.top()

    chip.set('tool', tool, 'task', task, 'output', f'{design}.v', step=step, index=index)


################################
#  Custom runtime options
################################
def runtime_options(chip):

    ''' Custom runtime options, returnst list of command line options.
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    options = []

    # Synthesize inputs and output Verilog netlist
    options.append('--synth')
    options.append('--std=08')
    options.append('--out=verilog')
    options.append('--no-formal')

    # currently only -fsynopsys and --latches supported
    valid_extraopts = ['-fsynopsys', '--latches']

    extra_opts = chip.get('tool', 'ghdl', 'task', task, 'var', 'extraopts', step=step, index=index)
    for opt in extra_opts:
        if opt in valid_extraopts:
            options.append(opt)
        else:
            chip.error('Unsupported option ' + opt)

    # Add sources
    for value in get_input_files(chip, 'input', 'rtl', 'vhdl'):
        options.append(value)

    # Set top module
    design = chip.top()
    options.append('-e')

    if chip.get('option', 'frontend') == 'vhdl':
        options.append(design)

    return options
