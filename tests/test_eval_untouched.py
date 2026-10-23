import json
import hashlib
import os

def test_eval_untouched():
    notebook_path = os.path.join(os.path.dirname(__file__), "..", "Train", "Evaluation", "Evaluation.ipynb")
    official_eval_path = os.path.join(os.path.dirname(__file__), "..", "eval", "official_eval.py")
    
    assert os.path.exists(notebook_path), f"Notebook not found at {notebook_path}"
    assert os.path.exists(official_eval_path), f"official_eval.py not found at {official_eval_path}"
    
    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = json.load(f)
        
    parts = []
    for cell_idx in [1, 3, 5, 7, 9]:
        src = "".join(nb["cells"][cell_idx]["source"])
        parts.append(src)
        
    expected_content = "\n\n".join(parts) + "\n"
    
    with open(official_eval_path, "r", encoding="utf-8") as f:
        actual_content = f.read()
        
    expected_hash = hashlib.sha256(expected_content.encode("utf-8")).hexdigest()
    actual_hash = hashlib.sha256(actual_content.encode("utf-8")).hexdigest()
    
    assert expected_hash == actual_hash, "eval/official_eval.py has been modified or does not match Evaluation.ipynb cells!"
    print("test_eval_untouched PASSED: Hash matches exactly.", expected_hash)

if __name__ == "__main__":
    test_eval_untouched()
