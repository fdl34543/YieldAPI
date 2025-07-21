from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from web3 import Web3
from datetime import datetime
import requests
import json

app = FastAPI()

# Allow frontend to access the API (change origin for prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Config
SEPOLIA_RPC = "https://sepolia.infura.io/v3/2ba3d93485814c04b0106479c8e9973d"
ETHERSCAN_API_KEY = "15W7XAPWQMGR8I34AB5KK7XQAEIAS9PEGZ"
web3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC))
DECIMALS = 1e6  # Adjust if vault uses 1e18

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
    adapter = get_best_yield_usdc()["adapter"]
    return get_vault_stats(adapter)

@app.get("/vault/feeAnalytics")
def fee_analytics():
    return getFeeAnalytics()

# Fee + Performance History
@app.get("/vault/performance")
def vault_performance():
    adapter = get_best_yield_usdc()["adapter"]
    return performanceHistory(adapter)

# --- Core logic from your script below ---

def get_best_yield_usdc():
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

def get_vault_stats(bestAdapter):
    vault_address = web3.to_checksum_address(bestAdapter)
    ABI_ENDPOINT = f'https://api-sepolia.etherscan.io/api?module=contract&action=getabi&address={vault_address}&apikey={ETHERSCAN_API_KEY}'
    vault_abi = json.loads(requests.get(ABI_ENDPOINT).json()['result'])
    vault = web3.eth.contract(address=vault_address, abi=vault_abi)

    total_assets = vault.functions.getTotalDeposits().call()
    total_shares = vault.functions.getTotalShares().call()
    share_price = vault.functions.sharePrice().call()

    deposit_topic = web3.keccak(text="Deposit(address,address,uint256,uint256)").hex()
    withdraw_topic = web3.keccak(text="Withdraw(address,address,uint256,uint256)").hex()

    latest_block = web3.eth.block_number
    latest_time = web3.eth.get_block(latest_block)["timestamp"]
    start_time = latest_time - 86400

    from_block = max(latest_block - 20000, 0)

    def get_logs(topic):
        return web3.eth.get_logs({
            "fromBlock": from_block,
            "toBlock": latest_block,
            "address": vault_address,
            "topics": [topic]
        })

    deposit_logs = get_logs(deposit_topic)
    withdraw_logs = get_logs(withdraw_topic)

    depositors = set()
    total_deposit = 0
    total_withdraw = 0

    for log in deposit_logs:
        block_time = web3.eth.get_block(log["blockNumber"])["timestamp"]
        if block_time >= start_time:
            depositor = "0x" + log["topics"][2].hex()[-40:]
            depositors.add(depositor)
            amount = int(log["data"][2:66], 16)
            total_deposit += amount

    for log in withdraw_logs:
        block_time = web3.eth.get_block(log["blockNumber"])["timestamp"]
        if block_time >= start_time:
            amount = int(log["data"][2:66], 16)
            total_withdraw += amount

    net_flow = total_deposit - total_withdraw

    return {
        "total_assets": round(total_assets / DECIMALS, 2),
        "total_shares": round(total_shares / DECIMALS, 2),
        "share_price": round(share_price / 1e18, 6),
        "unique_depositors": len(depositors),
        "24h_deposits": round(total_deposit / DECIMALS, 2),
        "24h_withdrawals": round(total_withdraw / DECIMALS, 2),
        "net_flow_24h": round(net_flow / DECIMALS, 2)
    }

def performanceHistory(bestAdapter):
    vault_address = web3.to_checksum_address(bestAdapter)
    ABI_ENDPOINT = f'https://api-sepolia.etherscan.io/api?module=contract&action=getabi&address={vault_address}&apikey={ETHERSCAN_API_KEY}'
    vault_abi = json.loads(requests.get(ABI_ENDPOINT).json()['result'])
    vault = web3.eth.contract(address=vault_address, abi=vault_abi)

    controller_address = web3.to_checksum_address("0x8E486c2EF1A1f84acA2a251863aEd0B468a69221")
    CABI_ENDPOINT = f'https://api-sepolia.etherscan.io/api?module=contract&action=getabi&address=0xBD7189cD389f3CfDa49F5c6F72C1508a198EA8a6&apikey={ETHERSCAN_API_KEY}'
    controller_abi = json.loads(requests.get(CABI_ENDPOINT).json()['result'])
    controller = web3.eth.contract(address=controller_address, abi=controller_abi)

    rebalance = controller.functions.rebalanceThreshold().call()
    rebalance_event = web3.keccak(text="Rebalanced(address,uint256)").hex()
    harvest_event = web3.keccak(text="YieldHarvested(uint256,uint256)").hex()

    logs = web3.eth.get_logs({
        "fromBlock": 0,
        "toBlock": "latest",
        "address": vault_address,
        "topics": [None]
    })

    performance_by_day = {}
    cumulative_yield = 0
    cumulative_gas = 0

    for log in logs:
        block = web3.eth.get_block(log['blockNumber'])
        date = datetime.utcfromtimestamp(block['timestamp']).strftime("%Y-%m-%d")

        if log['topics'][0].hex() == rebalance_event:
            performance_by_day.setdefault(date, {"rebalances": 0})
            performance_by_day[date]["rebalances"] += 1

        elif log['topics'][0].hex() == harvest_event:
            data = web3.codec.decode(["uint256", "uint256"], log["data"])
            yield_amt, gas_amt = data
            cumulative_yield += yield_amt
            cumulative_gas += gas_amt

    return {
        "performance_history": [{
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "apy": round(vault.functions.getCurrentAPY().call() / 100, 2),
            "total_assets": round(vault.functions.getTotalDeposits().call() / DECIMALS, 2),
            "rebalances": round(rebalance / 100)
        }],
        "cumulative_yield_generated": cumulative_yield / 1e6,
        "cumulative_gas_costs": cumulative_gas / 1e6,
        "net_yield": (cumulative_yield - cumulative_gas) / 1e6
    }
def getFeeAnalytics():
    vlt_address = web3.to_checksum_address("0x31cc89CFC8F4fa96816dc006134d655169e68388")
    ABI_ENDPOINT = f'https://api-sepolia.etherscan.io/api?module=contract&action=getabi&address={vlt_address}&apikey={ETHERSCAN_API_KEY}'
    vlt_abi = json.loads(requests.get(ABI_ENDPOINT).json()['result'])
    vlt = web3.eth.contract(address=vlt_address, abi=vlt_abi)

    fees = vlt.functions.getFeeAnalytics().call()

    return {
        "accrued_fees": fees[0] / 1e6,
        "fees_collected_24h": fees[1] / 1e6,
        "fees_collected_total": fees[2] / 1e6
    }

