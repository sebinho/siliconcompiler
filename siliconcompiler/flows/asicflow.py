import siliconcompiler

from siliconcompiler.flows._common import setup_frontend, setup_multiple_frontends

from siliconcompiler.tools.yosys import syn_asic
from siliconcompiler.tools.openroad import floorplan
from siliconcompiler.tools.openroad import physyn
from siliconcompiler.tools.openroad import place
from siliconcompiler.tools.openroad import cts
from siliconcompiler.tools.openroad import route
from siliconcompiler.tools.openroad import dfm
from siliconcompiler.tools.openroad import export as openroad_export
from siliconcompiler.tools.klayout import export as klayout_export

from siliconcompiler.tools.builtin import minimum


############################################################################
# DOCS
############################################################################
def make_docs(chip):
    n = 3
    return setup(chip, syn_np=n, floorplan_np=n, physyn_np=n, place_np=n, cts_np=n, route_np=n)


###########################################################################
# Flowgraph Setup
############################################################################
def setup(chip,
          flowname='asicflow',
          syn_np=1,
          floorplan_np=1,
          physyn_np=1,
          place_np=1,
          cts_np=1,
          route_np=1,
          multi=False):
    '''
    A configurable ASIC compilation flow.

    The 'asicflow' includes the stages below. The steps syn, floorplan,
    physyn, place, cts, route, and dfm have minimization associated
    with them. To view the flowgraph, see the .png file.

    * **import**: Sources are collected and packaged for compilation
    * **syn**: Translates RTL to netlist using Yosys
    * **floorplan**: Floorplanning
    * **physyn**: Physical Synthesis
    * **place**: Global and detailed placement
    * **cts**: Clock tree synthesis
    * **route**: Global and detailed routing
    * **dfm**: Metal fill, atenna fixes and any other post routing steps
    * **export**: Export design from APR tool and merge with library GDS
    * **sta**: Static timing analysis (signoff)
    * **lvs**: Layout versus schematic check (signoff)
    * **drc**: Design rule check (signoff)

    The syn, physyn, place, cts, route steps supports per process
    options that can be set up by setting '<step>_np'
    arg to a value > 1, as detailed below:

    * syn_np : Number of parallel synthesis jobs to launch
    * floorplan_np : Number of parallel floorplan jobs to launch
    * physyn_np : Number of parallel physical synthesis jobs to launch
    * place_np : Number of parallel place jobs to launch
    * cts_np : Number of parallel clock tree synthesis jobs to launch
    * route_np : Number of parallel routing jobs to launch
    '''

    flow = siliconcompiler.Flow(chip, flowname)

    # Linear flow, up until branch to run parallel verification steps.
    longpipe = ['syn',
                'synmin',
                'floorplan',
                'floorplanmin',
                'place',
                'placemin',
                'cts',
                'ctsmin',
                'route',
                'routemin',
                'dfm']

    # step --> task
    tasks = {
        'syn': syn_asic,
        'synmin': minimum,
        'floorplan': floorplan,
        'floorplanmin': minimum,
        'physyn': physyn,
        'physynmin': minimum,
        'place': place,
        'placemin': minimum,
        'cts': cts,
        'ctsmin': minimum,
        'route': route,
        'routemin': minimum,
        'dfm': dfm
    }

    np = {
        "syn": syn_np,
        "floorplan": floorplan_np,
        "physyn": physyn_np,
        "place": place_np,
        "cts": cts_np,
        "route": route_np
    }

    prevstep = None
    # Remove built in steps where appropriate
    flowpipe = []
    for step in longpipe:
        task = tasks[step]
        if task == minimum:
            if prevstep in np and np[prevstep] > 1:
                flowpipe.append(step)
        else:
            flowpipe.append(step)
        prevstep = step

    prevstep = None
    flowtasks = []
    if multi:
        prevstep = setup_multiple_frontends(chip, flow)
    else:
        flowtasks = setup_frontend(chip)

    for step in flowpipe:
        flowtasks.append((step, tasks[step]))

    # Programmatically build linear portion of flowgraph and fanin/fanout args
    for step, task in flowtasks:
        fanout = 1
        if step in np:
            fanout = np[step]
        # create nodes
        for index in range(fanout):
            # nodes
            flow.node(flowname, step, task, index=index)

            # edges
            if task == minimum:
                fanin = 1
                if prevstep in np:
                    fanin = np[prevstep]
                for i in range(fanin):
                    flow.edge(flowname, prevstep, step, tail_index=i)
            elif prevstep:
                flow.edge(flowname, prevstep, step, head_index=index)

            # metrics
            goal_metrics = ()
            weight_metrics = ()
            if task in (syn_asic, ):
                goal_metrics = ('errors',)
                weight_metrics = ()
            elif task in (floorplan, physyn, place, cts, route, dfm):
                goal_metrics = ('errors', 'setupwns', 'setuptns')
                weight_metrics = ('cellarea', 'peakpower', 'leakagepower')

            for metric in goal_metrics:
                flow.set('flowgraph', flowname, step, str(index), 'goal', metric, 0)
            for metric in weight_metrics:
                flow.set('flowgraph', flowname, step, str(index), 'weight', metric, 1.0)
        prevstep = step

    # add export
    flow.node(flowname, 'export', klayout_export, index=0)
    flow.node(flowname, 'export', openroad_export, index=1)
    flow.edge(flowname, prevstep, 'export', head_index=0)
    flow.edge(flowname, prevstep, 'export', head_index=1)

    return flow


##################################################
if __name__ == "__main__":
    flow = make_docs(siliconcompiler.Chip('<flow>'))
    flow.write_flowgraph(f"{flow.top()}.png", flow=flow.top())
