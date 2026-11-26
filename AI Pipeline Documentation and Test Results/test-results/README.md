# Zombie simulation conversion count test results

Both first implementations reported the expected conversion count in all five deterministic scenarios. Only the controlled implementation received the exact display label in advance.

| Scenario | Expected | Baseline actual | Count | Frozen check | Controlled actual | Count | Frozen check |
|---|---:|---:|---|---|---:|---|---|
| survivor | 0 | 0 | PASS | FAIL | 0 | PASS | PASS |
| death_without_turn | 0 | 0 | PASS | FAIL | 0 | PASS | PASS |
| successful_turn | 1 | 1 | PASS | FAIL | 1 | PASS | PASS |
| turned_then_died | 1 | 1 | PASS | FAIL | 1 | PASS | PASS |
| turns_across_visits | 2 | 2 | PASS | FAIL | 2 | PASS | PASS |

The count check reads the integer from either observed label. The frozen evaluator requires the exact label and expected count, and checks the per-visit states. All ten state histories matched. The baseline printed `Humans turned into zombies: 1` in the later-death case. The controlled version printed `Human-to-zombie conversions: 1`. The wording accounts for all five baseline failures.

## Evidence

- [Starting project](starting-results.json) — all five scenarios reached the expected states. The original report omitted the conversion line in every case.
- [Baseline first attempt replay](paired-run/baseline-replay.json) and [controlled first attempt replay](paired-run/controlled-replay.json) — rendered reports and expected and observed agent states for each visit.
- [Paired judgments](paired-run/comparison.json) — expected and observed counts plus both scores. A fresh replay reproduced these judgments.
- [Controlled first evaluation](controlled-first.json) and [controlled final verification](controlled-final.json) — both passed all five frozen checks. Neither candidate received a code correction.

The paired replay used seed 4242, one serial worker, and in-memory storage. These results cover the shared reporting path. Live database, GUI, and concurrent-worker behavior remain unverified. The publication copies omit the local project path from run metadata.
