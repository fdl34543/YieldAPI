from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from web3 import Web3
from datetime import datetime
import requests
import json
from typing import NamedTuple
from dotenv import load_dotenv
import os
# from sqlalchemy.orm import Session
# from db import SessionLocal, FundDeployment
# from typing import List
import time

app = FastAPI()

load_dotenv()

# Allow frontend to access the API (change origin for prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

VALID_API_KEY = "39a4f6be5b3a4d08ddaf45944cd8ce42"

# Config
SEPOLIA_RPC = "https://sepolia.infura.io/v3/2ba3d93485814c04b0106479c8e9973d"
ETHERSCAN_API_KEY = "15W7XAPWQMGR8I34AB5KK7XQAEIAS9PEGZ"
web3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC))
DECIMALS = 1e6  # Adjust if vault uses 1e18
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

controller_address = web3.to_checksum_address("0xcC0bdAb358f42EB86e09B6afD1109F3e59d0ab9B")
CABI_ENDPOINT = f'https://api-sepolia.etherscan.io/api?module=contract&action=getabi&address=0xBD7189cD389f3CfDa49F5c6F72C1508a198EA8a6&apikey={ETHERSCAN_API_KEY}'
controller_abi = json.loads(requests.get(CABI_ENDPOINT).json()['result'])
controller = web3.eth.contract(address=controller_address, abi=controller_abi)

usdc_address = web3.to_checksum_address("0xcBa412b6123A6f94348F25fAC5f4CD6c132D83D9")
usdcABI_ENDPOINT = f'https://api-sepolia.etherscan.io/api?module=contract&action=getabi&address={usdc_address}&apikey={ETHERSCAN_API_KEY}'
usdc_abi = json.loads(requests.get(usdcABI_ENDPOINT).json()['result'])
usdc = web3.eth.contract(address=usdc_address, abi=usdc_abi)

vlt_address = web3.to_checksum_address("0x31cc89CFC8F4fa96816dc006134d655169e68388")
vltABI_ENDPOINT = f'https://api-sepolia.etherscan.io/api?module=contract&action=getabi&address={vlt_address}&apikey={ETHERSCAN_API_KEY}'
time.sleep(1)
vlt_abi = json.loads(requests.get(vltABI_ENDPOINT).json()['result'])
vlt = web3.eth.contract(address=vlt_address, abi=vlt_abi)

account = web3.eth.account.from_key(PRIVATE_KEY)

url = 'https://api.etherscan.io/api?module=gastracker&action=gasoracle&apikey=15W7XAPWQMGR8I34AB5KK7XQAEIAS9PEGZ'
response = requests.get(url).text
datagwei = json.loads(response)
gweinow = datagwei["result"]["SafeGasPrice"]
gwein = float(gweinow) + 5

# Dependency to get DB session
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

def verify_api_key(api_key: str):
    if api_key != VALID_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

# Yield Metrics
@app.get("/yield/metrics")
def yield_metrics():
    url = "https://yields.llama.fi/pools"
    response = requests.get(url)
    data = response.json()

    protocols = ["aave-v3", "compound-v3"]
    adapter = {
        "aave-v3": "0xa9BE08b7078EAFB2a42866bD273BC7454251663E",
        "compound-v3": "0xFc11541A0A36747Bf278287fc67F6BbBeFd6E981"
    }

    best_pool = None
    best_apy = 0.0
    all_apys = []

    for pool in data.get("data", []):
        project = pool.get("project", "").lower()
        symbol = pool.get("symbol", "").upper()
        chain = pool.get("chain", "")
        apy = pool.get("apy", 0.0)

        if project in protocols and symbol == "USDC" and chain == "Ethereum":
            if apy > best_apy:
                best_apy = apy
                best_pool = pool

    for pool in data.get("data", []):
        project = pool.get("project", "").lower()
        symbol = pool.get("symbol", "").upper()
        chain = pool.get("chain", "")
        apy = pool.get("apy", 0.0)

        if project in protocols and symbol == "USDC" and chain == "Ethereum":
            all_apys.append({
                "protocol": pool.get("project"),
                "apy": apy,
                "24h_avg_apy": pool.get("apyPct1D", 0),
                "7d_avg_apy": pool.get("apyPct7D", 0),
                "performance_vs_best": round((apy / best_apy) * 100, 2) if best_apy else 0.0
            })

    best_protocol = best_pool["project"].lower() if best_pool else None

    return {
        "best_protocol": best_protocol,
        "apy": best_apy,
        "adapter": adapter.get(best_protocol),
        "chain": best_pool["chain"] if best_pool else None,
        "all_apys": all_apys
    }

