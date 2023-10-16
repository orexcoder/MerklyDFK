import toml

with open('config.toml', 'r', encoding='utf-8') as f:
    config = toml.load(f)

RPC = config.get('RPC')

IS_RANDOM = config.get('IS_RANDOM')

VALUE_AMOUNT_FROM = config.get('VALUE_FROM')
VALUE_AMOUNT_TO = config.get('VALUE_TO')

TRANSACTION_DELAY_FROM = config.get('TRANSACTION_DELAY_FROM')
TRANSACTION_DELAY_TO = config.get('TRANSACTION_DELAY_TO')

ACCOUNT_DELAY_FROM = config.get('ACCOUNT_DELAY_FROM')
ACCOUNT_DELAY_TO = config.get('ACCOUNT_DELAY_TO')

TRANSACTION_FROM = config.get('TRANSACTION_FROM')
TRANSACTION_TO = config.get('TRANSACTION_TO')