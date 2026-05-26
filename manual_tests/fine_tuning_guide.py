"""
Fine-Tuning Guide for Satellite YOLO Detection
================================================

WHY FINE-TUNING IS MANDATORY FOR SATELLITE IMAGERY:

The pretrained "keremberke/yolov8s-plane-detection" model was trained on
ground-level and low-altitude drone photos. Satellite imagery is COMPLETELY
DIFFERENT:

                    Ground Photo          Satellite Image
                    ============          ===============
    View angle:     Side / 3/4           Top-down (nadir)
    Object size:    30-80% of frame      0.5-5% of frame
    Detail level:   Wings, windows,       Blob, shadow,
                    engines, tail         shape outline
    Background:     Sky, runway,          Tarmac, soil,
                    taxiway, grass        rooftops
    Resolution:     cm-level             1-10m/pixel

RESULT: The pretrained model scores ~0.05 confidence on satellite planes
and has massive false positive rates. Fine-tuning fixes this.

PREREQUISITES:
    1. Python 3.11+ with PyTorch
    2. A labeled satellite dataset (see below for options)
    3. At least 8GB RAM (16GB+ recommended)
    4. GPU recommended (but CPU works, just slower)

DATASET OPTIONS:
    A) Roboflow "satellite-plane-detection" (fastest to start)
    B) Custom annotation with your own satellite imagery
    C) xView / DOTA public datasets (need format conversion)

Usage:
    # 1. Install dependencies
    pip install ultralytics roboflow

    # 2. Download satellite plane dataset
    python scripts/prepare_training_data.py \\
        --source roboflow --preset planes \\
        --api-key YOUR_KEY --output data/planes

    # 3. Fine-tune
    python scripts/fine_tune.sh --data data/planes/data.yaml --epochs 100

    # Or run this script:
    python manual_tests/fine_tuning_guide.py --api-key YOUR_KEY
"""

import argparse
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger()


def print_header(text: str):
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