# Vault Stats
@app.get("/vault/stats")
def vault_stats():
    adapter = getBestStrategy()["Adapter"]
    return get_vault_stats(adapter)

@app.get("/vault/feeAnalytics")
def fee_analytics():
    return getFeeAnalytics()

# Fee + Performance History
@app.get("/vault/performance")
def vault_performance():
    adapter = getBestStrategy()["Adapter"]
    return performanceHistory(adapter)

# Best Strategies
@app.get("/strategies/best")
def best_strategies():
    return getBestStrategy()

# All Strategies
@app.get("/strategies/all")
def all_strategies():
    return getAllStrategies()

# Funds Idle
@app.get("/funds/idle")
def funds_idle():
    return getFundIdle()

# Funds Deployment History
# @app.get("/funds/history")
# def funds_deploy():
#     return fundDeploymentHistory()

# Monitor All Strategies
@app.get("/monitor/all-strategies")
def monitor_strategies():
    return getAllStrategies()

# Monitor All Strategies
@app.get("/monitor/all-apy")
def monitor_apy():
    return allAPY()

# Monitor total assets under management
@app.get("/monitor/total-assets")
def monitor_allAssets():
    return allAssets()

#========= CONTROL =========

@app.get("/funds/deploy")
def funds_deploy(api_key: str):
    verify_api_key(api_key)
    return fundDeployment()

# Rebalancing
@app.get("/rebalancing")
def execute_rebalancing(api_key: str):
    verify_api_key(api_key)
    return Rebalancing()

# Emergency Withdraw
@app.get("/emergency-withdraw")
def emergency_withdraw(api_key: str):
    verify_api_key(api_key)
    return emergencyWithdraw()

# Pause Agent
@app.get("/pause")
def pause_agent(api_key: str):
    verify_api_key(api_key)
    return pauseAgent()

# Unpause Agent
@app.get("/unpause")
def unpause_agent(api_key: str):
    verify_api_key(api_key)
    return unpauseAgent()

#========= POST =========

# Register Strategies
class StrategyInput(BaseModel):
    name: str
    address: str

@app.post("/strategies/add")
async def add_strategy(data: StrategyInput):
    try:
        result = register_strategy(data.name, data.address)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# --- Core logic from your script below ---

def get_best_yield_usdc():
    url = "https://yields.llama.fi/pools"
    response = requests.get(url)
    data = response.json()

    protocols = ["aave-v3", "compound-v3"]
    adapter = {
        "aave-v3": "0x33a52745b360C3031Fd6B767F1097e31B1B7C367",
        "compound-v3": "0x82B3771C56c6E24251Ba9E68B5DE5B2059FC5bd4"
    }

    best_pool = None
    best_apy = 0.0
    all_apys = []

    for pool in data.get("data", []):
        project = pool.get("project", "").lower()
        symbol = pool.get("symbol", "").upper()
        chain = pool.get("chain", "")
        apy = pool.get("apy", 0.0)

        if project in protocols and symbol == "USDC" and chain == "Ethereum":
            if apy > best_apy:
                best_apy = apy
                best_pool = pool

    for pool in data.get("data", []):
        project = pool.get("project", "").lower()
        symbol = pool.get("symbol", "").upper()
        chain = pool.get("chain", "")
        apy = pool.get("apy", 0.0)

        if project in protocols and symbol == "USDC" and chain == "Ethereum":
            all_apys.append({
                "protocol": pool.get("project"),
                "apy": apy,
                "24h_avg_apy": pool.get("apyPct1D", 0),
                "7d_avg_apy": pool.get("apyPct7D", 0),
                "performance_vs_best": round((apy / best_apy) * 100, 2) if best_apy else 0.0
            })

    best_protocol = best_pool["project"].lower() if best_pool else None

    return {
        "best_protocol": best_protocol,
        "apy": best_apy,
        "adapter": adapter.get(best_protocol),
        "chain": best_pool["chain"] if best_pool else None,
        "all_apys": all_apys
    }

