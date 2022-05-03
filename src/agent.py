from forta_agent import Finding, FindingType, FindingSeverity, get_transaction_receipt, get_web3_provider, Web3

MEDIUM_GAS_THRESHOLD = 1000000
HIGH_GAS_THRESHOLD = 3000000
CRITICAL_GAS_THRESHOLD = 7000000

# MIN_BALANCE = int("500000000000000000")  # 0.5 eth


def provide_handle_block(w3):
    def handle_block(block_event):
        findings = []
        print(w3.eth.generate_gas_price())
        # balance = int(w3.eth.get_balance(
        #     Web3.toChecksumAddress(ACCOUNT), int(block_event.block_number)))
        # if (balance >= MIN_BALANCE):
        #     return findings

        # findings.append(Finding({
        #     'name': "Minimum Account Balance",
        #     'description': f'Account balance ({balance}) below threshold ({MIN_BALANCE})',
        #     'alert_id': "FORTA-6",
        #     'severity': FindingSeverity.Info,
        #     'type': FindingType.Suspicious,
        #     'metadata': {
        #         'account': ACCOUNT,
        #         'balance': balance
        #     }
        # }))
        return findings

    return handle_block

def get_severity(gas_used):
    if gas_used > CRITICAL_GAS_THRESHOLD:
        return FindingSeverity.Critical
    elif gas_used > HIGH_GAS_THRESHOLD:
        return FindingSeverity.High
    else:
        return FindingSeverity.Medium


w3 = get_web3_provider()
real_handle_block = provide_handle_block(w3)

def handle_block(block_event):
    return real_handle_block(block_event)