"""
server/health.py - Turns a telemetry snapshot into a health report.

CHANGES IN THIS VERSION: new file (code 6).

A "health report" is:
    - score:      0-100, higher is healthier
    - status:     "healthy" / "warning" / "critical" (overall)
    - components: per-thing status (disk, ram, cpu, ...)
    - warnings:   plain-language sentences a human can act on

Everything here is RULES, not machine learning. That's deliberate for now:
rules are explainable ("disk is 91% full, over the 85% warning line"), easy to
trust, and need no training data. ML slots in later for the things rules can't
see (e.g. predicting SSD failure from SMART trends).

THRESHOLDS is the one thing you tune. Change a number, change the behaviour -
no other code needs touching.
"""

# Penalty subtracted from the 100-point score for each component's state.
WARN_PENALTY = 15
CRITICAL_PENALTY = 35

# The rules. For each metric: at what value is it a warning vs critical, and
# a template for the human-readable message. {value} is filled in.
THRESHOLDS = {
    "disk_used_percent": {
        "warn": 85,
        "critical": 95,
        "label": "Disk",
        "message": "Disk is {value}% full",
    },
    "ram_used_percent": {
        "warn": 90,
        "critical": 97,
        "label": "Memory",
        "message": "Memory is {value}% used",
    },
    "cpu_percent": {
        "warn": 92,
        "critical": 98,
        "label": "CPU",
        "message": "CPU load is {value}%",
    },
}


def _evaluate_metric(value, rule):
    """Decide a single metric's status against its rule.

    Returns (status, message_or_None). A None value (metric missing) is
    treated as 'ok' so we never punish a device for not reporting something.
    """
    if value is None:
        return "ok", None

    if value >= rule["critical"]:
        return "critical", rule["message"].format(value=value) + \
            f" (critical over {rule['critical']}%)"
    if value >= rule["warn"]:
        return "warning", rule["message"].format(value=value) + \
            f" (warning over {rule['warn']}%)"
    return "ok", None


def evaluate(snapshot):
    """Produce a full health report for one snapshot.

    Note on battery: psutil reports battery CHARGE level, not battery HEALTH
    (wear). Charge level isn't a health signal, so we don't score it here.
    Real battery health (design vs full-charge capacity) comes with richer
    telemetry later and will get its own rule then.
    """
    components = {}
    warnings = []
    score = 100

    for metric, rule in THRESHOLDS.items():
        value = snapshot.get(metric)
        status, message = _evaluate_metric(value, rule)

        components[rule["label"]] = {
            "status": status,
            "value": value,
        }

        if status == "warning":
            score -= WARN_PENALTY
            warnings.append(message)
        elif status == "critical":
            score -= CRITICAL_PENALTY
            warnings.append(message)

    score = max(0, score)  # never go below zero

    # Overall status is driven by the worst component.
    if any(c["status"] == "critical" for c in components.values()):
        overall = "critical"
    elif any(c["status"] == "warning" for c in components.values()):
        overall = "warning"
    else:
        overall = "healthy"

    return {
        "hostname": snapshot.get("hostname"),
        "score": score,
        "status": overall,
        "components": components,
        "warnings": warnings,
    }


if __name__ == "__main__":
    import json
    # Quick self-test with a made-up snapshot.
    demo = {
        "hostname": "test-machine",
        "disk_used_percent": 91,   # warning
        "ram_used_percent": 40,    # ok
        "cpu_percent": 99,         # critical
    }
    print(json.dumps(evaluate(demo), indent=2))