def get_vault_stats(bestAdapter):
    vault_address = web3.to_checksum_address(bestAdapter)
    # ABI_ENDPOINT = f'https://api-sepolia.etherscan.io/api?module=contract&action=getabi&address={vault_address}&apikey={ETHERSCAN_API_KEY}'
    # vault_abi = json.loads(requests.get(ABI_ENDPOINT).json()['result'])

    with open("controllerABI.json", "r") as f:
        vault_abi = json.load(f)

    vault = web3.eth.contract(address=vault_address, abi=vault_abi)

    #total_assets = vault.functions.getTotalDeposits().call()
    total_shares = vault.functions.getTotalShares().call()
    share_price = vault.functions.sharePrice().call()

    total_assets = (total_shares / DECIMALS) * (share_price/ 10e17)

    # deposit_topic = web3.keccak(text="Deposit(address,address,uint256,uint256)").hex()
    # withdraw_topic = web3.keccak(text="Withdraw(address,address,uint256,uint256)").hex()

    # latest_block = web3.eth.block_number
    # latest_time = web3.eth.get_block(latest_block)["timestamp"]
    # start_time = latest_time - 86400

    # from_block = max(latest_block - 20000, 0)

    # def get_logs(topic):
    #     return web3.eth.get_logs({
    #         "fromBlock": from_block,
    #         "toBlock": latest_block,
    #         "address": vault_address,
    #         "topics": [topic]
    #     })

    # deposit_logs = get_logs(deposit_topic)
    # withdraw_logs = get_logs(withdraw_topic)

    # depositors = set()
    # total_deposit = 0
    # total_withdraw = 0

    # for log in deposit_logs:
    #     block_time = web3.eth.get_block(log["blockNumber"])["timestamp"]
    #     if block_time >= start_time:
    #         depositor = "0x" + log["topics"][2].hex()[-40:]
    #         depositors.add(depositor)
    #         amount = int(log["data"][2:66], 16)
    #         total_deposit += amount

    # for log in withdraw_logs:
    #     block_time = web3.eth.get_block(log["blockNumber"])["timestamp"]
    #     if block_time >= start_time:
    #         amount = int(log["data"][2:66], 16)
    #         total_withdraw += amount

    # net_flow = total_deposit - total_withdraw

    return {
        "total_assets": round(total_assets, 2),
        "total_shares": round(total_shares / DECIMALS, 2),
        "share_price": round(share_price / 1e18, 6),
        "unique_depositors": 0,
        "24h_deposits": 0,
        "24h_withdrawals": 0,
        "net_flow_24h": 0
    }

def performanceHistory(bestAdapter):
    vault_address = web3.to_checksum_address(bestAdapter)
    # ABI_ENDPOINT = f'https://api-sepolia.etherscan.io/api?module=contract&action=getabi&address={vault_address}&apikey={ETHERSCAN_API_KEY}'
    # vault_abi = json.loads(requests.get(ABI_ENDPOINT).json()['result'])

    with open("controllerABI.json", "r") as f:
        vault_abi = json.load(f)
    vault = web3.eth.contract(address=vault_address, abi=vault_abi)

    rebalance = controller.functions.rebalanceThreshold().call()
    rebalance_event = web3.keccak(text="Rebalanced(address,uint256)").hex()
    harvest_event = web3.keccak(text="YieldHarvested(uint256,uint256)").hex()

    # logs = web3.eth.get_logs({
    #     "fromBlock": 0,
    #     "toBlock": "latest",
    #     "address": vault_address,
    #     "topics": [None]
    # })

    # performance_by_day = {}
    # cumulative_yield = 0
    # cumulative_gas = 0

    # for log in logs:
    #     block = web3.eth.get_block(log['blockNumber'])
    #     date = datetime.utcfromtimestamp(block['timestamp']).strftime("%Y-%m-%d")

    #     if log['topics'][0].hex() == rebalance_event:
    #         performance_by_day.setdefault(date, {"rebalances": 0})
    #         performance_by_day[date]["rebalances"] += 1

    #     elif log['topics'][0].hex() == harvest_event:
    #         data = web3.codec.decode(["uint256", "uint256"], log["data"])
    #         yield_amt, gas_amt = data
    #         cumulative_yield += yield_amt
    #         cumulative_gas += gas_amt

    total_shares = vault.functions.getTotalShares().call()
    share_price = vault.functions.sharePrice().call()

    total_assets = (total_shares / DECIMALS) * (share_price/ 10e17)

    return {
        "performance_history": [{
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "apy": round(vault.functions.getCurrentAPY().call() / 100, 2),
            "total_assets": round(total_assets, 2),
            "rebalances": round(rebalance / 100)
        }],
        "cumulative_yield_generated": 0,
        "cumulative_gas_costs": 0,
        "net_yield": 0
    }

