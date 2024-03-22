from siliconcompiler.tools.surelog import parse as surelog_parse
from siliconcompiler.tools.chisel import convert as chisel_convert
from siliconcompiler.tools.bambu import convert as bambu_convert
from siliconcompiler.tools.bluespec import convert as bluespec_convert
from siliconcompiler.tools.ghdl import convert as ghdl_convert
from siliconcompiler.tools.sv2v import convert as sv2v_convert

from siliconcompiler.tools.builtin import concatenate


def __get_frontends():
    return {
        "verilog": [('import', surelog_parse)],
        "systemverilog": [('import', surelog_parse),
                          ('convert', sv2v_convert)],
        "chisel": [('import', chisel_convert)],
        "c": [('import', bambu_convert)],
        "bluespec": [('import', bluespec_convert)],
        "vhdl": [('import', ghdl_convert)]
    }


def setup_multiple_frontends(chip, flow):
    selected_frontends = []
    # Select frontend sets
    if chip.valid('input', 'rtl', 'vhdl'):
        selected_frontends.append("vhdl")

    if chip.valid('input', 'hll', 'c'):
        selected_frontends.append("c")
    if chip.valid('input', 'hll', 'bsv'):
        selected_frontends.append("bluespec")
    if chip.valid('input', 'hll', 'scala'):
        selected_frontends.append("chisel")
    if chip.valid('input', 'config', 'chisel'):
        selected_frontends.append("chisel")

    if chip.valid('input', 'rtl', 'verilog'):
        files = []
        for values, _, _ in chip.schema._getvals('input', 'rtl', 'verilog'):
            files.extend(values)

        frontend = "verilog"
        for f in files:
            if f.endswith('.sv'):
                frontend = "systemverilog"
        selected_frontends.append(frontend)

    concat_nodes = []
    flowname = flow.design
    for frontend, pipe in __get_frontends().items():
        if frontend not in selected_frontends:
            continue

        prev_step = None
        for step, task in pipe:
            step_name = f'{step}_{frontend}'

            flow.node(flowname, step_name, task)
            if prev_step:
                flow.edge(flowname, prev_step, step_name)

            prev_step = step_name

        if prev_step:
            concat_nodes.append(prev_step)

    concat_step = 'combine'
    flow.node(flowname, concat_step, concatenate)
    for node in concat_nodes:
        flow.edge(flowname, node, concat_step)

    return concat_step


def setup_frontend(chip):
    '''
    Return list of frontend steps to be prepended to flowgraph as list of
    (step, task) tuples.
    '''

    frontends = __get_frontends()
    frontend = chip.get('option', 'frontend')
    if frontend not in frontends:
        raise ValueError(f'Unsupported frontend: {frontend}')
    return frontends[frontend]
