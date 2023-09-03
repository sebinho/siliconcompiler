from siliconcompiler.tools.openroad import openroad
from siliconcompiler.tools.openroad.openroad import setup as setup_tool
from siliconcompiler.tools.openroad.openroad import build_pex_corners
from siliconcompiler.tools.openroad.show import copy_show_files, generic_show_setup
from siliconcompiler.tools.openroad.openroad import pre_process as or_pre_process


####################################################################
# Make Docs
####################################################################
def make_docs(chip):
    openroad.make_docs(chip)
    chip.set('tool', 'openroad', 'task', 'screenshot', 'var', 'show_filepath', '<path>')


def setup(chip):
    '''
    Generate a PNG file from a layout file
    '''

    tool = 'openroad'
    design = chip.top()
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    # Generic tool setup.
    setup_tool(chip)

    generic_show_setup(chip, task, True)

    chip.add('tool', tool, 'task', task, 'output', design + '.png', step=step, index=index)

    chip.set('tool', tool, 'task', task, 'var', 'show_vertical_resolution', '1024',
             step=step, index=index, clobber=False)

    chip.set('tool', tool, 'task', task, 'var', 'include_report_images', 'false',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'include_report_images',
             'true/false, include the images in reports/',
             field='help')


def pre_process(chip):
    or_pre_process(chip)
    copy_show_files(chip)
    build_pex_corners(chip)
