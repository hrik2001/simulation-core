from django.db import models


class SimulationParameters(models.Model):
    A = models.IntegerField()
    D = models.FloatField()
    fee = models.FloatField()
    fee_mul = models.FloatField()
    admin_fee = models.FloatField()

    class Meta:
        unique_together = ("A", "fee", "D", "fee_mul", "admin_fee")

    def __str__(self):
        return f"A: {self.A}, D: {self.D}, fee: {self.fee}, fee_mul: {self.fee_mul}, admin_fee: {self.admin_fee}"


class SimulationRun(models.Model):
    parameters = models.ForeignKey(SimulationParameters, on_delete=models.CASCADE, related_name="runs")
    run_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("parameters", "run_date")

    def __str__(self):
        return f"Run for {self.parameters} on {self.run_date}"


class TimeseriesData(models.Model):
    simulation_run = models.ForeignKey(SimulationRun, on_delete=models.CASCADE, related_name="timeseries_data")
    timestamp = models.DateTimeField()
    pool_value_virtual = models.FloatField()
    pool_value = models.FloatField()
    pool_balance = models.FloatField()
    liquidity_density = models.FloatField()
    pool_volume = models.FloatField()
    arb_profit = models.FloatField()
    pool_fees = models.FloatField()

    def __str__(self):
        return f"Timeseries data for {self.simulation_run} at {self.timestamp}"


class SummaryMetrics(models.Model):
    simulation_run = models.OneToOneField(SimulationRun, on_delete=models.CASCADE, related_name="summary_metrics")
    pool_value_virtual_annualized_returns = models.FloatField()
    pool_value_annualized_returns = models.FloatField()
    pool_balance_median = models.FloatField()
    pool_balance_min = models.FloatField()
    liquidity_density_median = models.FloatField()
    liquidity_density_min = models.FloatField()
    pool_volume_sum = models.FloatField()
    arb_profit_sum = models.FloatField()
    pool_fees_sum = models.FloatField()
    price_error_median = models.FloatField()

    def __str__(self):
        return f"Summary metrics for {self.simulation_run}"


class PriceErrorDistribution(models.Model):
    simulation_run = models.ForeignKey(SimulationRun, on_delete=models.CASCADE, related_name="price_error_distribution")
    price_error = models.FloatField()
    frequency = models.FloatField()

    def __str__(self):
        return f"Price error distribution for {self.simulation_run}: {self.price_error}"


class Pool(models.Model):
    address = models.CharField(max_length=42)
    name = models.CharField(max_length=100)
    params_dict = models.JSONField()
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.name
