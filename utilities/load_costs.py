# Modified from: https://github.com/PyPSA/pypsa-eur/blob/master/scripts/add_electricity.py

import pandas as pd
import yaml

def calculate_annuity(n, r):
    """
    Calculate the annuity factor for an asset with lifetime n years and.

    discount rate of r, e.g. annuity(20, 0.05) * 20 = 1.6
    """
    if isinstance(r, pd.Series):
        return pd.Series(1 / n, index=r.index).where(
            r == 0, r / (1.0 - 1.0 / (1.0 + r) ** n)
        )
    elif r > 0:
        return r / (1.0 - 1.0 / (1.0 + r) ** n)
    else:
        return 1 / n

def load_costs(tech_costs, config, Nyears=1.0):
    """
    Create and return a costs dataframe loaded from the tech_costs file
    config: a yaml file
    """
    # Read in costs from csv file
    costs = pd.read_csv(tech_costs, index_col=[0, 1]).sort_index()

    # Load config files
    with open(config, "r") as f:
        config = yaml.safe_load(f)

    # correct units to MW
    costs.loc[costs.unit.str.contains("/kW"), "value"] *= 1e3
    costs.unit = costs.unit.str.replace("/kW", "/MW")

    fill_values = config["fill_values"]
    costs = costs.value.unstack().fillna(fill_values)

    costs["capital_cost"] = (
        (
            calculate_annuity(costs["lifetime"], costs["discount rate"])
            + costs["FOM"] / 100.0
        )
        * costs["investment"]
        * Nyears
    )

    costs = costs.rename(columns={"CO2 intensity": "co2_emissions"})

    if "OCGT" in costs.index or "CCGT" in costs.index or "gas boiler steam" in costs.index:
        for tech in ["OCGT", "CCGT", "gas boiler steam"]:
            costs.at[tech, "fuel"] = costs.at["gas", "fuel"]
            costs.at[tech, "co2_emissions"] = costs.at["gas", "co2_emissions"] if "co2_emissions" in costs.index else 0.


    costs["marginal_cost"] = costs["VOM"] + costs["fuel"] / costs["efficiency"] if "fuel" in costs.columns else costs["VOM"]

    for attr in ("marginal_cost", "capital_cost"):
        overwrites = config.get(attr)
        if overwrites is not None:
            overwrites = pd.Series(overwrites)
            costs.loc[overwrites.index, attr] = overwrites

    return costs
