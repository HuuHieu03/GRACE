"""Adapters for actual stored experiment records; never fabricate missing raw."""


def normalize_records(data, condition="original", arm=None):
    if isinstance(data, list):
        rows = data
    elif "detailed_samples" in data:
        rows = []
        for r in data["detailed_samples"]:
            for suffix, name in [("a", "original"), ("b", "label_flip"), ("c", "repeat_original")]:
                if "pred_" + suffix not in r:
                    continue
                raw_key = "raw_resp_" + suffix
                rows.append({**r, "id": str(r["target_id"]), "arm": "b2", "condition": name,
                             "prediction": r["pred_" + suffix], "is_valid": r["valid_" + suffix],
                             "llm_raw_response": r.get(raw_key), "raw_response_available": raw_key in r})
    elif "detailed_records_b3" in data:
        rows = []
        for field, method in [("detailed_records_b2", "b2"), ("detailed_records_b3", "b3")]:
            for r in data.get(field, []):
                conditions = [("pred_a", "valid_a", "raw_resp_a", "original"),
                              ("pred_b_inverted", "valid_b", "raw_resp_b", "order_swap"),
                              ("pred_c_repeated", "valid_c", "raw_resp_c", "repeat_original")]
                if method == "b2" and "pred" in r:
                    conditions = [("pred", "valid", "llm_raw_response", "original")]
                for pk, vk, rk, name in conditions:
                    if pk not in r:
                        continue
                    rows.append({**r, "id": str(r["target_id"]), "arm": method, "condition": name,
                                 "prediction": r[pk], "is_valid": r.get(vk, r[pk] is not None),
                                 "llm_raw_response": r.get(rk), "raw_response_available": rk in r})
    elif isinstance(data, dict):
        found = next((k for k in ["records", "detailed_predictions", "results", "reparsed_records"] if k in data), None)
        if found is None:
            raise ValueError("Unsupported result schema; aggregate metrics are not per-ID predictions")
        rows = data[found]
    else:
        raise ValueError("Unsupported experiment data")
    result = []
    seen = set()
    for r in rows:
        if r.get("_type") in ("checkpoint_metadata", "event"):
            continue
        if condition is not None and r.get("condition", "original") != condition:
            continue
        if arm is not None and r.get("arm") != arm:
            continue
        row = dict(r)
        if isinstance(row.get("is_valid"), str):
            if row["is_valid"].lower() not in ("true", "false"):
                raise ValueError("Invalid CSV validity flag")
            row["is_valid"] = row["is_valid"].lower() == "true"
        row["id"] = str(r["id"]) if r.get("id") is not None else None
        key = (row["id"], row.get("arm"), row.get("condition", "original"))
        if row["id"] is not None and key in seen:
            raise ValueError("Duplicate experiment ID/arm/condition")
        seen.add(key)
        for name in ["target", "prediction"]:
            value = row.get(name)
            if value == "":
                value = None
            if isinstance(value, str) and value in ("0", "1"):
                value = int(value)
            if value is not None and value not in (0, 1):
                raise ValueError("Nonbinary " + name)
            row[name] = value
        if row["target"] is None:
            raise ValueError("Missing ground truth; cannot silently drop records")
        if "raw_response_available" not in row:
            row["raw_response_available"] = any(k in row and row[k] is not None for k in ["llm_raw_response", "raw_response"])
        if row.get("is_valid") is False:
            row["prediction"] = None
        result.append(row)
    return result
