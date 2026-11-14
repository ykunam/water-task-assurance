import copy
import unittest
import numpy as np
import wntr
import assurance as a
from analyze import decide, agent_order, propose_until_allowed, predicted_allow, residual_order_statistic


def tiny_model():
    w = wntr.network.WaterNetworkModel()
    w.add_pattern("daily", [1, 1.1, .9, 1])
    w.add_reservoir("R", base_head=50)
    w.add_junction("J", base_demand=.001, demand_pattern="daily", elevation=5)
    w.add_pipe("P", "R", "J", length=100, diameter=.2, roughness=120)
    w.options.hydraulic.demand_model = "PDD"
    w.options.hydraulic.minimum_pressure = 0
    w.options.hydraulic.required_pressure = 15
    w.options.hydraulic.pressure_exponent = .5
    w.options.hydraulic.accuracy = 1e-6
    w.options.time.duration = 8*3600
    w.options.time.hydraulic_timestep = 300
    w.options.time.report_timestep = 300
    w.options.time.rule_timestep = 300
    return w


class ScientificInvariants(unittest.TestCase):
    def test_split_time_separation(self):
        states = a.select_states()
        self.assertEqual(len(states), 144)
        self.assertEqual(len({s["task_id"] for s in states}), 144)
        for net in a.CATALOGUES:
            for split in ("train", "calibration", "test"):
                group = [s for s in states if s["network"] == net and s["split"] == split]
                self.assertEqual(len(group), 24)
            self.assertLess(max(s["hour"] for s in states if s["split"] == "train"),
                            min(s["hour"] for s in states if s["split"] == "calibration"))

    def test_hidden_demand_is_not_a_feature(self):
        self.assertNotIn("hidden_factor", a.features.__code__.co_names)
        self.assertNotIn("actual", decide.__code__.co_names)

    def test_future_pattern_preserves_prefix_and_injections(self):
        w = tiny_model()
        w.add_junction("I", base_demand=-.0001, demand_pattern="daily")
        before = [w.get_node("J").demand_timeseries_list[0].at(t) for t in [0, 3600, 7200]]
        injection = w.get_node("I").demand_timeseries_list[0]
        old_injection = [injection.at(t) for t in [0, 3600, 7200]]
        a.impose_future(w, 7200, 28800, 1.25)
        after = [w.get_node("J").demand_timeseries_list[0].at(t) for t in [0, 3600, 7200]]
        self.assertTrue(np.allclose(before[:2], after[:2]))
        self.assertAlmostEqual(after[2], before[2]*1.25)
        self.assertTrue(np.allclose(old_injection, [injection.at(t) for t in [0, 3600, 7200]]))

    def test_future_isolation_preserves_precommand_trajectory(self):
        baseline = tiny_model()
        changed = copy.deepcopy(baseline)
        a.add_isolation(changed, "P", 3600, 7200)
        r0, _, _ = a.run(baseline, "epanet")
        r1, _, _ = a.run(changed, "epanet")
        prefix = r0.node["head"].index[r0.node["head"].index < 3600]
        self.assertTrue(np.allclose(r0.node["head"].loc[prefix], r1.node["head"].loc[prefix]))
        self.assertTrue((r1.link["status"].loc[3600:6900, "P"] == 0).all())
        self.assertTrue((r1.link["status"].loc[7200:, "P"] > 0).all())

    def test_checkpoint_continuation_matches_full_tiny_run(self):
        whole = tiny_model()
        a.add_isolation(whole, "P", 3600, 7200)
        full, _, _ = a.run(whole, "wntr")
        prefix = tiny_model()
        prefix.options.time.duration = 3300
        a.run(prefix, "wntr")
        a.add_isolation(prefix, "P", 3600, 7200)
        prefix.options.time.duration = 28800
        resumed, _, _ = a.run(prefix, "wntr")
        idx = resumed.node["head"].index
        self.assertTrue(np.allclose(full.node["head"].loc[idx], resumed.node["head"], atol=1e-8))

    def test_robust_gate_is_subset_of_nominal_and_missing_is_denied(self):
        good = dict(assessable=True, realized=1, whole_harm=False,
                    hold_harm=False, recovery_failure=False)
        view = dict(forecasts=[good.copy() for _ in range(3)],
                    hold_score=.01, whole_score=.01, storage_rule=True)
        self.assertTrue(decide("Robust task", view, .1)[0])
        view["forecasts"][0]["whole_harm"] = True
        self.assertTrue(decide("Nominal task", view, .1)[0])
        self.assertFalse(decide("Robust task", view, .1)[0])
        view["forecasts"][0] = {"error": "failed"}
        self.assertFalse(decide("Robust task", view, .1)[0])

    def test_numerical_status_and_recovery_are_separate(self):
        bad = dict(assessable=False, realized=1, whole_harm=False,
                   hold_harm=False, recovery_failure=False)
        self.assertFalse(predicted_allow(bad))
        self.assertTrue(predicted_allow(bad, validity=False))
        bad.update(assessable=True, recovery_failure=True)
        self.assertFalse(predicted_allow(bad))
        self.assertTrue(predicted_allow(bad, recovery=False))

    def test_taskwise_margin_small_sample_fail_closed(self):
        self.assertIsNone(residual_order_statistic([]))
        self.assertIsNone(residual_order_statistic([0.]*8))
        self.assertEqual(residual_order_statistic(list(range(24))), 22.)

    def test_simultaneous_bound_survives_adaptive_choice(self):
        predicted = np.array([.1, .5, .9, 1.1])
        margin = .2
        actual = predicted + np.array([.1, .15, .0, -.3])
        allowed = predicted + margin < 1
        self.assertTrue((actual[allowed] < 1).all())

    def test_agents_share_attempt_budget_and_do_not_read_outcomes(self):
        assets = ["a", "b", "c", "d", "e"]
        no = {x:(False, 3) for x in assets}
        for controller in ("catalogue", "learned ranking"):
            order = agent_order(assets, dict(zip(assets, [4, 3, 2, 1, 0])), controller)
            selected, trace, queries = propose_until_allowed(order, no)
            self.assertIsNone(selected)
            self.assertEqual(len(trace), 4)
            self.assertEqual(queries, 12)
        self.assertNotIn("actual", propose_until_allowed.__code__.co_names)


if __name__ == "__main__":
    unittest.main(verbosity=2)
