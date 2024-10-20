import json
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict
from ..models import SimulationRun, SummaryMetrics, TimeseriesData, PriceErrorDistribution
from typing import Any


class SimulationJSONGenerator:
    def __init__(
        self,
        simulation_run: SimulationRun,
        summary_metrics: SummaryMetrics,
        timeseries_data: list[TimeseriesData],
        price_error_distribution: list[PriceErrorDistribution],
    ):
        self.simulation_run = simulation_run
        self.summary_metrics = summary_metrics
        self.timeseries_data = timeseries_data
        self.price_error_distribution = price_error_distribution

    def generate_all_json(self):
        return {
            "simulation_run": self.generate_simulation_run_json(),
            "parameters": self.generate_parameters_json(),
            "summary_metrics": self.generate_summary_metrics_json(),
            "timeseries_data": self.generate_timeseries_data_json(),
            "price_error_distribution": self.generate_price_error_distribution_json(),
        }

    def generate_simulation_run_json(self):
        return model_to_dict(self.simulation_run)

    def generate_parameters_json(self):
        return model_to_dict(self.simulation_run.parameters)

    def generate_summary_metrics_json(self):
        return model_to_dict(self.summary_metrics)

    def generate_timeseries_data_json(self):
        return [model_to_dict(data) for data in self.timeseries_data]

    def generate_price_error_distribution_json(self):
        return [model_to_dict(data) for data in self.price_error_distribution]


def generate_multiple_simulations_json(simulation_runs: list) -> list[dict[Any]]:
    try:
        data = []
        for run in simulation_runs:
            generator = SimulationJSONGenerator(run)
            data.append(generator.generate_all_json())
        return json.dumps(data, cls=DjangoJSONEncoder)
    except Exception as e:
        return json.dumps({"error": str(e)})
