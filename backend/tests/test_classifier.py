#!/usr/bin/env python3
"""
Test the hate speech classifier using test_data.json.
"""

import json
import os
from collections import defaultdict
import sys
from pathlib import Path
sys.path.insert(0,
str(Path(__file__).parent.parent))
from app.classification_model.hate_speech_classifier import HateSpeechClassifier, ClassificationInput


def load_test_data():
    """Load test data from test_data.json file."""
    test_file = os.path.join(os.path.dirname(__file__), "..","data","test_data.json")
    
    try:
        with open(test_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {test_file} not found!")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return []


def calculate_metrics(results, labels):
    """Calculate precision, recall, and F1 score for each label."""
    # Create confusion matrix data
    true_positives = defaultdict(int)
    false_positives = defaultdict(int)
    false_negatives = defaultdict(int)
    
    for result in results:
        expected = result["expected"]
        predicted = result["predicted"]
        
        if predicted == "ERROR":
            # Treat errors as false negatives for the expected label
            false_negatives[expected] += 1
            continue
            
        # Count true positives, false positives, false negatives
        for label in labels:
            if expected == label and predicted == label:
                true_positives[label] += 1
            elif expected != label and predicted == label:
                false_positives[label] += 1
            elif expected == label and predicted != label:
                false_negatives[label] += 1
    
    # Calculate metrics for each label
    metrics = {}
    
    for label in labels:
        tp = true_positives[label]
        fp = false_positives[label]
        fn = false_negatives[label]
        
        # Precision = TP / (TP + FP)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        
        # Recall = TP / (TP + FN)
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        
        # F1 = 2 * (precision * recall) / (precision + recall)
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        metrics[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "support": tp + fn  # Total actual instances of this label
        }
    
    # Calculate macro and micro averages
    total_tp = sum(true_positives.values())
    total_fp = sum(false_positives.values())
    total_fn = sum(false_negatives.values())
    
    # Micro averages (aggregate across all labels)
    micro_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    micro_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_f1 = 2 * (micro_precision * micro_recall) / (micro_precision + micro_recall) if (micro_precision + micro_recall) > 0 else 0.0
    
    # Macro averages (average of per-label metrics)
    valid_metrics = [m for m in metrics.values() if m["support"] > 0]
    macro_precision = sum(m["precision"] for m in valid_metrics) / len(valid_metrics) if valid_metrics else 0.0
    macro_recall = sum(m["recall"] for m in valid_metrics) / len(valid_metrics) if valid_metrics else 0.0
    macro_f1 = sum(m["f1"] for m in valid_metrics) / len(valid_metrics) if valid_metrics else 0.0
    
    return metrics, {
        "micro": {"precision": micro_precision, "recall": micro_recall, "f1": micro_f1},
        "macro": {"precision": macro_precision, "recall": macro_recall, "f1": macro_f1}
    }


def run_tests():
    """Run all tests from test_data.json."""
    print("Loading test data...")
    test_data = load_test_data()
    
    if not test_data:
        print("No test data found. Exiting.")
        return
    
    print(f"Found {len(test_data)} test cases.\n")
    
    # Initialize classifier
    try:
        classifier = HateSpeechClassifier()
    except Exception as e:
        print(f"Failed to initialize classifier: {e}")
        print("Make sure you have set the GROQ_API_KEY environment variable.")
        return
    
    # Track results
    correct = 0
    total = len(test_data)
    results = []
    
    print("Running tests...\n")
    
    for i, test_case in enumerate(test_data, 1):
        # Convert test case to ClassificationInput
        input_data = ClassificationInput(
            segment_text=test_case["text"],
            segment_start=test_case["start"],
            segment_end=test_case["end"],
            asr_mean_confidence=test_case["asr_conf"],
            confidence_threshold=0.45
        )
        
        # Classify
        try:
            result = classifier.classify(input_data)
            predicted = result.label
            expected = test_case["expected"]
            is_correct = predicted == expected
            
            if is_correct:
                correct += 1
            
            # Store result
            results.append({
                "test_id": i,
                "text": test_case["text"],
                "expected": expected,
                "predicted": predicted,
                "correct": is_correct,
                "confidence": test_case["asr_conf"],
                "rationale": result.rationale,
                "spans": [(s.quote, s.char_start, s.char_end) for s in result.spans]
            })
            
            # Print progress
            status = "✓" if is_correct else "✗"
            print(f"{status} Test {i:2d}/{total}: {predicted:12s} (expected: {expected:12s}) - {test_case['text'][:50]}...")
            
            if not is_correct:
                print(f"    Rationale: {result.rationale}")
                if result.spans:
                    print(f"    Spans: {[(s.quote, s.char_start, s.char_end) for s in result.spans]}")
                print()
            
        except Exception as e:
            print(f"✗ Test {i:2d}/{total}: ERROR - {str(e)}")
            results.append({
                "test_id": i,
                "text": test_case["text"],
                "expected": test_case["expected"],
                "predicted": "ERROR",
                "correct": False,
                "confidence": test_case["asr_conf"],
                "rationale": f"Error: {str(e)}",
                "spans": []
            })
    
    # Print summary
    accuracy = (correct / total) * 100
    print(f"\n{'='*60}")
    print(f"RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"Total tests: {total}")
    print(f"Correct: {correct}")
    print(f"Incorrect: {total - correct}")
    print(f"Accuracy: {accuracy:.1f}%")
    
    # Calculate precision, recall, F1 scores
    all_labels = ["NONE", "PROFANITY", "HATE", "EXTREMIST", "BOTH", "UNCLEAR", "UNCLEAR_ASR"]
    per_label_metrics, aggregate_metrics = calculate_metrics(results, all_labels)
    
    # Print breakdown by label with accuracy
    print(f"\n{'='*60}")
    print(f"BREAKDOWN BY EXPECTED LABEL")
    print(f"{'='*60}")
    
    label_stats = {}
    for result in results:
        expected = result["expected"]
        if expected not in label_stats:
            label_stats[expected] = {"correct": 0, "total": 0}
        
        label_stats[expected]["total"] += 1
        if result["correct"]:
            label_stats[expected]["correct"] += 1
    
    for label in sorted(label_stats.keys()):
        stats = label_stats[label]
        label_accuracy = (stats["correct"] / stats["total"]) * 100
        print(f"{label:12s}: {stats['correct']:2d}/{stats['total']:2d} ({label_accuracy:5.1f}%)")
    
    # Print detailed metrics
    print(f"\n{'='*80}")
    print(f"DETAILED METRICS (Precision, Recall, F1-Score)")
    print(f"{'='*80}")
    print(f"{'Label':<12} {'Precision':<10} {'Recall':<10} {'F1-Score':<10} {'Support':<8}")
    print(f"{'-'*80}")
    
    for label in sorted(all_labels):
        if label in per_label_metrics and per_label_metrics[label]["support"] > 0:
            metrics = per_label_metrics[label]
            print(f"{label:<12} {metrics['precision']:<10.3f} {metrics['recall']:<10.3f} "
                  f"{metrics['f1']:<10.3f} {metrics['support']:<8d}")
    
    print(f"{'-'*80}")
    
    # Print aggregate metrics
    print(f"\n{'='*60}")
    print(f"AGGREGATE METRICS")
    print(f"{'='*60}")
    
    micro = aggregate_metrics["micro"]
    macro = aggregate_metrics["macro"]
    
    print(f"Micro-averaged:")
    print(f"  Precision: {micro['precision']:.3f}")
    print(f"  Recall:    {micro['recall']:.3f}")
    print(f"  F1-Score:  {micro['f1']:.3f}")
    
    print(f"\nMacro-averaged:")
    print(f"  Precision: {macro['precision']:.3f}")
    print(f"  Recall:    {macro['recall']:.3f}")
    print(f"  F1-Score:  {macro['f1']:.3f}")
    
    print(f"\nOverall Accuracy: {accuracy:.1f}%")
    
    # Save detailed results
    data_dir = Path(__file__).parent.parent / 'data'
    data_dir.mkdir(exist_ok=True)

    results_file = data_dir / 'test_results.json'
    with open(results_file, 'w') as f:
        json.dump({
            "summary": {
                "total_tests": total,
                "correct": correct,
                "accuracy": accuracy,
                "label_breakdown": label_stats,
                "per_label_metrics": per_label_metrics,
                "aggregate_metrics": aggregate_metrics
            },
            "detailed_results": results
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: {results_file}")


if __name__ == "__main__":
    run_tests()