from typing import Optional
import os
import subprocess
from django.conf import settings
from celery import shared_task
from .models import Chain, CryoLogsMetadata
from web3 import Web3
import pandas as pd


def cryo_ingest_logs(
    contract_address: str,
    rpc: str,
    event_signature: str,
    label: str,
    start_block: int,
    end_block: Optional[int] = None,
    reorg_buffer: int = 1000,
    subdirs: str = "datatype"
):
    if os.path.exists(settings.MEDIA_ROOT):
        os.chdir(settings.MEDIA_ROOT)
        start_block_str = f"{int(start_block)/1e6}M"
        if end_block is None:
            end_block_str = ""
        else:
            end_block_str = f"{int(end_block)/1e6}M"
        block_str = f"{start_block_str}:{end_block_str}"
        print(f"{block_str=}")
        command = [
            '/code/bin/cryo', 'logs',
            '--label', label,
            '--blocks', block_str,
            '--reorg-buffer', str(reorg_buffer),
            '--rpc', str(rpc),
            '--subdirs', str(subdirs),
            '--contract', str(contract_address),
            '--event-signature', event_signature
        ]
        subprocess.run(command)
    else:
        raise Exception("Media directory doesn't exist")

@shared_task(name="task_cryo_logs")
def task_cryo_logs(
    contract_address: str,
    # rpc: str,
    chain_id: int,
    event_signature: str,
    label: str,
    start_block: int,
    end_block: Optional[int] = None,
    reorg_buffer: int = 1000,
    subdirs: str = "datatype"   
):  
    try: 
        chain = Chain.objects.get(chain_id=chain_id)
    except:
        raise Exception(f"Chain id {chain_id} not found")

    cryo_ingest_logs(
        contract_address,
        chain.rpc,
        event_signature,
        label,
        start_block,
        end_block,
        reorg_buffer,
        subdirs
    )

    try:
        metadata = CryoLogsMetadata.objects.get(label=label)
    except CryoLogsMetadata.DoesNotExist:
        metadata = CryoLogsMetadata(
            label=label,
            chain=chain
        )
        metadata.save()

    os.chdir(os.path.join(settings.MEDIA_ROOT, f"logs__{label}"))
    metadata.save()

@shared_task(name="task_web3py_logs")
def task_web3py_logs(
        contract_address,
        event_signature,
        label,
        start_block,
        chain_id: int,
        end_block=None,
        block_range=1000,
        **kwargs
    ):
    MEDIA_ROOT = settings.MEDIA_ROOT
    try: 
        chain = Chain.objects.get(chain_id=chain_id)
    except:
        raise Exception(f"Chain id {chain_id} not found")
    CHAIN_NAME = chain.chain_name.lower()
    RPC_URL = chain.rpc
    def connect_to_blockchain(rpc_url):
        """ Connect to the Ethereum blockchain using a given RPC URL. """
        return Web3(Web3.HTTPProvider(rpc_url))

    def get_latest_block(w3):
        """ Get the latest block number from the blockchain. """
        return w3.eth.block_number

    def parse_event_signature(signature):
        """ Parse the event signature to generate an ABI entry. """
        event_name = signature[:signature.find('(')]
        types = signature[signature.find('(') + 1:-1].split(',')
        inputs = [{'type': t.strip().split(" ")[0], 'name': t.strip().split(" ")[-1], 'indexed': 'indexed' in t.strip()} for t in types]
        abi = {
            'anonymous': False,
            'inputs': inputs,
            'name': event_name,
            'type': 'event'
        }
        print(f"{[abi]=}")
        return [abi]

    def adjust_column_names(event):
        """ Adjust the column names to include 'event__' prefix and '_string' suffix for integers. """
        data = event['args']
        adjusted_data = {}
        for key, value in data.items():
            new_key = f"event__{key}"
            if isinstance(value, int):
                adjusted_data[new_key + '_string'] = str(value)
            else:
                adjusted_data[new_key] = value
        adjusted_data["transaction_hash"] = event["transactionHash"]
        adjusted_data["log_index"] = event["logIndex"]
        adjusted_data["transaction_index"] = event["transactionIndex"]
        adjusted_data["block_number"] = event["blockNumber"]
        return adjusted_data

    def get_existing_blocks(label):
        """ Retrieve existing block numbers from stored .parquet files. """
        directory = os.path.join(MEDIA_ROOT, f"logs__{label}")
        if not os.path.exists(directory):
            os.makedirs(directory)
        existing_files = os.listdir(directory)
        existing_blocks = set()
        for file_name in existing_files:
            # parts = file_name.replace('.parquet', '').split('-')
            # if len(parts) == 3:
                # existing_blocks.update(range(int(parts[1]), int(parts[2]) + 1))
            parts = file_name.replace('.parquet', "").split("__")[-1].split("_to_")
            if len(parts) == 2:
                existing_blocks.update(range(int(parts[0]), int(parts[1]) + 1))
                
        return existing_blocks

    def fetch_block_data(w3, contract_address, start_block, end_block, event_signature):
        """ Fetch blockchain data based on contract address, block range, and event signature. """
        abi = parse_event_signature(event_signature)
        contract = w3.eth.contract(address=contract_address, abi=abi)
        event_name = abi[0]['name']
        events = getattr(contract.events, event_name)().get_logs(fromBlock=start_block, toBlock=end_block)
        print(events)
        data = [adjust_column_names(event) for event in events]
        return pd.DataFrame(data)

    def write_data_to_parquet(data, label, start_block, end_block):
        """ Write fetched data to a .parquet file following a specified naming convention. """
        directory = os.path.join(MEDIA_ROOT, f"logs__{label}")
        # file_path = os.path.join(directory, f"{CHAIN_NAME}__logs__{label}-{start_block}-{end_block}.parquet")
        file_path = os.path.join(directory, f"{CHAIN_NAME}__logs__{label}__{start_block}_to_{end_block}.parquet")
        data.to_parquet(file_path)
        print(f"Data for blocks {start_block} to {end_block} saved to {file_path}")

    """ Main function to handle fetching and storing blockchain data. """
    w3 = connect_to_blockchain(RPC_URL)
    if end_block is None:
        end_block = get_latest_block(w3)
    
    existing_blocks = get_existing_blocks(label)
    needed_blocks = set(range(start_block, end_block + 1)) - existing_blocks

    current_block = start_block
    while current_block <= end_block:
        next_block = min(current_block + block_range - 1, end_block)
        if set(range(current_block, next_block + 1)).intersection(existing_blocks):
            print(f"Skipping blocks {current_block} to {next_block} as they already exist.")
            current_block = next_block + 1
            continue
        
        data = fetch_block_data(w3, contract_address, current_block, next_block, event_signature)
        # if not data.empty:
        write_data_to_parquet(data, label, current_block, next_block)
        
        current_block = next_block + 1
    
    try:
        metadata = CryoLogsMetadata.objects.get(label=label)
    except CryoLogsMetadata.DoesNotExist:
        metadata = CryoLogsMetadata(
            label=label,
            chain=chain
        )
        metadata.save()

    os.chdir(os.path.join(settings.MEDIA_ROOT, f"logs__{label}"))
    metadata.save()

