import os
import shutil
import psutil
import sys
import xml.etree.ElementTree as ET
import re

PACKAGE_ROOT = os.path.dirname(os.path.abspath(__file__))

def copytree(src, dst, ignore=[], dirs_exist_ok=False, link=False):
    '''Simple implementation of shutil.copytree to give us a dirs_exist_ok
    option in Python < 3.8.

    If link is True, create hard links in dst pointing to files in src
    instead of copying them.
    '''
    os.makedirs(dst, exist_ok=dirs_exist_ok)

    for name in os.listdir(src):
        if name in ignore:
            continue

        srcfile = os.path.join(src, name)
        dstfile = os.path.join(dst, name)

        if os.path.isdir(srcfile):
            copytree(srcfile, dstfile, ignore=ignore, dirs_exist_ok=dirs_exist_ok)
        elif link:
            os.link(srcfile, dstfile)
        else:
            shutil.copy2(srcfile, dstfile)

def trim(docstring):
    '''Helper function for cleaning up indentation of docstring.

    This is important for properly parsing complex RST in our docs.

    Source:
    https://www.python.org/dev/peps/pep-0257/#handling-docstring-indentation'''
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxsize
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxsize:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)

def terminate_process(pid, timeout=3):
    '''Terminates a process and all its (grand+)children.

    Based on https://psutil.readthedocs.io/en/latest/#psutil.wait_procs and
    https://psutil.readthedocs.io/en/latest/#kill-process-tree.
    '''
    assert pid != os.getpid(), "won't terminate myself"
    parent = psutil.Process(pid)
    children = parent.children(recursive=True)
    children.append(parent)
    for p in children:
        try:
            p.terminate()
        except psutil.NoSuchProcess:
            # Process may have terminated on its own in the meantime
            pass

    _, alive = psutil.wait_procs(children, timeout=timeout)
    for p in alive:
        # If processes are still alive after timeout seconds, send more
        # aggressive signal.
        p.kill()

def escape_val_tcl(val, typestr):
    '''Recursive helper function for converting Python values to safe TCL
    values, based on the SC type string.'''
    if val is None:
        return ''
    elif typestr.startswith('('):
        # Recurse into each item of tuple
        subtypes = typestr.strip('()').split(',')
        valstr = ' '.join(escape_val_tcl(v, subtype.strip())
                          for v, subtype in zip(val, subtypes))
        return f'[list {valstr}]'
    elif typestr.startswith('['):
        # Recurse into each item of list
        subtype = typestr.strip('[]')
        valstr = ' '.join(escape_val_tcl(v, subtype) for v in val)
        return f'[list {valstr}]'
    elif typestr == 'bool':
        return 'true' if val else 'false'
    elif typestr == 'str':
        # Escape string by surrounding it with "" and escaping the few
        # special characters that still get considered inside "". We don't
        # use {}, since this requires adding permanent backslashes to any
        # curly braces inside the string.
        # Source: https://www.tcl.tk/man/tcl8.4/TclCmd/Tcl.html (section [4] on)
        escaped_val = (val.replace('\\', '\\\\') # escape '\' to avoid backslash substition (do this first, since other replaces insert '\')
                            .replace('[', '\\[')   # escape '[' to avoid command substition
                            .replace('$', '\\$')   # escape '$' to avoid variable substition
                            .replace('"', '\\"'))  # escape '"' to avoid string terminating early
        return '"' + escaped_val + '"'
    elif typestr in ('file', 'dir'):
        # Replace $VAR with $env(VAR) for tcl
        val = re.sub(r'\$(\w+)', r'$env(\1)', val)
        # Same escapes as applied to string, minus $ (since we want to resolve env vars).
        escaped_val = (val.replace('\\', '\\\\') # escape '\' to avoid backslash substition (do this first, since other replaces insert '\')
                            .replace('[', '\\[')   # escape '[' to avoid command substition
                            .replace('"', '\\"'))  # escape '"' to avoid string terminating early
        return '"' +  escaped_val + '"'
    else:
        # floats/ints just become strings
        return str(val)

# This class holds all the information about a single primitive defined in the FPGA arch file
class PbPrimitive:

    def __init__ (self, name, blif_model):
        self.name = name
        self.blif_model = blif_model
        self.ports = []

    def add_port(self, port):

        port_type = port.tag # can be input | output | clock
        port_name = port.attrib['name']
        num_pins = port.attrib['num_pins']
        port_class = port.attrib.get('port_class')

        new_port = { 'port_type': port_type,
                     'port_name': port_name,
                     'num_pins': num_pins,
                     'port_class': port_class }

        self.ports.append(new_port)

    def find_port(self, port_name):

        for port in self.ports:
            if re.match(port_name, port['port_name']):
                return port
        return None

 # This class parses the FPGA architecture file and stores all the information provided for every primitive
