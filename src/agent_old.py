# from forta_agent import Finding, FindingType, FindingSeverity, get_transaction_receipt

# MEDIUM_GAS_THRESHOLD = 1000000
# HIGH_GAS_THRESHOLD = 3000000
# CRITICAL_GAS_THRESHOLD = 7000000

# findings_count = 0


# def provide_handle_transaction(get_transaction_receipt):
#     def handle_transaction(transaction_event):
#         # limiting this agent to emit only 5 findings so that the alert feed is not spammed
#         global findings_count
#         if findings_count >= 5:
#             return []

#         findings = []

#         receipt = get_transaction_receipt(transaction_event.hash)
#         gas_used = int(receipt.gas_used)
#         if gas_used < MEDIUM_GAS_THRESHOLD:
#             return findings

#         findings.append(Finding({
#             'name': 'High Gas Used',
#             'description': f'Gas Used: {gas_used}',
#             'alert_id': 'FORTA-1',
#             'type': FindingType.Suspicious,
#             'severity': get_severity(gas_used),
#             'metadata': {
#                 'gas_used': gas_used
#             }
#         }))
#         findings_count += len(findings)
#         return findings

#     return handle_transaction


# def get_severity(gas_used):
#     if gas_used > CRITICAL_GAS_THRESHOLD:
#         return FindingSeverity.Critical
#     elif gas_used > HIGH_GAS_THRESHOLD:
#         return FindingSeverity.High
#     else:
#         return FindingSeverity.Medium


# real_handle_transaction = provide_handle_transaction(get_transaction_receipt)

# def handle_transaction(transaction_event):
#     return real_handle_transaction(transaction_event)


from forta_agent import Finding, FindingType, FindingSeverity, get_web3_provider, Web3

ACCOUNT = "0x6efef34e81fd201edf18c7902948168e9ebb88ae"
MIN_BALANCE = int("500000000000000000")  # 0.5 eth


def provide_handle_block(w3):
    def handle_block(block_event):
        findings = []

        balance = int(w3.eth.get_balance(
            Web3.toChecksumAddress(ACCOUNT), int(block_event.block_number)))
        if (balance >= MIN_BALANCE):
            return findings

        findings.append(Finding({
            'name': "Minimum Account Balance",
            'description': f'Account balance ({balance}) below threshold ({MIN_BALANCE})',
            'alert_id': "FORTA-6",
            'severity': FindingSeverity.Info,
            'type': FindingType.Suspicious,
            'metadata': {
                'account': ACCOUNT,
                'balance': balance
            }
        }))
        return findings

    return handle_block


w3 = get_web3_provider()
real_handle_block = provide_handle_block(w3)


def handle_block(block_event):
    return real_handle_block(block_event)