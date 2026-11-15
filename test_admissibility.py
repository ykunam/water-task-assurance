import itertools
import math
import unittest
from admissibility_audit import calibrate,allow,quantile,task_score


def e(s=0.,valid=True,realized=1):
    return dict(assessable=valid,realized=realized,hold_unmet_delta=s*.01,
        hold_tank_hours_delta=0.,whole_unmet_delta=0.,whole_tank_hours_delta=0.,
        terminal_unmet_delta=0.,terminal_storage_deficit=0.)


class CalibrationContractTests(unittest.TestCase):
    def test_invalid_eligible_outcome_is_not_excluded(self):
        self.assertEqual(task_score([dict(forecasts=[e()],actual=e(valid=False))])['score'],math.inf)
        self.assertEqual(task_score([dict(forecasts=[e()],actual=e(realized=0))])['score'],math.inf)

    def test_unavailable_candidates_cannot_inflate_the_score(self):
        rows=[dict(forecasts=[e(.2)],actual=e(.3)),dict(forecasts=[e(2.)],actual=e(100.))]
        self.assertAlmostEqual(task_score(rows)['score'],.1)
        self.assertEqual(task_score(rows)['eligible'],1)

    def test_empty_contexts_dilute_marginal_not_conditional_sample_size(self):
        tasks=[dict(task_id=str(i),candidates=[] if i<20 else [dict(forecasts=[e()],actual=e())]) for i in range(24)]
        self.assertEqual(calibrate(tasks)['margin'],0.)
        self.assertEqual(calibrate(tasks,opportunity_only=True)['margin'],math.inf)

    def test_rank_boundary_and_strict_acceptance(self):
        self.assertEqual(quantile([0.]*8)[0],math.inf)
        self.assertEqual(quantile([0.]*9)[0],0.)
        self.assertFalse(allow([e(.6)],.4));self.assertTrue(allow([e(.59)],.4))

    def test_simultaneous_bound_survives_any_candidate_order(self):
        forecasts=[[e(.1)],[e(.8)],[e(1.1)]];actual=[.3,1.,1.3];q=.2
        for order in itertools.permutations(range(3)):
            chosen=next((i for i in order if allow(forecasts[i],q)),None)
            self.assertIsNotNone(chosen);self.assertLess(actual[chosen],1)


if __name__=='__main__':unittest.main()
