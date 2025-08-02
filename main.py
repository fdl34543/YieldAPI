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
from eth_abi import decode
from eth_utils import remove_0x_prefix

app = FastAPI()

load_dotenv()

# Allow frontend to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

VALID_API_KEY = "39a4f6be5b3a4d08ddaf45944cd8ce42"

# Config
INFURA_KEY = os.getenv("INFURA_KEY")
SEPOLIA_RPC = f"https://mainnet.infura.io/v3/{INFURA_KEY}"
#SEPOLIA_RPC = f"https://sepolia.infura.io/v3/{INFURA_KEY}"
# SEPOLIA_RPC = f"https://eth-sepolia.g.alchemy.com/v2/ZUVnw8JKo7RBHLiXiyjuhEH1trRDNodx"
ETHERSCAN_API_KEY = "15W7XAPWQMGR8I34AB5KK7XQAEIAS9PEGZ"
web3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC))
DECIMALS = 1e6  # Adjust if vault uses 1e18
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
account = web3.eth.account.from_key(PRIVATE_KEY)

controller_address = web3.to_checksum_address("0x4851B11C449ab0Ed8a8071edF47A5f880818cfC0")
CABI_ENDPOINT = f'https://api.etherscan.io/api?module=contract&action=getabi&address=0x4851B11C449ab0Ed8a8071edF47A5f880818cfC0&apikey={ETHERSCAN_API_KEY}'
controller_abi = json.loads(requests.get(CABI_ENDPOINT).json()['result'])
controller = web3.eth.contract(address=controller_address, abi=controller_abi)

oracle_address = web3.to_checksum_address("0xEdA6eF355105778996c113C639A763533D18425b")
OABI_ENDPOINT = f'https://api.etherscan.io/api?module=contract&action=getabi&address=0xEdA6eF355105778996c113C639A763533D18425b&apikey={ETHERSCAN_API_KEY}'
oracle_abi = json.loads(requests.get(OABI_ENDPOINT).json()['result'])
oracle = web3.eth.contract(address=oracle_address, abi=oracle_abi)

usdc_address = web3.to_checksum_address("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")
usdcABI_ENDPOINT = f'https://api.etherscan.io/api?module=contract&action=getabi&address=0x43506849D7C04F9138D1A2050bbF3A0c054402dd&apikey={ETHERSCAN_API_KEY}'
time.sleep(2)
usdc_abi = json.loads(requests.get(usdcABI_ENDPOINT).json()['result'])
usdc = web3.eth.contract(address=usdc_address, abi=usdc_abi)

vlt_address = web3.to_checksum_address("0x8CE2E25fa9E0F56b42668B4Af1AB8d1b404a1e10")
vltABI_ENDPOINT = f'https://api.etherscan.io/api?module=contract&action=getabi&address={vlt_address}&apikey={ETHERSCAN_API_KEY}'
time.sleep(1)
vlt_abi = json.loads(requests.get(vltABI_ENDPOINT).json()['result'])
vlt = web3.eth.contract(address=vlt_address, abi=vlt_abi)

erc20_abi = [
    {
        "constant": True,
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    }
]

comet_address = web3.to_checksum_address("0xc3d688B66703497DAA19211EEdff47f25384cdc3")
comet = web3.eth.contract(address=comet_address, abi=erc20_abi)

ausd_address = web3.to_checksum_address("0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c")
ausd = web3.eth.contract(address=ausd_address, abi=erc20_abi)

morphoV_address = web3.to_checksum_address("0xBEEF01735c132Ada46AA9aA4c54623cAA92A64CB")
morphoV = web3.eth.contract(address=comet_address, abi=erc20_abi)

yearnV_address = web3.to_checksum_address("0xa354F35829Ae975e850e23e9615b11Da1B3dC4DE")
yearnV = web3.eth.contract(address=yearnV_address, abi=erc20_abi)

vesperP_address = web3.to_checksum_address("0x0C49066C0808Ee8c673553B7cbd99BCC9ABf113d")
vesperP = web3.eth.contract(address=vesperP_address, abi=erc20_abi)

url = 'https://api.etherscan.io/api?module=gastracker&action=gasoracle&apikey=15W7XAPWQMGR8I34AB5KK7XQAEIAS9PEGZ'
response = requests.get(url).text
datagwei = json.loads(response)
gweinow = datagwei["result"]["SafeGasPrice"]
gwein = float(gweinow) + 5


urlbest = "https://yield-api.norexa.ai/vstrategies/best"
headersbest = {
    "accept": "application/json"
}

