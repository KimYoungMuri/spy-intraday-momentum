from pathlib import Path
import yaml


def project_root() -> Path:
    # .../hw2/src/sis_hw2/utils/config.py -> parents[3] == hw2
    return Path(__file__).resolve().parents[3]


def load_config(path: str | Path | None = None) -> dict:
    cfg_path = Path(path) if path else project_root() / "config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)


def ensure_dirs(cfg: dict | None = None) -> None:
    cfg = cfg or load_config()
    root = project_root()
    for key in ("raw", "processed", "external", "tables", "figures", "logs", "reports"):
        (root / cfg["paths"][key]).mkdir(parents=True, exist_ok=True)
