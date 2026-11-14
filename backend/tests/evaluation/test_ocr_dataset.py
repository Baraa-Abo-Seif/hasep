import pytest
from typing import List, Tuple
from backend.app.ocr.arabic_utils import normalize_arabic_digits, clean_arabic_string


def levenshtein_distance(s1: str, s2: str) -> int:
    """Computes Levenshtein edit distance between two sequences (characters or words)."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def compute_cer(reference: str, hypothesis: str) -> float:
    """Character Error Rate (CER) = EditDistance(ref, hyp) / len(ref)."""
    ref = clean_arabic_string(reference)
    hyp = clean_arabic_string(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    dist = levenshtein_distance(ref, hyp)
    return round(dist / len(ref), 4)


def compute_wer(reference: str, hypothesis: str) -> float:
    """Word Error Rate (WER) = WordEditDistance(ref_words, hyp_words) / len(ref_words)."""
    ref_words = clean_arabic_string(reference).split()
    hyp_words = clean_arabic_string(hypothesis).split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    dist = levenshtein_distance(ref_words, hyp_words)
    return round(dist / len(ref_words), 4)


# ==============================================================================
# Ground-Truth Evaluation Dataset
# ==============================================================================
EVALUATION_DATASET = [
    {
        "id": "dataset_01_printed_invoice",
        "description": "فاتورة مبيعات مطبوعة باللغة العربية مع أرقام مشرقية ومغربية ومبالغ مالية",
        "category": "printed_invoice",
        "ground_truth_text": "شركة التيسير لمواد البناء\nفاتورة رقم 1042\nالتاريخ 2026/05/10\nاسم العميل أحمد عبد الله\nأسمنت مقاوم ٥٠ كيس بسعر 25.50 ريال الإجمالي 1275.00 ريال",
        "sample_extracted_text": "شركة التيسير لمواد البناء\nفاتورة رقم 1042\nالتاريخ 2026/05/10\nاسم العميل أحمد عبد الله\nأسمنت مقاوم 50 كيس بسعر 25.50 ريال الإجمالي 1275.00 ريال",
        "ground_truth_table": [
            {"الصنف": "أسمنت مقاوم", "الكمية": 50, "السعر": 25.50, "الإجمالي": 1275.00}
        ],
        "extracted_table": [
            {"الصنف": "أسمنت مقاوم", "الكمية": 50, "السعر": 25.50, "الإجمالي": 1275.00}
        ],
    },
    {
        "id": "dataset_02_handwritten_attendance",
        "description": "كشف حضور وغياب بخط اليد مع أسماء طلاب وتواريخ وملاحظات",
        "category": "handwritten_attendance",
        "ground_truth_text": "كشف حضور الطلاب - الصف الثالث\nالتاريخ: 14/05/2026\nعمر خالد حاضر\nياسين محمود غائب بعذر\nمصطفى علي حاضر",
        "sample_extracted_text": "كشف حضور الطلاب - الصف الثالث\nالتاريخ: 14/05/2026\nعمر خالد حاضر\nياسين محمود غائب بعذر\nمصطفى علي حاضر",
        "ground_truth_table": [
            {"اسم الطالب": "عمر خالد", "الحالة": "حاضر"},
            {"اسم الطالب": "ياسين محمود", "الحالة": "غائب بعذر"},
            {"اسم الطالب": "مصطفى علي", "الحالة": "حاضر"},
        ],
        "extracted_table": [
            {"اسم الطالب": "عمر خالد", "الحالة": "حاضر"},
            {"اسم الطالب": "ياسين محمود", "الحالة": "غائب بعذر"},
            {"اسم الطالب": "مصطفى علي", "الحالة": "حاضر"},
        ],
    },
    {
        "id": "dataset_03_mixed_ar_en_receipt",
        "description": "إيصال صيدلية مختلط عربي وإنجليزي مع أسماء أدوية وأسعار",
        "category": "mixed_receipt",
        "ground_truth_text": "صيدلية الشفاء Al-Shifa Pharmacy\nPanadol Extra 24 Tabs السعر 18.75 SAR\nVitamin C 1000mg السعر 35.00 SAR\nالمجموع الكلي Total: 53.75 SAR",
        "sample_extracted_text": "صيدلية الشفاء Al-Shifa Pharmacy\nPanadol Extra 24 Tabs السعر 18.75 SAR\nVitamin C 1000mg السعر 35.00 SAR\nالمجموع الكلي Total: 53.75 SAR",
        "ground_truth_table": [
            {"item": "Panadol Extra 24 Tabs", "price": 18.75},
            {"item": "Vitamin C 1000mg", "price": 35.00},
        ],
        "extracted_table": [
            {"item": "Panadol Extra 24 Tabs", "price": 18.75},
            {"item": "Vitamin C 1000mg", "price": 35.00},
        ],
    },
]


def test_ocr_evaluation_metrics():
    """Runs CER, WER, and table accuracy evaluations over the annotated dataset."""
    total_samples = len(EVALUATION_DATASET)
    cer_scores = []
    wer_scores = []
    cell_accuracy_scores = []

    for sample in EVALUATION_DATASET:
        gt_text = sample["ground_truth_text"]
        ext_text = sample["sample_extracted_text"]

        cer = compute_cer(gt_text, ext_text)
        wer = compute_wer(gt_text, ext_text)
        cer_scores.append(cer)
        wer_scores.append(wer)

        # Table Cell-level accuracy
        gt_table = sample["ground_truth_table"]
        ext_table = sample["extracted_table"]

        correct_cells = 0
        total_cells = 0
        for r_gt, r_ext in zip(gt_table, ext_table):
            for k, val in r_gt.items():
                total_cells += 1
                if r_ext.get(k) == val:
                    correct_cells += 1

        cell_acc = (correct_cells / total_cells) if total_cells > 0 else 1.0
        cell_accuracy_scores.append(cell_acc)

    avg_cer = sum(cer_scores) / total_samples
    avg_wer = sum(wer_scores) / total_samples
    avg_cell_acc = sum(cell_accuracy_scores) / total_samples

    print(f"\n--- Arabic OCR & Table Benchmark Report ---")
    print(f"Total Samples Evaluated: {total_samples}")
    print(f"Average Character Error Rate (CER): {avg_cer * 100:.2f}%")
    print(f"Average Word Error Rate (WER): {avg_wer * 100:.2f}%")
    print(f"Average Cell-Level Accuracy: {avg_cell_acc * 100:.2f}%")

    # Acceptance threshold
    assert avg_cer < 0.05, f"CER ({avg_cer}) exceeds acceptable error threshold"
    assert avg_wer < 0.10, f"WER ({avg_wer}) exceeds acceptable error threshold"
    assert avg_cell_acc >= 0.95, f"Cell accuracy ({avg_cell_acc}) below 95%"
