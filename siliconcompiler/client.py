# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import aiohttp
import asyncio
import subprocess
import time

###################################
def remote_run(chip, stage):
    '''Helper method to run a job stage on a remote compute cluster.
    Note that files will not be copied to the remote stage; typically
    the source files will be copied into the cluster's storage before
    calling this method.
    If the "-remote" parameter was not passed in, this method
    will print a warning and do nothing.

    '''

    #Looking up stage numbers
    stages = (chip.cfg['compile_stages']['value'] +
              chip.cfg['dv_stages']['value'])
    current = stages.index(stage)
    laststage = stages[current-1]
    start = stages.index(chip.cfg['start']['value'][-1]) #scalar
    stop = stages.index(chip.cfg['stop']['value'][-1]) #scalar
    #Check if stage should be explicitly skipped
    skip = stage in chip.cfg['skip']['value']

    if stage not in stages:
        chip.logger.error('Illegal stage name %s', stage)
        return
    elif (current < start) | (current > stop):
        chip.logger.info('Skipping stage: %s', stage)
        return
    else:
        chip.logger.info('Running stage: %s', stage)

    # Ask the remote server to start processing the requested step.
    loop = asyncio.get_event_loop()
    loop.run_until_complete(request_remote_run(chip, stage))

    # Check the job's progress periodically until it finishes.
    is_busy = True
    while is_busy:
      print("%s stage running. Please wait."%stage)
      time.sleep(1)
      is_busy = loop.run_until_complete(is_job_busy(chip, stage))
    print("%s stage completed!"%stage)

###################################
async def request_remote_run(chip, stage):
    '''Helper method to make an async request to start a job stage.

    '''
    async with aiohttp.ClientSession() as session:
        async with session.post("http://%s:%s/remote_run/%s/%s"%(
                                    chip.cfg['remote']['value'][0],
                                    chip.cfg['remoteport']['value'][0],
                                    chip.status['job_hash'],
                                    stage),
                                json=chip.cfg) \
        as resp:
            print(await resp.text())

###################################
async def is_job_busy(chip, stage):
    '''Helper method to make an async request asking the remote server
    whether a job is busy, or ready to accept a new step.
    Returns True if the job is busy, False if not.

    '''

    async with aiohttp.ClientSession() as session:
        async with session.get("http://%s:%s/check_progress/%s/%s"%(
                               chip.cfg['remote']['value'][0],
                               chip.cfg['remoteport']['value'][0],
                               chip.status['job_hash'],
                               stage)) \
        as resp:
            response = await resp.text()
            return (response != "Job has no running steps.")

###################################
def upload_sources_to_cluster(chip):
    '''Helper method to upload Verilog source files to a cloud compute
    cluster's shared storage. Required before the cluster will be able
    to run any job steps.

    TODO: This method will shortly be replaced with a server call.

    '''

    # Rename source files in the config dict; the 'import' step already
    # ran and collected the sources into a single 'verilator.v' file.
    # TODO: This bypasses the 'lock' call, which should probably be avoided.
    # TODO: Use 'jobid' config value, and maybe move this?
    chip.cfg['source']['value'] = ['%s/%s/import/job1/verilator.v'%(chip.cfg['nfsmount']['value'][0], chip.status['job_hash'])]

    # Ensure that the destination directory exists.
    subprocess.run(['ssh',
                    '-i',
                    chip.cfg['nfskey']['value'][0],
                    '%s@%s'%(chip.cfg['nfsuser']['value'][0], chip.cfg['nfshost']['value'][0]),
                    'mkdir',
                    '%s/%s'%(chip.cfg['nfsmount']['value'][0], chip.status['job_hash'])])

    # Copy Verilog sources using scp.
    subprocess.run(['scp',
                    '-i',
                    chip.cfg['nfskey']['value'][0],
                    '-rp',
                    '%s/import'%chip.cfg['build']['value'][0],
                    '%s@%s:%s/%s'%(
                        chip.cfg['nfsuser']['value'][0],
                        chip.cfg['nfshost']['value'][0],
                        chip.cfg['nfsmount']['value'][0],
                        chip.status['job_hash']
                    )])

    # TODO: Also upload .lib, .lef, etc files.
