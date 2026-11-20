from __future__ import annotations
import json, math, platform, sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

@dataclass(frozen=True)
class ElectrolysisInputs:
    target_productivity_kg_day: float = 15000.0
    current_per_bath_A: float = 25000.0
    current_density_A_m2: float = 400.0
    current_efficiency: float = 0.95
    cycle_time_hours: float = 24.0
    u_bath_V: float = 0.35
    j_busbar_econ_A_mm2: float = 1.25
    rows_count: int = 2
    heat_loss_per_bath_W: float = 11500.0
    use_shortened_bath_3m: bool = False

def run_simulation(run_id: str, params: ElectrolysisInputs) -> dict:
    for k,v in asdict(params).items():
        if k == "use_shortened_bath_3m":
            if type(v) is not bool: raise ValueError("Boolean expected")
        elif type(v) not in (int,float) or not math.isfinite(v) or v <= 0: raise ValueError("Positive finite parameter required: "+k)
    if type(params.rows_count) is not int or params.current_efficiency > 1: raise ValueError("Invalid rows/efficiency")
    F = 96485.0
    M_cu = 63.54
    valency = 2.0
    cathode_area_double = 2.0
    w_bath = 1.2
    h_bath = 1.3
    rho_el = 1200.0
    cp_el = 3400.0
    t_in, t_bath = 60.0, 55.0

    t_sec = params.cycle_time_hours * 3600.0
    m_bath_day_kg = ((M_cu * params.current_per_bath_A * t_sec * params.current_efficiency) / (valency * F) / 1000.0) * (24.0 / params.cycle_time_hours)
    n_baths_exact = params.target_productivity_kg_day / m_bath_day_kg
    step_align = max(1, params.rows_count)
    n_baths_fact = int(math.ceil(n_baths_exact / step_align) * step_align)
    baths_per_row = n_baths_fact // params.rows_count

    total_cathode_area = params.current_per_bath_A / params.current_density_A_m2
    cathodes_per_bath = math.ceil(total_cathode_area / cathode_area_double)
    anodes_per_bath = cathodes_per_bath + 1
    l_bath_calc = round(((cathodes_per_bath + anodes_per_bath) * 0.08) + 0.24, 3)
    l_bath_used = 3.0 if params.use_shortened_bath_3m else l_bath_calc

    # Габариты цеха с шагом колонн 6 м
    length_theor = (baths_per_row * w_bath) + ((baths_per_row - 1) * 0.3) + 6.0
    length_fact = math.ceil(length_theor / 6.0) * 6.0
    width_theor = (params.rows_count * l_bath_used) + (4.0 if params.rows_count > 1 else 2.5) + 3.0
    width_fact = math.ceil(width_theor / 6.0) * 6.0
    area_fact_m2 = length_fact * width_fact

    # Тепловой баланс и гидравлика
    q_joule_W = params.current_per_bath_A * params.u_bath_V
    q_circ_needed_W = params.heat_loss_per_bath_W - q_joule_W
    if q_circ_needed_W > 0:
        g_circ = q_circ_needed_W / (cp_el * (t_in - t_bath))
        v_circ_bath_l_min = (g_circ * 60.0 / rho_el) * 1000.0
        thermal_mode = "heating_required"
    else:
        v_circ_bath_l_min = 0.0
        thermal_mode = "cooling_or_excess_joule_heat"
    v_circ_total_m3_h = (v_circ_bath_l_min * n_baths_fact * 60.0) / 1000.0

    # Энергетика и масса медных шин (плотность меди 8960 кг/м3, условная трасса 60 м на 2 полюса)
    u_series_V = (n_baths_fact * params.u_bath_V) * 1.1
    s_busbar_mm2 = params.current_per_bath_A / params.j_busbar_econ_A_mm2
    busbar_strips = math.ceil(s_busbar_mm2 / 1000.0)
    copper_busbar_mass_kg = round((s_busbar_mm2 * 1e-6) * 60.0 * 8960.0, 1)
    p_dc_kw = (params.current_per_bath_A * u_series_V) / 1000.0
    p_trans_kw = (p_dc_kw / 0.94) * 1.2
    daily_dc_energy_kwh = p_dc_kw * 24.0

    # Вентиляция (12-кратный воздухообмен при высоте зала 8.4 м)
    v_vent_m3_h = area_fact_m2 * 8.4 * 12.0

    return {
        "run_id": run_id,
        "code_version": "copper_model_v2.0",
        "geometry_feasible": l_bath_used >= l_bath_calc,
        "warnings": [] if l_bath_used >= l_bath_calc else ["Selected bath shorter than electrode package"],
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "executed",
        "environment": {
            "python_version": platform.python_version(),
            "platform": sys.platform,
        },
        "inputs": asdict(params),
        "outputs": {
            "m_bath_day_kg": round(m_bath_day_kg, 2),
            "n_baths_exact": round(n_baths_exact, 2),
            "n_baths_fact": n_baths_fact,
            "baths_per_row": baths_per_row,
            "cathodes_per_bath": cathodes_per_bath,
            "actual_current_density_A_m2": params.current_per_bath_A/(cathodes_per_bath*cathode_area_double),
            "l_bath_calc_m": l_bath_calc,
            "l_bath_used_m": l_bath_used,
            "building_length_fact_m": length_fact,
            "building_width_fact_m": width_fact,
            "area_fact_m2": area_fact_m2,
            "q_joule_W": round(q_joule_W, 1),
            "q_circ_needed_W": round(q_circ_needed_W, 1),
            "thermal_mode": thermal_mode,
            "v_circ_total_m3_h": round(v_circ_total_m3_h, 2),
            "u_series_V": round(u_series_V, 2),
            "s_busbar_mm2": round(s_busbar_mm2, 1),
            "busbar_strips_100x10": busbar_strips,
            "copper_busbar_mass_kg": copper_busbar_mass_kg,
            "p_dc_kw": round(p_dc_kw, 2),
            "p_trans_kw": round(p_trans_kw, 2),
            "daily_dc_energy_kwh": round(daily_dc_energy_kwh, 1),
            "v_vent_m3_h": round(v_vent_m3_h, 1),
        },
    }

if __name__ == "__main__":
    data=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig")) if len(sys.argv)>1 else {}
    print(json.dumps(run_simulation("research",ElectrolysisInputs(**data)),ensure_ascii=False,indent=2))
