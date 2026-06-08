"""
helper.py
Corresponds to Java: Helper (com.axaxl.sumcomp.server.util.Helper)

transformGroupKeys: Restores the '&' character that was escaped in YAML config.
  - '&' is a special character in YAML, so config stores it as "SummComp"
  - The actual AD group name uses "Summ&Comp"
  - Java source: originalKey.replace("SummComp", "Summ&Comp")
"""
from pathlib import Path


def transform_group_keys(
    groups: dict[str, list[str]],
) -> dict[str, list[str]]:
    """
    Restores '&' characters escaped in YAML config.
    Java: originalKey.replace("SummComp", "Summ&Comp")
    """
    return {
        k.replace("SummComp", "Summ&Comp"): v
        for k, v in groups.items()
    }


def get_claim_by_key(claims: dict, key: str) -> str | None:
    """
    Corresponds to Java: Helper.getClaimByKey
    Safely retrieves a field from OIDC token claims.
    """
    val = claims.get(key)
    return str(val) if val is not None else None


def build_document_upload_path(
    user_id: str,
    submission_id: str,
    filename: str,
    path_pattern: str,
) -> str:
    """Corresponds to Java: Helper.buildDocumentUploadPath"""
    return path_pattern.format(user_id, submission_id, filename)


def get_filename_from_path(path: str) -> str:
    """Corresponds to Java: Helper.getFilenameFromPath"""
    return Path(path).name


def extract_user_id_from_document_path(path: str | None) -> str | None:
    """Corresponds to Java: Helper.extractUserIdFromDocumentPath"""
    if not path:
        return None
    return path.split("/")[0]
