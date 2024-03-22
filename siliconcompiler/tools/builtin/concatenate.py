from siliconcompiler.tools.builtin import _common
import os
import glob
from siliconcompiler import utils
from siliconcompiler import sc_open


def setup(chip):
    '''
    A no-operation that passes inputs to outputs.
    '''
    pass


def _select_inputs(chip, step, index):
    chip.logger.info("Running builtin task 'concatenate'")

    flow = chip.get('option', 'flow')
    return chip.get('flowgraph', flow, step, index, 'input')


def _gather_outputs(chip, step, index):
    '''Return set of filenames that are guaranteed to be in outputs
    directory after a successful run of step/index.'''

    flow = chip.get('option', 'flow')

    in_nodes = chip.get('flowgraph', flow, step, index, 'input')
    in_task_outputs = [chip._gather_outputs(*node) for node in in_nodes]

    if len(in_task_outputs) > 0:
        return in_task_outputs[0].union(*in_task_outputs[1:])

    return []


def _input_file_copy(chip, in_job, in_step, in_index):
    design = chip.top()

    for file in glob.glob(f"../../../{in_job}/{in_step}/{in_index}/outputs/*"):
        file_name = os.path.basename(file)

        if file_name == f'{design}.pkg.json':
            continue

        new_name, ext = os.path.splitext(file_name)

        new_name += f"_{in_step}{in_index}{ext}"

        utils.link_symlink_copy(file, f'inputs/{new_name}')


def run(chip):
    return _common.run(chip)


def post_process(chip):
    design = chip.top()

    files = {}
    for file in glob.glob("inputs/*"):
        if file.endswith(f'{chip.design}.pkg.json'):
            continue

        _, ext = os.path.splitext(file)

        files.setdefault(ext, []).append(file)

    for ext, in_files in files.items():
        with open(f'outputs/{design}{ext}', 'w') as out:
            for result in in_files:
                with sc_open(result) as in_file:
                    out.write(f'// Start of: {result}\n')
                    out.write(in_file.read())
                    out.write(f'// End of: {result}\n\n')
