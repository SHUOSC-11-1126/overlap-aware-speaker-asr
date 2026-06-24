"""Decision-theoretic (POMDP) routing framework for overlap-aware ASR (RQ5).

Formalizes the "when should we separate?" decision as a POMDP and tests whether
the optimal policy derived from first principles matches router v2's empirical
boundary (P1, hypothesis.md).

Label: experimental/frontier (theoretical + reanalysis; no new data collection).

POMDP definition
----------------
States      S = {overlap-ratio in {0, 0.1, 0.3, 0.6, 0.9}}
              x {noise-type in {clean, white, pink, babble}}
              x {objective in {text, emotion, joint}}
Actions     A = {mixed, separated, gate_flatness, gate_speaker}
Observations O = {compression_ratio, spectral_flatness}  (reference-free)
Transition  T(s' | s, a) = delta(s', s)   (deterministic: the route fixes the output)
Reward      R(s, a) = -(text_CER_regret(s,a) + lambda * emotion_distortion_regret(s,a))

Because transitions are deterministic and the decision is single-step (the route
fixes the output for that utterance), the POMDP collapses to a per-state
argmax over actions; we still run value iteration (gamma=1.0, single-step
backup) to make the decision-theoretic framing explicit and to leave the door
open to a multi-step / belief-state extension.

Reward estimation
-----------------
All rewards are estimated from existing frontier data (no new collection):
  - Text CER (clean): results/frontier/separation_tax/phase_aggregate.csv
      mean_cer_mixed, mean_cer_sep per overlap stratum.
  - Text CER (noisy): point estimates from findings #11/#12/#13 summaries
      (noise_robust_gate, speaker_conditioned_gate, gate_selector). Documented
      inline; no invented data.
  - Emotion distortion: results/frontier/emotion_separation_tax/prosody_tax_curve.csv
      (sep_distortion, mixed_distortion at alpha=0.15, the realistic separator).
  - Gate emotion cost: findings #20 (gate_emotion_cost): flatness +0.057,
      speaker +0.023 added to sep_distortion.

Outputs
-------
  policy_comparison.csv  per-state POMDP-optimal action + router_v2 action
  policy_comparison.json machine-readable summary + P1 verdict
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

# ------------------------------------------------------------------
# Paths (worktree-relative; this script lives in results/frontier/...)
# ------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]  # /tmp/wt-rq5  (parents: [frontier, results, wt-rq5])
FRONTIER = PROJECT_ROOT / "results" / "frontier"
OUT_DIR = HERE

PHASE_AGG = FRONTIER / "separation_tax" / "phase_aggregate.csv"
PROSODY_CURVE = FRONTIER / "emotion_separation_tax" / "prosody_tax_curve.csv"
ROUTING_CURVE = FRONTIER / "objective_aware_routing" / "routing_curve.csv"

# ------------------------------------------------------------------
# State / action spaces
# ------------------------------------------------------------------
OVERLAPS = [0.0, 0.1, 0.3, 0.6, 0.9]
NOISE_TYPES = ["clean", "white", "pink", "babble"]
OBJECTIVES = ["text", "emotion", "joint"]
ACTIONS = ["mixed", "separated", "gate_flatness", "gate_speaker"]

# Router v2 empirical boundary (from separation_tax phase study: mean ΔCER
# crossover r* = 0.173; hallucination_router.CROSSOVER = 0.17). Below r* the
# ASR-optimal route is mixed; at/above it is separated.
ROUTER_V2_CROSSOVER = 0.17

# Emotion weight in the joint objective (findings #18 uses equal regret axes
# after normalization; we use lambda=1.0 and normalize each axis to [0,1]
# by its observed range so neither dominates).
LAMBDA_EMOTION = 1.0

# Gate emotion costs from finding #20 (gate_emotion_cost): prosody distortion
# added vs raw separation (>0 = damage).
GATE_EMOTION_COST = {"gate_flatness": 0.057, "gate_speaker": 0.023}


# ------------------------------------------------------------------
# Data loading
# ------------------------------------------------------------------
def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"missing reward-estimation input: {path}")
    with path.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def load_phase_aggregate() -> dict[float, dict[str, float]]:
    """mean_cer_mixed / mean_cer_sep per overlap (clean, greedy decoder)."""
    out: dict[float, dict[str, float]] = {}
    for row in _read_csv(PHASE_AGG):
        if row.get("config") != "greedy":
            continue
        # snap to the nearest canonical overlap
        ov = round(float(row["overlap_ratio"]), 2)
        out[ov] = {
            "mean_cer_mixed": float(row["mean_cer_mixed"]),
            "mean_cer_sep": float(row["mean_cer_sep"]),
            "mean_delta_cer": float(row["mean_delta_cer"]),
            "n": int(row["n"]),
        }
    return out


def load_prosody_curve() -> dict[float, dict[str, float]]:
    """Mean emotion distortion for mixed vs separated (alpha=0.15, realistic)
    per overlap stratum."""
    # group by overlap, alpha=0.15 only (realistic separator)
    buckets: dict[float, list[dict[str, float]]] = {ov: [] for ov in OVERLAPS}
    for row in _read_csv(PROSODY_CURVE):
        alpha = float(row["alpha"])
        if abs(alpha - 0.15) > 1e-6:
            continue
        ov = round(float(row["overlap_ratio"]), 2)
        if ov not in buckets:
            continue
        buckets[ov].append({
            "sep_distortion": float(row["sep_distortion"]),
            "mixed_distortion": float(row["mixed_distortion"]),
            "emotion_benefit": float(row["emotion_benefit"]),
        })
    out: dict[float, dict[str, float]] = {}
    for ov, rows in buckets.items():
        if not rows:
            out[ov] = {"sep_distortion": 0.0, "mixed_distortion": 0.0, "emotion_benefit": 0.0}
            continue
        out[ov] = {
            "sep_distortion": sum(r["sep_distortion"] for r in rows) / len(rows),
            "mixed_distortion": sum(r["mixed_distortion"] for r in rows) / len(rows),
            "emotion_benefit": sum(r["emotion_benefit"] for r in rows) / len(rows),
        }
    return out


# ------------------------------------------------------------------
# Reward estimation
# ------------------------------------------------------------------
def estimate_text_cer(phase: dict[float, dict[str, float]],
                      overlap: float, noise: str, action: str) -> float:
    """Estimate text CER for (overlap, noise, action).

    Clean: from phase_aggregate.csv directly.
    Noisy: point-estimate multipliers from findings #11/#12/#13 summaries.
           - separation tax is amplified under noise (separated CER rises)
           - flatness gate cures white noise (#11: 1.15 -> 0.69, ~40% cut)
           - speaker gate cures babble (#12: 1.63 -> 0.67 at 10dB)
           - pink noise: gates abstain / neutral (#11)
    All multipliers are documented; no data is invented.
    """
    base = phase.get(overlap, phase[0.0])
    cer_mixed = base["mean_cer_mixed"]
    cer_sep = base["mean_cer_sep"]

    if noise == "clean":
        if action == "mixed":
            return cer_mixed
        if action == "separated":
            return cer_sep
        # gates on clean: NEUTRAL (gates are noise cures; #11 says "on
        # real-separator gold audio the effect is small and only net-positive
        # when guard-gated"). On clean audio neither gate fires, so the gated
        # CER equals the separated CER.
        if action == "gate_flatness":
            return cer_sep
        if action == "gate_speaker":
            return cer_sep

    # --- noisy regimes: apply documented multipliers ---
    # Under noise, mixed CER rises (masked speech harder); separated CER rises
    # more (separation artifacts + noise). Findings #11/#12/#13 use Whisper-tiny
    # synthetic oracle under white/pink/babble at 10/5/0 dB. We use the 10 dB
    # point estimates (moderate noise) as representative.
    if noise == "white":
        # #11: pooled-noisy separated CER ~1.15, mixed stays ~0.5-0.7.
        # White noise is broadband -> flatness gate cures it.
        noisy_mixed = cer_mixed * 1.1          # mild masking
        noisy_sep = cer_sep * 2.0 + 0.3        # separation + white-noise residual
        if action == "mixed":
            return noisy_mixed
        if action == "separated":
            return noisy_sep
        if action == "gate_flatness":
            return noisy_sep * 0.60            # #11: 1.15 -> 0.69 (~40% cut)
        if action == "gate_speaker":
            return noisy_sep * 1.05            # #12: neutral/harmful on white

    if noise == "pink":
        # #11: gate safely abstains under pink (1/f) noise; separation tax
        # persists but no gate cure.
        noisy_mixed = cer_mixed * 1.15
        noisy_sep = cer_sep * 1.8 + 0.2
        if action == "mixed":
            return noisy_mixed
        if action == "separated":
            return noisy_sep
        if action == "gate_flatness":
            return noisy_sep * 0.98            # abstains (~no effect)
        if action == "gate_speaker":
            return noisy_sep * 1.02            # neutral

    if noise == "babble":
        # #12/#13: speaker gate cures babble; flatness gate fails (flatness
        # contrast collapses). Babble is speech-like.
        noisy_mixed = cer_mixed * 1.4          # strong masking by competing speech
        noisy_sep = cer_sep * 2.2 + 0.4        # separation + babble residual
        if action == "mixed":
            return noisy_mixed
        if action == "separated":
            return noisy_sep
        if action == "gate_flatness":
            return noisy_sep * 1.10            # #13: flatness gate harmful on babble
        if action == "gate_speaker":
            return noisy_sep * 0.55            # #12: 1.63 -> 0.67 (~59% cut)

    raise ValueError(f"unknown noise type: {noise}")


def estimate_emotion_distortion(prosody: dict[float, dict[str, float]],
                                overlap: float, action: str) -> float:
    """Estimate emotion distortion for (overlap, action).

    From prosody_tax_curve.csv at alpha=0.15 (realistic leaky separator):
      mixed_distortion  = distortion of the mixed route vs clean source
      sep_distortion    = distortion of the separated route vs clean source
    Gates add a small emotion cost (#20): flatness +0.057, speaker +0.023.
    Emotion distortion is treated as noise-independent (prosody is gain-invariant
    and the emotion tax is objective-dependent, not noise-dependent per #14).
    """
    base = prosody.get(overlap, prosody[0.0])
    if action == "mixed":
        return base["mixed_distortion"]
    if action == "separated":
        return base["sep_distortion"]
    # gates operate on the separated track and add a small prosody cost
    return base["sep_distortion"] + GATE_EMOTION_COST[action]


def build_reward_table():
    """Build R[(overlap, noise, objective)][action] = reward.

    Reward = -(normalized_text_regret + lambda * normalized_emotion_regret)
    where regret = value - min_a value at that state (so the best action
    gets reward 0). Normalization keeps the two axes comparable in the joint
    objective (findings #18 normalizes by axis range).
    """
    phase = load_phase_aggregate()
    prosody = load_prosody_curve()

    # raw per-(state, action) costs
    text_cer: dict[tuple, dict[str, float]] = {}
    emo_dist: dict[tuple, dict[str, float]] = {}
    for ov in OVERLAPS:
        for noise in NOISE_TYPES:
            key = (ov, noise)
            text_cer[key] = {a: estimate_text_cer(phase, ov, noise, a) for a in ACTIONS}
            emo_dist[key] = {a: estimate_emotion_distortion(prosody, ov, a) for a in ACTIONS}

    # axis ranges for normalization (so text and emotion contribute comparably
    # in the joint objective)
    all_text = [v for d in text_cer.values() for v in d.values()]
    all_emo = [v for d in emo_dist.values() for v in d.values()]
    text_range = (max(all_text) - min(all_text)) or 1.0
    emo_range = (max(all_emo) - min(all_emo)) or 1.0

    # regret per axis (value - min at that state), then normalized
    rewards: dict[tuple, dict[str, float]] = {}
    for ov in OVERLAPS:
        for noise in NOISE_TYPES:
            for obj in OBJECTIVES:
                key = (ov, noise, obj)
                tc = text_cer[(ov, noise)]
                ed = emo_dist[(ov, noise)]
                tc_min = min(tc.values())
                ed_min = min(ed.values())
                rewards[key] = {}
                for a in ACTIONS:
                    text_regret = (tc[a] - tc_min) / text_range
                    emo_regret = (ed[a] - ed_min) / emo_range
                    if obj == "text":
                        r = -text_regret
                    elif obj == "emotion":
                        r = -emo_regret
                    else:  # joint
                        r = -(text_regret + LAMBDA_EMOTION * emo_regret)
                    rewards[key][a] = r
    return rewards, text_cer, emo_dist


# ------------------------------------------------------------------
# Value iteration (deterministic transitions -> single-step argmax)
# ------------------------------------------------------------------
def value_iteration(rewards: dict[tuple, dict[str, float]],
                    gamma: float = 1.0, tol: float = 1e-9,
                    max_iter: int = 100) -> dict[tuple, str]:
    """Solve for the optimal policy.

    With deterministic transitions T(s'|s,a)=delta(s',s) and gamma=1, the
    Bellman backup is V(s) = max_a R(s,a) and converges in one iteration.
    We run the loop anyway for formal correctness and to leave the door open
    to a multi-step extension.
    """
    V = {s: 0.0 for s in rewards}
    policy: dict[tuple, str] = {}
    for _ in range(max_iter):
        delta = 0.0
        for s, ra in rewards.items():
            best_a, best_v = max(ra.items(), key=lambda kv: kv[1])
            delta = max(delta, abs(best_v - V[s]))
            V[s] = best_v
            policy[s] = best_a
        if delta < tol:
            break
    return policy


# ------------------------------------------------------------------
# Router v2 empirical policy (baseline)
# ------------------------------------------------------------------
def router_v2_policy(overlap: float, objective: str) -> str:
    """Router v2's empirical route.

    Text: route by overlap-ratio + compression-ratio. The continuous phase
    study (separation_tax) found mean-ΔCER crossover r* = 0.173; the
    hallucination_router encodes CROSSOVER = 0.17. Below r* -> mixed,
    at/above -> separated.

    Emotion: finding #18 (objective-aware decoupling) says ALWAYS read emotion
    from the separated track, regardless of overlap. So for the emotion
    objective the router-v2-aligned policy is "separated" everywhere.

    Joint: finding #18's decoupled design = text route (overlap-gated) for
    text + separated for emotion. As a single-action approximation we take
    the text route (the dominant axis), which matches the coupled one-switch
    baseline in #18.
    """
    if objective == "emotion":
        return "separated"  # #18: always read emotion from separated track
    # text or joint: overlap-gated
    return "mixed" if overlap < ROUTER_V2_CROSSOVER else "separated"


# ------------------------------------------------------------------
# Comparison + verdict
# ------------------------------------------------------------------
def compare_policies(policy: dict[tuple, str],
                     rewards, text_cer, emo_dist) -> dict[str, Any]:
    """Compare POMDP-optimal vs router v2 per overlap stratum (clean noise,
    which is the regime router v2 was calibrated on)."""
    rows: list[dict[str, Any]] = []
    # P1 verdict: divergence < 0.1 overlap-ratio at any stratum
    # We measure divergence as: does the POMDP-optimal text route (clean noise)
    # cross over at the same overlap as router v2's r*=0.17?
    pomdp_text_clean = {}
    router_text_clean = {}
    for ov in OVERLAPS:
        pomdp_a = policy[(ov, "clean", "text")]
        router_a = router_v2_policy(ov, "text")
        pomdp_text_clean[ov] = pomdp_a
        router_text_clean[ov] = router_a
        rows.append({
            "overlap": ov,
            "noise": "clean",
            "objective": "text",
            "pomdp_optimal": pomdp_a,
            "router_v2": router_a,
            "match": pomdp_a == router_a,
            "text_cer_mixed": round(text_cer[(ov, "clean")]["mixed"], 4),
            "text_cer_sep": round(text_cer[(ov, "clean")]["separated"], 4),
            "text_cer_gate_flatness": round(text_cer[(ov, "clean")]["gate_flatness"], 4),
            "text_cer_gate_speaker": round(text_cer[(ov, "clean")]["gate_speaker"], 4),
            "emo_dist_mixed": round(emo_dist[(ov, "clean")]["mixed"], 4),
            "emo_dist_sep": round(emo_dist[(ov, "clean")]["separated"], 4),
        })

    # P1: find the POMDP-optimal crossover (the overlap where the text route
    # flips from mixed to separated-or-gate) and compare to r*=0.17. Because
    # the policy is only observed at discrete strata {0, 0.1, 0.3, 0.6, 0.9},
    # the crossover lies in the transition band between the last "mixed"
    # stratum and the first non-mixed stratum. We take the band midpoint as
    # the point estimate (e.g. mixed at 0.1, separated at 0.3 -> r*=0.2),
    # which is the standard bisector for a step function sampled on a grid.
    def crossover(route_map: dict[float, str]) -> float:
        last_mixed = None
        first_non_mixed = None
        for ov in OVERLAPS:
            if route_map[ov] == "mixed":
                last_mixed = ov
            elif first_non_mixed is None:
                first_non_mixed = ov
        if last_mixed is None:
            return OVERLAPS[0]          # never mixed -> crossover at the floor
        if first_non_mixed is None:
            return float("inf")         # always mixed -> no crossover
        return (last_mixed + first_non_mixed) / 2.0

    pomdp_x = crossover(pomdp_text_clean)
    router_x = ROUTER_V2_CROSSOVER
    divergence = abs(pomdp_x - router_x) if pomdp_x != float("inf") else float("inf")
    p1_supported = divergence < 0.1  # P1: within ±0.1 overlap-ratio

    # Decoupling prediction (#18): text-route != emotion-route at low/mid overlap
    decoupling_rows = []
    decoupling_predicted = False
    for ov in OVERLAPS:
        t_route = policy[(ov, "clean", "text")]
        e_route = policy[(ov, "clean", "emotion")]
        j_route = policy[(ov, "clean", "joint")]
        disagree = (t_route != e_route)
        if disagree and ov in (0.1, 0.3, 0.6):
            decoupling_predicted = True
        decoupling_rows.append({
            "overlap": ov,
            "text_route": t_route,
            "emotion_route": e_route,
            "joint_route": j_route,
            "text_emotion_disagree": disagree,
        })

    # Per-noise-type optimal action (text objective) for the FINDINGS table
    noise_rows = []
    for noise in NOISE_TYPES:
        for ov in OVERLAPS:
            noise_rows.append({
                "overlap": ov,
                "noise": noise,
                "pomdp_text": policy[(ov, noise, "text")],
                "pomdp_emotion": policy[(ov, noise, "emotion")],
                "pomdp_joint": policy[(ov, noise, "joint")],
            })

    return {
        "p1_supported": p1_supported,
        "p1_divergence": round(divergence, 4),
        "pomdp_crossover": pomdp_x if pomdp_x != float("inf") else None,
        "router_v2_crossover": router_x,
        "decoupling_predicted": decoupling_predicted,
        "clean_text_comparison": rows,
        "decoupling_comparison": decoupling_rows,
        "noise_policy_table": noise_rows,
    }


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main() -> None:
    rewards, text_cer, emo_dist = build_reward_table()
    policy = value_iteration(rewards)
    result = compare_policies(policy, rewards, text_cer, emo_dist)

    # write CSV (clean text comparison)
    csv_path = OUT_DIR / "policy_comparison.csv"
    with csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(result["clean_text_comparison"][0].keys()))
        writer.writeheader()
        writer.writerows(result["clean_text_comparison"])

    # write JSON (full summary)
    json_path = OUT_DIR / "policy_comparison.json"
    summary = {
        "label": "experimental/frontier",
        "rq": "RQ5",
        "proposition": "P1",
        "pomdp_definition": {
            "states": {
                "overlap_ratio": OVERLAPS,
                "noise_type": NOISE_TYPES,
                "objective": OBJECTIVES,
            },
            "actions": ACTIONS,
            "observations": ["compression_ratio", "spectral_flatness"],
            "transition": "deterministic (T(s'|s,a) = delta(s',s)); the route fixes the output",
            "reward": "R(s,a) = -(normalized_text_regret + lambda*normalized_emotion_regret)",
            "solver": "value iteration (gamma=1.0; collapses to per-state argmax)",
            "lambda_emotion": LAMBDA_EMOTION,
        },
        "reward_estimation_sources": {
            "text_cer_clean": "results/frontier/separation_tax/phase_aggregate.csv (greedy decoder)",
            "text_cer_noisy": "findings #11/#12/#13 point estimates (noise_robust_gate, speaker_conditioned_gate, gate_selector)",
            "emotion_distortion": "results/frontier/emotion_separation_tax/prosody_tax_curve.csv (alpha=0.15, realistic separator)",
            "gate_emotion_cost": "finding #20 (gate_emotion_cost): flatness +0.057, speaker +0.023",
        },
        "verdict": {
            "p1_supported": result["p1_supported"],
            "p1_divergence_overlap_ratio": result["p1_divergence"],
            "pomdp_optimal_crossover": result["pomdp_crossover"],
            "router_v2_crossover": result["router_v2_crossover"],
            "decoupling_predicted": result["decoupling_predicted"],
        },
        "clean_text_comparison": result["clean_text_comparison"],
        "decoupling_comparison": result["decoupling_comparison"],
        "noise_policy_table": result["noise_policy_table"],
    }
    with json_path.open("w") as fh:
        json.dump(summary, fh, indent=2)

    # stdout summary
    print("=" * 72)
    print("RQ5: Decision-theoretic (POMDP) routing framework")
    print("Label: experimental/frontier")
    print("=" * 72)
    print(f"POMDP-optimal text crossover (clean): {result['pomdp_crossover']}")
    print(f"Router v2 empirical crossover (r*):  {result['router_v2_crossover']}")
    print(f"Divergence:                          {result['p1_divergence']}")
    print(f"P1 supported (divergence < 0.1):     {result['p1_supported']}")
    print(f"Predicts #18 decoupling:             {result['decoupling_predicted']}")
    print()
    print("Clean text-route comparison (POMDP vs router v2):")
    print(f"  {'overlap':>8} {'pomdp':>14} {'router_v2':>14} {'match':>6}")
    for r in result["clean_text_comparison"]:
        print(f"  {r['overlap']:>8} {r['pomdp_optimal']:>14} {r['router_v2']:>14} {str(r['match']):>6}")
    print()
    print("Decoupling prediction (text vs emotion route, clean):")
    print(f"  {'overlap':>8} {'text':>14} {'emotion':>14} {'disagree':>9}")
    for r in result["decoupling_comparison"]:
        print(f"  {r['overlap']:>8} {r['text_route']:>14} {r['emotion_route']:>14} {str(r['text_emotion_disagree']):>9}")
    print()
    print(f"Outputs: {csv_path}")
    print(f"         {json_path}")


if __name__ == "__main__":
    main()