def getFeeAnalytics():

    fees = vlt.functions.getFeeAnalytics().call()

    return {
        "accrued_fees": fees[0] / 1e6,
        "fees_collected_24h": fees[1] / 1e6,
        "fees_collected_total": fees[2] / 1e6
    }

class Strategy(NamedTuple):
    name: str
    address: str

def getBestStrategy():
    allStrategies = controller.functions.getAllStrategies().call()
    #print(allStrategies)

    strategy_objs = [
        Strategy(name, address)
        for name, address in zip(allStrategies[0], allStrategies[1])
    ]

    bestStrategy = []

    # Example usage:
    for strategy in strategy_objs:
        try:
            #print(strategy.name, strategy.address)
            stra_address = web3.to_checksum_address(strategy.address)
            straABI_ENDPOINT = f'https://api-sepolia.etherscan.io/api?module=contract&action=getabi&address={stra_address}&apikey={ETHERSCAN_API_KEY}'
            stra_abi = json.loads(requests.get(straABI_ENDPOINT).json()['result'])
            stra = web3.eth.contract(address=stra_address, abi=stra_abi)

            apy = stra.functions.getCurrentAPY().call()

            bestStrategy.append({
                "name": strategy.name,
                "address": strategy.address,
                "apy": apy / 10**2
            })
        except:
            pass
    
    best = max(bestStrategy, key=lambda s: s['apy'])
    #print(f"✅ Best Strategy: {best['name']} ({best['address']}) with APY: {best['apy']}")

    return {
        "name": best['name'],
        "Adapter": best['address'],
        "APY": best['apy']
    }

def getAllStrategies():
    allStrategies = controller.functions.getAllStrategies().call()
    #print(allStrategies)

    strategy_list = [
        {"name": name, "address": address}
        for name, address in zip(allStrategies[0], allStrategies[1])
    ]

    return strategy_list

def register_strategy(name: str, address: str):
    adapter_address = web3.to_checksum_address(address)

    # Validate ABI
    abi_url = f"https://api-sepolia.etherscan.io/api?module=contract&action=getabi&address={adapter_address}&apikey={ETHERSCAN_API_KEY}"
    abi_response = requests.get(abi_url).json()
    if abi_response.get("status") != "1":
        raise ValueError("Invalid adapter contract address or ABI not found")

    # Prepare transaction
    tx = controller.functions.addStrategy(name, adapter_address).build_transaction({
        "from": account.address,
        "nonce": web3.eth.get_transaction_count(account.address),
        "gas": 300_000,
        "gasPrice": web3.to_wei("20", "gwei"),
    })

    # Sign and send transaction
    signed_tx = web3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)

    return {
        "message": "Strategy registered",
        "strategy": name,
        "adapter": adapter_address,
        "tx_hash": web3.to_hex(tx_hash),
    }

def getFundIdle():
    idleBalance = usdc.functions.balanceOf(controller_address).call()
    idleBalance = idleBalance / 10**6
    
    return {
        "idleBalance": idleBalance
    }

