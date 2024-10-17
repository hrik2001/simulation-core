import json
from django.utils.html import escape
from django.core.exceptions import ValidationError
from ..models import SimulationRun


class SimulationHTMLGenerator:
    def __init__(self, simulation_run):
        self.simulation_run = simulation_run
        self.params = simulation_run.parameters
        self.summary_metrics = simulation_run.summary_metrics
        self.timeseries_data = list(simulation_run.timeseries_data.all())
        self.price_error_distribution = list(simulation_run.price_error_distribution.all())

    def generate_vega_html(self):
        try:
            return f"""
            {{
              "config": {{"view": {{"continuousWidth": 300, "continuousHeight": 300}}}},
              "vconcat": [
                {{
                  "vconcat": [
                    {self.generate_selectors()},
                    {{
                      "concat": [
                        {self.generate_summary_metrics()},
                        {self.generate_timeseries_chart()},
                        {self.generate_pool_balance_chart()},
                        {self.generate_liquidity_density_chart()},
                        {self.generate_volume_chart()},
                        {self.generate_arb_profit_chart()},
                        {self.generate_pool_fees_chart()},
                        {self.generate_price_error_chart()}
                      ],
                      "columns": 2,
                      "data": {{"name": "data-09e2478ae15128cea7541a7e6262cbfe"}}
                    }}
                  ],
                  "resolve": {{"scale": {{"color": "independent"}}}},
                  "title": {{"text": "Summary Metrics", "fontSize": 16}}
                }},
                {self.generate_timeseries_section()}
              ],
              "resolve": {{"scale": {{"color": "independent"}}}},
              "$schema": "https://vega.github.io/schema/vega-lite/v5.16.3.json",
              "datasets": {{
                "data-09e2478ae15128cea7541a7e6262cbfe": {self.generate_summary_data()},
                "data-b494851b1f6188256da5f913a9436b80": {self.generate_timeseries_data()},
                "data-0f8e4b98424b62f3f82dc1a2298a3e11": {self.generate_price_error_data()},
                "data-de3d775f25859dd3a4bacfddf682eea1": [
                  {{"x": "A", "labels": "A"}},
                  {{"x": "fee", "labels": "fee"}}
                ],
                "data-02ee0ec22ef8ef732099c7bed2835f29": [
                  {{"color": "A", "labels": "A"}},
                  {{"color": "fee", "labels": "fee"}}
                ],
                "data-afa8dad1d7ddab0783c71f6c83c6cd56": [
                  {{"A": {self.params.A}, "labels": {self.params.A}}}
                ],
                "data-2f219ff108e149703953c4436710261d": [
                  {{"fee": {self.params.fee}, "labels": {self.params.fee}}}
                ],
                "data-4d71f46b9aefd1101b4723599b0c790a": [
                  {{"submetric": "pool_balance median", "labels": "Median"}},
                  {{"submetric": "pool_balance min", "labels": "Min"}}
                ],
                "data-f250ca5a7e483cd41a294ee460add125": [
                  {{"submetric": "liquidity_density median", "labels": "Median"}},
                  {{"submetric": "liquidity_density min", "labels": "Min"}}
                ]
              }}
            }}
            """
        except Exception as e:
            return f"Error generating JSON: {str(e)}"

    def generate_selectors(self):
        return """
        {
          "hconcat": [
            {
              "concat": [
                {
                  "data": {"name": "data-de3d775f25859dd3a4bacfddf682eea1"},
                  "mark": {"type": "rect"},
                  "encoding": {
                    "color": {"legend": null, "scale": {"scheme": "viridis"}},
                    "opacity": {
                      "condition": {"param": "param_251", "value": 1},
                      "value": 0.1
                    },
                    "y": {
                      "axis": {"orient": "left"},
                      "field": "labels",
                      "title": null,
                      "type": "ordinal"
                    }
                  },
                  "name": "view_251",
                  "title": "x"
                },
                {
                  "data": {"name": "data-02ee0ec22ef8ef732099c7bed2835f29"},
                  "mark": {"type": "rect"},
                  "encoding": {
                    "color": {"legend": null, "scale": {"scheme": "viridis"}},
                    "opacity": {
                      "condition": {"param": "param_252", "value": 1},
                      "value": 0.1
                    },
                    "y": {
                      "axis": {"orient": "left"},
                      "field": "labels",
                      "title": null,
                      "type": "ordinal"
                    }
                  },
                  "name": "view_252",
                  "title": "color"
                }
              ],
              "title": "Axis Selectors:"
            },
            {
              "concat": [
                {
                  "data": {"name": "data-afa8dad1d7ddab0783c71f6c83c6cd56"},
                  "mark": {"type": "rect"},
                  "encoding": {
                    "color": {
                      "field": "labels",
                      "legend": null,
                      "scale": {"scheme": "viridis"},
                      "type": "ordinal"
                    },
                    "opacity": {
                      "condition": {"param": "param_253", "value": 1},
                      "value": 0.1
                    },
                    "x": {
                      "axis": {"orient": "bottom"},
                      "field": "labels",
                      "title": null,
                      "type": "ordinal"
                    }
                  },
                  "name": "view_253",
                  "title": "A"
                },
                {
                  "data": {"name": "data-2f219ff108e149703953c4436710261d"},
                  "mark": {"type": "rect"},
                  "encoding": {
                    "color": {
                      "field": "labels",
                      "legend": null,
                      "scale": {"scheme": "viridis"},
                      "type": "ordinal"
                    },
                    "opacity": {
                      "condition": {"param": "param_254", "value": 1},
                      "value": 0.1
                    },
                    "x": {
                      "axis": {"orient": "bottom"},
                      "field": "labels",
                      "title": null,
                      "type": "ordinal"
                    }
                  },
                  "name": "view_254",
                  "title": "fee"
                }
              ],
              "resolve": {"scale": {"color": "independent"}},
              "title": "Toggle Filters:"
            }
          ]
        }
        """

    def generate_summary_metrics(self):
        return """
        {
          "mark": {"type": "line", "point": true},
          "encoding": {
            "color": {
              "field": "color",
              "scale": {"scheme": "viridis"},
              "title": null,
              "type": "ordinal"
            },
            "tooltip": [
              {
                "field": "pool_value_virtual annualized_returns",
                "title": "Annualized Returns (Virtual)",
                "type": "quantitative"
              },
              {"field": "A", "type": "quantitative"},
              {"field": "fee", "type": "quantitative"}
            ],
            "x": {
              "field": "x",
              "scale": {"zero": false},
              "title": null,
              "type": "quantitative"
            },
            "y": {
              "axis": {"format": "%"},
              "field": "pool_value_virtual annualized_returns",
              "scale": {"zero": false},
              "title": "Annualized Returns (Virtual)",
              "type": "quantitative"
            }
          },
          "name": "view_255",
          "title": "Annualized Returns (Virtual)",
          "transform": [
            {"calculate": "datum[param_251.x]", "as": "x"},
            {"calculate": "datum[param_252.color]", "as": "color"},
            {"filter": {"param": "param_253"}},
            {"filter": {"param": "param_254"}}
          ]
        }
        """

    def generate_timeseries_chart(self):
        return """
        {
          "mark": {"type": "line", "point": true},
          "encoding": {
            "color": {
              "field": "color",
              "scale": {"scheme": "viridis"},
              "title": null,
              "type": "ordinal"
            },
            "tooltip": [
              {
                "field": "pool_value annualized_returns",
                "title": "Annualized Returns (in USDC)",
                "type": "quantitative"
              },
              {"field": "A", "type": "quantitative"},
              {"field": "fee", "type": "quantitative"}
            ],
            "x": {
              "field": "x",
              "scale": {"zero": false},
              "title": null,
              "type": "quantitative"
            },
            "y": {
              "axis": {"format": "%"},
              "field": "pool_value annualized_returns",
              "scale": {"zero": false},
              "title": "Annualized Returns (in USDC)",
              "type": "quantitative"
            }
          },
          "name": "view_256",
          "title": "Annualized Returns (in USDC)",
          "transform": [
            {"calculate": "datum[param_251.x]", "as": "x"},
            {"calculate": "datum[param_252.color]", "as": "color"},
            {"filter": {"param": "param_253"}},
            {"filter": {"param": "param_254"}}
          ]
        }
        """

    def generate_pool_balance_chart(self):
        return """
        {
        "vconcat": [
            {
            "layer": [
                {
                "mark": {"type": "line", "point": true},
                "encoding": {
                    "color": {
                    "field": "color",
                    "scale": {"scheme": "viridis"},
                    "title": null,
                    "type": "ordinal"
                    },
                    "opacity": {
                    "condition": {
                        "test": "indexof(param_257.submetric, 'pool_balance median') != -1",
                        "value": 1
                    },
                    "value": 0
                    },
                    "tooltip": [
                    {
                        "field": "pool_balance median",
                        "title": "Median % Balanced",
                        "type": "quantitative"
                    },
                    {"field": "A", "type": "quantitative"},
                    {"field": "fee", "type": "quantitative"}
                    ],
                    "x": {
                    "field": "x",
                    "scale": {"zero": false},
                    "title": null,
                    "type": "quantitative"
                    },
                    "y": {
                    "axis": {"format": "%"},
                    "field": "pool_balance median",
                    "scale": {"zero": false},
                    "title": "% Balanced",
                    "type": "quantitative"
                    }
                },
                "name": "view_257",
                "title": "Pool Balance/Imbalance",
                "transform": [
                    {"calculate": "datum[param_251.x]", "as": "x"},
                    {"calculate": "datum[param_252.color]", "as": "color"},
                    {"filter": {"param": "param_253"}},
                    {"filter": {"param": "param_254"}}
                ]
                },
                {
                "mark": {"type": "line", "point": true},
                "encoding": {
                    "color": {
                    "field": "color",
                    "scale": {"scheme": "viridis"},
                    "title": null,
                    "type": "ordinal"
                    },
                    "opacity": {
                    "condition": {
                        "test": "indexof(param_257.submetric, 'pool_balance min') != -1",
                        "value": 1
                    },
                    "value": 0
                    },
                    "tooltip": [
                    {
                        "field": "pool_balance min",
                        "title": "Min % Balanced",
                        "type": "quantitative"
                    },
                    {"field": "A", "type": "quantitative"},
                    {"field": "fee", "type": "quantitative"}
                    ],
                    "x": {
                    "field": "x",
                    "scale": {"zero": false},
                    "title": null,
                    "type": "quantitative"
                    },
                    "y": {
                    "axis": {"format": "%"},
                    "field": "pool_balance min",
                    "scale": {"zero": false},
                    "title": "% Balanced",
                    "type": "quantitative"
                    }
                },
                "name": "view_258",
                "title": "Pool Balance/Imbalance",
                "transform": [
                    {"calculate": "datum[param_251.x]", "as": "x"},
                    {"calculate": "datum[param_252.color]", "as": "color"},
                    {"filter": {"param": "param_253"}},
                    {"filter": {"param": "param_254"}}
                ]
                }
            ],
            "data": {"name": "data-09e2478ae15128cea7541a7e6262cbfe"}
            },
            {
            "data": {"name": "data-4d71f46b9aefd1101b4723599b0c790a"},
            "mark": {"type": "rect"},
            "encoding": {
                "color": {"legend": null, "scale": {"scheme": "viridis"}},
                "opacity": {
                "condition": {"param": "param_257", "value": 1},
                "value": 0.1
                },
                "y": {
                "axis": {"orient": "right"},
                "field": "labels",
                "title": null,
                "type": "ordinal"
                }
            },
            "name": "view_259",
            "title": ""
            }
        ],
        "spacing": 2,
        "params": [
            {
            "name": "param_257",
            "select": {
                "type": "point",
                "fields": ["submetric"],
                "toggle": "true"
            },
            "bind": "legend"
            }
        ]
        }
        """

    def generate_liquidity_density_chart(self):
        return """
        {
          "vconcat": [
            {
              "layer": [
                {
                  "mark": {"type": "line", "point": true},
                  "encoding": {
                    "color": {
                      "field": "color",
                      "scale": {"scheme": "viridis"},
                      "title": null,
                      "type": "ordinal"
                    },
                    "opacity": {
                      "condition": {
                        "test": "indexof(param_260.submetric, 'liquidity_density median') != -1",
                        "value": 1
                      },
                      "value": 0
                    },
                    "tooltip": [
                      {
                        "field": "liquidity_density median",
                        "title": "Median Liquidity Density",
                        "type": "quantitative"
                      },
                      {"field": "A", "type": "quantitative"},
                      {"field": "fee", "type": "quantitative"}
                    ],
                    "x": {
                      "field": "x",
                      "scale": {"zero": false},
                      "title": null,
                      "type": "quantitative"
                    },
                    "y": {
                      "field": "liquidity_density median",
                      "scale": {"zero": false},
                      "title": "Liquidity Density",
                      "type": "quantitative"
                    }
                  },
                  "name": "view_260",
                  "title": "Liquidity Density",
                  "transform": [
                    {"calculate": "datum[param_251.x]", "as": "x"},
                    {"calculate": "datum[param_252.color]", "as": "color"},
                    {"filter": {"param": "param_253"}},
                    {"filter": {"param": "param_254"}}
                  ]
                },
                {
                  "mark": {"type": "line", "point": true},
                  "encoding": {
                    "color": {
                      "field": "color",
                      "scale": {"scheme": "viridis"},
                      "title": null,
                      "type": "ordinal"
                    },
                    "opacity": {
                      "condition": {
                        "test": "indexof(param_260.submetric, 'liquidity_density min') != -1",
                        "value": 1
                      },
                      "value": 0
                    },
                    "tooltip": [
                      {
                        "field": "liquidity_density min",
                        "title": "Min Liquidity Density",
                        "type": "quantitative"
                      },
                      {"field": "A", "type": "quantitative"},
                      {"field": "fee", "type": "quantitative"}
                    ],
                    "x": {
                      "field": "x",
                      "scale": {"zero": false},
                      "title": null,
                      "type": "quantitative"
                    },
                    "y": {
                      "field": "liquidity_density min",
                      "scale": {"zero": false},
                      "title": "Liquidity Density",
                      "type": "quantitative"
                    }
                  },
                  "name": "view_261",
                  "title": "Liquidity Density",
                  "transform": [
                    {"calculate": "datum[param_251.x]", "as": "x"},
                    {"calculate": "datum[param_252.color]", "as": "color"},
                    {"filter": {"param": "param_253"}},
                    {"filter": {"param": "param_254"}}
                  ]
                }
              ],
              "data": {"name": "data-09e2478ae15128cea7541a7e6262cbfe"}
            },
            {
              "data": {"name": "data-f250ca5a7e483cd41a294ee460add125"},
              "mark": {"type": "rect"},
              "encoding": {
                "color": {"legend": null, "scale": {"scheme": "viridis"}},
                "opacity": {
                  "condition": {"param": "param_260", "value": 1},
                  "value": 0.1
                },
                "y": {
                  "axis": {"orient": "right"},
                  "field": "labels",
                  "title": null,
                  "type": "ordinal"
                }
              },
              "name": "view_262",
              "title": ""
            }
          ],
          "spacing": 2
        }
        """

    def generate_volume_chart(self):
        return """
        {
          "mark": {"type": "line", "point": true},
          "encoding": {
            "color": {
              "field": "color",
              "scale": {"scheme": "viridis"},
              "title": null,
              "type": "ordinal"
            },
            "tooltip": [
              {
                "field": "pool_volume sum",
                "title": "Total Volume (of Any Coin)",
                "type": "quantitative"
              },
              {"field": "A", "type": "quantitative"},
              {"field": "fee", "type": "quantitative"}
            ],
            "x": {
              "field": "x",
              "scale": {"zero": false},
              "title": null,
              "type": "quantitative"
            },
            "y": {
              "field": "pool_volume sum",
              "scale": {"zero": false},
              "title": "Total Volume (of Any Coin)",
              "type": "quantitative"
            }
          },
          "name": "view_263",
          "title": "Total Volume (of Any Coin)",
          "transform": [
            {"calculate": "datum[param_251.x]", "as": "x"},
            {"calculate": "datum[param_252.color]", "as": "color"},
            {"filter": {"param": "param_253"}},
            {"filter": {"param": "param_254"}}
          ]
        }
        """

    def generate_arb_profit_chart(self):
        return """
        {
          "mark": {"type": "line", "point": true},
          "encoding": {
            "color": {
              "field": "color",
              "scale": {"scheme": "viridis"},
              "title": null,
              "type": "ordinal"
            },
            "tooltip": [
              {
                "field": "arb_profit sum",
                "title": "Total Arbitrageur Profit (in USDC)",
                "type": "quantitative"
              },
              {"field": "A", "type": "quantitative"},
              {"field": "fee", "type": "quantitative"}
            ],
            "x": {
              "field": "x",
              "scale": {"zero": false},
              "title": null,
              "type": "quantitative"
            },
            "y": {
              "field": "arb_profit sum",
              "scale": {"zero": false},
              "title": "Total Arbitrageur Profit (in USDC)",
              "type": "quantitative"
            }
          },
          "name": "view_264",
          "title": "Total Arbitrageur Profit (in USDC)",
          "transform": [
            {"calculate": "datum[param_251.x]", "as": "x"},
            {"calculate": "datum[param_252.color]", "as": "color"},
            {"filter": {"param": "param_253"}},
            {"filter": {"param": "param_254"}}
          ]
        }
        """

    def generate_pool_fees_chart(self):
        return """
        {
          "mark": {"type": "line", "point": true},
          "encoding": {
            "color": {
              "field": "color",
              "scale": {"scheme": "viridis"},
              "title": null,
              "type": "ordinal"
            },
            "tooltip": [
              {
                "field": "pool_fees sum",
                "title": "Total Pool Fees (in USDC)",
                "type": "quantitative"
              },
              {"field": "A", "type": "quantitative"},
              {"field": "fee", "type": "quantitative"}
            ],
            "x": {
              "field": "x",
              "scale": {"zero": false},
              "title": null,
              "type": "quantitative"
            },
            "y": {
              "field": "pool_fees sum",
              "scale": {"zero": false},
              "title": "Total Pool Fees (in USDC)",
              "type": "quantitative"
            }
          },
          "name": "view_265",
          "title": "Total Pool Fees (in USDC)",
          "transform": [
            {"calculate": "datum[param_251.x]", "as": "x"},
            {"calculate": "datum[param_252.color]", "as": "color"},
            {"filter": {"param": "param_253"}},
            {"filter": {"param": "param_254"}}
          ]
        }
        """

    def generate_price_error_chart(self):
        return """
        {
          "mark": {"type": "line", "point": true},
          "encoding": {
            "color": {
              "field": "color",
              "scale": {"scheme": "viridis"},
              "title": null,
              "type": "ordinal"
            },
            "tooltip": [
              {
                "field": "price_error median",
                "title": "Price Error (median)",
                "type": "quantitative"
              },
              {"field": "A", "type": "quantitative"},
              {"field": "fee", "type": "quantitative"}
            ],
            "x": {
              "field": "x",
              "scale": {"zero": false},
              "title": null,
              "type": "quantitative"
            },
            "y": {
              "field": "price_error median",
              "scale": {"zero": false},
              "title": "Price Error (median)",
              "type": "quantitative"
            }
          },
          "name": "view_266",
          "title": "Price Error (median)",
          "transform": [
            {"calculate": "datum[param_251.x]", "as": "x"},
            {"calculate": "datum[param_252.color]", "as": "color"},
            {"filter": {"param": "param_253"}},
            {"filter": {"param": "param_254"}}
          ]
        }
        """

    def generate_timeseries_section(self):
        return """
        {
          "vconcat": [
            {
              "hconcat": [
                {
                  "concat": [
                    {
                      "mark": {"type": "rect"},
                      "encoding": {
                        "color": {"legend": null, "scale": {"scheme": "viridis"}},
                        "opacity": {
                          "condition": {"param": "param_267", "value": 1},
                          "value": 0.1
                        },
                        "y": {
                          "axis": {"orient": "left"},
                          "field": "labels",
                          "title": null,
                          "type": "ordinal"
                        }
                      },
                      "name": "view_267",
                      "title": "color"
                    }
                  ],
                  "data": {"name": "data-02ee0ec22ef8ef732099c7bed2835f29"},
                  "title": "Axis Selectors:"
                },
                {
                  "concat": [
                    {
                      "data": {"name": "data-afa8dad1d7ddab0783c71f6c83c6cd56"},
                      "mark": {"type": "rect"},
                      "encoding": {
                        "color": {
                          "field": "labels",
                          "legend": null,
                          "scale": {"scheme": "viridis"},
                          "type": "ordinal"
                        },
                        "opacity": {
                          "condition": {"param": "param_268", "value": 1},
                          "value": 0.1
                        },
                        "x": {
                          "axis": {"orient": "bottom"},
                          "field": "labels",
                          "title": null,
                          "type": "ordinal"
                        }
                      },
                      "name": "view_268",
                      "title": "A"
                    },
                    {
                      "data": {"name": "data-2f219ff108e149703953c4436710261d"},
                      "mark": {"type": "rect"},
                      "encoding": {
                        "color": {
                          "field": "labels",
                          "legend": null,
                          "scale": {"scheme": "viridis"},
                          "type": "ordinal"
                        },
                        "opacity": {
                          "condition": {"param": "param_269", "value": 1},
                          "value": 0.1
                        },
                        "x": {
                          "axis": {"orient": "bottom"},
                          "field": "labels",
                          "title": null,
                          "type": "ordinal"
                        }
                      },
                      "name": "view_269",
                      "title": "fee"
                    }
                  ],
                  "resolve": {"scale": {"color": "independent"}},
                  "title": "Toggle Filters:"
                }
              ]
            },
            {
              "concat": [
                {
                  "mark": {"type": "line"},
                  "encoding": {
                    "color": {
                      "field": "color",
                      "scale": {"scheme": "viridis"},
                      "title": null,
                      "type": "ordinal"
                    },
                    "tooltip": [
                      {"field": "timestamp", "title": "Time", "type": "temporal"},
                      {
                        "field": "pool_value_virtual",
                        "title": "Pool Value (Virtual)",
                        "type": "quantitative"
                      },
                      {"field": "A", "type": "quantitative"},
                      {"field": "fee", "type": "quantitative"}
                    ],
                    "x": {"field": "timestamp", "title": null, "type": "temporal"},
                    "y": {
                      "field": "pool_value_virtual",
                      "scale": {"zero": false},
                      "title": "Pool Value (Virtual)",
                      "type": "quantitative"
                    }
                  },
                  "name": "view_270",
                  "title": "Pool Value (Virtual)",
                  "transform": [
                    {"calculate": "datum[param_267.color]", "as": "color"},
                    {"filter": {"param": "param_268"}},
                    {"filter": {"param": "param_269"}}
                  ]
                },
                {
                  "mark": {"type": "line"},
                  "encoding": {
                    "color": {
                      "field": "color",
                      "scale": {"scheme": "viridis"},
                      "title": null,
                      "type": "ordinal"
                    },
                    "tooltip": [
                      {"field": "timestamp", "title": "Time", "type": "temporal"},
                      {
                        "field": "pool_value",
                        "title": "Pool Value (in USDC)",
                        "type": "quantitative"
                      },
                      {"field": "A", "type": "quantitative"},
                      {"field": "fee", "type": "quantitative"}
                    ],
                    "x": {"field": "timestamp", "title": null, "type": "temporal"},
                    "y": {
                      "field": "pool_value",
                      "scale": {"zero": false},
                      "title": "Pool Value (in USDC)",
                      "type": "quantitative"
                    }
                  },
                  "name": "view_271",
                  "title": "Pool Value (in USDC)",
                  "transform": [
                    {"calculate": "datum[param_267.color]", "as": "color"},
                    {"filter": {"param": "param_268"}},
                    {"filter": {"param": "param_269"}}
                  ]
                },
                {
                  "mark": {"type": "line"},
                  "encoding": {
                    "color": {
                      "field": "color",
                      "scale": {"scheme": "viridis"},
                      "title": null,
                      "type": "ordinal"
                    },
                    "tooltip": [
                      {"field": "timestamp", "title": "Time", "type": "temporal"},
                      {
                        "field": "pool_balance",
                        "title": "% Balanced (Daily Median)",
                        "type": "quantitative"
                      },
                      {"field": "A", "type": "quantitative"},
                      {"field": "fee", "type": "quantitative"}
                    ],
                    "x": {"field": "timestamp", "title": null, "type": "temporal"},
                    "y": {
                      "axis": {"format": "%"},
                      "field": "pool_balance",
                      "scale": {"zero": false},
                      "title": "% Balanced (Daily Median)",
                      "type": "quantitative"
                    }
                  },
                  "name": "view_272",
                  "title": "Pool Balance/Imbalance",
                  "transform": [
                    {"calculate": "datum[param_267.color]", "as": "color"},
                    {"filter": {"param": "param_268"}},
                    {"filter": {"param": "param_269"}}
                  ]
                },
                {
                  "mark": {"type": "line"},
                  "encoding": {
                    "color": {
                      "field": "color",
                      "scale": {"scheme": "viridis"},
                      "title": null,
                      "type": "ordinal"
                    },
                    "tooltip": [
                      {"field": "timestamp", "title": "Time", "type": "temporal"},
                      {
                        "field": "liquidity_density",
                        "title": "Liquidity Density (Daily Median)",
                        "type": "quantitative"
                      },
                      {"field": "A", "type": "quantitative"},
                      {"field": "fee", "type": "quantitative"}
                    ],
                    "x": {"field": "timestamp", "title": null, "type": "temporal"},
                    "y": {
                      "field": "liquidity_density",
                      "scale": {"zero": false},
                      "title": "Liquidity Density (Daily Median)",
                      "type": "quantitative"
                    }
                  },
                  "name": "view_273",
                  "title": "Liquidity Density (Daily Median)",
                  "transform": [
                    {"calculate": "datum[param_267.color]", "as": "color"},
                    {"filter": {"param": "param_268"}},
                    {"filter": {"param": "param_269"}}
                  ]
                },
                {
                  "mark": {"type": "line"},
                  "encoding": {
                    "color": {
                      "field": "color",
                      "scale": {"scheme": "viridis"},
                      "title": null,
                      "type": "ordinal"
                    },
                    "tooltip": [
                      {"field": "timestamp", "title": "Time", "type": "temporal"},
                      {
                        "field": "pool_volume",
                        "title": "Daily Volume (of Any Coin)",
                        "type": "quantitative"
                      },
                      {"field": "A", "type": "quantitative"},
                      {"field": "fee", "type": "quantitative"}
                    ],
                    "x": {"field": "timestamp", "title": null, "type": "temporal"},
                    "y": {
                      "field": "pool_volume",
                      "scale": {"zero": false},
                      "title": "Daily Volume (of Any Coin)",
                      "type": "quantitative"
                    }
                  },
                  "name": "view_274",
                  "title": "Daily Volume (of Any Coin)",
                  "transform": [
                    {"calculate": "datum[param_267.color]", "as": "color"},
                    {"filter": {"param": "param_268"}},
                    {"filter": {"param": "param_269"}}
                  ]
                },
                {
                  "mark": {"type": "line"},
                  "encoding": {
                    "color": {
                      "field": "color",
                      "scale": {"scheme": "viridis"},
                      "title": null,
                      "type": "ordinal"
                    },
                    "tooltip": [
                      {"field": "timestamp", "title": "Time", "type": "temporal"},
                      {
                        "field": "arb_profit",
                        "title": "Daily Arbitrageur Profit (in USDC)",
                        "type": "quantitative"
                      },
                      {"field": "A", "type": "quantitative"},
                      {"field": "fee", "type": "quantitative"}
                    ],
                    "x": {"field": "timestamp", "title": null, "type": "temporal"},
                    "y": {
                      "field": "arb_profit",
                      "scale": {"zero": false},
                      "title": "Daily Arbitrageur Profit (in USDC)",
                      "type": "quantitative"
                    }
                  },
                  "name": "view_275",
                  "title": "Daily Arbitrageur Profit (in USDC)",
                  "transform": [
                    {"calculate": "datum[param_267.color]", "as": "color"},
                    {"filter": {"param": "param_268"}},
                    {"filter": {"param": "param_269"}}
                  ]
                },
                {
                  "mark": {"type": "line"},
                  "encoding": {
                    "color": {
                      "field": "color",
                      "scale": {"scheme": "viridis"},
                      "title": null,
                      "type": "ordinal"
                    },
                    "tooltip": [
                      {"field": "timestamp", "title": "Time", "type": "temporal"},
                      {
                        "field": "pool_fees",
                        "title": "Daily Pool Fees (in USDC)",
                        "type": "quantitative"
                      },
                      {"field": "A", "type": "quantitative"},
                      {"field": "fee", "type": "quantitative"}
                    ],
                    "x": {"field": "timestamp", "title": null, "type": "temporal"},
                    "y": {
                      "field": "pool_fees",
                      "scale": {"zero": false},
                      "title": "Daily Pool Fees (in USDC)",
                      "type": "quantitative"
                    }
                  },
                  "name": "view_276",
                  "title": "Daily Pool Fees (in USDC)",
                  "transform": [
                    {"calculate": "datum[param_267.color]", "as": "color"},
                    {"filter": {"param": "param_268"}},
                    {"filter": {"param": "param_269"}}
                  ]
                },
                {
                  "data": {"name": "data-0f8e4b98424b62f3f82dc1a2298a3e11"},
                  "mark": {"type": "line", "interpolate": "step-before"},
                  "encoding": {
                    "color": {
                      "field": "color",
                      "scale": {"scheme": "viridis"},
                      "title": null,
                      "type": "ordinal"
                    },
                    "tooltip": [
                      {
                        "field": "frequency",
                        "title": "Frequency",
                        "type": "quantitative"
                      },
                      {"field": "A", "type": "quantitative"},
                      {"field": "fee", "type": "quantitative"}
                    ],
                    "x": {
                      "field": "price_error",
                      "scale": {"clamp": true, "domain": [0, 0.05]},
                      "title": "Price Error (binned)",
                      "type": "quantitative"
                    },
                    "y": {
                      "axis": {"format": "%"},
                      "field": "frequency",
                      "scale": {"zero": true},
                      "title": "Frequency",
                      "type": "quantitative"
                    }
                  },
                  "name": "view_277",
                  "title": "Price Error",
                  "transform": [
                    {"calculate": "datum[param_267.color]", "as": "color"},
                    {"filter": {"param": "param_268"}},
                    {"filter": {"param": "param_269"}}
                  ]
                }
              ],
              "columns": 2,
              "data": {"name": "data-b494851b1f6188256da5f913a9436b80"}
            }
          ],
          "resolve": {"scale": {"color": "independent"}},
          "title": {"text": "Timeseries Data", "fontSize": 16}
        }
        """

    def generate_summary_data(self):
        return json.dumps(
            [
                {
                    "A": self.params.A,
                    "fee": self.params.fee,
                    "D": self.params.D,
                    "fee_mul": self.params.fee_mul,
                    "pool_value_virtual annualized_returns": self.summary_metrics.pool_value_virtual_annualized_returns,
                    "pool_value annualized_returns": self.summary_metrics.pool_value_annualized_returns,
                    "pool_balance median": self.summary_metrics.pool_balance_median,
                    "pool_balance min": self.summary_metrics.pool_balance_min,
                    "liquidity_density median": self.summary_metrics.liquidity_density_median,
                    "liquidity_density min": self.summary_metrics.liquidity_density_min,
                    "pool_volume sum": self.summary_metrics.pool_volume_sum,
                    "arb_profit sum": self.summary_metrics.arb_profit_sum,
                    "pool_fees sum": self.summary_metrics.pool_fees_sum,
                    "price_error median": self.summary_metrics.price_error_median,
                }
            ]
        )

    def generate_timeseries_data(self):
        return json.dumps(
            [
                {
                    "A": self.params.A,
                    "fee": self.params.fee,
                    "D": self.params.D,
                    "fee_mul": self.params.fee_mul,
                    "timestamp": data.timestamp.isoformat(),
                    "pool_value_virtual": data.pool_value_virtual,
                    "pool_value": data.pool_value,
                    "pool_balance": data.pool_balance,
                    "liquidity_density": data.liquidity_density,
                    "pool_volume": data.pool_volume,
                    "arb_profit": data.arb_profit,
                    "pool_fees": data.pool_fees,
                }
                for data in self.timeseries_data
            ]
        )

    def generate_price_error_data(self):
        return json.dumps(
            [
                {
                    "A": self.params.A,
                    "fee": self.params.fee,
                    "D": self.params.D,
                    "fee_mul": self.params.fee_mul,
                    "price_error": data.price_error,
                    "frequency": data.frequency,
                }
                for data in self.price_error_distribution
            ]
        )
