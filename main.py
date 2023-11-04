import random
import time
import config
from colorama import init
import csv
import ccxt

from retry import retry
from web3 import Web3
from eth_abi.packed import encode_packed
from termcolor import cprint

from config import IS_RANDOM, VALUE_AMOUNT_TO, VALUE_AMOUNT_FROM, TRANSACTION_FROM, TRANSACTION_TO, ACCOUNT_DELAY_FROM, ACCOUNT_DELAY_TO, TRANSACTION_DELAY_FROM, TRANSACTION_DELAY_TO, ABI_MERKLY_REFUEL

init(autoreset=True)

def get_prices(ticket):
    exchange = ccxt.binance()

    try:
        ticker = exchange.fetch_ticker(ticket)  # Fetch the ticker data for the symbol
        last_price = ticker['last']  # Get the last price from the ticker data
        return last_price
    except Exception as e:
        print(f"Error fetching price for {ticket}: {e}")
        return None

class TransactionManager:

    def __init__(self, rpc, keys_file, proxies_file):
        self.web3 = Web3(Web3.HTTPProvider(rpc))

        with open(keys_file, "r") as f:
            self.keys = [row.strip() for row in f]

        with open(proxies_file, "r") as f:
            self.proxies = [row.strip() for row in f]


    def add_gas_price(self, contract_txn):
        gas_price = self.web3.eth.gas_price
        contract_txn['gasPrice'] = int(gas_price * random.uniform(1.01, 1.02))
        return contract_txn

    def add_gas_limit_layerzero(self, contract_txn):
        pluser = [1.05, 1.07]
        gasLimit = self.web3.eth.estimate_gas(contract_txn)
        contract_txn['gas'] = int(gasLimit * random.uniform(pluser[0], pluser[1]))
        return contract_txn


    @retry(ValueError, tries=3, delay=2, backoff=2)
    def merkly_refuel(self, private, type_tx, token_price):
        value_from = int((VALUE_AMOUNT_FROM / token_price) * 10 ** 18)
        value_to = int((VALUE_AMOUNT_TO / token_price) * 10 ** 18)
        value = random.randint(value_from, value_to)
        account = self.web3.eth.account.from_key(private)
        address = Web3.to_checksum_address(account.address)

        types = ["uint16", "uint", "uint", "address"]
        values = [2, 200000, value, address]
        adapter_params = encode_packed(types, values)

        hex_string = adapter_params.hex()
        nonce = self.web3.eth.get_transaction_count(address)

        contract = self.web3.eth.contract(
            address=Web3.to_checksum_address('0x0E1f20075C90Ab31FC2Dd91E536e6990262CF76d'), abi=ABI_MERKLY_REFUEL)

        if type_tx == 'Klaytn':
            cummision = int(0.364688857840070016 * 10 ** 18)
            recipient_address = "0x79DB0f1A83f8e743550EeB5DD5B0B83334F2F083"

            def_str = f'0x126928c4000000000000000000000000000000000000000000000000000000000000008a000000000000000000000000000000000000000000000000000000000000006000000000000000000000000000000000000000000000000000000000000000a00000000000000000000000000000000000000000000000000000000000000014{address[2:]}0000000000000000000000000000000000000000000000000000000000000000000000000000000000000056'

            input_data = def_str + hex_string
            '''рабочий костыль'''
            transaction = {
                'to': recipient_address,
                'from': address,
                'gas': 280000,
                'nonce': nonce,
                'type': 2,
                'chainId': '0x2019',
                'data': input_data,
                'maxFeePerGas': 54250000000,
                'maxPriorityFeePerGas': 24250000000,
                'value': value + cummision,
            }

        elif type_tx == 'Polygon':
            cummision = int(0.015414351335138046 * 10 ** 18)
            transaction = contract.functions.bridgeGas(
                212, #Conflux ID
                address,
                adapter_params).build_transaction(
                {
                    "from": address,
                    "value": value + cummision,
                    "nonce": nonce,
                    'gasPrice': 0,
                    'gas': 0,
                }
            )
            transaction = self.add_gas_price(transaction)
            transaction = self.add_gas_limit_layerzero(transaction)

        signed_transaction = self.web3.eth.account.sign_transaction(transaction, private)

        transaction_hash = self.web3.eth.send_raw_transaction(signed_transaction.rawTransaction)

        is_approve = self.web3.eth.wait_for_transaction_receipt(transaction_hash, timeout=30, poll_latency=0.1).status
        if is_approve == 0:
            if type_tx == 'Klaytn':
                cprint(f'\n>>> Transaction failed | https://scope.klaytn.com/tx/{transaction_hash.hex()} ', 'red')
                result = 'error'
            elif type_tx == 'Polygon':
                cprint(f'\n>>> Transaction failed | https://polygonscan.com/tx/{transaction_hash.hex()} ', 'red')
                result = 'error'
        else:
            if type_tx == 'Klaytn':
                cprint(f'\n>>> Transaction success | https://scope.klaytn.com/tx/{transaction_hash.hex()} ', 'green')
                result = 'success'
            elif type_tx == 'Polygon':
                cprint(f'\n>>> Transaction success | https://polygonscan.com/tx/{transaction_hash.hex()} ', 'green')
                result = 'success'
        return result