class Arch:

    def __init__(self, arch_file_name):
        self.arch_file = ET.parse(arch_file_name)
        self.complexblocklist = self.arch_file.find("complexblocklist") # finding the tag that contains all the pb_types
        self.pb_primitives = []
        self.find_pb_primitives(self.complexblocklist) # only the primitives (pb_types that have the blif_model attribute) will be stored

    # Find the pb_types that possess the 'blif_model' attribute and add them to the pb_primitives list
    def find_pb_primitives(self, root):
        for pb_type in root.iter('pb_type'):
            if "blif_model" in pb_type.attrib:
                self.add_pb_primitive(pb_type)

    # Parses the given primitive tag and stores the extracted info
    def add_pb_primitive(self, pb_type):
        new_pb = PbPrimitive(pb_type.tag, pb_type.attrib["blif_model"])
        for port in pb_type.iter():
            if port.tag in ['input', 'output', 'clock']:
                new_pb.add_port(port)
        self.pb_primitives.append(new_pb)

    # Finds all the lut primitives to return the size of the largest lut
    def find_max_lut_size(self):
        max_lut_size = 0
        for pb_type in self.pb_primitives:
            if pb_type.blif_model == ".names":
                in_port = pb_type.find_port("in")
                lut_size = in_port["num_pins"]
                max_lut_size = max(max_lut_size, int(lut_size))

        return max_lut_size

    # Finds all the memory primitives to return the maximum address length
    def find_memory_addr_width(self):
        max_add_size = 0
        for pb_type in self.pb_primitives:
            if "port_ram" in pb_type.blif_model:
                add_port = pb_type.find_port("^addr")
                add_size = add_port["num_pins"]
                max_add_size = max(max_add_size, int(add_size))

        return max_add_size

def get_file_ext(filename):
    '''Get base file extension for a given path, disregarding .gz.'''
    if filename.endswith('.gz'):
        filename = os.path.splitext(filename)[0]
    filetype = os.path.splitext(filename)[1].lower().lstrip('.')
    return filetype

def get_default_iomap():
    """
    Default input file map for SC with filesets and extensions
    """

    # Record extensions:

    # High level languages
    hll_c = ('c', 'cc', 'cpp', 'c++', 'cp', 'cxx', 'hpp')
    hll_bsv = ('bsv',)
    hll_scala = ('scala',)
    hll_python = ('py',)

    # Register transfer languages
    rtl_verilog = ('v', 'vg', 'sv', 'verilog')
    rtl_vhdl = ('vhd', 'vhdl')

    # Timing libraries
    timing_liberty = ('lib', 'ccs')

    # Layout
    layout_def = ('def',)
    layout_lef = ('lef',)
    layout_gds = ('gds', 'gds2', 'gdsii')
    layout_oas = ('oas', 'oasis')
    layout_gerber = ('gbr', 'gerber')
    layout_odb = ('odb',)

    # Netlist
    netlist_cdl = ('cdl',)
    netlist_sp = ('sp', 'spice')

    # Waveform
    waveform_vcd = ('vcd',)

    # Constraint
    constraint_sdc = ('sdc', )

    # FPGA constraints
    fpga_xdc = ('xdc',)
    fpga_pcf = ('pcf',)

    # Build default map with fileset and type
    default_iomap = {}
    default_iomap.update({ext: ('hll', 'c') for ext in hll_c})
    default_iomap.update({ext: ('hll', 'bvs') for ext in hll_bsv})
    default_iomap.update({ext: ('hll', 'scala') for ext in hll_scala})
    default_iomap.update({ext: ('hll', 'python') for ext in hll_python})

    default_iomap.update({ext: ('rtl', 'verilog') for ext in rtl_verilog})
    default_iomap.update({ext: ('rtl', 'vhdl') for ext in rtl_vhdl})

    default_iomap.update({ext: ('timing', 'liberty') for ext in timing_liberty})

    default_iomap.update({ext: ('layout', 'def') for ext in layout_def})
    default_iomap.update({ext: ('layout', 'lef') for ext in layout_lef})
    default_iomap.update({ext: ('layout', 'gds') for ext in layout_gds})
    default_iomap.update({ext: ('layout', 'oas') for ext in layout_oas})
    default_iomap.update({ext: ('layout', 'gerber') for ext in layout_gerber})
    default_iomap.update({ext: ('layout', 'odb') for ext in layout_odb})

    default_iomap.update({ext: ('netlist', 'cdl') for ext in netlist_cdl})
    default_iomap.update({ext: ('netlist', 'sp') for ext in netlist_sp})

    default_iomap.update({ext: ('waveform', 'vcd') for ext in waveform_vcd})

    default_iomap.update({ext: ('constraint', 'sdc') for ext in constraint_sdc})

    default_iomap.update({ext: ('fpga', 'xdc') for ext in fpga_xdc})
    default_iomap.update({ext: ('fpga', 'pcf') for ext in fpga_pcf})

    return default_iomap


def format_fileset_type_table(indent=12):
    '''
    Generate a table to use in the __doc__ of the input function which auto
    updates based on the iomap
    '''
    table  = "filetype  | fileset    | suffix (case insensitive)\n"
    indent = " " * indent
    table += f"{indent}----------|------------|---------------------------------------------\n"

    iobytype = {}
    for ext, settype in get_default_iomap().items():
        fileset, filetype = settype
        iobytype.setdefault((fileset, filetype), []).append(ext)

    for settype, exts in iobytype.items():
        fileset, filetype = settype
        ext = ",".join(exts)
        table += f"{indent}{filetype:<10}| {fileset:<11}| {ext}\n"

    return table