def step_guide(api_key: str = None):
    """
    Interactive step-by-step guide for fine-tuning.
    """
    print_header("SATELLITE YOLO FINE-TUNING GUIDE")
    print(
        "This guide walks you through the complete process of training\n"
        "a YOLOv8 model to detect objects in satellite imagery.\n"
        "\n"
        "The pretrained model from HuggingFace sees planes as large side-on\n"
        "objects. After fine-tuning on satellite data, it will detect\n"
        "top-down planes at tarmacs and airports.\n"
    )

    # Step 1: Dataset
    print_header("STEP 1: Get a Labeled Satellite Dataset")
    print(
        "Options:\n"
        "  1. Use a Roboflow preset (recommended for quick start)\n"
        "  2. Use your own labeled data\n"
        "  3. Use public datasets (xView, DOTA)\n"
        "\n"
        "Roboflow datasets available:\n"
        "  - planes: Satellite airplane detection\n"
        "  - ships: Satellite ship detection from radar\n"
        "  - vehicles: Vehicle detection in satellite imagery\n"
        "  - oil_tanks: Oil storage tank detection\n"
    )

    if api_key:
        print("✓ API key provided - can download datasets")
        dataset_choice = input(
            "\nWhich dataset preset? (planes/ships/vehicles/oil_tanks, "
            "or Enter to skip): "
        ).strip()

        if dataset_choice:
            print(f"\nDownloading {dataset_choice} dataset...")
            from scripts.prepare_training_data import download_satellite_dataset_preset

            yaml_path = download_satellite_dataset_preset(
                dataset_choice, api_key, "data"
            )
            print(f"✓ Dataset ready: {yaml_path}")
        else:
            print("Skipping dataset download.")
            yaml_path = input("Enter path to your data.yaml: ").strip()
    else:
        print("! No API key. You'll need to provide a local dataset.")
        yaml_path = input("Enter path to your data.yaml: ").strip()

    if not yaml_path or not Path(yaml_path).exists():
        print(f"✗ data.yaml not found at: {yaml_path}")
        print("Please prepare your dataset first using:")
        print("  python scripts/prepare_training_data.py --help")
        return

    # Step 2: Analyze
    print_header("STEP 2: Analyze Your Dataset")
    from scripts.prepare_training_data import validate_dataset, estimate_small_object_anchors

    print("Validating dataset...")
    report = validate_dataset(yaml_path)
    print(f"  Images: {report.get('total_images', '?')}")
    print(f"  Labels: {report.get('total_labels', '?')}")
    print(f"  Classes: {report.get('num_classes', '?')}: {report.get('class_names', [])}")
    print(f"  Label coverage: {report.get('label_coverage', '?')}%")
    print(f"  Valid: {'YES' if report.get('valid') else 'NO - check warnings'}")

    print("\nAnalyzing object sizes...")
    stats = estimate_small_object_anchors(yaml_path)
    if "error" not in stats:
        print(f"  Total boxes: {stats['total_boxes']}")
        print(f"  Mean area: {stats.get('mean_area', 0):.6f} (normalized 0-1)")
        print(f"  Median area: {stats.get('median_area', 0):.6f}")
        print(f"  Recommended: {stats.get('recommendation', 'N/A')}")

    # Step 3: Training params
    print_header("STEP 3: Configure Training Parameters")
    print(
        "Suggested parameters for satellite detection:\n"
        "  - Model: yolov8m.pt or yolov8l.pt (small objects need more features)\n"
        "  - Epochs: 100-200 (satellite domain shift needs more training)\n"
        "  - Image size: 640 (good balance for small objects)\n"
        "  - Batch: as large as your GPU memory allows\n"
        "  - Learning rate: 0.001 (AdamW optimizer)\n"
    )

    model = input("Model [yolov8m.pt]: ").strip() or "yolov8m.pt"
    epochs = input("Epochs [100]: ").strip() or "100"
    imgsz = input("Image size [640]: ").strip() or "640"
    batch = input("Batch size [16]: ").strip() or "16"
    device = input("Device [cpu] (or cuda:0): ").strip() or "cpu"

    # Step 4: Train
    print_header("STEP 4: Start Training")
    print(
        f"Running: fine_tune_yolo(\n"
        f"  data_yaml='{yaml_path}',\n"
        f"  pretrained_model='{model}',\n"
        f"  epochs={epochs}, batch={batch}, imgsz={imgsz},\n"
        f"  device='{device}'\n"
        f")\n"
    )

    confirm = input("Start training? (y/n): ").strip().lower()
    if confirm != "y":
        print("Training cancelled.")
        print(f"\nTo run later, use:")
        print(f"  python scripts/fine_tune.sh --data {yaml_path} --model {model} --epochs {epochs}")
        return

    from backend.app.services.training import fine_tune_yolo

    results = fine_tune_yolo(
        data_yaml=yaml_path,
        pretrained_model=model,
        epochs=int(epochs),
        batch=int(batch),
        imgsz=int(imgsz),
        device=device,
        augment=True,
        cos_lr=True,
    )

    # Results
    print_header("TRAINING COMPLETE")
    print(f"  Model path: {results['model_path']}")
    print(f"  Best mAP50: {results['best_map50']:.4f}")
    print(f"  Best mAP50-95: {results['best_map5095']:.4f}")
    print(f"  Precision: {results['best_precision']:.4f}")
    print(f"  Recall: {results['best_recall']:.4f}")
    print(f"  Epochs trained: {results['epochs_trained']}")

    # Step 5: Export
    print_header("STEP 5: Export for Deployment")
    from backend.app.services.training import export_for_deployment

    export_path = export_for_deployment(
        model_path=results["model_path"],
        format="onnx",
        half=True,
    )
    print(f"  ONNX model: {export_path}")

    # Step 6: Test
    print_header("STEP 6: Test on Satellite Image")
    print(
        "Run detection using your fine-tuned model:\n\n"
        f'  python manual_tests/Commercial_aviation_fixed.py \\\n'
        f'      --image manual_tests/airport_patch_highres.tif \\\n'
        f'      --finetuned {results["model_path"]}\n'
    )

    print("\nOr via the API:")
    print(f'  curl -X POST http://localhost:8000/api/v1/analytics/detect/airplanes \\')
    print(f'    -F "file=@manual_tests/airport_patch_highres.tif"')
    print(f'    -F "confidence=0.15"')

    print(
        "\n\n=== NEXT STEPS ===\n"
        "1. Add more training data to improve accuracy\n"
        "2. Try different YOLO backbones (yolov8l, yolov8x)\n"
        "3. Experiment with SAHI slice sizes for your specific imagery\n"
        "4. Set up automated retraining as new data arrives\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Interactive fine-tuning guide for satellite YOLO"
    )
    parser.add_argument("--api-key", help="Roboflow API key")
    args = parser.parse_args()

    step_guide(api_key=args.api_key)
