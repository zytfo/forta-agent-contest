# Unusual Price Changes Agent

## Description

This agent detects transactions with unusual price changes

## Supported Chains

- Ethereum

## Alerts

- FORTA-15
  - Fired when a price change is higher than current trend + predicted value
  - Type is always set to "suspicious"
  - Metadata "price_change" field contains the price change
  - Metadata "pool" field contains pool address

## Test Data