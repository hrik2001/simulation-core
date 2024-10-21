from pathlib import Path

import pandas as pd
from django.http import JsonResponse


def get_drawdowns(request):
    data_dir = Path(__file__).parent / "data"
    btc_path = data_dir / "BTC_impact.csv"
    eth_path = data_dir / "ETH_impact.csv"
    drawdown_df = pd.concat(
        [pd.read_csv(btc_path), pd.read_csv(eth_path)], ignore_index=True
    )

    drawdown_df["drawdown_start"] = pd.to_datetime(drawdown_df["drawdown_start"])
    drawdown_df["drawdown_end"] = pd.to_datetime(drawdown_df["drawdown_end"])
    drawdown_df["duration"] = (
        drawdown_df["drawdown_end"] - drawdown_df["drawdown_start"]
    )
    drawdown_df["duration"] = drawdown_df["duration"].dt.days

    average_duration = drawdown_df["duration"].mean()
    drawdown_dict = drawdown_df.to_dict(orient="records")

    response = {
        "drawdowns": drawdown_dict,
        "average_duration": average_duration,
    }

    return JsonResponse(response, safe=False)
