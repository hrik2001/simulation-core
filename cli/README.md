# CLI

**CLI** is a command line tool to interact with the Python backend. It can be used to generate slippage graphs.

## How to use

If you don't the environment yet, first create one:
```
# python3 -m venv venv
# pip install -r requirements.txt
```

From the project root, activate the environment:
```
# source ./venv/bin/activate
```

List supported assets:
```
# python3 cli/main.py list
> ethereum
    > usd-coin
    > tether
    > crvusd
    > weth
    ...
```

Generate simple slippage graph with all quotes:
```
# python3 cli/main.py plot --collateral=coinbase-wrapped-btc --debt=usd-coin --network=ethereum --plot=simple
```

Generate simple slippage graph with the latest quote:
```
# python3 cli/main.py plot --collateral=coinbase-wrapped-btc --debt=usd-coin --network=ethereum --plot=simple --timestamp=now
```

Generate simple slippage graph at a specific Unix timestamp:
```
# python3 cli/main.py plot --collateral=coinbase-wrapped-btc --debt=usd-coin --network=ethereum --plot=simple --timestamp=1722526011
```

Generate regression slippage graph with regression:
```
# python3 cli/main.py plot --collateral=coinbase-wrapped-btc --debt=usd-coin --network=ethereum --plot=regression --timestamp=now
```

When you're done, exit the environment:
```
# deactive
```
