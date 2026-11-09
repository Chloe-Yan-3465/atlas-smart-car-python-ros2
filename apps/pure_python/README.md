# 纯 Python 入口

安装仓库根目录后使用统一命令：

```bash
python3 -m pip install -e '.[cpu]'
smartcar run --dry-run --source /path/to/images --max-frames 20
smartcar manual --serial-port /dev/ttyUSB0
smartcar camera-test --source /dev/video0
smartcar model-test --image demo.jpg
smartcar serial-test --serial-port /dev/ttyUSB0 --rpm 30
```

Atlas 上将 `config/car.yaml` 的 `models.backend` 改为 `om`，并先加载 CANN 环境。实车前先使用 `--dry-run`。

