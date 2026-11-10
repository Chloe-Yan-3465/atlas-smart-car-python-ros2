# Third-party notices

The landmark training pipeline invokes Ultralytics YOLOv5. YOLOv5 source is not
vendored by this repository; obtain the version required for training and comply
with its GNU GPL v3 license. A copy is stored at
`training/YOLOV5_GPL-3.0_LICENSE`. The archived model artifacts were supplied by
the course material and their provenance/checksums are documented under `models/`.

The fetch script `training/landmark/fetch_yolov5.sh` selects upstream YOLOv5
`v7.0` by default. Users should retain upstream copyright notices when obtaining
or redistributing that source. The six archived lane and landmark weights originate
from course Group 3 material. Their precise training-data provenance and
redistribution permissions have not been independently verified; the repository's
own software license does not establish rights to third-party data or weights.