def fundDeployment():
    MIN_DEPLOYMENT_AMOUNT = 1000 / 10**6

    idleBalanced = usdc.functions.balanceOf(controller_address).call()
    idleBalance = idleBalanced / 10**6

    if idleBalance > MIN_DEPLOYMENT_AMOUNT:
        bestStrat = getBestStrategy()
        bestStratName = bestStrat["name"]
        bestStratAdapt = bestStrat["Adapter"]

        tx = controller.functions.deployToStrategy(bestStratName, idleBalanced).build_transaction({
            "from": account.address,
            "nonce": web3.eth.get_transaction_count(account.address),
            "gas": 300_000,
            "gasPrice": web3.to_wei("20", "gwei"),
        })

        # Sign and send transaction
        signed_tx = web3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)

        now = datetime.now()

        timeNow = now.strftime('%Y-%m-%d %H:%M:%S')

        # Save to DB
        # db = SessionLocal()
        # deployment = FundDeployment(
        #     method = "fundDeployment",
        #     strategy_name=bestStratName,
        #     adapter_address=bestStratAdapt,
        #     time_stamp=timeNow,
        #     idle_balance=idleBalanced,
        #     tx_hash=web3.to_hex(tx_hash)
        # )
        # db.add(deployment)
        # db.commit()
        # db.close()

        return {
            "message": "Fund Deployed",
            "name": bestStratName,
            "adapter": bestStratAdapt,
            "time_stamp": timeNow,
            "idleBalance": idleBalanced,
            "tx_hash": web3.to_hex(tx_hash),
        }

# def fundDeploymentHistory():
#     db: Session = SessionLocal()
#     try:
#         deployments = (
#             db.query(FundDeployment)
#             .order_by(FundDeployment.time_stamp.desc())  # Newest on top
#             .all()
#         )
#         result = []
#         for d in deployments:
#             result.append({
#                 "id": d.id,
#                 "method": d.method,
#                 "strategy_name": d.strategy_name,
#                 "adapter_address": d.adapter_address,
#                 "time_stamp": d.time_stamp.strftime('%Y-%m-%d %H:%M:%S'),
#                 "idle_balance": float(d.idle_balance),
#                 "tx_hash": d.tx_hash
#             })
#         return result
#     finally:
#         db.close()

def Rebalancing():
    allStrategies = controller.functions.getAllStrategies().call()
    #print(allStrategies)

    strategy_objs = [
        Strategy(name, address)
        for name, address in zip(allStrategies[0], allStrategies[1])
    ]

    apyData = []

    # Example usage:
    for strategy in strategy_objs:
        try:
            #print(strategy.name, strategy.address)
            stra_address = web3.to_checksum_address(strategy.address)
            straABI_ENDPOINT = f'https://api-sepolia.etherscan.io/api?module=contract&action=getabi&address={stra_address}&apikey={ETHERSCAN_API_KEY}'
            stra_abi = json.loads(requests.get(straABI_ENDPOINT).json()['result'])
            stra = web3.eth.contract(address=stra_address, abi=stra_abi)

            apy = stra.functions.getCurrentAPY().call()

            apyData.append({
                "name": strategy.name,
                "address": strategy.address,
                "apy": apy / 10**2
            })
        except:
            pass

    # Get highest APY
    highest = max(apyData, key=lambda x: x['apy'])

    # Get lowest APY
    lowest = min(apyData, key=lambda x: x['apy'])

    apyDifference = highest['apy'] - lowest['apy']

    gas_price_gwei = gwein
    gas_units = 300000

    idleBalanced = usdc.functions.balanceOf(controller_address).call()

    gas_price_eth = gas_price_gwei * 1e-9  # Gwei to ETH
    gasEstimate = gas_units * gas_price_eth  # in ETH

    annual_gain = 20000000 * (apyDifference / 100)
    gain_period = (30 / 365) * annual_gain
    isProfitable = gain_period - gasEstimate

    if isProfitable > 100:
        tx = controller.functions.rebalance().build_transaction({
            "from": account.address,
            "nonce": web3.eth.get_transaction_count(account.address),
            "gas": 300_000,
            "gasPrice": web3.to_wei(str(gwein), "gwei"),
        })

        # Sign and send transaction
        signed_tx = web3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)

        now = datetime.now()

        timeNow = now.strftime('%Y-%m-%d %H:%M:%S')

        # Save to DB
        # db = SessionLocal()
        # deployment = FundDeployment(
        #     method = "rebalancing",
        #     strategy_name=highest['name'],
        #     adapter_address=highest['address'],
        #     time_stamp=timeNow,
        #     idle_balance=idleBalanced,
        #     tx_hash=web3.to_hex(tx_hash)
        # )
        # db.add(deployment)
        # db.commit()
        # db.close()

        return {
            "message": "rebalancing",
            "name": highest['name'],
            "adapter": highest['address'],
            "time_stamp": timeNow,
            "idleBalance": idleBalanced,
            "tx_hash": web3.to_hex(tx_hash),
        }

