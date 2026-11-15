import unittest
import numpy as np
import wntr
from followup_validation import states,profile_future


class FollowupInvariants(unittest.TestCase):
    def test_later_schedule_and_new_baseline_scales(self):
        selected=states()
        self.assertEqual(len(selected),48)
        self.assertEqual(len({s['task_id'] for s in selected}),48)
        self.assertTrue(all(s['hour']>240 and s['scale'] in [.95,1.05] for s in selected))
        self.assertTrue(all(len(s['hidden_profile'])==3 and all(.7<=f<=1.3 for f in s['hidden_profile']) for s in selected))
        self.assertEqual(states(),selected)

    def test_profile_preserves_prefix_and_negative_injections(self):
        w=wntr.network.WaterNetworkModel();w.options.time.pattern_timestep=3600
        w.add_pattern('native',[1.,1.2,.8,1.1]);w.add_reservoir('R',base_head=100)
        w.add_junction('J',base_demand=.01,demand_pattern='native',elevation=0)
        w.add_junction('I',base_demand=-.005,demand_pattern='native',elevation=0)
        j=w.get_node('J').demand_timeseries_list[0];inj=w.get_node('I').demand_timeseries_list[0]
        times=list(range(0,13*3600,3600));positive=[j.at(t) for t in times];negative=[inj.at(t) for t in times]
        profile_future(w,3*3600,12*3600,[.8,1.2,.9],4)
        for t,old in zip(times,positive):
            expected=1 if t<3*3600 else .8 if t<5*3600 else 1.2 if t<7*3600 else .9
            self.assertAlmostEqual(j.at(t),old*expected)
        self.assertEqual([inj.at(t) for t in times],negative)

    def test_hidden_profile_never_coincides_with_forecast_labels(self):
        self.assertTrue(all(s['hidden_factor'] not in [.85,1.,1.15] for s in states()))


if __name__=='__main__':unittest.main()
