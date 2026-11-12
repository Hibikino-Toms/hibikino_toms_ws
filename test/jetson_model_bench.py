#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jetson_model_bench.py
=====================
在 Jetson 上单独测试 YOLO / SAM3 的效果与性能。

功能
----
- 实时显示摄像头画面 + 识别结果（框 / 掩码）+ 当前帧数
- 运行中按 [s] 在 YOLO 与 SAM3 之间切换（会释放旧模型显存再加载新模型）
- 每次加载模型后自动：预热 N 秒 -> 评估 M 秒 -> 输出报告
  报告包含：平均 FPS、推理耗时 (mean/p50/p95/max)、内存 (系统/进程/torch)、
           CPU / GPU 占用、温度、功耗、模型加载时间与加载内存增量
- 结果保存到 bench_results/ (JSON 汇总 + 逐帧 CSV + 跨次对比用的 bench_summary.csv)

依赖
----
ultralytics >= 8.3.237 (SAM3 需要)、opencv-python、numpy、torch
可选：pyrealsense2 (RealSense)、psutil (非 Jetson 时的监控后备)
Jetson 上会自动调用 tegrastats 读取 RAM / GPU / 温度 / 功耗，无需额外安装。

示例
----
# RealSense 手先相机，先跑 YOLO，可切到 SAM3
python3 jetson_model_bench.py --yolo best.pt --sam3 sam3.pt --source realsense --serial 230322272057

# USB 相机 0，只测 TensorRT 引擎，评估 120 秒
python3 jetson_model_bench.py --yolo best.engine --source 0 --duration 120

# 用同一段视频对比两个模型（结果可复现），无界面，评估完自动退出
python3 jetson_model_bench.py --yolo best.pt --sam3 sam3.pt --source test.mp4 --no-show --start sam3