responsebest = requests.get(urlbest, headers=headersbest)
databest = responsebest.json()
best_Adapter = databest["Adapter"]


def verify_api_key(api_key: str):
    if api_key != VALID_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

# Yield Metrics
@app.get("/yield/metrics")
def yield_metrics():
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
            straABI_ENDPOINT = f'https://api.etherscan.io/api?module=contract&action=getabi&address={stra_address}&apikey={ETHERSCAN_API_KEY}'
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

    apyData = []

    for strategy in strategy_objs:
        try:
            apy = oracle.functions.getAPY(strategy.address).call()

            apyData.append({
                "name": strategy.name,
                "address": strategy.address,
                "apy": apy / 10**2
            })
        except:
            print()

    return {
        "best_protocol": best['name'],
        "apy": best['apy'],
        "adapter": best['address'],
        "all_apys": apyData
    }

# Vault Stats
@app.get("/vault/stats")
def vault_stats():
    # adapter = getBestStrategy()["Adapter"]
    return get_vault_stats(best_Adapter)
    # adapter = getBestStrategy()["Adapter"]
    # return get_vault_stats(adapter)

@app.get("/vault/feeAnalytics")
def fee_analytics():
    return getFeeAnalytics()

# Fee + Performance History
@app.get("/vault/performance")
def vault_performance():
    adapter = getBestStrategy()["Adapter"]
    return performanceHistory(adapter)

# User Position
@app.get("/user/{address}/position")
def get_user_position(address: str):
    # 1. Current shares
    raw_shares = vlt.functions.balanceOf(address).call()
    shares = raw_shares / 1e6

    # 2. Share price / assets per share
    share_price = vlt.functions.convertToAssets(10**6).call() / 1e6
    value_usd = shares * share_price

    # 3. Historical deposits / withdrawals
    deposits, withdrawals = get_user_transactions(address)  # <-- use your etherscan filter
    total_deposited = sum(d["assets"] for d in deposits)
    total_withdrawn = sum(w["assets"] for w in withdrawals)

    # Shares received = deposited assets / avg price at deposit time
    shares_received = sum(d["shares"] for d in deposits)
    avg_entry_price = (total_deposited / shares_received) if shares_received else 0

    # 4. Unrealized profit
    unrealized_profit = value_usd - (shares * avg_entry_price)

    # 5. Lifetime earnings
    lifetime_earnings = (total_withdrawn + value_usd) - total_deposited

    return {
        "shares": shares,
        "value_usd": value_usd,
        "avg_entry_price": avg_entry_price,
        "unrealized_profit": unrealized_profit,
        "lifetime_earnings": lifetime_earnings
    }

# Best Strategies
@app.get("/strategies/best")
def best_strategies():
    return getBestStrategy()

# All Strategies
@app.get("/strategies/all")
def all_strategies():
    return getAllStrategies()

# Strategies Current Allocation
@app.get("/strategies/allocation")
def strategies_allocation():
    return getStrategiesAllocation()

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
    
# Deploy Funds To Strat
class DeployStrat(BaseModel):
    name: str
    amount: int

@app.post("/funds/deploy/strat")
async def funds_deploy_to_strategy(data: DeployStrat):
    try:
        result = fundDeploytoStrat(data.name, data.amount)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# --- Core logic from your script below ----

def get_user_transactions(address):
    url = f"https://api.etherscan.io/api"
    params = {
        "module": "account",
        "action": "txlist",
        "address": "0x8CE2E25fa9E0F56b42668B4Af1AB8d1b404a1e10",
        "startblock": 0,
        "endblock": 99999999,
        "sort": "desc",
        "apikey": ETHERSCAN_API_KEY
    }
    res = requests.get(url, params=params)
    time.sleep(3)
    res = res.json()
    txs = res.get("result", [])

    deposits = []
    withdrawals = []

    deposit_selector = "0x6e553f65"
    withdraw_selector = "0x2e1a7d4d"

    for tx in txs:
        if tx.get("from", "").lower() != address.lower():
            continue  # skip if not user

        input_data = tx.get("input", "")
        if not input_data or input_data == "0x":
            continue

        # DEPOSIT
        if input_data.startswith(deposit_selector):
            params = bytes.fromhex(remove_0x_prefix(input_data)[8:])
            assets, receiver = decode(["uint256", "address"], params)
            deposits.append({
                "assets": assets / 1e6,   # normalize to USDC decimals (6)
                "shares": assets / 1e6,   # for stable vault shares ≈ assets
                "blockTime": int(tx.get("timeStamp", 0)),
                "txHash": tx["hash"]
            })

        # WITHDRAW
        elif input_data.startswith(withdraw_selector):
            params = bytes.fromhex(remove_0x_prefix(input_data)[8:])
            assets, receiver, owner = decode(["uint256", "address", "address"], params)
            withdrawals.append({
                "assets": assets / 1e6,
                "blockTime": int(tx.get("timeStamp", 0)),
                "txHash": tx["hash"]
            })

    return deposits, withdrawals
    

