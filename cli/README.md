# CLI

**CLI** is a command line tool to interact with the Python backend. It can be used to generate slippage graphs.

## How to use

If you don't the environment yet, first create one:
```
# python3 -m venv venv
# source venv/bin/activate
# pip install -r requirements.txt
```

During the instalation, you might have an error related to a missing OS library. To obtain it, [you need to install PostgreSQL](https://www.postgresqltutorial.com/postgresql-getting-started/) on your OS. On MacOS, you can just use `brew`:
```
# brew install postgresql
```

If you already have the environment installed, just activate it:
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

Generate slippage graph with regression line:
```
# python3 cli/main.py plot --collateral=coinbase-wrapped-btc --debt=usd-coin --network=ethereum --plot=regression --timestamp=now
```

When you're done, exit the environment:
```
# deactive
```