按键：[s] 切换模型  [r] 重新评估  [q]/[ESC] 退出
"""

import argparse
import csv
import gc
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime

import cv2
import numpy as np

try:
    import torch
except ImportError:
    torch = None

try:
    import psutil
except ImportError:
    psutil = None


# ============================================================
# 通用工具
# ============================================================
def cuda_ok():
    return torch is not None and torch.cuda.is_available()


def cuda_initialized():
    return cuda_ok() and torch.cuda.is_initialized()


def cuda_sync():
    """GPU 是异步执行的，计时前必须同步，否则测到的时间偏小"""
    if cuda_initialized():
        torch.cuda.synchronize()


def proc_rss_mb():
    """当前进程常驻内存 (MB)"""
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0
    except OSError:
        pass
    if psutil:
        return psutil.Process().memory_info().rss / 1048576.0
    return float("nan")


def read_meminfo_mb():
    """系统内存 (used, total) MB。Jetson 是 CPU/GPU 共享内存，GPU 占用也算在这里"""
    try:
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                k, v = line.split(":", 1)
                info[k] = int(v.split()[0])
        total = info["MemTotal"] / 1024.0
        avail = info.get("MemAvailable", info.get("MemFree", 0)) / 1024.0
        return total - avail, total
    except Exception:
        if psutil:
            vm = psutil.virtual_memory()
            return (vm.total - vm.available) / 1048576.0, vm.total / 1048576.0
    return float("nan"), float("nan")


def read_proc_stat():
    with open("/proc/stat") as f:
        vals = [int(x) for x in f.readline().split()[1:]]
    idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
    return idle, sum(vals)


_GPU_LOAD_PATHS = None


def read_gpu_load_sysfs():
    """Jetson GPU 负载 (0-100)，读不到返回 None"""
    global _GPU_LOAD_PATHS
    if _GPU_LOAD_PATHS is None:
        cands = ["/sys/devices/gpu.0/load", "/sys/devices/platform/gpu.0/load"]
        cands += glob.glob("/sys/devices/platform/*.ga10b/load")
        cands += glob.glob("/sys/devices/platform/bus@0/*.gpu/load")
        cands += glob.glob("/sys/devices/platform/*.gv11b/load")
        _GPU_LOAD_PATHS = [p for p in cands if os.path.exists(p)]
    for p in _GPU_LOAD_PATHS:
        try:
            with open(p) as f:
                return int(f.read().strip()) / 10.0
        except Exception:
            continue
    return None


def nanmean(xs):
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and np.isnan(x))]
    return float(np.mean(xs)) if xs else None


def nanmax(xs):
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and np.isnan(x))]
    return float(np.max(xs)) if xs else None


# ============================================================
# 系统监控 (tegrastats 优先)
# ============================================================
_RE_RAM = re.compile(r"RAM (\d+)/(\d+)MB")
_RE_SWAP = re.compile(r"SWAP (\d+)/(\d+)MB")
_RE_CPU = re.compile(r"CPU \[([^\]]*)\]")
_RE_GR3D = re.compile(r"GR3D_FREQ (\d+)%")
_RE_TEMP = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)@(-?\d+(?:\.\d+)?)C\b")
_RE_PWR_IN = re.compile(r"\b(VDD_IN|POM_5V_IN|VIN_SYS_5V0|VDD_TOTAL)\s+(\d+)(?:mW)?/(\d+)")


def parse_tegrastats(line):
    s = {}
    m = _RE_RAM.search(line)
    if not m:
        return None
    s["ram_used_mb"], s["ram_total_mb"] = float(m.group(1)), float(m.group(2))
    m = _RE_SWAP.search(line)
    if m:
        s["swap_used_mb"] = float(m.group(1))
    m = _RE_CPU.search(line)
    if m:
        loads = []
        for item in m.group(1).split(","):
            item = item.strip()
            if "%" in item:
                try:
                    loads.append(float(item.split("%")[0]))
                except ValueError:
                    pass
        if loads:
            s["cpu_avg"] = float(np.mean(loads))
            s["cpu_max_core"] = float(np.max(loads))
    m = _RE_GR3D.search(line)
    if m:
        s["gpu_load"] = float(m.group(1))
    temps = {k.lower(): float(v) for k, v in _RE_TEMP.findall(line)}
    temps.pop("pmic", None)  # PMIC 一般是固定值，没有参考意义
    if temps:
        s["temp_max_c"] = max(temps.values())
        if "gpu" in temps:
            s["temp_gpu_c"] = temps["gpu"]
        if "cpu" in temps:
            s["temp_cpu_c"] = temps["cpu"]
    m = _RE_PWR_IN.search(line)
    if m:
        s["power_w"] = float(m.group(2)) / 1000.0
    return s


class SystemMonitor(threading.Thread):
    def __init__(self, interval_ms=500):
        super().__init__(daemon=True)
        self.interval_ms = interval_ms
        self.samples = deque(maxlen=50000)
        self.latest = {}
        self.lock = threading.Lock()
        self._stop_evt = threading.Event()
        self.proc = None
        self.backend = "tegrastats" if shutil.which("tegrastats") else "proc"

    def run(self):
        if self.backend == "tegrastats":
            try:
                self._run_tegrastats()
                return
            except Exception as e:
                print(f"[Monitor] tegrastats 不可用，改用 /proc: {e}")
                self.backend = "proc"
        self._run_fallback()

    def _push(self, s):
        s["t"] = time.time()
        s["proc_rss_mb"] = proc_rss_mb()
        if cuda_initialized():
            try:
                s["torch_alloc_mb"] = torch.cuda.memory_allocated() / 1048576.0
                s["torch_reserved_mb"] = torch.cuda.memory_reserved() / 1048576.0
            except Exception:
                pass
        with self.lock:
            self.samples.append(s)
            self.latest = s

    def _run_tegrastats(self):
        self.proc = subprocess.Popen(
            ["tegrastats", "--interval", str(self.interval_ms)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
        got = False
        for line in self.proc.stdout:
            if self._stop_evt.is_set():
                break
            s = parse_tegrastats(line)
            if s:
                got = True
                self._push(s)
        if not got and not self._stop_evt.is_set():
            raise RuntimeError("tegrastats 没有输出")

    def _run_fallback(self):
        try:
            prev = read_proc_stat()
        except Exception:
            prev = None
        while not self._stop_evt.wait(self.interval_ms / 1000.0):
            s = {}
            s["ram_used_mb"], s["ram_total_mb"] = read_meminfo_mb()
            if prev is not None:
                cur = read_proc_stat()
                d_idle, d_total = cur[0] - prev[0], cur[1] - prev[1]
                prev = cur
                if d_total > 0:
                    s["cpu_avg"] = 100.0 * (1 - d_idle / d_total)
            g = read_gpu_load_sysfs()
            if g is not None:
                s["gpu_load"] = g
            self._push(s)

    def window(self, t0, t1):
        with self.lock:
            return [s for s in self.samples if t0 <= s["t"] <= t1]

    def get_latest(self):
        with self.lock:
            return dict(self.latest)

    def stop(self):
        self._stop_evt.set()
        if self.proc is not None:
            try:
                self.proc.terminate()
            except Exception:
                pass


# ============================================================
# 图像源
# ============================================================
class LiveCamera:
    """后台线程持续取帧，主线程只拿最新一帧（避免缓冲导致延迟）"""

    def __init__(self, args):
        self.args = args
        self.frame = None
        self.frame_id = -1
        self.cam_fps = 0.0
        self.stopped = False
        self.cond = threading.Condition()
        self._open()
        self.th = threading.Thread(target=self._loop, daemon=True)
        self.th.start()

    def _open(self):
        a = self.args
        src = a.source
        self.rs_pipe = None
        self.cap = None
        if src.lower() == "realsense":
            import pyrealsense2 as rs
            self.rs = rs
            self.rs_pipe = rs.pipeline()
            cfg = rs.config()
            if a.serial:
                cfg.enable_device(a.serial)
            cfg.enable_stream(rs.stream.color, a.width, a.height, rs.format.bgr8, a.fps)
            self.rs_pipe.start(cfg)
            print(f"[Camera] RealSense {a.serial or '(默认设备)'} {a.width}x{a.height}@{a.fps}")
        else:
            if "!" in src:  # GStreamer 管线 (CSI 相机等)
                self.cap = cv2.VideoCapture(src, cv2.CAP_GSTREAMER)
            else:
                dev = int(src) if src.isdigit() else src
                self.cap = cv2.VideoCapture(dev, cv2.CAP_V4L2) if isinstance(dev, int) else cv2.VideoCapture(dev)
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, a.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, a.height)
                self.cap.set(cv2.CAP_PROP_FPS, a.fps)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if not self.cap.isOpened():
                raise RuntimeError(f"无法打开相机: {src}")
            w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"[Camera] {src} {w}x{h}")

    def _grab(self):
        if self.rs_pipe is not None:
            frames = self.rs_pipe.wait_for_frames(5000)
            c = frames.get_color_frame()
            return np.asanyarray(c.get_data()).copy() if c else None
        ok, img = self.cap.read()
        return img if ok else None

    def _loop(self):
        cnt, t0 = 0, time.time()
        while not self.stopped:
            try:
                img = self._grab()
            except Exception as e:
                print(f"[Camera] 取帧失败: {e}")
                time.sleep(0.1)
                continue
            if img is None:
                time.sleep(0.01)
                continue
            with self.cond:
                self.frame = img
                self.frame_id += 1
                self.cond.notify_all()
            cnt += 1
            if time.time() - t0 >= 1.0:
                self.cam_fps = cnt / (time.time() - t0)
                cnt, t0 = 0, time.time()

    def read(self, last_id, timeout=2.0):
        """等待一帧比 last_id 新的图像（模型比相机快时不重复推理同一帧）"""
        with self.cond:
            self.cond.wait_for(lambda: self.frame_id != last_id or self.stopped, timeout)
            return self.frame_id, self.frame

    @property
    def ended(self):
        return False

    def release(self):
        self.stopped = True
        self.th.join(timeout=2)
        if self.rs_pipe is not None:
            try:
                self.rs_pipe.stop()
            except Exception:
                pass
        if self.cap is not None:
            self.cap.release()


class VideoFileSource:
    """视频文件：逐帧顺序读取，不丢帧，适合两个模型做可复现对比"""

    def __init__(self, path, loop=True):
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            raise RuntimeError(f"无法打开视频: {path}")
        self.loop = loop
        self.frame_id = -1
        self._ended = False
        self.cam_fps = self.cap.get(cv2.CAP_PROP_FPS) or 0.0
        print(f"[Video] {path} ({int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))} 帧)")

    def read(self, last_id, timeout=None):
        ok, img = self.cap.read()
        if not ok and self.loop:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, img = self.cap.read()
        if not ok:
            self._ended = True
            return self.frame_id, None
        self.frame_id += 1
        return self.frame_id, img

    @property
    def ended(self):
        return self._ended

    def release(self):
        self.cap.release()


def open_source(args):
    s = args.source
    if s.lower() != "realsense" and "!" not in s and not s.isdigit() \
            and not s.startswith("/dev/") and os.path.isfile(s):
        return VideoFileSource(s, loop=not args.no_loop)
    return LiveCamera(args)


# ============================================================
# 模型封装
# ============================================================
class YoloRunner:
    kind = "yolo"

    def __init__(self, path, args):
        from ultralytics import YOLO
        self.name = os.path.basename(path)
        self.model = YOLO(path, task=args.task) if args.task else YOLO(path)
        self.kw = dict(conf=args.conf, iou=args.iou, imgsz=args.imgsz, verbose=False)
        if args.device:
            self.kw["device"] = args.device
        if args.half:
            self.kw["half"] = True
        if args.classes:
            self.kw["classes"] = args.classes

    def infer(self, frame):
        t0 = time.perf_counter()
        r = self.model.predict(frame, **self.kw)[0]
        cuda_sync()
        ms = (time.perf_counter() - t0) * 1000.0
        detail = {f"yolo_{k}_ms": float(v) for k, v in (r.speed or {}).items()}
        return r, ms, detail

    def close(self):
        del self.model


class Sam3Runner:
    kind = "sam3"

    def __init__(self, path, args):
        from ultralytics.models.sam import SAM3SemanticPredictor
        # 部分 ultralytics 版本 (如 8.4.110) 的 SAM3SemanticModel 缺少 mask_threshold，
        # postprocess 时会 AttributeError。新版里该值为 0.0（logit 阈值），这里补上。
        try:
            from ultralytics.models.sam.sam3.sam3_image import SAM3SemanticModel
            if not hasattr(SAM3SemanticModel, "mask_threshold"):
                SAM3SemanticModel.mask_threshold = 0.0
                print("[SAM3] 已补丁: SAM3SemanticModel.mask_threshold = 0.0")
        except Exception as e:
            print(f"[SAM3] mask_threshold 补丁未应用: {e}")
        self.name = os.path.basename(path)
        self.prompts = [p.strip() for p in args.prompt.split(",") if p.strip()]
        base = dict(conf=args.sam_conf, task="segment", mode="predict",
                    model=path, verbose=False, save=False)
        if args.device:
            base["device"] = args.device
        if args.sam_imgsz:
            base["imgsz"] = args.sam_imgsz
        kw = {"bpe_path": args.bpe} if args.bpe else {}
        # 新版 ultralytics 用 quantize=16，旧版用 half=True，依次尝试
        variants = [{"quantize": 16}, {"half": True}, {}] if args.half else [{}]
        last_err = None
        self.predictor = None
        for extra in variants:
            try:
                self.predictor = SAM3SemanticPredictor(overrides={**base, **extra}, **kw)
                if extra:
                    print(f"[SAM3] FP16 参数: {extra}")
                break
            except (SyntaxError, TypeError, KeyError, ValueError) as e:
                last_err = e
        if self.predictor is None:
            raise last_err

    def infer(self, frame):
        t0 = time.perf_counter()
        self.predictor.set_image(frame)          # 图像编码 (最重的部分)
        cuda_sync()
        t1 = time.perf_counter()
        results = self.predictor(text=self.prompts)  # 文本提示 -> 检测/分割
        cuda_sync()
        t2 = time.perf_counter()
        r = results[0] if results else None
        detail = {"sam_encode_ms": (t1 - t0) * 1000.0, "sam_decode_ms": (t2 - t1) * 1000.0}
        return r, (t2 - t0) * 1000.0, detail

    def close(self):
        del self.predictor


def count_dets(r):
    if r is None:
        return 0
    try:
        if r.boxes is not None:
            return len(r.boxes)
        if r.masks is not None:
            return len(r.masks)
    except Exception:
        pass
    return 0


def release_cuda():
    gc.collect()
    if cuda_initialized():
        torch.cuda.empty_cache()


def load_runner(kind, args, sample_frame):
    path = args.yolo if kind == "yolo" else args.sam3
    print(f"\n[Load] 加载 {kind}: {path}")
    release_cuda()
    ram0, _ = read_meminfo_mb()
    rss0 = proc_rss_mb()
    t0 = time.perf_counter()
    runner = YoloRunner(path, args) if kind == "yolo" else Sam3Runner(path, args)
    # 第一次推理才真正初始化 CUDA/权重，算进加载时间，避免污染评估
    runner.infer(sample_frame)
    load_s = time.perf_counter() - t0
    time.sleep(0.5)
    ram1, _ = read_meminfo_mb()
    info = dict(load_time_s=load_s, load_ram_delta_mb=ram1 - ram0,
                load_rss_delta_mb=proc_rss_mb() - rss0)
    print(f"[Load] 完成 {load_s:.1f}s, 系统内存 +{info['load_ram_delta_mb']:.0f} MB, "
          f"进程RSS +{info['load_rss_delta_mb']:.0f} MB")
    return runner, info


# ============================================================
# 评估
# ============================================================
class EvalSession:
    def __init__(self, runner, load_info, warmup_s, duration_s):
        self.kind, self.name = runner.kind, runner.name
        self.load_info = load_info
        self.warmup_s, self.duration_s = warmup_s, duration_s
        self.t_create = time.time()
        self.state = "warmup"
        self.t_start = self.t_end = None
        self.frames = []
        self.reported = False

    def update(self, rec):
        """返回 True 表示本次评估刚刚完成"""
        now = rec["t"]
        if self.state == "warmup" and now - self.t_create >= self.warmup_s:
            self.state = "running"
            self.t_start = now
            if cuda_initialized():
                torch.cuda.reset_peak_memory_stats()
        if self.state == "running":
            self.frames.append(rec)
            if now - self.t_start >= self.duration_s:
                self.state = "done"
                self.t_end = now
                return True
        return False

    def status_text(self):
        now = time.time()
        if self.state == "warmup":
            return f"WARMUP {max(0, self.warmup_s - (now - self.t_create)):.1f}s", 0.0
        if self.state == "running":
            el = now - self.t_start
            return f"EVAL {el:.0f}/{self.duration_s:.0f}s", min(1.0, el / self.duration_s)
        return "EVAL DONE  (r: re-run)", 1.0


def summarize(sess, monitor, baseline, partial=False):
    fr = sess.frames
    if len(fr) < 2:
        return None
    t_end = sess.t_end or fr[-1]["t"]
    span = max(1e-6, t_end - sess.t_start)
    infer = np.array([f["infer_ms"] for f in fr])
    loop_dt = np.array([f["loop_dt_ms"] for f in fr[1:]])
    inst_fps = 1000.0 / np.clip(loop_dt, 1e-3, None)
    sys_s = monitor.window(sess.t_start, t_end)

    def col(k):
        return [s.get(k) for s in sys_s]

    ram_avg, ram_peak = nanmean(col("ram_used_mb")), nanmax(col("ram_used_mb"))
    out = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "partial": partial,
        "model_kind": sess.kind,
        "model_name": sess.name,
        "eval_seconds": round(span, 2),
        "frames": len(fr),
        # --- 速度 ---
        "pipeline_fps_avg": len(fr) / span,
        "pipeline_fps_min": float(np.min(inst_fps)) if len(inst_fps) else None,
        "pipeline_fps_p5": float(np.percentile(inst_fps, 5)) if len(inst_fps) else None,
        "infer_fps_avg": 1000.0 / float(np.mean(infer)),
        "infer_ms_mean": float(np.mean(infer)),
        "infer_ms_p50": float(np.percentile(infer, 50)),
        "infer_ms_p95": float(np.percentile(infer, 95)),
        "infer_ms_max": float(np.max(infer)),
        "infer_ms_std": float(np.std(infer)),
        "detections_avg": float(np.mean([f["n_det"] for f in fr])),
        # --- 内存 ---
        "ram_total_mb": nanmax(col("ram_total_mb")),
        "ram_baseline_mb": baseline["ram_used_mb"],
        "ram_used_avg_mb": ram_avg,
        "ram_used_peak_mb": ram_peak,
        "ram_increase_vs_baseline_mb": (ram_peak - baseline["ram_used_mb"]) if ram_peak else None,
        "swap_used_peak_mb": nanmax(col("swap_used_mb")),
        "proc_rss_avg_mb": nanmean(col("proc_rss_mb")),
        "proc_rss_peak_mb": nanmax(col("proc_rss_mb")),
        "torch_alloc_peak_mb": (torch.cuda.max_memory_allocated() / 1048576.0) if cuda_initialized() else None,
        "torch_reserved_peak_mb": nanmax(col("torch_reserved_mb")),
        # --- 负载/温度/功耗 ---
        "cpu_avg_pct": nanmean(col("cpu_avg")),
        "cpu_max_core_pct": nanmax(col("cpu_max_core")),
        "gpu_avg_pct": nanmean(col("gpu_load")),
        "gpu_max_pct": nanmax(col("gpu_load")),
        "temp_max_c": nanmax(col("temp_max_c")),
        "temp_gpu_max_c": nanmax(col("temp_gpu_c")),
        "power_avg_w": nanmean(col("power_w")),
        "power_max_w": nanmax(col("power_w")),
        "monitor_backend": monitor.backend,
        "monitor_samples": len(sys_s),
    }
    # 模型内部分阶段耗时
    detail_keys = sorted({k for f in fr for k in f if k.startswith(("yolo_", "sam_"))})
    for k in detail_keys:
        out[k.replace("_ms", "_ms_mean")] = nanmean([f.get(k) for f in fr])
    out.update(sess.load_info)
    return out


def fmt(v, unit="", nd=1):
    if v is None:
        return "N/A"
    return f"{v:.{nd}f}{unit}"


def print_report(rep):
    tag = " (中途结束，部分数据)" if rep["partial"] else ""
    print("\n" + "=" * 64)
    print(f" 评估报告{tag}: [{rep['model_kind'].upper()}] {rep['model_name']}")
    print("=" * 64)
    print(f" 评估时长 / 帧数        : {rep['eval_seconds']:.1f} s / {rep['frames']} 帧")
    print(f" 实际平均 FPS (含相机)  : {fmt(rep['pipeline_fps_avg'])}   (最低 {fmt(rep['pipeline_fps_min'])}, 5% 分位 {fmt(rep['pipeline_fps_p5'])})")
    print(f" 纯推理 FPS             : {fmt(rep['infer_fps_avg'])}")
    print(f" 推理耗时 mean/p50/p95/max : {fmt(rep['infer_ms_mean'])} / {fmt(rep['infer_ms_p50'])} / "
          f"{fmt(rep['infer_ms_p95'])} / {fmt(rep['infer_ms_max'])} ms")
    for k, v in rep.items():
        if k.startswith(("yolo_", "sam_")):
            print(f"   - {k:<22}: {fmt(v, ' ms')}")
    print(f" 平均检测数             : {fmt(rep['detections_avg'], nd=2)}")
    print(f" 模型加载时间           : {fmt(rep['load_time_s'], ' s')}  (加载时系统内存 +{fmt(rep['load_ram_delta_mb'], ' MB', 0)})")
    print(f" 系统内存 avg / peak    : {fmt(rep['ram_used_avg_mb'], '', 0)} / {fmt(rep['ram_used_peak_mb'], '', 0)} MB  "
          f"(总 {fmt(rep['ram_total_mb'], '', 0)} MB, 比加载模型前 +{fmt(rep['ram_increase_vs_baseline_mb'], '', 0)} MB)")
    print(f" SWAP peak              : {fmt(rep['swap_used_peak_mb'], ' MB', 0)}")
    print(f" 进程 RSS avg / peak    : {fmt(rep['proc_rss_avg_mb'], '', 0)} / {fmt(rep['proc_rss_peak_mb'], ' MB', 0)}")
    print(f" torch 显存 alloc/reserved peak: {fmt(rep['torch_alloc_peak_mb'], '', 0)} / {fmt(rep['torch_reserved_peak_mb'], ' MB', 0)}")
    print(f" CPU 平均 / 最忙核心    : {fmt(rep['cpu_avg_pct'], '%')} / {fmt(rep['cpu_max_core_pct'], '%')}")
    print(f" GPU 平均 / 峰值        : {fmt(rep['gpu_avg_pct'], '%')} / {fmt(rep['gpu_max_pct'], '%')}")
    print(f" 温度最高 (GPU)         : {fmt(rep['temp_max_c'], ' C')} ({fmt(rep['temp_gpu_max_c'], ' C')})")
    print(f" 功耗 avg / max         : {fmt(rep['power_avg_w'], ' W', 2)} / {fmt(rep['power_max_w'], ' W', 2)}")
    print("=" * 64 + "\n")


def save_report(rep, sess, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.join(out_dir, f"{stamp}_{sess.kind}_{os.path.splitext(sess.name)[0]}")
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2, ensure_ascii=False)
    keys = sorted({k for fr in sess.frames for k in fr})
    with open(base + "_frames.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(sess.frames)
    summ = os.path.join(out_dir, "bench_summary.csv")
    new = not os.path.exists(summ)
    with open(summ, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rep.keys()), extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(rep)
    print(f"[Save] {base}.json / _frames.csv, 汇总追加到 {summ}")


def finish_session(sess, monitor, baseline, out_dir, partial=False):
    if sess is None or sess.reported or sess.t_start is None:
        return
    rep = summarize(sess, monitor, baseline, partial=partial)
    if rep is None:
        return
    sess.reported = True
    print_report(rep)
    save_report(rep, sess, out_dir)


# ============================================================
# 显示
# ============================================================
def draw_hud(img, lines, progress):
    h, w = img.shape[:2]
    scale = max(0.5, min(1.0, w / 1280.0))
    lh = int(26 * scale + 6)
    box_h = lh * len(lines) + 18
    overlay = img.copy()
    cv2.rectangle(overlay, (0, 0), (int(620 * scale) + 40, box_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.55, img, 0.45, 0, img)
    for i, (txt, color) in enumerate(lines):
        cv2.putText(img, txt, (10, 10 + lh * (i + 1) - 6), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6 * scale + 0.1, color, 2 if i < 2 else 1, cv2.LINE_AA)
    bw = int(620 * scale)
    cv2.rectangle(img, (10, box_h - 8), (10 + bw, box_h - 2), (80, 80, 80), -1)
    cv2.rectangle(img, (10, box_h - 8), (10 + int(bw * progress), box_h - 2), (0, 200, 255), -1)
    return img


def render(frame, r, runner, stats, mon, sess, cam_fps):
    vis = frame
    if r is not None:
        try:
            vis = r.plot()
        except Exception:
            vis = frame.copy()
    else:
        vis = frame.copy()
    st, prog = sess.status_text()

    def g(k, nd=0):
        v = mon.get(k)
        return "--" if v is None else f"{v:.{nd}f}"

    lines = [
        (f"{runner.kind.upper()}: {runner.name}", (0, 255, 255)),
        (f"FPS {stats['fps_ema']:5.1f}   infer {stats['infer_ema']:6.1f} ms (max {1000 / max(stats['infer_ema'], 1e-3):5.1f} fps)", (0, 255, 0)),
        (f"Detections: {stats['n_det']}   Camera: {cam_fps:4.1f} fps", (255, 255, 255)),
        (f"RAM {g('ram_used_mb')}/{g('ram_total_mb')} MB  RSS {g('proc_rss_mb')} MB", (255, 255, 255)),
        (f"GPU {g('gpu_load')}%  CPU {g('cpu_avg')}%  Temp {g('temp_max_c', 1)}C  Pwr {g('power_w', 2)}W", (255, 255, 255)),
        (st, (0, 200, 255)),
        ("[s] switch  [r] re-eval  [q] quit", (180, 180, 180)),
    ]
    return draw_hud(vis, lines, prog)


# ============================================================
# 主程序
# ============================================================
def parse_args():
    p = argparse.ArgumentParser(description="Jetson YOLO / SAM3 性能与效果测试",
                                formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("--yolo", default=None, help="YOLO 权重 (.pt / .engine / .onnx)")
    p.add_argument("--sam3", default=None, help="SAM3 权重 (sam3.pt)")
    p.add_argument("--start", choices=["yolo", "sam3"], default="yolo", help="先运行哪个模型")
    # 图像源
    p.add_argument("--source", default="realsense",
                   help="realsense / 相机编号(0) / /dev/videoX / 视频文件 / GStreamer 管线")
    p.add_argument("--serial", default=None, help="RealSense 序列号 (手先: 230322272057)")
    p.add_argument("--width", type=int, default=640)
    p.add_argument("--height", type=int, default=480)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--no-loop", action="store_true", help="视频文件播完不循环")
    # YOLO 参数
    p.add_argument("--conf", type=float, default=0.25)
    p.add_argument("--iou", type=float, default=0.45)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--task", default=None, help="TensorRT 引擎需要时指定: segment / detect")
    p.add_argument("--classes", type=int, nargs="*", default=None, help="只保留这些类别 ID")
    # SAM3 参数
    p.add_argument("--prompt", default="tomato", help="SAM3 文本提示，多个用逗号分隔，如 'red tomato,green tomato'")
    p.add_argument("--sam-conf", type=float, default=0.4)
    p.add_argument("--sam-imgsz", type=int, default=None,
                   help="SAM3 输入尺寸 (需为14的倍数，原生训练尺寸 1008；不指定则用 ultralytics 默认)")
    p.add_argument("--bpe", default=None, help="bpe_simple_vocab_16e6.txt.gz 路径 (旧版 ultralytics 需要)")
    # 通用
    p.add_argument("--device", default=None, help="如 0 / cuda:0 / cpu，默认自动")
    p.add_argument("--half", action=argparse.BooleanOptionalAction, default=True, help="FP16 推理")
    p.add_argument("--warmup", type=float, default=5.0, help="预热秒数（不计入评估）")
    p.add_argument("--duration", type=float, default=60.0, help="评估秒数")
    p.add_argument("--monitor-interval", type=int, default=500, help="系统监控采样间隔 ms")
    p.add_argument("--no-show", action="store_true", help="不显示画面 (SSH/无显示器)，评估完自动退出")
    p.add_argument("--exit-after-eval", action="store_true", help="评估完成后退出")
    p.add_argument("--display-width", type=int, default=1280, help="显示窗口最大宽度")
    p.add_argument("--out", default="bench_results", help="结果保存目录")
    a = p.parse_args()
    if not a.yolo and not a.sam3:
        p.error("至少指定 --yolo 或 --sam3 之一")
    for k in ("yolo", "sam3"):
        path = getattr(a, k)
        if path and not os.path.exists(path):
            p.error(f"找不到文件: {path}")
    if a.no_show:
        a.exit_after_eval = True
    return a


def main():
    args = parse_args()
    available = [k for k in ("yolo", "sam3") if getattr(args, k)]
    current = args.start if args.start in available else available[0]

    monitor = SystemMonitor(args.monitor_interval)
    monitor.start()
    print(f"[Monitor] 后端: {monitor.backend}")

    source = open_source(args)
    # 取第一帧，用于预热模型
    fid, first = -1, None
    for _ in range(50):
        fid, first = source.read(-1, timeout=2.0)
        if first is not None:
            break
    if first is None:
        print("取不到图像，退出")
        source.release()
        monitor.stop()
        return

    # 基线：加载任何模型之前的内存
    time.sleep(1.0)
    ram_used, ram_total = read_meminfo_mb()
    baseline = {"ram_used_mb": ram_used, "proc_rss_mb": proc_rss_mb()}
    print(f"[Baseline] 系统内存 {ram_used:.0f}/{ram_total:.0f} MB, 进程 RSS {baseline['proc_rss_mb']:.0f} MB")

    try:
        runner, load_info = load_runner(current, args, first)
    except BaseException:
        # 加载失败时先关相机线程，避免 "terminate called ... core dump"
        source.release()
        monitor.stop()
        raise
    sess = EvalSession(runner, load_info, args.warmup, args.duration)
    stats = {"fps_ema": 0.0, "infer_ema": 0.0, "n_det": 0}

    show = not args.no_show
    win = "Jetson Model Bench"
    if show:
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    last_id = fid
    t_prev = time.perf_counter()
    try:
        while True:
            fid, frame = source.read(last_id, timeout=2.0)
            if frame is None:
                if source.ended:
                    print("视频结束")
                    break
                continue
            if fid == last_id:  # 超时仍无新帧
                continue
            last_id = fid

            r, infer_ms, detail = runner.infer(frame)
            now = time.perf_counter()
            loop_dt = now - t_prev
            t_prev = now
            n_det = count_dets(r)

            a = 0.1
            stats["fps_ema"] = (1 / loop_dt) if stats["fps_ema"] == 0 else (1 - a) * stats["fps_ema"] + a / loop_dt
            stats["infer_ema"] = infer_ms if stats["infer_ema"] == 0 else (1 - a) * stats["infer_ema"] + a * infer_ms
            stats["n_det"] = n_det

            rec = {"t": time.time(), "frame_id": fid, "infer_ms": infer_ms,
                   "loop_dt_ms": loop_dt * 1000.0, "n_det": n_det, **detail}
            if sess.update(rec):
                finish_session(sess, monitor, baseline, args.out)
                if args.exit_after_eval:
                    break

            if show:
                vis = render(frame, r, runner, stats, monitor.get_latest(), sess,
                             getattr(source, "cam_fps", 0.0))
                if vis.shape[1] > args.display_width:
                    s = args.display_width / vis.shape[1]
                    vis = cv2.resize(vis, None, fx=s, fy=s)
                cv2.imshow(win, vis)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                elif key == ord("r"):
                    finish_session(sess, monitor, baseline, args.out, partial=True)
                    sess = EvalSession(runner, load_info, args.warmup, args.duration)
                    print("[Eval] 重新开始评估")
                elif key == ord("s"):
                    if len(available) < 2:
                        print("[Switch] 只指定了一个模型，无法切换（同时传 --yolo 和 --sam3）")
                        continue
                    finish_session(sess, monitor, baseline, args.out, partial=True)
                    runner.close()
                    del runner
                    release_cuda()
                    current = "sam3" if current == "yolo" else "yolo"
                    runner, load_info = load_runner(current, args, frame)
                    sess = EvalSession(runner, load_info, args.warmup, args.duration)
                    stats = {"fps_ema": 0.0, "infer_ema": 0.0, "n_det": 0}
                    t_prev = time.perf_counter()
    except KeyboardInterrupt:
        print("\nCtrl+C")
    finally:
        finish_session(sess, monitor, baseline, args.out, partial=(sess.state != "done"))
        source.release()
        monitor.stop()
        if show:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