def allAPY():
    allStrategies = controller.functions.getAllStrategies().call()
    #print(allStrategies)

    strategy_objs = [
        Strategy(name, address)
        for name, address in zip(allStrategies[0], allStrategies[1])
    ]

    apyData = []

    # Example usage:
    for strategy in strategy_objs:
        try:
            #print(strategy.name, strategy.address)
            stra_address = web3.to_checksum_address(strategy.address)
            straABI_ENDPOINT = f'https://api-sepolia.etherscan.io/api?module=contract&action=getabi&address={stra_address}&apikey={ETHERSCAN_API_KEY}'
            stra_abi = json.loads(requests.get(straABI_ENDPOINT).json()['result'])
            stra = web3.eth.contract(address=stra_address, abi=stra_abi)

            apy = stra.functions.getCurrentAPY().call()

            apyData.append({
                "name": strategy.name,
                "address": strategy.address,
                "apy": apy / 10**2
            })
        except:
            pass

    return apyData

def allAssets():
    idleBalanced = usdc.functions.balanceOf(controller_address).call()
    idleBalance = idleBalanced / 10**6

    vtlAssets = vlt.functions.totalAssets().call()
    vtlAssets = vtlAssets / 10**6

    return {
        "vaultTotalAssets": vtlAssets,
        "controllerIdleBalance": idleBalance,
    }

def emergencyWithdraw():
    bestStrat = getBestStrategy()
    bestStratName = bestStrat["name"]
    bestStratAdapt = bestStrat["Adapter"]

    url = "https://yield-api.norexa.ai/vault/stats"
    headers = {
        "accept": "application/json"
    }

    response = requests.get(url, headers=headers)
    data = response.json()
    total_assets = data["total_assets"]
    total_asset = total_assets *10**6

    tx = controller.functions.emergencyWithdraw(bestStratName).build_transaction({
        "from": account.address,
        "nonce": web3.eth.get_transaction_count(account.address),
        "gas": 300_000,
        "gasPrice": web3.to_wei("20", "gwei"),
    })

    # Sign and send transaction
    signed_tx = web3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)

    now = datetime.now()

    timeNow = now.strftime('%Y-%m-%d %H:%M:%S')

    # Save to DB
    # db = SessionLocal()
    # deployment = FundDeployment(
    #     method = "emergencyWithdraw",
    #     strategy_name=bestStratName,
    #     adapter_address=bestStratAdapt,
    #     time_stamp=timeNow,
    #     idle_balance=total_asset,
    #     tx_hash=web3.to_hex(tx_hash)
    # )
    # db.add(deployment)
    # db.commit()
    # db.close()

    return {
        "message": "Emergency Withdraw",
        "name": bestStratName,
        "adapter": bestStratAdapt,
        "time_stamp": timeNow,
        "idleBalance": total_asset,
        "tx_hash": web3.to_hex(tx_hash),
    }

def pauseAgent():
    tx = controller.functions.pause().build_transaction({
        "from": account.address,
        "nonce": web3.eth.get_transaction_count(account.address),
        "gas": 300_000,
        "gasPrice": web3.to_wei("20", "gwei"),
    })

    # Sign and send transaction
    signed_tx = web3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)

    now = datetime.now()

    timeNow = now.strftime('%Y-%m-%d %H:%M:%S')

    return {
        "message": "Controller Paused",
        "time_stamp": timeNow,
        "tx_hash": web3.to_hex(tx_hash),
    }

def unpauseAgent():
    tx = controller.functions.unpause().build_transaction({
        "from": account.address,
        "nonce": web3.eth.get_transaction_count(account.address),
        "gas": 300_000,
        "gasPrice": web3.to_wei("20", "gwei"),
    })

    # Sign and send transaction
    signed_tx = web3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)

    now = datetime.now()

    timeNow = now.strftime('%Y-%m-%d %H:%M:%S')

    return {
        "message": "Controller Unpaused",
        "time_stamp": timeNow,
        "tx_hash": web3.to_hex(tx_hash),
    }