# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

#Standard Modules
import sys
import logging
import argparse
import os
import re
import json
import sys
import importlib.resources

#Shorten siliconcompiler as sc
import siliconcompiler as sc
from siliconcompiler.schema import schema
from siliconcompiler.foundry.nangate45 import nangate45_pdk
from siliconcompiler.foundry.nangate45 import nangate45_lib
from siliconcompiler.eda.verilator import setup_verilator
from siliconcompiler.eda.yosys import setup_yosys
from siliconcompiler.eda.openroad import setup_openroad
from siliconcompiler.eda.klayout import setup_klayout

###########################
def cmdline():
    '''Handles the command line configuration usign argparse. 
    All configuration parameters are exposed at the command line interface.
    This is outside of the class since this can be called 

    '''
    def_cfg = schema()

    os.environ["COLUMNS"] = '100'

    # Argument Parser
    
    parser = argparse.ArgumentParser(prog='sc',
                                     formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=50),
                                     prefix_chars='-+',
                                     description="Silicon Compiler Collection (SC)")

    # Required positional source file argument
    parser.add_argument('source',
                        nargs='+',
                        help=def_cfg['source']['help'])

    #Recursive argument adder
    add_arg(def_cfg, parser)
    
    #Parsing args and converting to dict
    cmdargs = vars(parser.parse_args())

    # Copying flat parse_args to nested cfg dict based on key type
    # Values are lists of varying legnth based on cfg parameter
    # stdlib, macro, tool has length 3 or 4 depending on type
    # (timing, cells, power has length 4)
    # Format is "key(s) val"

    #scalars, list, lists of lists need to be treated
    #destination is the nested cfg dictionary

    cfg= {}
    
    for key,all_vals in cmdargs.items():
       
        switch = key.split('_')
        param = switch[0]
        if len(switch) > 1 :
            param = param + "_" + switch[1]            

        if param not in cfg:
            cfg[param] = {}

        #Iterate over list since these are dynamic
        if switch[0] in ('stdcell', 'macro', 'tool'):
            for val in all_vals:
                if val[0] not in cfg[param]:
                        cfg[param][val[0]]={}
                if switch[1] not in cfg[param][val[0]].keys():
                        cfg[param][val[0]][switch[1]] = {}
                if switch[1] in ('timing', 'power', 'cells'):
                    if val[1] not in cfg[param][val[0]][switch[1]].keys():
                        cfg[param][val[0]][switch[1]][val[1]]={}
                        cfg[param][val[0]][switch[1]][val[1]]['value'] = val[2]
                    else:
                        cfg[param][val[0]][switch[1]][val[1]]['value'].extend(val[2])
                else:
                    if 'value' not in cfg[param][val[0]][switch[1]].keys():
                        cfg[param][val[0]][switch[1]]['value'] = val[1]
                    else:
                        cfg[param][val[0]][switch[1]]['value'].extend(val[1])
        else:
            if 'value' not in cfg:
                 cfg[param] = {}
                 cfg[param]['value'] = all_vals

            else:
                cfg[param]['value'].extend(all_vals)
        
    return cfg

###########################
def add_arg(cfg, parser, keys=None):
    ''' Recursively add command line arguments from cfg dictionary
    '''
    if keys is None:
        keys = []
    for k,v in sorted(cfg.items()):
        #print(k,v)
        #No command line switches for these odd balls
        if k in ('source', 'stages'):
            pass
        #Optimizing command line switches for these
        elif k in ('tool'):
            for k2 in cfg['tool']['syn'].keys():
                parser.add_argument(cfg[k]['syn'][k2]['switch'],
                                    dest=k+"_"+k2,
                                    metavar=cfg[k]['syn'][k2]['switch_args'],
                                    action='append',
                                    help=cfg[k]['syn'][k2]['help'],
                                    default = argparse.SUPPRESS)
        #All others
        else:            
            newkeys =  keys.copy()
            newkeys.append(str(k))            
            if 'defvalue' in cfg[k].keys():                
                keystr = '_'.join(newkeys)
                if cfg[k]['type'][-1] == 'bool': #scalar
                    parser.add_argument(cfg[k]['switch'],
                                        metavar=cfg[k]['switch_args'],
                                        dest=keystr,
                                        action='store_const',
                                        const=['True'],
                                        help=cfg[k]['help'],
                                        default = argparse.SUPPRESS)
                else:
                    parser.add_argument(cfg[k]['switch'],
                                        metavar=cfg[k]['switch_args'],
                                        dest=keystr,
                                        action='append',
                                        help=cfg[k]['help'],
                                        default = argparse.SUPPRESS)
            else:
                newkeys.append(str(k))
                add_arg(cfg[k], parser, keys=newkeys) 

###########################
def main():

    scriptdir = os.path.dirname(os.path.abspath(__file__))
    root = re.sub('siliconcompiler/siliconcompiler','siliconcompiler', scriptdir)
    
    #Command line inputs, read once
    cmdlinecfg = cmdline()
    
    if 'debug' in  cmdlinecfg.keys():
        loglevel = cmdlinecfg['debug']['value'][-1]
    else:
        loglevel = "DEBUG"
        
    #Create one (or many...) instances of Chip class
    mychip = sc.Chip(loglevel=loglevel)

    # Reading in user variables
    mychip.readenv()

    # Loading presetvalues from the command line
    if 'target' in  cmdlinecfg.keys():
        target = cmdlinecfg['target']['value'][-1]
        if target in ('nangate45', 'asap7'):
            setup_verilator(mychip, root+'/eda/asic')
            setup_yosys(mychip, root+'/eda/asic')
            setup_openroad(mychip, root+'/eda/asic')
            setup_klayout(mychip, root+'/eda/asic')            
            if target == 'nangate45': 
                nangate45_pdk(mychip, root+'/foundry/')
                nangate45_lib(mychip, root+'/foundry/')
            elif target == 'asap7':
                asap7_pdk(mychip, root+'/foundry/')
                asap7_lib(mychip, root+'/foundry/')
    
    # Reading in config files specified at command line
    if 'cfgfile' in  cmdlinecfg.keys():        
        for cfgfile in cmdlinecfg['cfgfile']['value']:
            chip.readcfg(cfgfile)
        
    # Override with command line arguments
    mychip.mergecfg(cmdlinecfg)
        
    #Resolve as absolute paths (should be a switch)
    mychip.abspath()

    #Checks settings and fills in missing values
    #mychip.check()

    #Creating hashes for all sourced files
    #mychip.hash()

    #Lock chip configuration
    mychip.lock()
    
    #Printing out run-config
    mychip.writecfg("sc_setup.json")

    all_stages = mychip.get('stages')
    for stage in all_stages:
        mychip.run(stage)
    
#########################
if __name__ == "__main__":    
    sys.exit(main())