def get_normal_transactions():
    url = f"https://api.etherscan.io/api"
    params = {
        "module": "account",
        "action": "txlist",
        "address": "0x8CE2E25fa9E0F56b42668B4Af1AB8d1b404a1e10",
        "startblock": 0,
        "endblock": 99999999,
        "sort": "desc",
        "apikey": ETHERSCAN_API_KEY
    }
    response = requests.get(url, params=params)
    time.sleep(2)
    return response.json()

def depositValue(tx_data):
    txValue = []
    for tx in tx_data.get("result", []):
        if tx.get("input", "").startswith("0x6e553f65"):  # deposit(uint256,address)
            data = tx["input"]

            # strip "0x" and the first 8 hex chars (function selector)
            params = bytes.fromhex(remove_0x_prefix(data)[8:])

            # decode ABI: first param = uint256, second = address
            assets, receiver = decode(["uint256", "address"], params)

            txValue.append(assets / 1e6)

    sum_tx_value = sum(txValue)
    return sum_tx_value

def uniqueDepositor(tx_data):
    depositors = set()
    txValue = []
    for tx in tx_data.get("result", []):
        if tx.get("input", "").startswith("0x6e553f65"):  # deposit(uint256,address)
            data = tx["input"]

            # strip "0x" and the first 8 hex chars (function selector)
            params = bytes.fromhex(remove_0x_prefix(data)[8:])

            # decode ABI: first param = uint256, second = address
            assets, receiver = decode(["uint256", "address"], params)

            depositor = tx.get("from")  # depositor wallet
            if depositor not in depositors:
                depositors.add(depositor)

    unique = len(depositors)
    return unique

def withdrawValue(tx_data):
    txValue = []
    for tx in tx_data.get("result", []):
        if tx.get("input", "").startswith("0x2e1a7d4d"):  # deposit(uint256,address)
            data = tx["input"]

            # strip "0x" and the first 8 hex chars (function selector)
            params = bytes.fromhex(remove_0x_prefix(data)[8:])

            # decode ABI: first param = uint256, second = address
            assets, receiver = decode(["uint256", "address"], params)

            txValue.append(assets / 1e6)

    sum_tx_value = sum(txValue)
    return sum_tx_value

def get_vault_stats(best_Adapter):
# def get_vault_stats(bestAdapter):
    bestAdapter = best_Adapter

    vault_address = web3.to_checksum_address(bestAdapter)
    # ABI_ENDPOINT = f'https://api.etherscan.io/api?module=contract&action=getabi&address={vault_address}&apikey={ETHERSCAN_API_KEY}'
    # time.sleep(2)
    # vault_abi = json.loads(requests.get(ABI_ENDPOINT).json()['result'])

    # with open("controllerABI.json", "r") as f:
    #     vault_abi = json.load(f)

    vault_abi = [{"inputs":[],"stateMutability":"nonpayable","type":"constructor"},
{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"updater","type":"address"},
{"indexed":False,"internalType":"uint256","name":"newAPY","type":"uint256"},
{"indexed":False,"internalType":"uint256","name":"sharePrice","type":"uint256"}],
"name":"MetricsUpdated","type":"event"},
{"inputs":[],"name":"getTotalShares","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
"stateMutability":"view","type":"function"},
{"inputs":[],"name":"sharePrice","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
"stateMutability":"view","type":"function"}]

    vault = web3.eth.contract(address=vault_address, abi=vault_abi)

    #total_assets = vault.functions.getTotalDeposits().call()
    total_shares = vault.functions.getTotalShares().call()
    share_price = vault.functions.sharePrice().call()

    total_assets = (total_shares / DECIMALS) * (share_price/ 10e17)

    idleBalanced = usdc.functions.balanceOf(controller_address).call()
    idleBalance = idleBalanced / 10**6

    vtlAssets = vlt.functions.totalAssets().call()
    vtlAssets = vtlAssets / 10**6
    
    eth_txs = get_normal_transactions()
    deposit_value = depositValue(eth_txs)
    withdraw_value = withdrawValue(eth_txs)
    unique = uniqueDepositor(eth_txs)
    netFlow = deposit_value - withdraw_value

    return {
        "BalanceUnderManagement":{
            "vaultTotalAssets": vtlAssets,
            "controllerIdleBalance": idleBalance,
        },
        "total_assets": round(total_assets, 5),
        "total_shares": round(total_shares / DECIMALS, 2),
        "share_price": round(share_price / 1e18, 6),
        "unique_depositors": unique,
        "24h_deposits": deposit_value,
        "24h_withdrawals": withdraw_value,
        "net_flow_24h": netFlow
    }

