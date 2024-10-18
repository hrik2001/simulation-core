import pandas as pd
import altair as alt
from django.db.models import Avg, Min, Sum, Max


class SimulationDataProcessor:
    def __init__(self, simulation_runs):
        self.simulation_runs = simulation_runs
        self.summary_data = self._process_summary_data()
        self.timeseries_data = self._process_timeseries_data()
        self.price_error_data = self._process_price_error_data()

    def _process_summary_data(self):
        data = []
        for run in self.simulation_runs:
            data.append(
                {
                    "A": run.parameters.A,
                    "fee": run.parameters.fee,
                    "D": run.parameters.D,
                    "fee_mul": run.parameters.fee_mul,
                    "pool_value_virtual_annualized_returns": run.summary_metrics.pool_value_virtual_annualized_returns,
                    "pool_value_annualized_returns": run.summary_metrics.pool_value_annualized_returns,
                    "pool_balance_median": run.summary_metrics.pool_balance_median,
                    "pool_balance_min": run.summary_metrics.pool_balance_min,
                    "liquidity_density_median": run.summary_metrics.liquidity_density_median,
                    "liquidity_density_min": run.summary_metrics.liquidity_density_min,
                    "pool_volume_sum": run.summary_metrics.pool_volume_sum,
                    "arb_profit_sum": run.summary_metrics.arb_profit_sum,
                    "pool_fees_sum": run.summary_metrics.pool_fees_sum,
                    "price_error_median": run.summary_metrics.price_error_median,
                }
            )
        return pd.DataFrame(data)

    def _process_timeseries_data(self):
        data = []
        for run in self.simulation_runs:
            for ts in run.timeseries_data.all():
                data.append(
                    {
                        "A": run.parameters.A,
                        "fee": run.parameters.fee,
                        "D": run.parameters.D,
                        "fee_mul": run.parameters.fee_mul,
                        "timestamp": ts.timestamp,
                        "pool_value_virtual": ts.pool_value_virtual,
                        "pool_value": ts.pool_value,
                        "pool_balance": ts.pool_balance,
                        "liquidity_density": ts.liquidity_density,
                        "pool_volume": ts.pool_volume,
                        "arb_profit": ts.arb_profit,
                        "pool_fees": ts.pool_fees,
                    }
                )
        return pd.DataFrame(data)

    def _process_price_error_data(self):
        data = []
        for run in self.simulation_runs:
            for pe in run.price_error_distribution.all():
                data.append(
                    {
                        "A": run.parameters.A,
                        "fee": run.parameters.fee,
                        "D": run.parameters.D,
                        "fee_mul": run.parameters.fee_mul,
                        "price_error": pe.price_error,
                        "frequency": pe.frequency,
                    }
                )
        return pd.DataFrame(data)