class CSVWriter:
    def __init__(self, csv_file):
        self.csv_file = csv_file

    def write_to_csv(self, type_tx, key, address, result, number_of_txn):
        with open(self.csv_file, 'a', newline='') as file:
            writer = csv.writer(file)

            if file.tell() == 0:
                writer.writerow(['type', 'key', 'address', 'result', 'transaction number'])

            writer.writerow([type_tx, key, address, result, number_of_txn + 1])

def main():
    cprint(f'\n============================================= 0rex =============================================', 'cyan')
    cprint(f'\ndonate: 0x5086028342e11b4ea1c405ca9923c4f3ffa0056f', 'cyan')
    cprint(f'\nsubscribe to me : https://t.me/orex_code', 'magenta')
    print()

    cprint(f'Выберите режим работы: \n Klaytn->Fuse выберите 1 \n Polygon->Conflux выберите 2 ')
    work_mode = int(input())

    if work_mode == 1:
        work_mode = 'Klaytn'
        token_price = get_prices('KLAY/USDT')
    elif work_mode == 2:
        work_mode = 'Polygon'
        token_price = get_prices('MATIC/USDT')
    transaction_manager = TransactionManager(config.RPCs[work_mode], "files/keys.txt", "files/proxy.txt")
    csv_writer = CSVWriter('result.csv')

    if len(transaction_manager.keys) == 0:
        cprint('Не вставлены приватные ключи в файл keys.txt!', 'red')
        return

    cprint(f'Начинаю работу на {len(transaction_manager.keys)} кошельках...')
    if IS_RANDOM:
        random.shuffle(transaction_manager.keys)
    last_index = max(index for index, _ in enumerate(transaction_manager.keys))
    numbered_list_keys = list(enumerate(transaction_manager.keys, start=0))

    tx_count = random.randint(TRANSACTION_FROM, TRANSACTION_TO)
    for number, key in numbered_list_keys:
        if transaction_manager.proxies:
            if IS_RANDOM:
                proxy = random.choice(transaction_manager.proxies)
            else:
                proxy = transaction_manager.proxies[number]
        else:
            proxy = None
        cprint(f'Proxy: {proxy}')

        for i in range(tx_count):
            try:
                res = transaction_manager.merkly_refuel(key, work_mode, token_price)
            except ValueError as e:
                cprint(f"После 3х попыток не удалось сделать Refuel: \n{str(e)}", 'red')
                res = e.args[0]['message']
            account = transaction_manager.web3.eth.account.from_key(key)
            csv_writer.write_to_csv(work_mode, key, account.address, res, i)
            if (i != tx_count - 1):
                time_sleep_txn = random.randint(TRANSACTION_DELAY_FROM, TRANSACTION_DELAY_TO)
                cprint(f'Сплю {time_sleep_txn} сек между транзакциями на аккаунте {account.address}', 'blue')
                time.sleep(time_sleep_txn)
        if (number != last_index):
            time_sleep_accs = random.randint(ACCOUNT_DELAY_FROM, ACCOUNT_DELAY_TO)
            cprint(f'Сплю {time_sleep_accs} сек между аккаунтами', 'blue')
            time.sleep(time_sleep_accs)
    cprint(f'Все {last_index + 1} кошельков были отработаны', 'green')

if __name__ == '__main__':
    main()
