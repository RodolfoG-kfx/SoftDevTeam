import argparse
import json

from ai_dev_team import run_project


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the AI dev team pipeline.")
    parser.add_argument("--idea", required=True, help="Product idea to implement.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    result = run_project(args.idea)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