class SimulationChartGenerator:
    def __init__(self, data_processor):
        self.data = data_processor

    def _create_parameter_selectors(self):
        a_selector = alt.selection_single(
            name="A_selector",
            fields=["A"],
            bind=alt.binding_select(options=sorted(self.data.summary_data["A"].unique()), name="A"),
        )
        fee_selector = alt.selection_single(
            name="fee_selector",
            fields=["fee"],
            bind=alt.binding_select(options=sorted(self.data.summary_data["fee"].unique()), name="Fee"),
        )
        d_selector = alt.selection_single(
            name="D_selector",
            fields=["D"],
            bind=alt.binding_select(options=sorted(self.data.summary_data["D"].unique()), name="D"),
        )
        fee_mul_selector = alt.selection_single(
            name="fee_mul_selector",
            fields=["fee_mul"],
            bind=alt.binding_select(options=sorted(self.data.summary_data["fee_mul"].unique()), name="Fee Multiplier"),
        )
        return a_selector & fee_selector & d_selector & fee_mul_selector

    def generate_pool_balance_chart(self):
        selectors = self._create_parameter_selectors()

        base = (
            alt.Chart(self.data.timeseries_data)
            .encode(x="timestamp:T", color=alt.Color("A:N", scale=alt.Scale(scheme="viridis")))
            .add_selection(selectors)
        )

        median_line = (
            base.mark_line()
            .encode(y="pool_balance:Q", tooltip=["timestamp:T", "pool_balance:Q", "A:N", "fee:Q", "D:Q", "fee_mul:Q"])
            .transform_filter(selectors)
        )

        min_line = (
            base.mark_line(strokeDash=[5, 5])
            .encode(y="pool_balance:Q", tooltip=["timestamp:T", "pool_balance:Q", "A:N", "fee:Q", "D:Q", "fee_mul:Q"])
            .transform_aggregate(pool_balance="min(pool_balance)", groupby=["timestamp", "A", "fee", "D", "fee_mul"])
            .transform_filter(selectors)
        )

        chart = (median_line + min_line).properties(title="Pool Balance over Time", width=600, height=400).interactive()

        return chart

    def generate_liquidity_density_chart(self):
        selectors = self._create_parameter_selectors()

        chart = (
            alt.Chart(self.data.timeseries_data)
            .mark_line()
            .encode(
                x="timestamp:T",
                y="liquidity_density:Q",
                color=alt.Color("A:N", scale=alt.Scale(scheme="viridis")),
                tooltip=["timestamp:T", "liquidity_density:Q", "A:N", "fee:Q", "D:Q", "fee_mul:Q"],
            )
            .properties(title="Liquidity Density over Time", width=600, height=400)
            .add_selection(selectors)
            .transform_filter(selectors)
            .interactive()
        )

        return chart

    def generate_volume_chart(self):
        selectors = self._create_parameter_selectors()

        chart = (
            alt.Chart(self.data.timeseries_data)
            .mark_bar()
            .encode(
                x="timestamp:T",
                y="pool_volume:Q",
                color=alt.Color("A:N", scale=alt.Scale(scheme="viridis")),
                tooltip=["timestamp:T", "pool_volume:Q", "A:N", "fee:Q", "D:Q", "fee_mul:Q"],
            )
            .properties(title="Daily Trading Volume", width=600, height=400)
            .add_selection(selectors)
            .transform_filter(selectors)
            .interactive()
        )

        return chart

    def generate_arb_profit_chart(self):
        selectors = self._create_parameter_selectors()

        chart = (
            alt.Chart(self.data.timeseries_data)
            .mark_line()
            .encode(
                x="timestamp:T",
                y="arb_profit:Q",
                color=alt.Color("A:N", scale=alt.Scale(scheme="viridis")),
                tooltip=["timestamp:T", "arb_profit:Q", "A:N", "fee:Q", "D:Q", "fee_mul:Q"],
            )
            .properties(title="Arbitrage Profit over Time", width=600, height=400)
            .add_selection(selectors)
            .transform_filter(selectors)
            .interactive()
        )

        return chart

    def generate_price_error_distribution_chart(self):
        selectors = self._create_parameter_selectors()

        chart = (
            alt.Chart(self.data.price_error_data)
            .mark_bar()
            .encode(
                x="price_error:Q",
                y="frequency:Q",
                color=alt.Color("A:N", scale=alt.Scale(scheme="viridis")),
                tooltip=["price_error:Q", "frequency:Q", "A:N", "fee:Q", "D:Q", "fee_mul:Q"],
            )
            .properties(title="Price Error Distribution", width=600, height=400)
            .add_selection(selectors)
            .transform_filter(selectors)
            .interactive()
        )

        return chart


def generate_simulation_charts(simulation_runs):
    try:
        processor = SimulationDataProcessor(simulation_runs)
        generator = SimulationChartGenerator(processor)

        charts = {
            "pool_balance": generator.generate_pool_balance_chart(),
            "liquidity_density": generator.generate_liquidity_density_chart(),
            "volume": generator.generate_volume_chart(),
            "arb_profit": generator.generate_arb_profit_chart(),
            "price_error_distribution": generator.generate_price_error_distribution_chart(),
        }

        return charts
    except Exception as e:
        return f"Error generating charts: {str(e)}"