def performanceHistory(bestAdapter):
    vault_address = web3.to_checksum_address(bestAdapter)
    ABI_ENDPOINT = f'https://api.etherscan.io/api?module=contract&action=getabi&address={vault_address}&apikey={ETHERSCAN_API_KEY}'
    time.sleep(2)
    vault_abi = json.loads(requests.get(ABI_ENDPOINT).json()['result'])

    # with open("controllerABI.json", "r") as f:
    #     vault_abi = json.load(f)

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
            straABI_ENDPOINT = f'https://api.etherscan.io/api?module=contract&action=getabi&address={stra_address}&apikey={ETHERSCAN_API_KEY}'
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
    abi_url = f"https://api.etherscan.io/api?module=contract&action=getabi&address={adapter_address}&apikey={ETHERSCAN_API_KEY}"
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

def getStrategiesAllocation():
    compound = comet.functions.balanceOf("0x53CB26F7E9d982121BcFe8506111fd9Ab0f99A1f").call()
    Aave = ausd.functions.balanceOf("0x5c44B10AF7Ed8F18751B56DF80A84B57dd3bfEcD").call()
    Morpho = morphoV.functions.balanceOf("0xedAf7B13Cf5736612825B4aFA88D18Edab8f7592").call()
    Yearn = yearnV.functions.balanceOf("0x93B89230465e664f37C41cfc66B2924182eaEa52").call()
    Vesper = vesperP.functions.balanceOf("0xA8e0e78B8949247CbCa68656d0c7b7512f3655D2").call()

    return {
        "Compound": round(compound / 10**6, 4),
        "Aave": round(Aave / 10**6, 4),
        "Morpho": round(Morpho / 10**6, 4),
        "Yearn": round(Yearn / 10**6, 4),
        "Vesper": round(Vesper / 10**12, 4)
    }

def getFundIdle():
    idleBalance = usdc.functions.balanceOf(controller_address).call()
    idleBalance = idleBalance / 10**6
    
    return {
        "idleBalance": idleBalance
    }

def fundDeploytoStrat(toStrat,amount):
    MIN_DEPLOYMENT_AMOUNT = 1000 / 10**6

    amount = amount * 10**6

    if amount > MIN_DEPLOYMENT_AMOUNT:
        
        bestStratName = toStrat

        tx = controller.functions.deployToStrategy(bestStratName, amount).build_transaction({
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
            "time_stamp": timeNow,
            "amount": amount,
            "tx_hash": web3.to_hex(tx_hash),
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
            apy = oracle.functions.getAPY(strategy.address).call()

            apyData.append({
                "name": strategy.name,
                "address": strategy.address,
                "apy": apy / 10**2
            })
        except:
            print()

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

    # gas_estimate = web3.eth.estimate_gas({
    #     "from": account.address,
    #     "to": controller.address,  # Ensure the 'to' address is the controller contract
    #     "data": controller.functions.rebalance().encode_transaction_data()
    # })

    if isProfitable > 100:
        tx = controller.functions.rebalance().build_transaction({
            "from": account.address,
            "nonce": web3.eth.get_transaction_count(account.address),
            "gas": 900_000,
            "maxFeePerGas": web3.to_wei("20", "gwei"),
            "maxPriorityFeePerGas": web3.to_wei("10", "gwei"),
            "chainId": 1,
            "type": 2
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
            "tx_hash": web3.to_hex(tx_hash),
        }

def allAPY():
    allStrategies = controller.functions.getAllStrategies().call()

    strategy_objs = [
        Strategy(name, address)
        for name, address in zip(allStrategies[0], allStrategies[1])
    ]

    apyData = []

    # Example usage:
    for strategy in strategy_objs:
        try:
            apy = oracle.functions.getAPY(strategy.address).call()

            apyData.append({
                "name": strategy.name,
                "address": strategy.address,
                "apy": apy / 10**2
            })
        except:
            print()

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
        "maxFeePerGas": web3.to_wei("20", "gwei"),
        "maxPriorityFeePerGas": web3.to_wei("10", "gwei"),
        # "chainId": 11155111,  # Sepolia
        "type": 2
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