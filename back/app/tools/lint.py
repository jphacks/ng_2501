import subprocess
import json
import sys
from pathlib import Path
from pprint import pprint


def run_ruff_format(path: str | Path):
    """Format code using Ruff before analysis."""
    print("\n🧹 Running Ruff format...")
    result = subprocess.run(
        ["ruff", "format", str(path)],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        print("✅ Ruff format completed successfully.")
    else:
        print("⚠️ Ruff format encountered an issue:")
        print(result.stderr)


def run_pyright(path: str | Path):
    """Run Pyright and print readable diagnostics."""
    print("\n🔍 Running Pyright type check...")
    result = subprocess.run(
        ["pyright", str(path), "--outputjson"],
        text=True,
        capture_output=True,
        check=False,
    )

    if not result.stdout.strip():
        print("⚠️ Pyright returned no JSON output.")
        if result.stderr.strip():
            print("stderr:", result.stderr)
        return None

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("❌ Failed to parse Pyright output!")
        print(result.stdout)
        return None

    summary = data.get("summary", {})
    diagnostics = data.get("generalDiagnostics", [])

    # 🔽 「Wildcard import」警告を除外
    filtered_diagnostics = [
        d for d in diagnostics
        if "Wildcard import" not in d["message"]
    ]

    print(f" Pyright finished: {summary.get('filesAnalyzed', 0)} files analyzed.")
    print(f" {len([d for d in filtered_diagnostics if d['severity']=='error'])} errors "
          f"|  {len([d for d in filtered_diagnostics if d['severity']=='warning'])} warnings\n")

    # --- 詳細なエラー出力 ---
    if filtered_diagnostics:
        print("===  Pyright Diagnostics (filtered) ===")
        for diag in filtered_diagnostics:
            file = Path(diag["file"]).name
            line = diag["range"]["start"]["line"] + 1
            severity = diag["severity"].upper()
            msg = diag["message"].split("\n")[0]
            print(f"{file}:{line} [{severity}] → {msg}")
    else:
        print("No issues found by Pyright!")

    data["generalDiagnostics"] = filtered_diagnostics
    return data


def format_and_linter(path: str | Path = "."):
    """Ruff format → Pyright check"""
    path = Path(path)
    if not path.exists():
        print(f"❌ Target path does not exist: {path}")
        sys.exit(1)

    print(f"🧠 Running lint sequence for: {path}")

    # Step 1: Ruff format
    run_ruff_format(path)

    # Step 2: Pyright analysis
    report = run_pyright(path)

    # Step 3: Summary
    if report:
        summary = report.get("summary", {})
        print("\n=== 🧾 Summary ===")
        print(json.dumps(summary, indent=2))
    else:
        print("⚠️ Pyright returned no summary.")
    print("\n✅ Lint check finished.")
    
    return report


if __name__ == "__main__":
    target = "tmp/abc.py"
    report=format_and_linter(target)
    pprint(report)


# {'generalDiagnostics': [{'file': '/workspaces/ai_agent/back/tmp/abc.py',
#                          'message': 'Cannot access attribute "playjvadpo" for '
#                                     'class "GeneratedScene*"\n'
#                                     '\xa0\xa0Attribute "playjvadpo" is unknown',
#                          'range': {'end': {'character': 23, 'line': 13},
#                                    'start': {'character': 13, 'line': 13}},
#                          'rule': 'reportAttributeAccessIssue',
#                          'severity': 'error'},
#                         {'file': '/workspaces/ai_agent/back/tmp/abc.py',
#                          'message': 'Argument of type "ManimColor" cannot be '
#                                     'assigned to parameter "color" of type '
#                                     '"str" in function "__init__"\n'
#                                     '\xa0\xa0"ManimColor" is not assignable to '
#                                     '"str"',
#                          'range': {'end': {'character': 74, 'line': 295},
#                                    'start': {'character': 68, 'line': 295}},
#                          'rule': 'reportArgumentType',
#                          'severity': 'error'}],
#  'summary': {'errorCount': 37,
#              'filesAnalyzed': 1,
#              'informationCount': 0,
#              'timeInSec': 1.321,
#              'warningCount': 1},
#              'time': '1760162953258',
#              'version': '1.1.406'}